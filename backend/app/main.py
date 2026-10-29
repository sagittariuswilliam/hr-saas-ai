"""
HR-SaaS 后端应用入口
严格按需求文档实现
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings

# 注意：不在这里自动创建表，避免导入时就连接数据库
# 应该用 alembic 或者单独的初始化脚本来创建表

app = FastAPI(
    title="HR-SaaS Platform API",
    description="人力资源 SaaS 管理平台 API 文档",
    version="1.0.0",
    debug=settings.DEBUG
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
from .core.exceptions import BusinessException, business_exception_handler, general_exception_handler
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 注册 API 路由
from .api.auth import router as auth_router
from .api.users import router as users_router
from .api.projects import router as projects_router
from .api.positions import router as positions_router
from .api.resumes import router as resumes_router
from .api.dashboard import router as dashboard_router
from .api.interview import router as interview_router

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(positions_router, prefix=settings.API_V1_STR)
app.include_router(resumes_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(interview_router, prefix=settings.API_V1_STR)


@app.get("/health", summary="健康检查")
def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "hr-saas-api",
        "version": "1.0.0"
    }


@app.get("/", summary="根路径")
def root():
    return {
        "message": "欢迎使用 HR SaaS API 服务",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
