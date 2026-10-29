# HR-SaaS 后端服务

人力资源管理系统后端 API 服务，基于 FastAPI 开发。

## 技术栈

- **Python 3.11+**
- **FastAPI 0.100+** - Web 框架
- **SQLAlchemy 2.0** - ORM
- **Pydantic 2.0** - 数据验证
- **python-jose** - JWT 认证
- **Passlib** - 密码加密
- **SQLite**（默认，可换 MySQL）- 数据库
- **OpenAI 兼容 LLM**（默认阿里云百炼 Qwen）- AI 简历匹配评分 / 面试出题与评分
- **DashScope qwen3-asr-flash**（可选）- 面试语音作答转写

## 核心功能

### 1. 用户认证与权限
- JWT Token 认证
- 基于角色的权限控制（ADMIN/HR/MANAGER/EMPLOYEE）
- 密码加密存储

### 2. 用户管理 CRUD
- 创建、编辑、删除用户
- 重置密码
- 分页列表查询
- 支持关键词、角色、状态过滤

### 3. 项目管理
- 招聘项目的增删改查
- 项目状态管理（草稿/招聘中/已关闭/暂停）

### 4. 职位管理
- 职位的增删改查
- 职位状态管理
- 关联到具体项目

### 5. 简历管理
- 文件上传（支持 PDF/Word/TXT）
- 简历文本提取
- AI 结构化解析（调用豆包大模型）
- 简历状态追踪

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # 应用入口
│   ├── config.py                # 配置管理
│   ├── database.py              # 数据库连接
│   ├── models/                  # 数据库模型
│   │   ├── __init__.py
│   │   └── models.py            # 8张核心表
│   ├── schemas/                 # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   └── resume.py
│   ├── api/                     # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证
│   │   ├── users.py             # 用户管理
│   │   ├── projects.py          # 项目/职位
│   │   └── resumes.py           # 简历
│   ├── core/                    # 核心功能
│   │   ├── __init__.py
│   │   ├── security.py          # 认证安全
│   │   └── exceptions.py        # 异常处理
│   └── services/                # 业务服务
│       ├── __init__.py
│       └── resume_parser.py     # 简历解析
├── scripts/
│   └── init_db.py               # 数据库初始化
├── requirements.txt             # 依赖包
├── .env.example                 # 环境变量示例
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等信息
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

默认管理员账号:
- 用户名: `admin`
- 密码: `admin123`

### 4. 启动服务

```bash
python -m app.main
```

或使用 uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口列表

### 认证接口
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息
- `POST /api/auth/refresh` - 刷新 Token

### 用户管理
- `GET /api/users` - 用户列表（分页）
- `POST /api/users` - 创建用户
- `GET /api/users/{id}` - 获取用户详情
- `PUT /api/users/{id}` - 更新用户
- `DELETE /api/users/{id}` - 删除用户
- `POST /api/users/{id}/reset-password` - 重置密码

### 项目管理
- `GET /api/projects` - 项目列表（分页）
- `POST /api/projects` - 创建项目
- `GET /api/projects/{id}` - 项目详情
- `PUT /api/projects/{id}` - 更新项目
- `DELETE /api/projects/{id}` - 删除项目

### 职位管理
- `GET /api/jobs` - 职位列表（分页）
- `POST /api/jobs` - 创建职位
- `GET /api/jobs/{id}` - 职位详情
- `PUT /api/jobs/{id}` - 更新职位
- `DELETE /api/jobs/{id}` - 删除职位

### 简历管理
- `GET /api/resumes` - 简历列表（分页）
- `POST /api/resumes/upload` - 上传简历文件
- `GET /api/resumes/{id}` - 简历详情
- `PUT /api/resumes/{id}` - 更新简历
- `DELETE /api/resumes/{id}` - 删除简历
- `POST /api/resumes/{id}/parse` - AI 解析简历
- `GET /api/resumes/{id}/content` - 获取简历内容

## 数据库表结构

共 8 张核心表:

1. `users` - 用户表
2. `projects` - 招聘项目表
3. `jobs` - 职位表
4. `resumes` - 简历表
5. `match_results` - AI 匹配结果表
6. `status_logs` - 状态变更日志表
7. `operation_logs` - 操作日志表
8. *（关联关系已定义）*

## 统一响应格式

### 成功响应
```json
{
    "code": 200,
    "message": "success",
    "data": {}
}
```

### 错误响应
```json
{
    "code": 400,
    "message": "错误信息",
    "detail": "详细说明"
}
```

## 开发规范

- 遵循 PEP8 代码规范
- 使用类型注解
- 所有 API 都有完整的文档字符串
- 异常统一处理，返回标准格式

## 注意事项

1. 生产环境中务必修改 `SECRET_KEY`
2. 配置 CORS 允许的域名，不要使用 `*`
3. 数据库密码使用强密码
4. 豆包 API 密钥需要在火山引擎官网申请
5. 文件上传目录需要设置正确的权限

## License

MIT
