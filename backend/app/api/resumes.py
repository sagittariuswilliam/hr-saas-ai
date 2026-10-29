import os
import json
import time
import traceback
"""
简历管理 API
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Tuple, Dict, Any, List
from ..core.database import get_db
from ..core.security import get_current_user, get_current_deliverer_or_admin
from ..models.models import User, Resume, Project, Position, ResumeStatus

router = APIRouter(prefix="/resumes", tags=["简历管理"])

# 允许的文件扩展名 / 单文件大小上限（与单文件上传保持一致）
_ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx']
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
from ..core.config import settings as _settings
_UPLOAD_DIR = os.path.join(_settings.UPLOAD_DIR, "resumes")


@router.get("", summary="获取简历列表")
def get_resumes(
    project_id: Optional[int] = Query(None, description="按项目ID筛选"),
    position_id: Optional[int] = Query(None, description="按职位ID筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    keyword: Optional[str] = Query(None, description="按姓名/手机号搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取简历列表 - 关联项目和职位名称"""
    query = db.query(
        Resume.id,
        Resume.project_id,
        Resume.position_id,
        Resume.candidate_name,
        Resume.candidate_phone,
        Resume.candidate_email,
        Resume.years_of_experience,
        Resume.highest_education,
        Resume.file_path,
        Resume.status,
        Resume.parse_status,
        Resume.skills,
        Resume.match_score,
        Resume.uploader_id,
        Resume.created_at,
        Resume.updated_at,
        Project.project_name,
        Position.position_name
    ).outerjoin(Project, Resume.project_id == Project.id) \
     .outerjoin(Position, Resume.position_id == Position.id) \
     .filter(Resume.is_deleted == 0)
    
    # 按项目筛选
    if project_id:
        query = query.filter(Resume.project_id == project_id)
    
    # 按职位筛选
    if position_id:
        query = query.filter(Resume.position_id == position_id)
    
    # 按状态筛选
    if status:
        query = query.filter(Resume.status == status)
    
    # 按关键词搜索
    if keyword:
        query = query.filter(
            (Resume.candidate_name.contains(keyword)) |
            (Resume.candidate_phone.contains(keyword))
        )
    
    # 数据权限控制
    if current_user.role.value == "deliverer":
        query = query.filter(Project.created_by == current_user.id)
    
    # 分页
    total = query.count()
    resumes = query.order_by(Resume.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    # 转换为字典列表
    result = []
    for r in resumes:
        item = {
            "id": r.id,
            "project_id": r.project_id,
            "position_id": r.position_id,
            "candidate_name": r.candidate_name,
            "phone": r.candidate_phone,
            "email": r.candidate_email,
            "work_years": r.years_of_experience,
            "education": r.highest_education,
            "match_score": r.match_score,
            "resume_file": r.file_path,
            "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            "parse_status": r.parse_status,
            "parsed_data": r.skills,
            "created_by": r.uploader_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "project_name": r.project_name,
            "position_name": r.position_name
        }
        result.append(item)
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": result
        }
    }



