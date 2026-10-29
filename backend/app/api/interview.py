"""
AI 面试 API
HR 侧（JWT 鉴权）：建会话→审定题目→发送（生成候选人链接）→看会话列表/报告
候选人侧（公开，凭 token）：逐题作答（断点续答/1轮追问）→交卷（自动评分，不回传分数）
"""
from datetime import datetime, timedelta
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import (
    User, Resume, Position,
    InterviewSession, InterviewAnswer, InterviewReport,
)
from ..services import interview_service, asr

router = APIRouter(prefix="/interview", tags=["AI面试"])

# 语音作答录音存放根目录（与 resumes.py 的 uploads 目录同级）
from ..core.config import settings as _settings
_UPLOAD_ROOT = _settings.UPLOAD_DIR
_VOICE_DIR = os.path.join(_UPLOAD_ROOT, "interview_voices")

# 会话有效期 72 小时
_SESSION_TTL_HOURS = 72

# 原声保留 30 天：超期文件由 cleanup_voice 定时删除，
# HR 试听接口对超期/缺失文件返回 410
_VOICE_RETENTION_DAYS = 30


# ==================== 请求体模型 ====================

class SessionCreateRequest(BaseModel):
    """建会话：候选人=简历"""
    resume_id: int


class QuestionsUpdateRequest(BaseModel):
    """HR 审定后的题目数组（可删题/改题/补题）"""
    questions: List[dict]


class AnswerRequest(BaseModel):
    """候选人提交/覆盖某题答案（断点续答）"""
    question_index: int
    answer_text: str
    elapsed_seconds: Optional[int] = None
    paste_detected: bool = False
    followup_answer: Optional[str] = None
    voice_url: Optional[str] = None  # 两步式语音作答：转写文本经确认后随答案挂录音引用


# ==================== 内部工具 ====================

