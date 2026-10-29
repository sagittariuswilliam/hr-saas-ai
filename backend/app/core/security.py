"""
安全相关工具函数
JWT 生成与验证、密码加密、权限控制
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import hashlib
import hmac
import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import settings
from ..core.database import get_db
from ..models.models import User
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# 登录速率限制（内存）
LOGIN_RATE_LIMIT: Dict[str, Dict[str, Any]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 5


# ==================== 密码加密 ====================

def _get_password_hash(password: str) -> str:
    """简单的密码哈希实现（兼容 bcrypt 格式）"""
    # 使用 pbkdf2 算法，不需要额外依赖
    salt = b'hr_saas_salt_fixed_value_2024'  # 固定 salt（生产环境应配置）
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return 'pbkdf2:' + base64.b64encode(dk).decode('ascii')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 支持两种格式：我们自己生成的 pbkdf2 格式，和标准 hash 格式
    if hashed_password.startswith('pbkdf2:'):
        salt = b'hr_saas_salt_fixed_value_2024'
        dk = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        expected = 'pbkdf2:' + base64.b64encode(dk).decode('ascii')
        return hmac.compare_digest(hashed_password, expected)
    else:
        # 简单 sha256 格式兼容
        return hmac.compare_digest(
            hashlib.sha256(plain_password.encode()).hexdigest(),
            hashed_password
        )


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return _get_password_hash(password)


# ==================== JWT Token ====================

def create_access_token(subject: dict) -> str:
    """生成访问令牌"""
    to_encode = subject.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证 token 并返回 payload"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


# ==================== 登录速率限制 ====================

def check_login_rate_limit(client_ip: str) -> bool:
    """检查是否超过登录速率限制"""
    if client_ip not in LOGIN_RATE_LIMIT:
        return True
    
    limit_info = LOGIN_RATE_LIMIT[client_ip]
    
    # 检查是否已经解锁
    if limit_info["locked_until"] and datetime.utcnow() > limit_info["locked_until"]:
        # 解锁，重置计数器
        del LOGIN_RATE_LIMIT[client_ip]
        return True
    
    # 检查是否锁定
    if limit_info["locked_until"] and datetime.utcnow() < limit_info["locked_until"]:
        return False
    
    # 检查尝试次数
    return limit_info["attempts"] < MAX_LOGIN_ATTEMPTS


def increment_login_attempts(client_ip: str) -> int:
    """增加登录尝试次数，返回剩余尝试次数"""
    if client_ip not in LOGIN_RATE_LIMIT:
        LOGIN_RATE_LIMIT[client_ip] = {
            "attempts": 0,
            "locked_until": None
        }
    
    limit_info = LOGIN_RATE_LIMIT[client_ip]
    limit_info["attempts"] += 1
    
    # 达到最大尝试次数，锁定账户
    if limit_info["attempts"] >= MAX_LOGIN_ATTEMPTS:
        limit_info["locked_until"] = datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES)
    
    remaining = max(0, MAX_LOGIN_ATTEMPTS - limit_info["attempts"])
    return remaining


def reset_login_attempts(client_ip: str):
    """重置登录尝试次数（登录成功后调用）"""
    if client_ip in LOGIN_RATE_LIMIT:
        del LOGIN_RATE_LIMIT[client_ip]


# ==================== 用户认证 ====================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    username: Optional[str] = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username, User.is_deleted == 0).first()
    if user is None:
        raise credentials_exception
    
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    return current_user


async def get_current_active_admin(current_user: User = Depends(get_current_user)) -> User:
    """获取当前管理员（权限检查）"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员角色"
        )
    return current_user


def get_current_recruiter_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """获取当前招聘人员或管理员"""
    allowed_roles = ["admin", "recruiter"]
    if current_user.role.value not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要招聘人员或管理员角色"
        )
    return current_user


def get_current_deliverer_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """获取当前交付人员/招聘人员/管理员"""
    allowed_roles = ["admin", "deliverer", "recruiter"]
    if current_user.role.value not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要交付人员/招聘人员/管理员角色"
        )
    return current_user
