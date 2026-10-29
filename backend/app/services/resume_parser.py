"""
简历解析服务
文件文本提取 + 大模型结构化解析 + 正则兜底提取
"""
import os
import re
import json
from typing import Dict, Any, Optional, List, Tuple
from PyPDF2 import PdfReader
import docx

from ..core.config import settings


class ResumeExtractor:
    """简历文本提取器"""

    @staticmethod
    def extract_from_pdf(file_path: str) -> str:
        """从PDF提取文本"""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            raise Exception(f"PDF文件提取失败: {str(e)}")

    @staticmethod
    def extract_from_word(file_path: str) -> str:
        """从Word文档提取文本"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            # 同时读取表格
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + "\t"
                    text += "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Word文件提取失败: {str(e)}")

    @staticmethod
    def extract_text(file_path: str, file_name: str) -> str:
        """
        根据文件扩展名自动提取文本

        Args:
            file_path: 文件路径
            file_name: 原始文件名

        Returns:
            提取的文本内容
        """
        ext = os.path.splitext(file_name.lower())[1]

        if ext == ".pdf":
            return ResumeExtractor.extract_from_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return ResumeExtractor.extract_from_word(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        else:
            raise Exception(f"不支持的文件格式: {ext}")

    @staticmethod
    def extract_text_safe(file_path: str, file_name: str) -> str:
        """
        健壮版文本提取：
        1) 先尝试扩展名对应的解析器
        2) 失败时尝试以纯文本方式读取
        3) 再失败时尝试 PDF 解析
        4) 任何情况下都不抛异常，返回空字符串
        """
        # 尝试 1：按扩展名
        try:
            text = ResumeExtractor.extract_text(file_path, file_name)
            if text:
                return text
        except Exception:
            pass

        # 尝试 2：纯文本
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read().strip()
            if raw and len(raw) > 5:
                return raw
        except Exception:
            pass

        # 尝试 3：PDF 兜底
        try:
            text = ResumeExtractor.extract_from_pdf(file_path)
            if text:
                return text
        except Exception:
            pass

        return ""


class RegexResumeParser:
    """
    基于正则的简历字段提取器（兜底方案）

    当大模型 API 不可用或返回 mock 数据时，使用正则提取关键字段。
    """

    # 中国大陆手机号
    PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
    # 邮箱 - 支持手机号+空格+@+邮箱 这种格式
    EMAIL_RE = re.compile(
        r"(?:[A-Za-z0-9._%+\-]+\s*)?@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
    )
    # 排除 PDF 二进制噪点里截出来的伪邮箱（如 "zu@k.jj"、"a@b.c"）
    EMAIL_BLOCKLIST_TLDS = {"jj", "x", "cc", "mm", "qqqq", "cm", "hk"}

    # 工作年限：12年工作经验 / 5年Python经验 / 工作年限：8 年
    YEARS_RE = re.compile(
        r"(?:工作年限|工作经验|工龄|从业)[^\d]{0,8}?(\d{1,2})\s*(?:年|years?|yrs?)",
        re.IGNORECASE,
    )
    # 兜底：纯数字+年 紧邻 "经验/工作" 上下文
    YEARS_FALLBACK_RE = re.compile(
        r"(\d{1,2})\s*年(?:\s*(?:以上)?(?:工作经验?|开发经验?|相关经验?|从业))",
        re.IGNORECASE,
    )
    # 英文: "5 years experience" / "Experience: 5 years"
    YEARS_EN_RE = re.compile(
        r"(\d{1,2})\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp|work)",
        re.IGNORECASE,
    )
    # 中文简历正文里常见："16年工作经验" / "10 年工作经验"（无"工作年限"前缀）
    YEARS_LOOSE_RE = re.compile(
        r"(\d{1,2})\s*年\s*工作(?:经验)?",
        re.IGNORECASE,
    )
    # 表格式简历：根据最早工作起始年月推算工作年限
    # 匹配 "2017.06-2017-09" / "2017.06-2020.06" / "2024.01.02-2026.03.31" 等
    WORK_START_RE = re.compile(
        r"(?<![\d.])((?:19|20)\d{2})[.\-/年](\d{1,2})(?:[.\-/月](\d{1,2}))?"
    )

    # 学历关键词（按学历层级排序，便于取最高）
    EDUCATION_KEYWORDS: List[Tuple[str, int]] = [
        ("博士", 6), ("phd", 6), ("doctor", 6),
        ("硕士", 5), ("研究生", 5), ("master", 5), ("mba", 5),
        ("本科", 4), ("学士", 4), ("大学", 3), ("college", 4),
        ("大专", 2), ("专科", 2), ("associate", 2), ("diploma", 2),
        ("高中", 1), ("中专", 1), ("职高", 1), ("high school", 1),
    ]

    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        if not text:
            return None
        m = cls.PHONE_RE.search(text)
        return m.group(1) if m else None

    @classmethod
    def extract_email(cls, text: str) -> Optional[str]:
        if not text:
            return None
        for m in cls.EMAIL_RE.finditer(text):
            email = m.group(0).lower()
            tld = email.rsplit(".", 1)[-1]
            # 排除 PDF 噪点产生的伪邮箱
            if tld in cls.EMAIL_BLOCKLIST_TLDS:
                continue
            # TLD 至少 2 个字母，且 local part 至少 2 个字符
            local = email.split("@", 1)[0]
            if len(local) < 2 or len(tld) < 2:
                continue
            return email
        return None

    @classmethod
    def extract_years_of_experience(cls, text: str) -> Optional[float]:
        """
        提取工作年限（按优先级尝试多种模式）：
        1) "工作年限：X年" / "工作经验X年" 等显式标签
        2) "X 年工作经验"（无前缀）
        3) 英文 "X years experience"
        4) 表格式简历：根据最早工作/教育起始年月，到当前日期推算
        """
        if not text:
            return None
        # 1-3 显式表述
        for pattern in (cls.YEARS_RE, cls.YEARS_FALLBACK_RE, cls.YEARS_EN_RE, cls.YEARS_LOOSE_RE):
            m = pattern.search(text)
            if m:
                try:
                    val = float(m.group(1))
                    if 0 <= val <= 60:
                        return val
                except (ValueError, IndexError):
                    continue

        # 4) 表格式简历：根据"工作经历"段的起始年月推算
        #    关键点：必须只取"工作经历"段落里的日期，避免把出生年月、毕业时间算进去
        #    步骤：
        #    a) 找出"工作经历"标记位置；找不到时回退用全文
        #    b) 在该段内收集所有 19xx/20xx.YY 形式的日期
        #    c) 排除靠近"出生"标记的日期（避免把生日算成工作起点）
        from datetime import datetime

        work_section_text = text
        # 找 "工作经历" / "工作经验" 标题位置
        markers = ["工作经历", "工作经验", "WORK EXPERIENCE", "Work Experience", "EMPLOYMENT"]
        marker_pos = -1
        for mk in markers:
            idx = text.find(mk)
            if idx >= 0:
                marker_pos = idx
                break
        if marker_pos >= 0:
            work_section_text = text[marker_pos:]

        # 收集候选日期
        candidates: List[Tuple[int, int]] = []  # (yyyymm, 原start_pos)
        for m in cls.WORK_START_RE.finditer(work_section_text):
            try:
                y = int(m.group(1))
                mo = int(m.group(2)) if m.group(2) else 1
                if 1990 <= y <= 2030 and 1 <= mo <= 12:
                    # 排除出生日期：附近 30 字符内有"出生"
                    ctx_start = max(0, m.start() - 30)
                    ctx = work_section_text[ctx_start:m.start()]
                    if "出生" in ctx:
                        continue
                    # 排除毕业日期：附近 30 字符内有"毕业"
                    if "毕业" in ctx:
                        continue
                    candidates.append((y * 100 + mo, m.start()))
            except (ValueError, IndexError):
                continue

        if candidates:
            earliest_yyyymm = min(c[0] for c in candidates)
            earliest_year = earliest_yyyymm // 100
            earliest_month = earliest_yyyymm % 100
            now = datetime.now()
            months = (now.year - earliest_year) * 12 + (now.month - earliest_month)
            years = months / 12.0
            # 合理性检查：起始年份不能太早，也不能导致年限 > 60
            if 0 <= years <= 60:
                return round(years, 1)
        return None

    @classmethod
    def extract_highest_education(cls, text: str) -> Optional[str]:
        """
        提取最高学历。
        1) 优先匹配 "学历：本科" 这种 "学历/学位：xxx" 的标签写法
        2) 否则扫描文本中出现的学历关键词，取层级最高的
        """
        if not text:
            return None
        # 1) 标签写法（兼容 "最高学历  大专" / "学历：本科" / "Education: Master" 等写法）
        labeled_re = re.compile(
            r"(?:最高\s*学历|学历|学位|教育程度|education|degree)\s*[:：\s]{1,4}([^\n\r,，;；]{1,15})",
            re.IGNORECASE,
        )
        m = labeled_re.search(text)
        if m:
            value = m.group(1).strip()
            # 清洗 PDF 文本流混入的闭合括号 / 句点
            value_clean = re.sub(r"[\)\]\}\>。，,.;:：]+$", "", value).strip()
            for keyword, _ in cls.EDUCATION_KEYWORDS:
                if keyword.lower() in value_clean.lower():
                    return cls._normalize_education(keyword)
            # 没识别出标准学历，但有非空标签内容，原样返回
            if value_clean:
                return value_clean

        # 2) 扫描所有出现的学历关键词
        text_lower = text.lower()
        best_level = 0
        best_keyword = None
        for keyword, level in cls.EDUCATION_KEYWORDS:
            kw_lower = keyword.lower()
            if kw_lower in text_lower:
                if level > best_level:
                    best_level = level
                    best_keyword = keyword
        return cls._normalize_education(best_keyword) if best_keyword else None

    @staticmethod
    def _normalize_education(keyword: str) -> str:
        """学历中文规范化（同时清洗 PDF 源码流带来的杂质）"""
        if not keyword:
            return keyword
        # 清洗 PDF 文本流中混入的闭合括号 / 句点 / 引号
        cleaned = re.sub(r"[\)\]\}\>。，,.;:：]+$", "", keyword).strip()
        mapping = {
            "phd": "博士", "doctor": "博士",
            "master": "硕士", "mba": "硕士",
            "bachelor": "本科",
            "associate": "大专", "diploma": "大专",
            "high school": "高中",
        }
        k = cleaned.lower()
        return mapping.get(k, cleaned)

    @classmethod
    def parse(cls, text: str) -> Dict[str, Any]:
        """
        从文本中提取结构化字段。
        任何字段提取不到则值为 None。
        """
        return {
            "phone": cls.extract_phone(text),
            "email": cls.extract_email(text),
            "years_of_experience": cls.extract_years_of_experience(text),
            "highest_education": cls.extract_highest_education(text),
        }


class DoubaoResumeParser:
    """火山引擎豆包简历解析器"""

    def __init__(self):
        self.api_key = settings.DOUBAO_API_KEY
        self.api_secret = settings.DOUBAO_API_SECRET
        self.model = settings.DOUBAO_MODEL

    def _build_prompt(self, resume_text: str) -> str:
        """构建简历解析提示词"""
        return f"""
