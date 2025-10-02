# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本代码库中工作时提供指导。

## 核心开发原则

**🚫 禁止 Mock 方案**
- 所有操作必须使用真实数据
- 所有监控数据必须来自真实系统指标
- 所有终端操作必须是真实的容器执行会话

**🚫 禁止简化方案**
- 实现完整的错误处理和边缘情况处理
- 实现完整的性能优化和缓存机制
- 实现完整的安全验证和权限控制

**🚫 禁止临时方案**
- 所有实现必须达到生产级质量
- 所有代码必须可长期维护
- 所有架构必须支持未来扩展需求

## 项目概述

FluxCaption 是一个为 Jellyfin 媒体库设计的 AI 驱动字幕翻译系统。系统能自动检测缺失的字幕语言，对没有字幕的媒体执行 ASR（自动语音识别），并使用本地 LLM 模型（通过 Ollama）翻译字幕。

**技术栈：**
- 后端：Python FastAPI + Celery + SQLAlchemy 2 + Alembic
- 前端：React 19 + Vite + TypeScript + Tailwind CSS + Radix UI
- AI/推理：Ollama（本地 LLM 模型）
- 存储：PostgreSQL / MySQL / SQLite / SQL Server（多数据库支持）
- 消息队列：Redis（Celery broker）
- 媒体集成：Jellyfin API

## 常用命令

### 后端开发

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 启动 FastAPI 服务器（开发模式，自动重载）
uvicorn app.main:app --reload

# 启动 Celery worker
celery -A app.workers.celery_app worker -l INFO

# 启动 Celery beat 调度器
celery -A app.workers.celery_app beat -l INFO

# 运行测试
pytest -m unit                              # 仅单元测试
pytest -m "integration and not slow"        # 集成测试
```

### 前端开发

```bash
# 安装依赖
pnpm i

# 启动开发服务器
pnpm dev

# 生产构建
pnpm build
```

### Docker Compose

```bash
# 启动所有服务
docker compose -f docker-compose.yml up -d

# 环境配置
cp .env.example .env
# 编辑 .env 填入必需的值（JELLYFIN_API_KEY, OLLAMA_BASE_URL 等）
```

## 架构概览

### 后端进程拓扑

后端由多个独立进程组成：

1. **FastAPI API 服务器**：处理 REST 端点和 SSE（Server-Sent Events）实时进度更新
2. **Celery Workers**：在独立队列中执行三种类型的任务：
   - `scan`：扫描 Jellyfin 库查找缺失的字幕语言
   - `translate`：翻译现有字幕文件
   - `asr_then_translate`：提取音频 → ASR → 翻译（用于无字幕媒体）
3. **Celery Beat**：定时任务（周期性扫描、清理）
4. **Redis**：Celery broker 和缓存；也用于从 worker 转发 SSE 事件
5. **Database**：SQLAlchemy 2 同步引擎（多数据库支持）
6. **Ollama**：独立服务，用于 LLM 模型管理和推理
7. **Jellyfin**：外部媒体服务器集成

### 后端目录结构

```
backend/
  app/
    main.py                          # FastAPI 应用入口
    core/                            # 配置、数据库、日志、事件
    api/routers/                     # health、models、jellyfin、jobs、upload
    services/                        # 业务逻辑层
      jellyfin_client.py             # Jellyfin API 集成
      ollama_client.py               # Ollama API（pull/generate）
      subtitle_service.py            # 字幕解析/翻译
      asr_service.py                 # faster-whisper 集成
      writeback.py                   # 上传到 Jellyfin 或侧载文件
      detector.py                    # 缺失语言检测
      prompts.py                     # LLM 提示词模板
    models/                          # SQLAlchemy ORM 模型
      types.py                       # 自定义类型（GUID）
      translation_job.py
      media_asset.py
      subtitle.py
      model_registry.py
      setting.py
      base.py
    schemas/                         # Pydantic 请求/响应模式
    workers/
      celery_app.py                 # Celery 配置
      tasks.py                      # 任务定义
  migrations/                       # Alembic 数据库迁移
