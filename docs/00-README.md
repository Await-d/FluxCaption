# AI 媒体字幕翻译系统 · 项目总览（README）

> 面向：所有角色（PM/FE/BE/DevOps/QA）  
> 版本：v1.1

本项目提供一个**基于 Python FastAPI + Celery 的后端**与**React 19 的前端**，实现对 Jellyfin 媒体库的**自动字幕补齐**与**字幕文件翻译**，并通过 **Ollama** 自动拉取/管理本地大语言模型。支持 **PostgreSQL / MySQL(MariaDB) / SQLite / SQL Server** 多数据库。

---

## 快速开始（最小命令集合）

```bash
# 1) 克隆仓库 & 准备 .env
cp .env.example .env && vi .env

# 2) 启动依赖（任选一个 compose 方案）
docker compose -f docker-compose.yml up -d

# 3) 初始化数据库
alembic upgrade head

# 4) 启动服务
uvicorn app.main:app --reload
celery -A app.workers.celery_app worker -l INFO
celery -A app.workers.celery_app beat -l INFO

# 5) 前端（单独仓库/目录）
pnpm i && pnpm dev
```

---

## 目录导航

- **后端开发指南**：`01-BACKEND.md`
- **前端开发指南（React 19）**：`02-FRONTEND.md`
- **API 契约（OpenAPI 摘要）**：`03-API_CONTRACT.md`
- **数据模型 & 多数据库策略**：`04-DATA_MODEL_AND_DB.md`
- **AI/字幕处理流水线（ASR/MT/写回）**：`05-PIPELINES_ASR_MT_SUBTITLES.md`
- **部署与运维（DevOps）**：`06-DEPLOYMENT_DEVOPS.md`
- **测试与质量（QA）**：`07-TESTING_QA.md`
- **协作规范（Contributing）**：`08-CONTRIBUTING.md`

---

## 关键能力

- 自动扫描 Jellyfin 媒体库，识别**缺失语言**字幕并排队翻译。
- **自动下载**所需的 Ollama 模型；翻译阶段实时进度（SSE）。
- 支持 `.srt/.ass/.vtt` 读写与转换；保留 ASS 样式标签。
- 无字幕媒体：**ASR（faster‑whisper）→ 翻译 → 回写**。
- 多数据库可切换；统一 ORM 与迁移流程。

---

## 技术栈一览

- **后端**：FastAPI、SQLAlchemy 2、Alembic、Celery、httpx、pysubs2、faster-whisper、ffmpeg
- **前端**：React 19、Vite、TypeScript、Tailwind CSS、Radix UI、TanStack Query、Zustand
- **AI/推理**：Ollama（/api/tags、/api/pull、/api/generate）
- **存储**：PostgreSQL / MySQL(MariaDB) / SQLite / SQL Server
- **消息/缓存**：Redis
