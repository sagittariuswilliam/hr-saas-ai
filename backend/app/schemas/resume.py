"""
简历相关 Pydantic 模型
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from app.models import ResumeStatus, MatchStatus


class ResumeBase(BaseModel):
    """简历基础模型"""
    candidate_name: str = Field(..., max_length=50, description="候选人姓名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    job_id: Optional[int] = Field(None, description="应聘职位ID")
    source: Optional[str] = Field(None, max_length=50, description="简历来源")


class ResumeCreate(ResumeBase):
    """创建简历模型"""
    file_path: str = Field(..., description="文件路径")
    file_name: str = Field(..., description="原始文件名")
    content: Optional[str] = Field(None, description="提取的文本内容")


class ResumeUpdate(BaseModel):
    """更新简历模型"""
    candidate_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[ResumeStatus] = None
    rating: Optional[float] = None
    structured_data: Optional[str] = None


class ResumeResponse(ResumeBase):
    """简历响应模型"""
    id: int
    status: ResumeStatus
    file_path: str
    file_name: str
    rating: Optional[float] = None
    structured_data: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumeListResponse(BaseModel):
    """简历列表响应模型"""
    total: int
    page: int
    page_size: int
    items: list[ResumeResponse]

    class Config:
        from_attributes = True


class ResumeParseRequest(BaseModel):
    """简历解析请求模型"""
    resume_id: int = Field(..., description="简历ID")


class ResumeParseResponse(BaseModel):
    """简历解析响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class MatchResultResponse(BaseModel):
    """匹配结果响应模型"""
    id: int
    resume_id: int
    job_id: int
    match_score: float
    match_reason: Optional[str]
    status: MatchStatus
    ai_analysis: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