请作为专业的HR专家，分析以下简历内容，提取结构化信息。

简历内容：
{resume_text}

请以JSON格式返回，包含以下字段：
{{
    "basic_info": {{
        "name": "姓名",
        "phone": "手机号",
        "email": "邮箱",
        "gender": "性别",
        "age": 年龄,
        "location": "所在城市"
    }},
    "education": [
        {{
            "school": "学校名称",
            "major": "专业",
            "degree": "学历",
            "start_date": "开始时间",
            "end_date": "结束时间"
        }}
    ],
    "work_experience": [
        {{
            "company": "公司名称",
            "position": "职位",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "description": "工作描述"
        }}
    ],
    "skills": ["技能1", "技能2"],
    "languages": ["语言1", "语言2"],
    "certificates": ["证书1"],
    "projects": [
        {{
            "name": "项目名称",
            "role": "角色",
            "description": "项目描述"
        }}
    ],
    "summary": "个人简介摘要"
}}

只返回JSON，不要其他说明。
"""

    async def parse(self, resume_text: str) -> Dict[str, Any]:
        """
        使用大模型解析简历

        Args:
            resume_text: 简历文本内容

        Returns:
            结构化解析结果
        """
        # 如果没有配置API密钥，返回模拟结果
        if not self.api_key:
            return self._mock_parse(resume_text)

        try:
            # 这里接入火山引擎豆包API
            # 实际使用时需要调用 volcengine SDK
            prompt = self._build_prompt(resume_text)

            # 模拟API调用（实际项目中替换为真实调用）
            result = await self._call_doubao_api(prompt)
            return result
        except Exception as e:
            raise Exception(f"简历解析失败: {str(e)}")

    async def _call_doubao_api(self, prompt: str) -> Dict[str, Any]:
        """调用豆包API"""
        # 实际项目中实现真实的API调用
        # 示例代码：
        # from volcengine.maas import MaasService, MaasException, ChatRole
        # maas = MaasService('maas-api.ml-platform-cn-beijing.volces.com', 'cn-beijing')
        # maas.set_ak(self.api_key)
        # maas.set_sk(self.api_secret)
        # response = maas.chat(...)
        # return json.loads(response.choices[0].message.content)

        return self._mock_parse(prompt)

    def _mock_parse(self, resume_text: str) -> Dict[str, Any]:
        """模拟解析结果（测试用）"""
        return {
            "basic_info": {
                "name": "候选人",
                "phone": "13800138000",
                "email": "candidate@example.com",
                "gender": "未知",
                "age": None,
                "location": "北京"
            },
            "education": [],
            "work_experience": [],
            "skills": [],
            "languages": [],
            "certificates": [],
            "projects": [],
            "summary": resume_text[:200] + "..."
        }


# 服务实例
# 注意：不在模块加载时实例化 DoubaoResumeParser，因为它的 __init__ 依赖
# settings.DOUBAO_API_KEY，而该字段在 Settings 中可能未定义，会在 import 时
# 抛 AttributeError，导致任何 from .resume_parser import ... 的代码全部失败
# （包括上传接口里的 ResumeExtractor 调用）。
resume_extractor = ResumeExtractor()
regex_resume_parser = RegexResumeParser()


def get_resume_parser() -> Optional[DoubaoResumeParser]:
    """惰性获取豆包简历解析器，配置缺失时返回 None。"""
    try:
        # 兜底：Settings 里没有的字段取不到时走正则
        if not getattr(settings, "DOUBAO_API_KEY", None):
            return None
        return DoubaoResumeParser()
    except Exception:
        return None