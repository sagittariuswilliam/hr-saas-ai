"""
全局异常处理
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from .config import settings

# 配置日志
logger = logging.getLogger(__name__)


class BusinessException(Exception):
    """业务异常"""
    def __init__(self, code: int, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器 - 生产环境隐藏详细错误"""
    error_msg = "服务器内部错误"
    
    if settings.ENVIRONMENT == "production":
        # 生产环境只记录日志，不返回详情
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        detail = None
    else:
        # 开发环境返回详细错误
        detail = str(exc)
    
    # 处理数据库异常
    if isinstance(exc, SQLAlchemyError):
        error_msg = "数据库操作异常"
        if settings.ENVIRONMENT == "production":
            logger.error(f"Database error: {str(exc)}", exc_info=True)
            detail = None
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": error_msg,
            "data": None,
            "detail": detail
        }
    )