@router.post("/{resume_id}/analyze", summary="AI分析简历匹配度")
def analyze_resume_match(
    resume_id: int,
    force: bool = Query(False, description="是否强制重新分析"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """调用大模型分析简历与职位的匹配度"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.is_deleted == 0
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    # 如果已有分析结果且不强制刷新，直接返回
    if resume.match_detail and resume.match_score and not force:
        try:
            detail = json.loads(resume.match_detail) if resume.match_detail else {}
            # 获取职位名称
            position_name = ""
            if resume.position_id:
                position = db.query(Position).filter(Position.id == resume.position_id).first()
                if position:
                    position_name = position.position_name
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "match_score": resume.match_score,
                    "candidate_name": resume.candidate_name,
                    "position_name": position_name,
                    **detail
                }
            }
        except:
            pass
    
    # 获取职位 JD
    jd_text = ""
    position_name = ""
    if resume.position_id:
        position = db.query(Position).filter(Position.id == resume.position_id).first()
        if position:
            jd_text = position.jd_content or ""
            position_name = position.position_name
    
    # 提取简历文本
    years_str = (
        f"{resume.years_of_experience} 年"
        if resume.years_of_experience is not None and resume.years_of_experience >= 0
        else "未知"
    )
    resume_text = f"""
候选人姓名: {resume.candidate_name or '未知'}
电话: {resume.candidate_phone or ''}
邮箱: {resume.candidate_email or ''}
工作年限: {years_str}
最高学历: {resume.highest_education or '未知'}

【技能】
{resume.skills or '未提供（请从工作经历中提取）'}

【工作经历】
{resume.work_experience or '未提供'}

【教育经历】
{resume.education_experience or '未提供'}
"""
    
    # 调用大模型分析（如果没配置就返回模拟数据）
    try:
        from ..services.llm import get_llm
        llm = get_llm()
        result = llm.analyze_resume_match(resume_text, jd_text, position_name)
        
        if not result:
            # 没配置或调用失败，返回模拟数据
            result = {
                "match_score": 75,
                "summary": "AI分析服务未配置，使用模拟数据展示",
                "dimensions": [
                    {"name": "技能匹配度", "weight": 40, "score": 80, "desc": "核心技能基本匹配"},
                    {"name": "经验匹配度", "weight": 30, "score": 70, "desc": "工作年限满足要求"},
                    {"name": "学历匹配度", "weight": 20, "score": 75, "desc": "学历符合要求"},
                    {"name": "其他因素", "weight": 10, "score": 65, "desc": "综合表现良好"}
                ],
                "pros": ["拥有相关工作经验", "技能栈匹配度高", "学历达标", "项目经历丰富", "职业方向吻合"],
                "cons": ["行业经验需进一步考察", "部分高级技能需要验证"]
            }
    except Exception as e:
        # 出错返回模拟数据
        import traceback
        print(f"=== AI分析异常 ===")
        print(f"异常类型: {type(e).__name__}")
        print(f"异常信息: {e}")
        print(f"详细堆栈:\n{traceback.format_exc()}")
        print("=" * 50)
        result = {
            "match_score": 75,
            "summary": "AI服务暂不可用，使用模拟数据展示",
            "dimensions": [
                {"name": "技能匹配度", "weight": 40, "score": 80, "desc": "核心技能基本匹配"},
                {"name": "经验匹配度", "weight": 30, "score": 70, "desc": "工作年限满足要求"},
                {"name": "学历匹配度", "weight": 20, "score": 75, "desc": "学历符合要求"},
                {"name": "其他因素", "weight": 10, "score": 65, "desc": "综合表现良好"}
            ],
            "pros": ["拥有相关工作经验", "技能栈匹配度高", "学历达标", "项目经历丰富", "职业方向吻合"],
            "cons": ["行业经验需进一步考察", "部分高级技能需要验证"]
        }
    
    # 保存结果到数据库
    resume.match_score = result.get('match_score', 0)
    resume.match_detail = json.dumps(result, ensure_ascii=False)
    db.commit()
    
    # 返回结果时添加候选人名称和职位名称
    result['candidate_name'] = resume.candidate_name
    result['position_name'] = position_name
    
    return {"code": 0, "message": "分析完成", "data": result}


@router.get("/{resume_id}", summary="获取简历详情")
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取简历详情"""
    resume = db.query(
        Resume.id,
        Resume.project_id,
        Resume.position_id,
        Resume.candidate_name,
        Resume.candidate_phone,
        Resume.candidate_email,
        Resume.years_of_experience,
        Resume.highest_education,
        Resume.file_path,
        Resume.status,
        Resume.parse_status,
        Resume.skills,
        Resume.match_score,
        Resume.uploader_id,
        Resume.created_at,
        Resume.updated_at,
        Project.project_name,
        Position.position_name
    ).outerjoin(Project, Resume.project_id == Project.id) \
     .outerjoin(Position, Resume.position_id == Position.id) \
     .filter(Resume.id == resume_id, Resume.is_deleted == 0).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    # 转换为字典，确保字段名与前端一致
    result = {
        "id": resume.id,
        "project_id": resume.project_id,
        "position_id": resume.position_id,
        "candidate_name": resume.candidate_name,
        "phone": resume.candidate_phone,
        "email": resume.candidate_email,
        "work_years": resume.years_of_experience,
        "education": resume.highest_education,
        "match_score": resume.match_score,
        "resume_file": resume.file_path,
        "status": resume.status.value if hasattr(resume.status, 'value') else str(resume.status),
        "parse_status": resume.parse_status,
        "parsed_data": resume.skills,
        "created_by": resume.uploader_id,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
        "project_name": resume.project_name,
        "position_name": resume.position_name
    }
    
    return {"code": 0, "message": "success", "data": result}


# ----------------- 本地启发式评分（LLM 不可用时的兜底） -----------------

# 学历层级（用于启发式评分）
_EDU_LEVEL = {
    "博士": 6, "硕士": 5, "研究生": 5, "本科": 4, "学士": 4,
    "大学": 3, "大专": 2, "专科": 2, "高中": 1, "中专": 1, "职高": 1,
}


def _edu_level(value: Optional[str]) -> int:
    """从学历字符串中提取层级（0 = 未知）"""
    if not value:
        return 0
    v = value.strip()
    for k, lvl in _EDU_LEVEL.items():
        if k in v:
            return lvl
    return 0


def _field_completeness(resume) -> int:
    """简历字段完整度评分 0-100"""
    score = 0
    fields = [
        (resume.candidate_phone, 15),
        (resume.candidate_email, 15),
        (resume.years_of_experience, 20),
        (resume.highest_education, 15),
        (resume.work_experience, 20),
        (resume.education_experience, 10),
        (resume.skills, 5),
    ]
    for val, weight in fields:
        if val:
            score += weight
    return score


def _heuristic_score(resume, jd_text: str, position_name: str) -> int:
    """
    基于已解析字段的本地启发式评分 (0-100)。
    当 LLM API 不可用时使用，保证前端始终有可用结果。
    """
    # 基础分：按字段完整度
    base = 30 + int(_field_completeness(resume) * 0.4)  # 30 + 0..28

    # 工作年限加分
    years = resume.years_of_experience
    if years is not None:
        if years >= 10:
            base += 20
        elif years >= 5:
            base += 15
        elif years >= 3:
            base += 10
        elif years >= 1:
            base += 5
        else:
            base += 2

    # 学历加分
    edu_lvl = _edu_level(resume.highest_education)
    if edu_lvl >= 5:  # 硕士及以上
        base += 15
    elif edu_lvl >= 4:  # 本科
        base += 12
    elif edu_lvl >= 2:  # 大专
        base += 8
    elif edu_lvl >= 1:  # 高中
        base += 3

    # 有工作经历文本 → 轻微加分
    if resume.work_experience and len(resume.work_experience) > 50:
        base += 5

    return max(10, min(95, base))


def _heuristic_analysis(resume, jd_text: str, position_name: str) -> dict:
    """
    本地启发式 AI 分析（LLM 不可用时兜底）。
    返回与 LLM 一致的 JSON 字段。
    """
    score = _heuristic_score(resume, jd_text, position_name)
    completeness = _field_completeness(resume)
    years = resume.years_of_experience
    edu_lvl = _edu_level(resume.highest_education)

    pros: list[str] = []
    cons: list[str] = []

    # 基本信息
    if resume.candidate_phone:
        pros.append("已提供手机号，方便后续联系")
    else:
        cons.append("未提取到手机号，建议人工补充")
    if resume.candidate_email:
        pros.append("已提供邮箱")
    else:
        cons.append("未提取到邮箱，建议人工补充")

    # 工作年限
    if years is not None:
        if years >= 5:
            pros.append(f"工作年限 {years} 年，符合多数岗位的资历要求")
        else:
            pros.append(f"工作年限 {years} 年，具备一定行业经验")
    else:
        cons.append("简历中未明确工作年限，无法评估资历深度")

    # 学历
    if edu_lvl >= 4:
        pros.append(f"最高学历 {resume.highest_education}，学历背景良好")
    elif edu_lvl >= 2:
        pros.append(f"最高学历 {resume.highest_education}，满足常规学历要求")
    elif edu_lvl >= 1:
        cons.append(f"最高学历 {resume.highest_education}，需确认是否满足岗位学历门槛")
    else:
        cons.append("未识别到学历信息，建议人工核实")

    # 工作经历文本
    if resume.work_experience and len(resume.work_experience) > 50:
        pros.append("简历正文已成功解析，可用于详细评估")
    else:
        cons.append("简历正文较短或为图片扫描件，建议上传可复制文本的 PDF")

    # 总分定位 summary
    if score >= 80:
        summary = (
            f"候选人{' ' + (resume.candidate_name or '')}整体条件与"
            f"{position_name or '目标'}岗位较为匹配，建议推进面试。"
        )
    elif score >= 60:
        summary = (
            f"候选人具备基础条件与{position_name or '目标'}岗位部分匹配，"
            f"建议结合工作经历进一步评估。"
        )
    elif score >= 40:
        summary = (
            f"候选人简历完整度较低（{completeness} 分），"
            f"与{position_name or '目标'}岗位匹配度有限，建议人工核实关键信息。"
        )
    else:
        summary = (
            "候选人简历信息严重缺失，无法有效评估，建议补充完整简历后再行评估。"
        )

    # 维度评分（与 LLM 输出保持一致的 schema）
    skill_score = min(100, 40 + completeness // 3)
    exp_score = (
        min(100, 30 + int((years or 0) * 4))
        if years is not None else 25
    )
    edu_score = min(100, 30 + edu_lvl * 12)
    other_score = min(100, 40 + completeness // 4)

    return {
        "match_score": score,
        "summary": summary,
        "dimensions": [
            {
                "name": "技能匹配度",
                "weight": 40,
                "score": skill_score,
                "desc": (
                    "基于简历字段完整度推断；如需精细评估，建议由人工结合"
                    "JD 关键词与候选人项目经历复核。"
                ),
            },
            {
                "name": "经验匹配度",
                "weight": 30,
                "score": exp_score,
                "desc": (
                    f"工作年限 {years} 年（已知）"
                    if years is not None else "工作年限未识别，需人工核实"
                ),
            },
            {
                "name": "学历匹配度",
                "weight": 20,
                "score": edu_score,
                "desc": (
                    f"最高学历 {resume.highest_education}"
                    if resume.highest_education else "学历未识别，需人工核实"
                ),
            },
            {
                "name": "其他因素",
                "weight": 10,
                "score": other_score,
                "desc": (
                    f"简历完整度 {completeness}/100，关键信息"
                    f"{'较完整' if completeness >= 60 else '存在缺失'}"
                ),
            },
        ],
        "pros": pros[:5],
        "cons": cons[:5],
        "_source": "heuristic",  # 标记兜底来源，便于前端区分
    }


def _process_resume_upload(
    db: Session,
    filename: str,
    content: bytes,
    project_id: Optional[int],
    position_id: Optional[int],
    current_user: User,
) -> Tuple[bool, Dict[str, Any]]:
    """
    共用核心：保存文件 → 入库 → 解析 → AI 评分。
    使用 SAVEPOINT (begin_nested) 把单个文件的失败隔离在子事务中，
    不影响同批次的其它文件，也不污染外层 Session。

    Returns:
        (True,  {"resume_id": ..., "candidate_name": ..., "match_score": ...})  成功
        (False, {"error": "..."})                                                  失败
    """
    savepoint = db.begin_nested()
    try:
        # ---- 1. 落盘文件 ----
        os.makedirs(_UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(_UPLOAD_DIR, f"{int(time.time())}_{filename}")
        with open(file_path, "wb") as f:
            f.write(content)

        # ---- 2. 入库 ----
        resume = Resume(
            project_id=project_id if project_id else None,
            position_id=position_id if position_id else None,
            candidate_name=filename.rsplit('.', 1)[0] if '.' in filename else filename,
            candidate_phone="",
            candidate_email="",
            original_filename=filename,
            file_path=file_path,
            file_size=len(content),
            status=ResumeStatus.SUBMITTED,
            parse_status=0,
            uploader_id=current_user.id,
        )
        db.add(resume)
        db.flush()  # 拿到 resume.id，不提交 savepoint

        # ---- 3. 解析文本 ----
        resume_text = ""
        try:
            from ..services.resume_parser import ResumeExtractor, RegexResumeParser

            resume_text = ResumeExtractor.extract_text_safe(file_path, filename)
            is_image_pdf = (
                resume_text
                and resume_text[:10].lstrip().startswith("%PDF-")
                and len(resume_text) > 500
            )

            parsed: dict = {}
            if resume_text and not is_image_pdf:
                parsed = RegexResumeParser.parse(resume_text)

            phone = parsed.get("phone")
            email = parsed.get("email")
            years = parsed.get("years_of_experience")
            education = parsed.get("highest_education")

            if phone:
                resume.candidate_phone = phone
            if email:
                resume.candidate_email = email
            if years is not None:
                resume.years_of_experience = years
            if education:
                resume.highest_education = education

            if resume_text and not is_image_pdf:
                snippet = resume_text.strip()
                resume.work_experience = snippet[:2000]
                resume.education_experience = snippet[:2000]
                resume.skills = None
            else:
                resume.work_experience = None
                resume.education_experience = None
                resume.skills = None

            extracted_any = bool(resume_text and not is_image_pdf) or any(
                [phone, email, years is not None, education]
            )
            resume.parse_status = 1 if extracted_any else 2
        except Exception as e:
            # 解析失败：resume 仍入库，但 parse_status=2（与原行为一致）
            print(f"[解析] ✗ 简历解析异常: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            resume.parse_status = 2

        # ---- 4. AI 评分：已改为后台任务（见 _score_resume_background），
        #      上传请求不再同步等待 LLM，避免批量上传超时。
        #      调用方在 helper 成功后为含 position_id 的简历 add_task。

        # ---- 5. 提交 savepoint（单文件原子提交）----
        savepoint.commit()

        return True, {
            "resume_id": resume.id,
            "candidate_name": resume.candidate_name,
            "match_score": resume.match_score,
            "parse_status": resume.parse_status,
        }

    except SQLAlchemyError as e:
        savepoint.rollback()
        err = f"数据库写入失败: {type(e).__name__}: {e}"
        print(f"[helper] ✗ {err}")
        return False, {"error": err}
    except OSError as e:
        savepoint.rollback()
        err = f"文件落盘失败: {type(e).__name__}: {e}"
        print(f"[helper] ✗ {err}")
        return False, {"error": err}
    except Exception as e:
        savepoint.rollback()
        err = f"简历处理失败: {type(e).__name__}: {e}"
        print(f"[helper] ✗ {err}")
        print(traceback.format_exc())
        return False, {"error": err}


def _score_resume_background(resume_id: int, position_id: Optional[int]):
    """
    后台 AI 评分任务（方案B：上传请求与 LLM 调用解耦）。
    FastAPI BackgroundTasks 对同步函数走线程池执行，不阻塞事件循环。
    独立 Session，失败不影响已入库的简历；失败时启发式兜底。
    """
    from ..core.database import SessionLocal
    from ..services.llm import get_llm

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return
        position = db.query(Position).filter(Position.id == position_id).first() if position_id else None
        jd_text = position.jd_content if position else ""
        position_name = position.position_name if position else ""

        years_str = (
            f"{resume.years_of_experience} 年"
            if resume.years_of_experience is not None and resume.years_of_experience >= 0
            else "未知"
        )
        resume_text_for_ai = f"""
候选人姓名: {resume.candidate_name or '未知'}
电话: {resume.candidate_phone or ''}
邮箱: {resume.candidate_email or ''}
工作年限: {years_str}
最高学历: {resume.highest_education or '未知'}

【工作经历】
{resume.work_experience or '未提供'}

【教育经历】
{resume.education_experience or '未提供'}

【技能】
{resume.skills or '未提供（请从工作经历中提取）'}
"""
        try:
            llm = get_llm()
            result = llm.analyze_resume_match(resume_text_for_ai, jd_text, position_name)
        except Exception as e:
            print(f"[后台评分][resume_id={resume_id}] ✗ LLM 调用失败: {type(e).__name__}: {e}")
            result = None

        if result:
            resume.match_score = result.get('match_score', 70)
            resume.match_detail = json.dumps(result, ensure_ascii=False)
        else:
            resume.match_score = _heuristic_score(resume, jd_text, position_name)
            resume.match_detail = json.dumps(
                _heuristic_analysis(resume, jd_text, position_name),
                ensure_ascii=False,
            )
        db.commit()
        print(f"[后台评分][resume_id={resume_id}] ✓ match_score={resume.match_score}")
    except Exception as e:
        print(f"[后台评分][resume_id={resume_id}] ✗ {type(e).__name__}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/upload", summary="上传简历文件")
async def upload_resume(
    background_tasks: BackgroundTasks,
    project_id: Optional[int] = Form(None),
    position_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """上传简历文件并自动解析内容（单文件入口，逻辑由 _process_resume_upload 共用）"""
    # 入口处做参数级校验：文件格式 / 大小 → 直接 400（保持与原行为一致）
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="只支持 PDF/DOC/DOCX 格式文件")

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    success, payload = _process_resume_upload(
        db=db,
        filename=file.filename or "resume.pdf",
        content=content,
        project_id=project_id,
        position_id=position_id,
        current_user=current_user,
    )

    if not success:
        # 解析/入库/AI 阶段失败：payload 含 error，按 spec 转 500
        raise HTTPException(status_code=500, detail=payload.get("error", "简历处理失败"))

    # 有关联职位 → 后台异步 AI 评分（不阻塞响应）
    if position_id:
        background_tasks.add_task(_score_resume_background, payload["resume_id"], position_id)

    return {
        "code": 0,
        "message": "上传成功",
        "data": {
            "id": payload["resume_id"],
            "filename": file.filename,
            "match_score": payload.get("match_score"),
        },
    }


@router.post("/upload-batch", summary="批量上传简历文件（1-10 份）")
async def upload_resume_batch(
    background_tasks: BackgroundTasks,
    project_id: Optional[int] = Form(None),
    position_id: Optional[int] = Form(None),
    files: Optional[List[UploadFile]] = File(None, description="1-10 个简历文件"),
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """
    批量上传简历（1-10 份）。每份文件独立处理：
      - 格式/大小校验失败的 → results 中标记 failed（不抛 400，单文件级错误）
      - 解析/入库/AI 阶段失败的 → results 中标记 failed，其它文件继续
      - 0 文件 / >10 文件 → 400 Bad Request
      - 全部失败 → 400 Bad Request
    """
    # 1. 数量校验：1 ≤ len ≤ 10
    if not files or len(files) < 1:
        raise HTTPException(status_code=400, detail="文件数不能为 0，请至少上传 1 个文件")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="文件数不能超过 10 个")

    print(f"[批量上传] 开始处理: 用户={current_user.username}, 文件数={len(files)}, "
          f"project_id={project_id}, position_id={position_id}")

    results: List[Dict[str, Any]] = []
    succeeded = 0
    failed = 0

    for idx, file in enumerate(files, start=1):
        filename = file.filename or f"resume_{idx}.pdf"
        file_log_prefix = f"[批量上传][{idx}/{len(files)}] {filename}"

        # 1a. 读取文件内容（在 helper 之外读，避免 SpooledTemporaryFile 提前关闭）
        try:
            content = await file.read()
        except Exception as e:
            err = f"读取文件失败: {type(e).__name__}: {e}"
            print(f"{file_log_prefix} ✗ {err}")
            results.append({"filename": filename, "status": "failed", "error": err})
            failed += 1
            continue

        # 1b. 前置校验：扩展名 + 大小（单文件级错误，不影响其他文件）
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in _ALLOWED_EXTENSIONS:
            err = "只支持 PDF/DOC/DOCX 格式文件"
            print(f"{file_log_prefix} ✗ {err}")
            results.append({"filename": filename, "status": "failed", "error": err})
            failed += 1
            continue
        if len(content) > _MAX_FILE_SIZE:
            err = "文件大小不能超过 10MB"
            print(f"{file_log_prefix} ✗ {err} (size={len(content)})")
            results.append({"filename": filename, "status": "failed", "error": err})
            failed += 1
            continue

        # 1c. 调用共用 helper（内部使用 SAVEPOINT 隔离单个文件的事务）
        try:
            ok, payload = _process_resume_upload(
                db=db,
                filename=filename,
                content=content,
                project_id=project_id,
                position_id=position_id,
                current_user=current_user,
            )
        except Exception as e:
            # 兜底：helper 自己已经管理 savepoint，这里只是双保险
            err = f"处理异常: {type(e).__name__}: {e}"
            print(f"{file_log_prefix} ✗ {err}")
            print(traceback.format_exc())
            try:
                db.rollback()
            except Exception:
                pass
            results.append({"filename": filename, "status": "failed", "error": err})
            failed += 1
            continue

        if ok:
            succeeded += 1
            results.append({
                "filename": filename,
                "status": "success",
                "resume_id": payload["resume_id"],
                "candidate_name": payload.get("candidate_name"),
            })
            print(f"{file_log_prefix} ✓ 成功 resume_id={payload['resume_id']}")
            # 有关联职位 → 后台异步 AI 评分（响应已不再等 LLM）
            if position_id:
                background_tasks.add_task(_score_resume_background, payload["resume_id"], position_id)
        else:
            failed += 1
            results.append({
                "filename": filename,
                "status": "failed",
                "error": payload.get("error", "简历处理失败"),
            })
            print(f"{file_log_prefix} ✗ 失败: {payload.get('error')}")

    total = len(files)
    print(f"[批量上传] 完成: total={total}, succeeded={succeeded}, failed={failed}")

    # 全部失败 → 400（spec 要求）
    if succeeded == 0 and failed > 0:
        return {
            "code": 400,
            "message": "所有文件处理失败",
            "data": {
                "total": total,
                "succeeded": 0,
                "failed": failed,
                "results": results,
            },
        }

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        },
    }



@router.put("/{resume_id}/status", summary="更新简历状态")
def update_resume_status(
    resume_id: int,
    status_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新简历状态"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.is_deleted == 0
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    new_status = status_update.get('status')
    if not new_status:
        raise HTTPException(status_code=400, detail="状态不能为空")
    
    valid_statuses = [
        'submitted', 'viewed', 'interview_scheduled',
        'interviewing', 'hired', 'rejected', 'onboarded'
    ]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="无效的状态值")
    
    # 转换为枚举类型
    from ..models.models import ResumeStatus
    resume.status = ResumeStatus(new_status)
    db.commit()
    
    return {"code": 0, "message": "状态更新成功"}

@router.delete("/{resume_id}", summary="删除简历")
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """删除简历"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.is_deleted == 0
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    # 软删除
    resume.is_deleted = 1
    db.commit()
    
    return {"code": 0, "message": "删除成功"}


@router.get("/{resume_id}/download", summary="下载简历文件")
def download_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载简历文件"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.is_deleted == 0
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    
    if not resume.file_path:
        raise HTTPException(status_code=404, detail="简历文件不存在")
    
    from fastapi.responses import FileResponse
    import os
    import urllib.parse
    if os.path.exists(resume.file_path):
        filename = resume.original_filename or f"resume_{resume_id}.pdf"
        # URL 编码文件名以支持中文
        encoded_filename = urllib.parse.quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
        return FileResponse(resume.file_path, headers=headers, media_type="application/octet-stream")
    else:
        raise HTTPException(status_code=404, detail="文件不存在")



@router.get("/stats/summary", summary="获取简历统计数据")
def get_resume_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取简历统计数据用于数据看板"""
    from sqlalchemy import func
    
    # 总简历数
    total = db.query(func.count(Resume.id)).filter(Resume.is_deleted == 0).scalar()
    
    # 各状态数量
    status_counts = db.query(Resume.status, func.count(Resume.id))         .filter(Resume.is_deleted == 0)         .group_by(Resume.status)         .all()
    
    # 平均匹配度
    avg_match = db.query(func.avg(Resume.match_score))         .filter(Resume.is_deleted == 0, Resume.match_score.isnot(None))         .scalar()
    
    # 按状态分类计数
    funnel = {
        'total': total or 0,
        'submitted': 0,
        'interviewing': 0,
        'onboarded': 0,
        'avg_match_score': round(float(avg_match) if avg_match else 0, 1)
    }
    
    for status, count in status_counts:
        status_str = status.value if hasattr(status, 'value') else str(status)
        if status_str in funnel:
            funnel[status_str] = count
    
    # 合并面试相关
    for status, count in status_counts:
        status_str = status.value if hasattr(status, 'value') else str(status)
        if 'interview' in status_str:
            funnel['interviewing'] += count
    
    return {
        "code": 0,
        "message": "success",
        "data": funnel
    }