```

### 前端架构

- **状态管理**：TanStack Query 管理服务器状态，Zustand 管理 UI 状态
- **实时更新**：EventSource (SSE) 用于任务进度流式传输
- **表单**：react-hook-form + zod 验证
- **路由**：主要页面：Dashboard、Models、Library、Jobs、Translate、Settings
- **样式**：Tailwind CSS 支持暗色模式，Radix UI 提供无障碍组件

### 多数据库策略

系统使用统一方法支持 PostgreSQL、MySQL、SQLite 和 SQL Server：

- **主键**：GUID 通过 TypeDecorator 存储为 `CHAR(36)`，实现跨数据库兼容
- **枚举**：存储为 `String` 并使用 Pydantic 验证（避免数据库特定的枚举类型）
- **集合**：媒体语言使用子表；任务目标语言使用 JSON 列
- **时间戳**：始终使用 UTC 存储，使用 `DateTime(timezone=True)`
- **迁移**：Alembic 脚本避免方言特定功能
- **幂等性**：服务层使用"先检查再写入"而非方言特定的 UPSERT

### 数据模型

**核心表：**
- `translation_jobs`：任务状态、源/目标语言、进度、错误日志
- `media_assets`：Jellyfin 项目元数据、时长、校验和
- `media_audio_langs` / `media_subtitle_langs`：语言可用性（子表以支持查询）
- `subtitles`：字幕文件注册表，包含存储位置、格式、来源（asr/mt/manual）

**索引**：任务查询的 `(status, created_at)` 关键索引，语言查找的 `asset_id` 和 `lang` 索引

## 处理管线

### 翻译管线阶段

1. **模型准备**：检查 Ollama 模型可用性；如缺失则通过 `/api/pull` 自动拉取
2. **输入检测**：
   - 已有字幕 → 直接翻译
   - 无字幕 → 先执行 ASR
3. **ASR**（可选）：FFmpeg 音频提取 → faster-whisper → SRT/VTT 输出
4. **翻译 (MT)**：
   - 使用 pysubs2 解析字幕文件
   - 剥离 ASS 格式标签（如 `{\i1}`）
   - 通过 Ollama `/api/generate` 翻译纯文本
   - 将格式标签恢复到翻译文本
5. **后处理**：标点符号规范化、行长度控制、标签恢复
6. **回写**：通过 API 上传到 Jellyfin 或写入侧载文件
7. **注册**：更新 `subtitles` 表并刷新 `media_subtitle_langs`

### ASR 详情（faster-whisper）

- 输入：16kHz 单声道 WAV（FFmpeg 提取）
- 长音频：分段处理带重叠
- 输出：带时间戳的 SRT/VTT
- 性能：支持 8 位量化、GPU/CPU 自适应

### 翻译详情（Ollama）

- **模型拉取**：`/api/pull` 带流式进度（status/completed/total）转发到 SSE
- **推理**：`/api/generate`（或 `/api/chat`）
- **提示词策略**：
  - System：专业字幕翻译；不增删内容
  - User：源语言、目标语言、纯文本输入
  - Output：仅翻译（无时间戳/编号）
- **批量处理**：可合并 N 行以提高 token 效率和上下文一致性

### 字幕格式处理

- **库**：pysubs2 用于读写 `.srt/.ass/.vtt`
- **ASS 标签**：保留格式如 `{\i1}`、定位、轮廓样式
- **处理策略**：
  1. 解析 → 剥离标签 → 提取纯文本
  2. 翻译纯文本
  3. 将标签恢复到翻译文本
  4. 根据目标语言规则重排行宽/换行

## 关键技术细节

### FastAPI + 同步 SQLAlchemy

- Web 层是异步的，但数据库操作使用**同步 SQLAlchemy**
- 数据库调用通过 `run_in_threadpool` 包装以保证兼容性
- 支持多种数据库驱动，无异步复杂性

### Celery 配置

- 关键设置：`acks_late`、`task_reject_on_worker_lost`、`worker_max_tasks_per_child`
- 防止任务丢失和内存膨胀
- Worker 并发度针对 GPU/CPU 资源竞争进行调优

### SSE 进度流式传输

- Worker 将事件发布到 Redis
- API 服务器订阅并通过 EventSource 转发到前端
- 事件格式：`{ phase, status, completed, total }`
- 阶段：`pull → asr → mt → post → writeback`

### JellyfinClient 集成

- `GET /Items?Fields=MediaStreams`：获取字幕/音频语言信息
- `POST /Items/{itemId}/Subtitles`：上传字幕，包含 Data/Format/Language
- 侧载模式：写入与媒体文件相同的目录（可选）

### 数据库会话管理

```python
# app/core/db.py 模式
engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except:
        s.rollback()
        raise
    finally:
        s.close()
