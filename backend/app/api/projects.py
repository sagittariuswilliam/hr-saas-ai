"""
项目管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..core.database import get_db
from ..core.security import get_current_user, get_current_deliverer_or_admin
from ..models.models import User, Project
from ..schemas.user import ProjectCreate, ProjectUpdate, ProjectResponse, ApiResponse

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.get("/all", summary="获取所有项目（不分页）")
def get_all_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有项目列表，用于下拉选择"""
    query = db.query(Project).filter(Project.is_deleted == 0)
    
    # 数据权限控制：交付人员只能看到自己创建的项目
    if current_user.role.value == "deliverer":
        query = query.filter(Project.created_by == current_user.id)
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    # 转换为字典列表
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "project_name": p.project_name,
            "client_name": p.client_name,
            "status": p.status,
            "created_by": p.created_by,
            "created_at": p.created_at.isoformat() if p.created_at else None
        })
    
    return {"code": 0, "message": "success", "data": result}


@router.get("", summary="获取项目列表")
def get_projects(
    status: Optional[int] = Query(None, description="按状态筛选"),
    keyword: Optional[str] = Query(None, description="按项目名称搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取项目列表（分页）"""
    query = db.query(Project).filter(Project.is_deleted == 0)
    
    # 按状态筛选
    if status is not None:
        query = query.filter(Project.status == status)
    
    # 按关键词搜索
    if keyword:
        query = query.filter(Project.project_name.contains(keyword))
    
    # 数据权限控制：交付人员只能看到自己创建的项目
    if current_user.role.value == "deliverer":
        query = query.filter(Project.created_by == current_user.id)
    
    # 分页
    total = query.count()
    projects = query.order_by(Project.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    # 转换为字典列表
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "project_name": p.project_name,
            "client_name": p.client_name,
            "status": p.status,
            "created_by": p.created_by,
            "created_at": p.created_at.isoformat() if p.created_at else None
        })
    
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


def get_projects(
    status: Optional[int] = Query(None, description="按状态筛选"),
    keyword: Optional[str] = Query(None, description="按项目名称搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取项目列表"""
    query = db.query(Project).filter(Project.is_deleted == 0)
    
    # 按状态筛选
    if status is not None:
        query = query.filter(Project.status == status)
    
    # 按关键词搜索
    if keyword:
        query = query.filter(Project.project_name.contains(keyword))
    
    # 数据权限控制：交付人员只能看到自己创建的项目
    if current_user.role.value == "deliverer":
        query = query.filter(Project.created_by == current_user.id)
    
    # 分页
    total = query.count()
    projects = query.order_by(Project.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": projects
        }
    }


@router.get("/{project_id}", summary="获取项目详情")
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取项目详情"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == 0
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 数据权限控制
    if current_user.role.value == "deliverer" and project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该项目")
    
    return {"code": 0, "message": "success", "data": project}


@router.post("", summary="创建项目", status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """创建项目 - 只有交付人员或管理员可以创建"""
    project = Project(
        **project_data.model_dump(),
        created_by=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return {"code": 0, "message": "项目创建成功", "data": {"id": project.id}}


@router.put("/{project_id}", summary="更新项目")
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """更新项目"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == 0
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 数据权限控制
    if current_user.role.value == "deliverer" and project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该项目")
    
    # 更新字段
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    
    return {"code": 0, "message": "项目更新成功", "data": project}


@router.delete("/{project_id}", summary="删除项目")
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """删除项目"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == 0
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 数据权限控制
    if current_user.role.value == "deliverer" and project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该项目")
    
    # 软删除
    project.is_deleted = 1
    db.commit()
    
    return {"code": 0, "message": "项目删除成功"}


@router.get("/{project_id}/stats", summary="项目统计信息")
def get_project_stats(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取项目统计信息（简历数量、各状态数量等）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == 0
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 数据权限控制
    if current_user.role.value == "deliverer" and project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该项目")
    
    # 统计简历数量 - 这里先返回基础信息
    from ..models.models import Resume
    resume_count = db.query(Resume).filter(
        Resume.project_id == project_id,
        Resume.is_deleted == 0
    ).count()
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "project_id": project_id,
            "project_name": project.project_name,
            "resume_count": resume_count,
            "status": project.status
        }
    }
