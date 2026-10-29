"""
用户管理 API - CRUD
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import get_db
from ..core.security import (
    get_password_hash,
    get_current_user,
    get_current_active_admin
)
from ..models.models import User, UserRole
from ..schemas.user import (
    UserCreate,
    UserUpdate,
    UserResetPassword,
    UserResponse,
    ApiResponse
)

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", summary="获取用户列表")
def get_users(
    role: Optional[UserRole] = Query(None, description="按角色筛选"),
    status: Optional[int] = Query(None, description="按状态筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索（用户名、姓名）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """获取用户列表 - 只有管理员可以查看"""
    query = db.query(User).filter(User.is_deleted == 0)
    
    # 筛选条件
    if role:
        query = query.filter(User.role == role)
    if status is not None:
        query = query.filter(User.status == status)
    if keyword:
        query = query.filter(
            User.username.contains(keyword) | 
            User.real_name.contains(keyword)
        )
    
    # 分页
    total = query.count()
    users = query.order_by(User.created_at.desc())\
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
            "items": users
        }
    }


@router.get("/{user_id}", summary="获取用户详情")
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """获取用户详情"""
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == 0
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {"code": 0, "message": "success", "data": user}


@router.post("", summary="创建用户", status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """创建新用户 - 只有管理员可以创建"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(
        User.username == user_data.username,
        User.is_deleted == 0
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user = User(
        **user_data.model_dump(exclude={"password"}),
        password_hash=get_password_hash(user_data.password),
        status=1
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"code": 0, "message": "用户创建成功", "data": {"id": user.id}}


@router.put("/{user_id}", summary="更新用户信息")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """更新用户信息"""
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == 0
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能修改自己的角色
    if user.id == current_user.id and user_data.role is not None and user_data.role != user.role:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    
    # 更新字段
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return {"code": 0, "message": "用户信息更新成功", "data": user}


@router.patch("/{user_id}/password", summary="重置用户密码")
def reset_user_password(
    user_id: int,
    pwd_data: UserResetPassword,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """重置用户密码"""
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == 0
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.password_hash = get_password_hash(pwd_data.new_password)
    db.commit()
    
    return {"code": 0, "message": "密码重置成功"}


@router.delete("/{user_id}", summary="删除用户")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """删除用户（软删除）"""
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == 0
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    # 软删除
    user.is_deleted = 1
    db.commit()
    
    return {"code": 0, "message": "用户删除成功"}


@router.patch("/{user_id}/status", summary="修改用户状态")
def change_user_status(
    user_id: int,
    status_data: dict,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """修改用户状态 1-启用 0-禁用"""
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == 0
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能禁用自己
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    
    new_status = status_data.get("status")
    if new_status not in [0, 1]:
        raise HTTPException(status_code=400, detail="无效的状态值")
    
    user.status = new_status
    db.commit()
    
    status_text = "启用" if new_status == 1 else "禁用"
    return {"code": 0, "message": f"用户已{status_text}"}
