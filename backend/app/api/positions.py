"""
职位管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from ..core.database import get_db
from ..core.security import get_current_user, get_current_deliverer_or_admin
from ..models.models import User, Position, Project, Resume
from ..schemas.user import PositionCreate, PositionUpdate, ApiResponse

router = APIRouter(prefix="/positions", tags=["职位管理"])


@router.get("", summary="获取职位列表")
def get_positions(
    project_id: Optional[int] = Query(None, description="按项目ID筛选"),
    status: Optional[int] = Query(None, description="按状态筛选 1-启用 2-暂停 3-关闭"),
    keyword: Optional[str] = Query(None, description="按职位名称搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取职位列表 - 关联项目名称"""
    query = db.query(
        Position.id,
        Position.project_id,
        Position.position_name,
        Position.salary_range,
        Position.work_location,
        Position.jd_content,
        Position.required_skills,
        Position.hiring_count,
        Position.status,
        Position.created_by,
        Position.created_at,
        Position.updated_at,
        Project.project_name
    ).outerjoin(Project, Position.project_id == Project.id).filter(
        Position.is_deleted == 0
    )
    
    # 按项目筛选
    if project_id:
        query = query.filter(Position.project_id == project_id)
    
    # 按状态筛选
    if status is not None:
        query = query.filter(Position.status == status)
    
    # 按关键词搜索
    if keyword:
        query = query.filter(Position.position_name.contains(keyword))
    
    # 数据权限控制：交付人员只能看到自己项目的职位
    if current_user.role.value == "deliverer":
        query = query.filter(Project.created_by == current_user.id)
    
    # 分页
    total = query.count()
    positions = query.order_by(Position.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    # 转换为字典列表
    result = []
    for p in positions:
        item = {
            "id": p.id,
            "project_id": p.project_id,
            "position_name": p.position_name,
            "salary_range": p.salary_range,
            "work_location": p.work_location,
            "jd_content": p.jd_content,
            "required_skills": p.required_skills,
            "hiring_count": p.hiring_count,
            "status": p.status,
            "created_by": p.created_by,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "project_name": p.project_name
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


@router.get("/all", summary="获取所有职位（不分页）")
def get_all_positions(
    project_id: Optional[int] = Query(None, description="按项目ID筛选"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有职位 - 用于下拉选择"""
    query = db.query(Position).filter(Position.is_deleted == 0)
    
    if project_id:
        query = query.filter(Position.project_id == project_id)
    
    positions = query.order_by(Position.created_at.desc()).all()
    return {"code": 0, "message": "success", "data": positions}


@router.get("/{position_id}", summary="获取职位详情")
def get_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取职位详情"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.is_deleted == 0
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    return {"code": 0, "message": "success", "data": position}


@router.post("", summary="创建职位", status_code=status.HTTP_201_CREATED)
def create_position(
    position_data: PositionCreate,
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """创建职位"""
    position = Position(
        **position_data.model_dump(),
        created_by=current_user.id
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    
    return {"code": 0, "message": "职位创建成功", "data": {"id": position.id}}


@router.put("/{position_id}", summary="更新职位")
def update_position(
    position_id: int,
    position_data: PositionUpdate,
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """更新职位"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.is_deleted == 0
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    # 更新字段
    update_data = position_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(position, field, value)
    
    db.commit()
    db.refresh(position)
    
    return {"code": 0, "message": "职位更新成功", "data": position}


@router.delete("/{position_id}", summary="删除职位")
def delete_position(
    position_id: int,
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """删除职位"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.is_deleted == 0
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    # 软删除
    position.is_deleted = 1
    db.commit()
    
    return {"code": 0, "message": "职位删除成功"}


@router.patch("/{position_id}/status", summary="修改职位状态")
def change_position_status(
    position_id: int,
    status_data: dict = Body(...),
    current_user: User = Depends(get_current_deliverer_or_admin),
    db: Session = Depends(get_db),
):
    """修改职位状态 1-启用 2-暂停 3-关闭"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.is_deleted == 0
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    new_status = status_data.get("status")
    if new_status not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="无效的状态值")
    
    position.status = new_status
    db.commit()
    
    status_map = {1: "启用", 2: "暂停", 3: "关闭"}
    return {"code": 0, "message": f"职位状态已更新为：{status_map[new_status]}"}
