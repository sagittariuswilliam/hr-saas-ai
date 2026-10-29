"""
数据库模型
严格按照需求文档设计
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
import enum


# ==================== 枚举定义 ====================

class UserRole(str, enum.Enum):
    """用户角色"""
    ADMIN = "admin"          # 系统管理员
    RECRUITER = "recruiter"  # 招聘人员
    DELIVERER = "deliverer"  # 交付人员


class ResumeStatus(str, enum.Enum):
    """简历状态"""
    SUBMITTED = "submitted"          # 已提交
    VIEWED = "viewed"                # 已查看
    INTERVIEW_SCHEDULED = "interview_scheduled"  # 已约面
    INTERVIEWING = "interviewing"    # 面试中
    HIRED = "hired"                  # 已录用
    REJECTED = "rejected"            # 已淘汰
    ONBOARDED = "onboarded"          # 已入职


class MatchRecommendation(str, enum.Enum):
    """匹配推荐结果"""
    STRONG_MATCH = "strong_match"    # 强匹配
    MATCH = "match"                  # 匹配
    WEAK_MATCH = "weak_match"        # 弱匹配
    NO_MATCH = "no_match"            # 不匹配


# ==================== 模型定义 ====================

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    email = Column(String(100), comment="邮箱")
    phone = Column(String(20), comment="手机号")
    role = Column(Enum(UserRole), nullable=False, default=UserRole.RECRUITER, comment="角色")
    status = Column(Integer, nullable=False, default=1, comment="状态：1-启用 0-禁用")
    last_login_at = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")
    login_failed_count = Column(Integer, default=0, comment="登录失败次数")
    locked_until = Column(DateTime, comment="锁定截止时间")
    created_by = Column(Integer, comment="创建人ID")
    is_deleted = Column(Integer, default=0, comment="是否删除：0-否 1-是")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class Project(Base):
    """项目表"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(100), nullable=False, comment="项目名称")
    client_name = Column(String(100), comment="客户名称")
    description = Column(Text, comment="项目描述")
    recruiter_id = Column(Integer, ForeignKey("users.id"), comment="招聘负责人ID")
    deliverer_id = Column(Integer, ForeignKey("users.id"), comment="交付负责人ID")
    status = Column(Integer, nullable=False, default=1, comment="状态：1-进行中 0-已结束")
    created_by = Column(Integer, comment="创建人ID")
    is_deleted = Column(Integer, default=0, comment="是否删除：0-否 1-是")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联
    recruiter = relationship("User", foreign_keys=[recruiter_id])
    deliverer = relationship("User", foreign_keys=[deliverer_id])
    positions = relationship("Position", back_populates="project", cascade="all, delete-orphan")


class Position(Base):
    """职位表"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True, comment="所属项目ID")
    position_name = Column(String(100), nullable=False, comment="职位名称")
    salary_range = Column(String(50), comment="薪资范围")
    work_location = Column(String(100), comment="工作地点")
    jd_content = Column(Text, comment="职位描述")
    required_skills = Column(JSON, comment="技能要求列表")
    hiring_count = Column(Integer, default=1, comment="招聘人数")
    status = Column(Integer, nullable=False, default=1, comment="状态：1-招聘中 0-已关闭")
    created_by = Column(Integer, comment="创建人ID")
    is_deleted = Column(Integer, default=0, comment="是否删除：0-否 1-是")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联
    project = relationship("Project", back_populates="positions")
    resumes = relationship("Resume", back_populates="position", cascade="all, delete-orphan")


class Resume(Base):
    """简历表"""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True, comment="所属项目ID")
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True, index=True, comment="匹配的职位ID")
    original_filename = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_size = Column(Integer, comment="文件大小（字节）")
    candidate_name = Column(String(50), comment="候选人姓名")
    candidate_phone = Column(String(20), comment="候选人手机号")
    candidate_email = Column(String(100), comment="候选人邮箱")
    years_of_experience = Column(Float, comment="工作年限")
    highest_education = Column(String(50), comment="最高学历")
    skills = Column(JSON, comment="技能列表")
    work_experience = Column(Text, comment="工作经历")
    education_experience = Column(Text, comment="教育经历")
    parse_status = Column(Integer, default=0, comment="解析状态：0-未解析 1-解析成功 2-解析失败")
    status = Column(Enum(ResumeStatus), nullable=False, default=ResumeStatus.SUBMITTED, comment="简历状态")
    match_score = Column(Integer, comment="AI匹配度评分：0-100")
    match_detail = Column(Text, comment="AI匹配详情JSON")
    uploader_id = Column(Integer, ForeignKey("users.id"), comment="上传人ID")
    is_deleted = Column(Integer, default=0, comment="是否删除：0-否 1-是")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联
    position = relationship("Position", back_populates="resumes")
    matching_result = relationship("ResumeMatchingResult", back_populates="resume", uselist=False, cascade="all, delete-orphan")


class ResumeMatchingResult(Base):
    """简历匹配结果表"""
    __tablename__ = "resume_matching_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False, unique=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    
    # 匹配得分（各维度）
    skill_match_score = Column(Float, comment="技能匹配得分")
    experience_match_score = Column(Float, comment="经验匹配得分")
    education_match_score = Column(Float, comment="学历匹配得分")
    total_score = Column(Float, comment="综合匹配得分")
    
    recommendation = Column(Enum(MatchRecommendation), comment="推荐结果")
    match_reason = Column(Text, comment="匹配理由")
    ai_suggestion = Column(Text, comment="AI建议")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联
    resume = relationship("Resume", back_populates="matching_result")


class OperationLog(Base):
    """系统操作日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String(50), comment="操作人用户名")
    operation_type = Column(String(50), nullable=False, index=True, comment="操作类型")
    target_type = Column(String(50), comment="目标类型")
    target_id = Column(Integer, comment="目标ID")
    ip_address = Column(String(50), comment="IP地址")
    user_agent = Column(String(500), comment="用户代理")
    request_params = Column(JSON, comment="请求参数")
    response_result = Column(JSON, comment="响应结果")
    status = Column(Integer, default=1, comment="状态：1-成功 0-失败")
    error_message = Column(Text, comment="错误信息")
    execution_time = Column(Integer, comment="执行时间（毫秒）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")


