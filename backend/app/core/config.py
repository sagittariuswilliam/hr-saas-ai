from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置 - 完整版本"""
    ENVIRONMENT: str = "production"
    
    # 项目基础配置
    PROJECT_NAME: str = "HR-SaaS Platform"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # 数据库配置 - 使用 SQLite
    DATABASE_URL: str = "sqlite:///./hr_saas.db"
    
    # JWT 配置
    SECRET_KEY: str = "hr-saas-secret-key-change-in-production-2024"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1天
    
    # CORS 配置
    CORS_ORIGINS: str = "*"
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # 阿里 Qwen 大模型 API（AI 匹配分析 / AI 面试评分用）
    # OpenAI 兼容协议（/chat/completions）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen3.8-flash"
    # 视觉模型（可选）
    LLM_VL_MODEL: str = "qwen-vl-plus"

    # 语音转写（AI 面试语音作答）：DashScope 百炼 qwen3-asr-flash
    # 未配置 DASHSCOPE_API_KEY 时语音作答功能自动禁用，文字作答不受影响
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_ASR_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


settings = Settings()
