"""
项目与职位相关 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models import ProjectStatus, JobStatus


class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., max_length=100, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    budget: Optional[float] = Field(None, description="招聘预算")


class ProjectCreate(ProjectBase):
    """创建项目模型"""
    pass


class ProjectUpdate(BaseModel):
    """更新项目模型"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None


class ProjectResponse(ProjectBase):
    """项目响应模型"""
    id: int
    status: ProjectStatus
    creator_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应模型"""
    total: int
    page: int
    page_size: int
    items: list[ProjectResponse]

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    """职位基础模型"""
    title: str = Field(..., max_length=100, description="职位名称")
    description: Optional[str] = Field(None, description="职位描述")
    requirements: Optional[str] = Field(None, description="任职要求")
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    location: Optional[str] = Field(None, max_length=100, description="工作地点")
    salary_min: Optional[int] = Field(None, description="薪资下限")
    salary_max: Optional[int] = Field(None, description="薪资上限")
    headcount: int = Field(default=1, ge=1, description="招聘人数")


class JobCreate(JobBase):
    """创建职位模型"""
    project_id: int = Field(..., description="所属项目ID")


class JobUpdate(BaseModel):
    """更新职位模型"""
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    headcount: Optional[int] = None
    status: Optional[JobStatus] = None


class JobResponse(JobBase):
    """职位响应模型"""
    id: int
    project_id: int
    status: JobStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """职位列表响应模型"""
    total: int
    page: int
    page_size: int
    items: list[JobResponse]

    class Config:
        from_attributes = True
