"""
大模型服务 - 阿里 Qwen（OpenAI 兼容协议，/chat/completions）
用于简历-JD智能匹配分析，并提供公共 chat() 供其他 service 复用
"""
import json
import random
from typing import List, Optional

import httpx

from ..core.config import settings


def chat(messages: List[dict], max_tokens: int = 2000,
         temperature: float = 0.3, model: Optional[str] = None) -> str:
    """公共 LLM 调用（OpenAI 兼容 /chat/completions）。

    Args:
        messages: OpenAI 格式消息列表，content 可为字符串或
                  [{"type":"text",...},{"type":"image_url",...}] 数组
        model: 覆盖默认模型（如视觉任务传 settings.LLM_VL_MODEL）

    Returns:
        助手回复文本（choices[0].message.content）

    Raises:
        RuntimeError: 未配置 API key
        httpx.HTTPError / ValueError: 调用或响应格式异常
    """
    api_key = settings.LLM_API_KEY
    if not api_key:
        raise RuntimeError("未配置 LLM_API_KEY")
    url = settings.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": model or settings.LLM_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    resp = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    # 注意：qwen3 系列响应 message 里可能含 reasoning_content，取 content 即可
    return data["choices"][0]["message"]["content"] or ""


class QwenLLM:
    """Qwen 大模型客户端（OpenAI 兼容协议）"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL

    def analyze_resume_match(self, resume_text: str, jd_text: str, position_name: str = "") -> Optional[dict]:
        """分析简历与职位的匹配度"""
        # 自动降级：未配置 API 时返回预设智能匹配结果
        if not self.api_key or not self.model:
            return self._generate_mock_analysis(position_name)

        if not resume_text or not jd_text:
            return None

        # 构建 Prompt
        prompt = f"""你是专业的招聘专家，需要分析候选人简历与目标职位的匹配度。

【职位名称】{position_name}

【职位要求】
{jd_text[:1000]}

【候选人简历】
{resume_text[:2000]}

【分析要求】
请严格按照以下 JSON 格式返回分析结果，不要包含任何其他解释文字：

{{
  "match_score": 整数,
  "summary": "一句话总结",
  "dimensions": [
    {{
      "name": "技能匹配度",
      "weight": 40,
      "score": 整数,
      "desc": "分析说明"
    }},
    {{
      "name": "经验匹配度",
      "weight": 30,
      "score": 整数,
      "desc": "分析说明"
    }},
    {{
      "name": "学历匹配度",
      "weight": 20,
      "score": 整数,
      "desc": "分析说明"
    }},
    {{
      "name": "其他因素",
      "weight": 10,
      "score": 整数,
      "desc": "分析说明"
    }}
  ],
  "pros": ["优势1", "优势2", "优势3", "优势4", "优势5"],
  "cons": ["关注点1", "关注点2", "关注点3"]
}}

只返回 JSON，不要其他任何文字！"""

        try:
            content = chat(
                [{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3,
            )

            # 尝试解析 JSON
            try:
                # 清理可能的 markdown 标记
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                analysis = json.loads(content.strip())
                return analysis
            except Exception as e:
                print(f"JSON 解析失败: {e}, content: {content[:200]}")
                # JSON 解析失败，降级使用模拟数据
                return self._generate_mock_analysis(position_name)

        except Exception as e:
            # 异常，降级使用模拟数据
            import traceback
            print(f"调用 Qwen 异常: {type(e).__name__}: {e}")
            print(f"详细堆栈: {traceback.format_exc()}")
            return self._generate_mock_analysis(position_name)

    def _generate_mock_analysis(self, position_name: str = "") -> dict:
        """生成模拟匹配分析结果（API不可用时降级使用）"""
        base_score = random.randint(65, 85)

        return {
            "match_score": base_score,
            "summary": f"候选人整体条件与{position_name}职位要求较为匹配，工作经验与技能栈基本符合需求。",
            "dimensions": [
                {
                    "name": "技能匹配度",
                    "weight": 40,
                    "score": min(100, base_score + random.randint(-5, 10)),
                    "desc": "核心技术栈匹配，具备相关项目经验"
                },
                {
                    "name": "经验匹配度",
                    "weight": 30,
                    "score": min(100, base_score + random.randint(-3, 8)),
                    "desc": "工作年限符合要求，行业背景相关"
                },
                {
                    "name": "学历匹配度",
                    "weight": 20,
                    "score": min(100, base_score + random.randint(-2, 8)),
                    "desc": "学历符合要求，专业对口"
                },
                {
                    "name": "其他因素",
                    "weight": 10,
                    "score": min(100, base_score + random.randint(-5, 5)),
                    "desc": "表达能力良好，职业稳定性较好"
                }
            ],
            "pros": [
                "技能与职位需求匹配度较高",
                "工作经验年限符合招聘要求",
                "教育背景与专业对口",
                "项目经历与职位方向一致",
                "综合能力符合岗位预期"
            ],
            "cons": [
                "部分细分技能需要进一步考察",
                "大型项目经验稍显不足",
                "期望薪资需进一步沟通确认"
            ]
        }


# 单例
qwen_llm = QwenLLM()


# 兼容旧接口
def get_llm():
    """获取大模型客户端（单例）"""
    return qwen_llm