# ==================== AI 面试模块模型 ====================

class InterviewSession(Base):
    """AI 面试会话表"""
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False, index=True, comment="候选人（简历ID）")
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True, comment="职位ID")
    token = Column(String(32), unique=True, index=True, comment="候选人答题链接 token（16位随机串，send 时生成）")
    status = Column(String(20), nullable=False, default="draft", index=True,
                    comment="状态：draft-草稿 sent-已发送 in_progress-作答中 submitted-已交卷 report_ready-报告已生成 expired-已过期")
    questions_json = Column(JSON, comment="题目+评分要点快照（LLM 生成后经 HR 审定的最终版）")
    voice_answer_urls = Column(JSON, comment="语音作答录音文件相对路径数组（下标=题号-1，文本作答为 NULL；升级路线 V1.1）")
    voice_consent_at = Column(DateTime, comment="语音作答单独同意时间（VR-02 合规红线：授权弹窗确认后落库，未同意不可转写）")
    created_by = Column(Integer, comment="创建人（HR user id）")
    sent_at = Column(DateTime, comment="发送时间")
    expires_at = Column(DateTime, comment="过期时间（sent 时 +72h）")
    submitted_at = Column(DateTime, comment="候选人交卷时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class InterviewAnswer(Base):
    """AI 面试答案表（每题一行，支持断点续答覆盖）"""
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True, comment="会话ID")
    question_index = Column(Integer, nullable=False, comment="题号（从1开始）")
    answer_text = Column(Text, comment="候选人作答内容")
    answered_at = Column(DateTime, server_default=func.now(), comment="作答时间")
    elapsed_seconds = Column(Integer, comment="该题作答耗时（秒，前端上报）")
    paste_detected = Column(Integer, default=0, comment="疑似粘贴：0-否 1-是（前端判定，后端只存）")
    followup_question = Column(Text, comment="AI 追问（每题最多1轮，null=无追问）")
    followup_answer = Column(Text, comment="候选人对追问的回答")

    # 同一会话同一题只允许一行（upsert 覆盖实现断点续答）
    __table_args__ = (
        Index("idx_session_question", "session_id", "question_index", unique=True),
    )


class InterviewReport(Base):
    """AI 面试评估报告表（仅 HR 可见）"""
    __tablename__ = "interview_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, unique=True, index=True, comment="会话ID")
    total_score = Column(Integer, comment="总分 0-100")
    verdict = Column(String(20), comment="结论：recommend(>=80)/pending(60-79)/reject(<60)")
    per_question_json = Column(Text, comment="逐题评分 JSON：[{index,score,max_score,comment}]")
    highlights = Column(Text, comment="亮点 JSON 数组")
    concerns = Column(Text, comment="风险/关注点 JSON 数组")
    paste_warnings = Column(Text, comment="粘贴预警 JSON 数组（来自 paste_detected）")
    hr_followup_json = Column(Text, comment="建议 HR 复试追问问题 JSON 数组")
    generated_at = Column(DateTime, server_default=func.now(), comment="报告生成时间")
