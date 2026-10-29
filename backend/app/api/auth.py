"""
认证相关 API
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..core.security import (
    create_access_token,
    verify_password,
    get_current_user
)
from ..models.models import User

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", summary="用户登录")
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """用户登录 - 支持 JSON 和 form-data 两种格式"""
    # 尝试解析 JSON
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的请求格式"
            )
    else:
        # form-data 格式
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名和密码不能为空"
        )
    
    # 查询用户
    user = db.query(User).filter(User.username == username, User.is_deleted == 0).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查用户状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 创建 token
    access_token = create_access_token(subject={"sub": user.username})
    
    # 返回用户信息（与前端期望字段匹配）
    return {
        "code": 0,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "real_name": user.real_name,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                "email": user.email,
                "phone": user.phone,
                "status": user.status
            }
        }
    }


@router.get("/me", summary="获取当前用户信息")
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户信息"""
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "real_name": current_user.real_name,
            "role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
            "email": current_user.email,
            "phone": current_user.phone,
            "status": current_user.status
        }
    }
