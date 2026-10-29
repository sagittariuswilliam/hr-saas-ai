"""
Pydantic Schema 定义
严格按照数据库 Model 字段
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Any
from datetime import datetime


# ============= 通用响应 Schema =============

class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


# ============= 用户相关 Schema =============

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    real_name: str = Field(..., min_length=2, max_length=50, description="真实姓名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    role: str = Field("recruiter", description="角色：admin/recruiter/deliverer")

    @field_validator('email', 'phone', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """将空字符串转换为 None，避免验证失败"""
        if v == '':
            return None
        return v


class UserCreate(UserBase):
    """创建用户"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserUpdate(BaseModel):
    """更新用户"""
    real_name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[int] = None


class UserResetPassword(BaseModel):
    """重置密码"""
    new_password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """用户登录"""
    username: str
    password: str


class UserResponse(UserBase):
    """用户响应"""
    id: int
    status: int
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============= 项目相关 Schema =============

class ProjectBase(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=100, description="项目名称")
    client_name: Optional[str] = Field(None, max_length=100, description="客户名称")
    description: Optional[str] = Field(None, description="项目描述")
    recruiter_id: Optional[int] = Field(None, description="招聘负责人ID")
    deliverer_id: Optional[int] = Field(None, description="交付负责人ID")


class ProjectCreate(ProjectBase):
    """创建项目"""
    pass


class ProjectUpdate(BaseModel):
    """更新项目"""
    project_name: Optional[str] = Field(None, min_length=2, max_length=100)
    client_name: Optional[str] = None
    description: Optional[str] = None
    recruiter_id: Optional[int] = None
    deliverer_id: Optional[int] = None
    status: Optional[int] = None


class ProjectResponse(ProjectBase):
    """项目响应"""
    id: int
    status: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= 职位相关 Schema =============

class PositionBase(BaseModel):
    project_id: int = Field(..., description="所属项目ID")
    position_name: str = Field(..., min_length=2, max_length=100, description="职位名称")
    salary_range: Optional[str] = Field(None, max_length=50, description="薪资范围")
    work_location: Optional[str] = Field(None, max_length=100, description="工作地点")
    jd_content: Optional[str] = Field(None, description="职位描述")
    required_skills: Optional[List[str]] = Field(None, description="技能要求列表")
    hiring_count: Optional[int] = Field(1, ge=1, description="招聘人数")
    status: Optional[int] = Field(1, description="状态：1-启用 2-暂停 3-关闭")


class PositionCreate(PositionBase):
    """创建职位"""
    pass


class PositionUpdate(BaseModel):
    """更新职位"""
    project_id: Optional[int] = None
    position_name: Optional[str] = Field(None, min_length=2, max_length=100)
    salary_range: Optional[str] = None
    work_location: Optional[str] = None
    jd_content: Optional[str] = None
    required_skills: Optional[List[str]] = None
    hiring_count: Optional[int] = None
    status: Optional[int] = None


class PositionResponse(PositionBase):
    """职位响应"""
    id: int
    status: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= 简历相关 Schema =============

class ResumeBase(BaseModel):
    project_id: int = Field(..., description="所属项目ID")
    position_id: int = Field(..., description="匹配的职位ID")
    candidate_name: Optional[str] = Field(None, max_length=50, description="候选人姓名")
    candidate_phone: Optional[str] = Field(None, max_length=20, description="候选人手机号")
    candidate_email: Optional[str] = Field(None, max_length=100, description="候选人邮箱")
    years_of_experience: Optional[float] = Field(None, description="工作年限")
    highest_education: Optional[str] = Field(None, max_length=50, description="最高学历")
    skills: Optional[List[str]] = Field(None, description="技能列表")
    work_experience: Optional[str] = Field(None, description="工作经历")
    education_experience: Optional[str] = Field(None, description="教育经历")


class ResumeCreate(ResumeBase):
    """创建简历"""
    pass


class ResumeUpdate(BaseModel):
    """更新简历"""
    project_id: Optional[int] = None
    position_id: Optional[int] = None
    candidate_name: Optional[str] = None
    candidate_phone: Optional[str] = None
    candidate_email: Optional[str] = None
    years_of_experience: Optional[float] = None
    highest_education: Optional[str] = None
    skills: Optional[List[str]] = None
    work_experience: Optional[str] = None
    education_experience: Optional[str] = None
    status: Optional[str] = None


class ResumeResponse(ResumeBase):
    """简历响应"""
    id: int
    original_filename: str
    file_path: str
    file_size: Optional[int]
    status: str
    parse_status: int
    uploader_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= 分页响应 Schema =============

class MatchingResultResponse(BaseModel):
    """简历匹配结果响应"""
    id: int
    resume_id: int
    position_id: int
    skill_match_score: Optional[float] = None
    experience_match_score: Optional[float] = None
    education_match_score: Optional[float] = None
    total_score: Optional[float] = None
    recommendation: Optional[str] = None
    match_reason: Optional[str] = None
    ai_suggestion: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """分页响应"""
    total: int
    page: int
    page_size: int
    items: List[Any]