```

## 配置与环境

### 必需的环境变量

```ini
DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/ai_subs
DB_VENDOR=postgres  # or mysql, sqlite, mssql
REDIS_URL=redis://redis:6379/0
JELLYFIN_BASE_URL=http://jellyfin:8096
JELLYFIN_API_KEY=xxxx
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_KEEP_ALIVE=30m
DEFAULT_MT_MODEL=qwen2.5:7b-instruct
ASR_MODEL=medium
REQUIRED_LANGS=zh-CN,en,ja
WRITEBACK_MODE=upload  # or sidecar
```

### 关键约定

- **时区**：所有时间戳均以 UTC 存储
- **语言代码**：BCP-47 格式（由 Pydantic 验证）
- **术语表/词汇表**：可选的 JSON 配置；在翻译前后应用
- **格式检测**：根据文件扩展名自动检测字幕格式

## 代码风格与贡献

### Python（后端）

- 格式化：ruff + black
- 类型检查：关键模块使用 mypy
- 提交格式：Conventional Commits（`feat:`、`fix:`、`docs:`）

### TypeScript（前端）

- Linter：eslint
- 格式化：prettier
- 提交格式：Conventional Commits

### Pull Request

- 关联相关 issue
- 包含变更描述和风险评估
- API 变更：更新 `docs/03-API_CONTRACT.md`
- 数据库变更：包含 Alembic 迁移脚本和回滚评估

## 测试策略

### 测试金字塔

- **单元测试**：字幕解析/保存、提示词生成、OllamaClient 流式传输、DB CRUD
- **集成测试**：Ollama + Jellyfin + Redis + DB 集成
- **端到端测试**：前端任务创建 → SSE 进度 → 回写验证

### 多数据库 CI 矩阵

针对 PostgreSQL、MySQL、SQLite、SQL Server 进行测试：
- 迁移成功（`alembic upgrade head`）
- CRUD 和分页一致性
- 缺失语言检测查询正确性

### 典型测试用例

1. 手动 SRT 上传 → 翻译 → 预览 → 上传到 Jellyfin
2. 无字幕媒体 → ASR → 翻译 → 上传
3. 缺失模型 → 自动 `/api/pull` → 翻译 → 成功
4. 侧载回写 → Jellyfin 自动检测
5. 长音频 → 正确分段 → 连续时间轴

## 性能优化

### 后端

- Worker 并发和 `prefetch_multiplier` 调优（避免 GPU/ASR 竞争）
- ASR 大文件分段；受控内存的批量翻译
- 带速率限制的 Jellyfin 重试逻辑
- Ollama `/api/pull` 心跳检测

### 前端

- 路由级代码分割
- TanStack Query 智能缓存和后台刷新
- 列表虚拟化（媒体库、任务队列）
- Memo/selector 避免大对象重渲染

## 部署注意事项

- **进程**：api（Uvicorn）、worker（Celery 多副本）、beat（单实例）、ollama（独立容器）
- **监控**：结构化 JSON 日志，包含 `job_id、phase、duration、media_id、model`
- **指标**：任务吞吐量/延迟/失败率、模型拉取时间、ASR/MT 阶段分布
- **安全**：最小 Jellyfin API key 权限；生产环境内部网络；API 可选 JWT/Key 认证
- **回滚**：带标签的容器镜像；Alembic `downgrade`（谨慎使用）

## 文档结构

- `docs/00-README.md`：项目概览和快速开始
- `docs/01-BACKEND.md`：后端架构和开发
- `docs/02-FRONTEND.md`：前端架构和开发
- `docs/03-API_CONTRACT.md`：OpenAPI 端点摘要
- `docs/04-DATA_MODEL_AND_DB.md`：数据库模式和多数据库策略
- `docs/05-PIPELINES_ASR_MT_SUBTITLES.md`：AI 管线详情
- `docs/06-DEPLOYMENT_DEVOPS.md`：部署和运维
- `docs/07-TESTING_QA.md`：测试策略和质量保证
- `docs/08-CONTRIBUTING.md`：协作和代码标准

## 文件创建策略

**🚫 未经明确用户许可，禁止创建文档文件**
- 除非用户明确要求，否则不要创建任何 `.md` 文件（文档、README、指南等）
- 不要主动创建 `docs/` 文件
- 始终先询问用户："是否应为 [目的] 创建文档文件？"

**🚫 未经明确用户许可，禁止创建测试文件**
- 除非用户明确要求，否则不要创建测试文件（`test_*.py`、`*.test.ts`、`*.spec.ts` 等）
- 不要主动创建测试 fixtures 或测试数据文件
- 始终先询问用户："是否应为 [功能] 创建测试？"

**✅ 何时需要请求许可**
- 创建任何新的 `.md` 文件之前
- 在 `tests/`、`__tests__/` 或类似目录中创建任何测试文件之前
- 创建示例文件或示例代码文件之前

**✅ 无需询问即可创建的内容**
- 作为实际应用程序一部分的源代码文件（`.py`、`.ts`、`.tsx` 等）
- 应用程序运行所需的配置文件
- 实现数据库更改时的数据库迁移文件
- 构建过程中的构建产物或生成的代码
