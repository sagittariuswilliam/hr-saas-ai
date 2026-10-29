# HR-SaaS 人力资源管理系统（开源版）

> 面向小型团队 / 猎头工作室的简历管理 + AI 智能招聘系统。
>
> **两大 AI 能力**：① 简历-JD 智能匹配评分（4 维度打分 + 推荐结论）② AI 异步面试（LLM 出题 → HR 审定 → 候选人 H5 链接作答（支持语音录音作答）→ ASR 转写 → LLM 综合评分报告）。

An open-source HR SaaS for small teams: resume management, AI-powered resume↔job-description matching, and async AI interviews (text or voice answers, auto-scored reports).

**License: MIT**

---

## ✨ 功能一览

| 模块 | 说明 |
|------|------|
| 简历管理 | 上传 PDF/DOCX → 自动解析姓名/电话/履历 → 多维筛选 / 状态流转（投递→面试→offer→入职） |
| AI 匹配分析 | 简历 vs 职位 JD 四维评分：技能 40% / 经验 30% / 学历 20% / 其他 10%，附推荐结论；LLM 异常自动降级为启发式评分 |
| AI 面试（文字） | LLM 按简历+JD 生成面试题与评分要点 → HR 审定改题 → 生成候选人专属链接（72h 有效）→ 逐题作答/断点续答/1 轮追问 → 交卷后 LLM 逐题评分 + 综合报告 |
| AI 面试（语音） | 候选人手机录音作答 → qwen3-asr 转写 → HR 可试听原声（30 天自动清理）→ 同一评分链路 |
| 职位 / 项目 / 用户 | CRUD、角色权限（管理员 / 招聘专员）、密码重置、操作日志 |
| 数据看板 | 简历漏斗、今日面试、平均匹配度、ECharts 图表 |

## 🛠 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy / SQLite（可换 MySQL）/ JWT 鉴权
- **前端**: Vue 3.4 + Vite 5 + Element Plus + Pinia + ECharts + TypeScript
- **AI**: 任意 OpenAI 兼容协议的 LLM 网关（默认配置阿里云百炼 Qwen）；语音转写用 DashScope qwen3-asr-flash（可选）

## 🚀 快速开始

### 1. 后端

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 按需填 LLM_API_KEY / SECRET_KEY
python init_db.py           # 建表 + 创建默认管理员 admin / admin123
uvicorn app.main:app --host 0.0.0.0 --port 8000
# API 文档: http://localhost:8000/docs
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev                 # 开发模式
# 生产: npm run build 后由 nginx 或 python3 -m http.server 托管 dist/
```

### 3. 一键启动（开发演示）

```bash
./start.sh
```

## ⚙️ 关键配置（backend/.env）

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | 默认 `sqlite:///./hr_saas.db`，可换 MySQL 连接串 |
| `SECRET_KEY` | JWT 签名密钥，**生产环境务必更换** |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | OpenAI 兼容 LLM，驱动简历匹配 + 面试出题评分；不配置时匹配评分自动降级为关键词启发式，面试模块不可用 |
| `DASHSCOPE_API_KEY` | 可选，语音作答转写；不配置则语音按钮自动禁用，文字作答不受影响 |
| `UPLOAD_DIR` | 简历原件 / 面试录音存储目录 |

## 📁 目录结构

```
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── api/               # auth / resumes / positions / projects / users / dashboard / interview
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── schemas/           # Pydantic schema
│   │   ├── services/          # llm(匹配评分) / interview_service / asr(语音转写) / resume_parser
│   │   └── core/              # config / security(JWT) / database
│   ├── init_db.py             # 建表 + 种子管理员
│   ├── scripts/cleanup_voice.py  # 面试原声 30 天清理（建议 cron 每日执行）
│   └── requirements.txt
├── frontend/
│   └── src/views/             # login / dashboard / positions / projects / users / resumes / interview
├── deploy/                    # nginx HTTPS 反代模板（语音录音功能需要安全上下文）
├── DESIGN.md / DESIGN-GUIDE.md  # 设计规范（配色/字体/动效 token）
└── start.sh
```

## 🔒 安全与隐私提示

- 候选人面试链接为公开 token 页（16 位随机串 + 72h 过期），报告数据需 HR 登录态才可见
- 面试录音默认 30 天自动删除（`scripts/cleanup_voice.py` 挂 cron）
- 本仓库不包含任何真实简历 / 用户数据；`hr_saas.db`、`uploads/`、`.env` 均在 `.gitignore` 中
- 生产部署请务必：更换 `SECRET_KEY`、修改默认管理员密码、启用 HTTPS（见 `deploy/`）

## 🗺 路线图

- **v1.1**: PDF 扫描件 OCR 解析 / Docker Compose 一键部署
- **v2.0**: MySQL + Redis / 多人协作权限细化 / 实时语音面试官（预研中）

欢迎提 Issue / PR。