def _session_dict(s: InterviewSession) -> dict:
    return {
        "id": s.id,
        "resume_id": s.resume_id,
        "position_id": s.position_id,
        "token": s.token,
        "status": s.status,
        "questions_json": s.questions_json,
        "created_by": s.created_by,
        "sent_at": s.sent_at.isoformat() if s.sent_at else None,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _is_expired(s: InterviewSession) -> bool:
    """sent/in_progress 且超过 expires_at 视为过期（惰性判定，同时落库）"""
    if s.status in ("sent", "in_progress") and s.expires_at and datetime.now() > s.expires_at:
        s.status = "expired"
        return True
    return False


def _get_public_session(token: str, db: Session) -> InterviewSession:
    s = db.query(InterviewSession).filter(InterviewSession.token == token).first()
    if not s or s.status == "draft":
        raise HTTPException(status_code=404, detail="链接无效，请联系 HR 确认")
    if _is_expired(s):
        raise HTTPException(status_code=410, detail="该面试链接已过期（72小时有效），请联系 HR 重新发送")
    return s


# ==================== HR 侧接口 ====================

@router.post("/sessions", summary="创建面试会话（AI 出题）")
def create_session(
    req: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读简历+职位 JD，调 LLM 出 6 题，建 draft 会话"""
    resume = db.query(Resume).filter(Resume.id == req.resume_id, Resume.is_deleted == 0).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    if not resume.position_id:
        raise HTTPException(status_code=400, detail="该简历未匹配职位，无法出题")
    position = db.query(Position).filter(Position.id == resume.position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="关联职位不存在")

    resume_text = " | ".join(filter(None, [
        resume.candidate_name, resume.highest_education,
        f"{resume.years_of_experience or ''}年经验" if resume.years_of_experience else None,
        json_dumps_safe(resume.skills),
        (resume.work_experience or "")[:1500],
    ]))
    questions = interview_service.generate_questions(
        position.jd_content or "", resume_text, position.position_name
    )

    session = InterviewSession(
        resume_id=resume.id,
        position_id=position.id,
        status="draft",
        questions_json=questions,
        created_by=current_user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"code": 0, "message": "success", "data": _session_dict(session)}


def json_dumps_safe(v) -> str:
    import json
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)


@router.put("/sessions/{session_id}/questions", summary="HR 审定题目（仅 draft 可改）")
def update_questions(
    session_id: int,
    req: QuestionsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    if s.status != "draft":
        raise HTTPException(status_code=400, detail="仅草稿状态可修改题目")
    # 硬校验：拒绝空题干（防白卷入库/发出）
    for i, q in enumerate(req.questions, 1):
        if not str((q or {}).get("text") or "").strip():
            raise HTTPException(status_code=400, detail=f"第 {i} 题题干为空，不能保存")
    # 重排 index，保证前端按序渲染
    questions = req.questions
    for i, q in enumerate(questions, 1):
        q["index"] = i
    s.questions_json = questions
    db.commit()
    db.refresh(s)
    return {"code": 0, "message": "success", "data": _session_dict(s)}


@router.post("/sessions/{session_id}/send", summary="发送面试链接（生成 token，72h 有效）")
def send_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    if s.status not in ("draft",):
        raise HTTPException(status_code=400, detail=f"当前状态（{s.status}）不可发送")
    if not s.questions_json:
        raise HTTPException(status_code=400, detail="题目为空，不可发送")
    if any(not str(q.get("text") or "").strip() for q in s.questions_json):
        raise HTTPException(status_code=400, detail="存在空题干，请点击「审定题目」补充后再发送")

    token = interview_service.generate_token()
    now = datetime.now()
    s.token = token
    s.status = "sent"
    s.sent_at = now
    s.expires_at = now + timedelta(hours=_SESSION_TTL_HOURS)
    db.commit()

    resume = db.query(Resume).filter(Resume.id == s.resume_id).first()
    name = (resume.candidate_name if resume else "") or "候选人"
    link = f"/interview/i/{token}"
    script = (
        f"{name}您好，我是公司 HR。您的岗位初筛已通过，"
        f"这里有一个约 15 分钟的线上面试（支持语音作答），共 {len(s.questions_json)} 道题，"
        f"链接 72 小时内有效，请合理安排时间完成：{link} 。"
        "手机端请复制链接后用浏览器（Safari/Chrome/系统浏览器）打开，微信内直接点开可能无法访问；"
        "页面内点🎤即可语音作答，说完自动转文字，可修改后发送。"
        "请独立作答，全程结果仅用于本次招聘评估。"
    )
    return {"code": 0, "message": "success", "data": {"token": token, "link": link, "script": script}}


@router.get("/resumes/{resume_id}/sessions", summary="某候选人的面试会话列表")
def list_sessions_by_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = db.query(InterviewSession).filter(
        InterviewSession.resume_id == resume_id
    ).order_by(InterviewSession.created_at.desc()).all()

    result = []
    for s in sessions:
        _is_expired(s)
        total_q = len(s.questions_json or [])
        answered = db.query(InterviewAnswer).filter(
            InterviewAnswer.session_id == s.id
        ).count()
        result.append({**_session_dict(s), "total_questions": total_q, "answered_count": answered})
    db.commit()  # 持久化惰性 expired 状态
    return {"code": 0, "message": "success", "data": result}


@router.get("/resumes/summary", summary="批量面试摘要（简历列表 badge 用）")
def sessions_summary(
    resume_ids: str,  # 逗号分隔
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = [int(x) for x in resume_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return {"code": 0, "message": "success", "data": {}}
    sessions = db.query(InterviewSession).filter(
        InterviewSession.resume_id.in_(ids)
    ).order_by(InterviewSession.created_at.desc()).all()
    scored = dict(db.query(InterviewSession.id, InterviewReport.total_score).join(
        InterviewReport, InterviewReport.session_id == InterviewSession.id
    ).all())
    summary = {}
    for s in sessions:
        _is_expired(s)
        # 每人取"最好的一份"：有报告取最高分，否则取最新状态
        cur = summary.get(s.resume_id)
        item = {"session_id": s.id, "status": s.status,
                "total_score": scored.get(s.id)}
        if cur is None or (item["total_score"] is not None and
                           (cur["total_score"] is None or item["total_score"] > cur["total_score"])):
            summary[s.resume_id] = item
    db.commit()
    return {"code": 0, "message": "success", "data": {str(k): v for k, v in summary.items()}}


@router.get("/sessions/{session_id}/report", summary="获取面试报告（仅 HR）")
def get_report(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    report = db.query(InterviewReport).filter(InterviewReport.session_id == session_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="候选人尚未交卷，暂无报告")
    import json
    # 每题原声状态（VR-12）：voice_urls[i] = 第 i+1 题录音相对路径或 None；
    # voice_available[i] = 文件存在且未超 30 天保留期
    n = len((report.per_question_json and json.loads(report.per_question_json or "[]")) or [])
    urls = list(s.voice_answer_urls or [])
    while len(urls) < n:
        urls.append(None)
    voice_available = []
    for i in range(n):
        u = urls[i] if i < len(urls) else None
        ok = False
        if u:
            fp = os.path.realpath(os.path.join(_UPLOAD_ROOT, u))
            if fp.startswith(os.path.realpath(_VOICE_DIR)) and os.path.isfile(fp):
                age_days = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(fp))).days
                ok = age_days < _VOICE_RETENTION_DAYS
        voice_available.append(ok)
    return {"code": 0, "message": "success", "data": {
        "session_id": s.id,
        "resume_id": s.resume_id,
        "position_id": s.position_id,
        "total_score": report.total_score,
        "verdict": report.verdict,
        "per_question": json.loads(report.per_question_json or "[]"),
        "highlights": json.loads(report.highlights or "[]"),
        "concerns": json.loads(report.concerns or "[]"),
        "paste_warnings": json.loads(report.paste_warnings or "[]"),
        "hr_followup": json.loads(report.hr_followup_json or "[]"),
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "voice_urls": urls[:n],
        "voice_available": voice_available,
    }}


@router.get("/sessions/{session_id}/voice/{q_index}", summary="HR 试听原声（登录态，30 天内）")
def get_session_voice(
    session_id: int,
    q_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """VR-12：报告页「试听原声」。仅 HR 登录态可取，按会话+题号定位文件，
    超 30 天或文件已清理返回 410，路径不可被外部构造（防目录穿越）。"""
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    urls = s.voice_answer_urls or []
    rel = urls[q_index - 1] if 0 < q_index <= len(urls) else None
    if not rel:
        raise HTTPException(status_code=404, detail="该题无录音作答")
    fp = os.path.realpath(os.path.join(_UPLOAD_ROOT, rel))
    if not fp.startswith(os.path.realpath(_VOICE_DIR)):
        raise HTTPException(status_code=400, detail="非法路径")
    if not os.path.isfile(fp):
        raise HTTPException(status_code=410, detail="原声已按隐私策略删除")
    age_days = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(fp))).days
    if age_days >= _VOICE_RETENTION_DAYS:
        raise HTTPException(status_code=410, detail="原声已按隐私策略删除")
    media = {".wav": "audio/wav", ".webm": "audio/webm", ".m4a": "audio/mp4", ".mp3": "audio/mpeg"}
    ext = os.path.splitext(fp)[1].lower()
    return FileResponse(fp, media_type=media.get(ext, "application/octet-stream"))


# ==================== 候选人侧公开接口（凭 token，无鉴权） ====================

@router.get("/i/{token}", summary="候选人查看面试（按进度逐题放出）")
def candidate_view(
    token: str,
    db: Session = Depends(get_db),
):
    s = _get_public_session(token, db)
    questions = s.questions_json or []
    answers = {a.question_index: a for a in db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == s.id).all()}

    readonly = s.status in ("submitted", "report_ready")
    # 逐题放出：已答题回显完整题干；当前第一道未答题放出题干；其后未开始的题不泄露题干
    first_unanswered = next((q.get("index") for q in questions
                             if q.get("index") not in answers), None)
    result = []
    for q in questions:
        idx = q.get("index")
        a = answers.get(idx)
        if a is not None or readonly:
            # 已答题：回显题目+答案+追问
            item = {
                "index": idx, "type": q.get("type"), "text": q.get("text"),
                "min_words": q.get("min_words"), "status": "answered",
                "answer_text": a.answer_text if a else None,
                "followup_question": a.followup_question if a else None,
                "followup_answer": a.followup_answer if a else None,
            }
            if item["answer_text"] is None:  # readonly 但该题空
                item["status"] = "unanswered"
            result.append(item)
        elif idx == first_unanswered:
            result.append({
                "index": idx, "type": q.get("type"), "text": q.get("text"),
                "min_words": q.get("min_words"), "status": "current",
            })
        else:
            result.append({"index": idx, "status": "locked"})

    db.commit()  # 惰性过期落库
    return {"code": 0, "message": "success", "data": {
        "status": s.status,
        "readonly": readonly,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "voice_consent_at": s.voice_consent_at.isoformat() if s.voice_consent_at else None,
        "questions": result,
    }}


@router.post("/i/{token}/voice-consent", summary="语音作答单独同意（VR-02，同意后方可转写）")
def candidate_voice_consent(
    token: str,
    db: Session = Depends(get_db),
):
    s = _get_public_session(token, db)
    if s.status in ("submitted", "report_ready"):
        raise HTTPException(status_code=400, detail="已交卷")
    if not s.voice_consent_at:
        s.voice_consent_at = datetime.now()
        db.commit()
    return {"code": 0, "message": "success",
            "data": {"voice_consent_at": s.voice_consent_at.isoformat()}}


@router.post("/i/{token}/answer", summary="候选人提交/覆盖某题答案（断点续答）")
def candidate_answer(
    token: str,
    req: AnswerRequest,
    db: Session = Depends(get_db),
):
    s = _get_public_session(token, db)
    if s.status in ("submitted", "report_ready"):
        raise HTTPException(status_code=400, detail="已交卷，不可再修改答案")

    questions = s.questions_json or []
    q = next((x for x in questions if x.get("index") == req.question_index), None)
    if not q:
        raise HTTPException(status_code=400, detail="题号不存在")

    a = db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == s.id,
        InterviewAnswer.question_index == req.question_index,
    ).first()
    if a is None:
        a = InterviewAnswer(session_id=s.id, question_index=req.question_index)
        db.add(a)

    a.answer_text = req.answer_text
    a.elapsed_seconds = req.elapsed_seconds
    a.paste_detected = 1 if req.paste_detected else 0
    a.answered_at = datetime.now()

    # 两步式语音作答：把转写阶段保存的录音路径挂到会话（下标=题号-1）
    if req.voice_url:
        urls = list(s.voice_answer_urls or []) + [None] * (req.question_index - len(s.voice_answer_urls or []))
        urls[req.question_index - 1] = req.voice_url
        s.voice_answer_urls = urls

    followup = None
    if req.followup_answer is not None:
        # 候选人补充回答追问
        a.followup_answer = req.followup_answer
    else:
        # 首次提交该题（且尚无追问）→ 服务端规则判定是否追问，最多 1 轮
        if not a.followup_question:
            followup = interview_service.maybe_followup(q, req.answer_text)
            if followup:
                a.followup_question = followup

    if s.status == "sent":
        s.status = "in_progress"
    db.commit()
    db.refresh(a)
    return {"code": 0, "message": "success", "data": {
        "question_index": a.question_index,
        "followup_question": a.followup_question,
        "has_followup_answer": bool(a.followup_answer),
    }}


@router.post("/i/{token}/transcribe-voice", summary="候选人语音转写（存录音+返回转写文本，不落答案库）")
def candidate_transcribe_voice(
    token: str,
    question_index: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    升级路线 V1.1 P2 两步式语音作答第 1 步：
      录音 → 存 uploads/interview_voices/ → qwen3-asr-flash 同步转写 → 只返回文本。
    候选人检查/编辑转写文本后，走现有 POST /i/{token}/answer 提交（voice_url 一并带回挂引用）。
    转写失败：录音已保存，返回 transcription_ok=false，前端提示改用文本作答。
    """
    s = _get_public_session(token, db)
    if s.status in ("submitted", "report_ready"):
        raise HTTPException(status_code=400, detail="已交卷，不可再修改答案")
    # VR-02 合规硬门槛：未完成单独同意不得转写（服务端强制，绕开前端弹窗也无效）
    # 注意：门槛放在读文件+落盘之前——未同意的音频一律不留存服务器（数据最小化红线）
    if not s.voice_consent_at:
        raise HTTPException(status_code=403, detail="请先同意语音作答授权说明")

    questions = s.questions_json or []
    q = next((x for x in questions if x.get("index") == question_index), None)
    if not q:
        raise HTTPException(status_code=400, detail="题号不存在")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".wav", ".webm", ".m4a", ".mp3"):
        raise HTTPException(status_code=400, detail="不支持的录音格式")
    audio_bytes = file.file.read()
    if len(audio_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="录音过大（>10MB），请缩短作答时间")

    # 用会话 id + 随机名存每次录音（同题重录产生新文件，旧文件不删——转写成功与否都可追溯）
    import uuid as _uuid
    fname = f"q{question_index}_{_uuid.uuid4().hex[:8]}{ext}"
    voice_dir = os.path.join(_VOICE_DIR, token)
    os.makedirs(voice_dir, exist_ok=True)
    rel_path = f"interview_voices/{token}/{fname}"
    with open(os.path.join(voice_dir, fname), "wb") as f:
        f.write(audio_bytes)

    transcript = ""
    transcription_ok = True
    try:
        transcript = asr.transcribe_wav(audio_bytes)
    except asr.ASRError:
        transcription_ok = False

    return {
        "code": 0,
        "message": "success",
        "data": {
            "question_index": question_index,
            "transcription_ok": transcription_ok,
            "transcript": transcript if transcription_ok else None,
            "voice_url": rel_path,
        },
    }


@router.post("/i/{token}/submit", summary="候选人交卷（服务端评分，不回传分数）")
def candidate_submit(
    token: str,
    db: Session = Depends(get_db),
):
    s = _get_public_session(token, db)
    if s.status in ("submitted", "report_ready"):
        return {"code": 0, "message": "已完成，结果将由 HR 反馈", "data": None}
    if s.status not in ("in_progress", "sent"):
        raise HTTPException(status_code=400, detail="当前状态不可交卷")

    questions = s.questions_json or []
    answers = {a.question_index: a for a in db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == s.id).all()}
    missing = [q.get("index") for q in questions if q.get("index") not in answers]
    if missing:
        raise HTTPException(status_code=400, detail=f"第 {missing} 题尚未作答，请完成后再交卷")

    s.status = "submitted"
    s.submitted_at = datetime.now()
    db.commit()

    # 同步评分生成报告
    answer_payload = [{
        "index": idx,
        "answer_text": a.answer_text,
        "followup_answer": a.followup_answer,
        "paste_detected": bool(a.paste_detected),
    } for idx, a in sorted(answers.items())]
    report_dict = interview_service.grade_answers(questions, answer_payload)

    import json
    report = InterviewReport(
        session_id=s.id,
        generated_at=datetime.now(),  # 与 submitted_at 同为本地时间，避免 SQLite UTC/本地混用
        total_score=report_dict["total_score"],
        verdict=report_dict["verdict"],
        per_question_json=json.dumps(report_dict["per_question"], ensure_ascii=False),
        highlights=json.dumps(report_dict["highlights"], ensure_ascii=False),
        concerns=json.dumps(report_dict["concerns"], ensure_ascii=False),
        paste_warnings=json.dumps(report_dict["paste_warnings"], ensure_ascii=False),
        hr_followup_json=json.dumps(report_dict["hr_followup"], ensure_ascii=False),
    )
    db.add(report)
    s.status = "report_ready"
    db.commit()

    # 绝不返回分数
    return {"code": 0, "message": "已完成，结果将由 HR 反馈", "data": None}
