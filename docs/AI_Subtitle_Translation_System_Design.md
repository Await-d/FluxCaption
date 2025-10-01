
# AI 媒体字幕翻译系统 · 设计文档（Python 后端 & React 19 前端 · 多数据库版）

> 版本：v1.1 • 状态：可实施 • 作者：系统设计生成 • 目标读者：后端/前端/DevOps/QA

---

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 整体架构总览](#2-整体架构总览)
  - [2.1 组件清单](#21-组件清单)
  - [2.2 数据/控制流](#22-数据控制流)
- [3. 技术选型与理由](#3-技术选型与理由)
  - [3.1 后端框架](#31-后端框架)
  - [3.2 任务队列](#32-任务队列)
  - [3.3 多数据库支持与兼容策略](#33-多数据库支持与兼容策略)
  - [3.4 字幕/音视频处理](#34-字幕音视频处理)
  - [3.5 LLM 推理（Ollama）](#35-llm-推理ollama)
  - [3.6 前端栈（React 19）](#36-前端栈react-19)
  - [3.7 通信协议（REST + SSE/WS）](#37-通信协议rest--ssews)
  - [3.8 部署依赖](#38-部署依赖)
- [4. 技术路线（MVP → 迭代）](#4-技术路线mvp--迭代)
- [5. 数据模型与数据库设计](#5-数据模型与数据库设计)
  - [5.1 关键建模与跨库策略](#51-关键建模与跨库策略)
  - [5.2 表结构摘要](#52-表结构摘要)
  - [5.3 索引与查询模式](#53-索引与查询模式)
  - [5.4 迁移与版本控制](#54-迁移与版本控制)
  - [5.5 驱动矩阵与连接字符串](#55-驱动矩阵与连接字符串)
- [6. 核心服务设计与实现要点](#6-核心服务设计与实现要点)
  - [6.1 JellyfinClient（媒体库集成）](#61-jellyfinclient媒体库集成)
  - [6.2 SubtitleService（字幕读写/格式）](#62-subtitleservice字幕读写格式)
  - [6.3 ASRService（无字幕 → 语音转写）](#63-asrservice无字幕--语音转写)
  - [6.4 MTService / OllamaClient（翻译/模型管理）](#64-mtservice--ollamaclient翻译模型管理)
  - [6.5 WritebackService（回写 Jellyfin / 侧车）](#65-writebackservice回写-jellyfin--侧车)
  - [6.6 Detector（缺失语言检测）](#66-detector缺失语言检测)
  - [6.7 Job Orchestrator（编排/进度）](#67-job-orchestrator编排进度)
- [7. API 契约（OpenAPI 摘要）](#7-api-契约openapi-摘要)
- [8. 进程与队列拓扑](#8-进程与队列拓扑)
- [9. 字幕质量保障与后处理](#9-字幕质量保障与后处理)
- [10. Jellyfin 集成细节与安全](#10-jellyfin-集成细节与安全)
- [11. 前端对接说明（React 19）](#11-前端对接说明react-19)
- [12. 配置清单（.env）](#12-配置清单env)
- [13. 部署与运维](#13-部署与运维)
- [14. 测试策略与覆盖](#14-测试策略与覆盖)
- [15. 风险清单与缓解](#15-风险清单与缓解)
- [16. 里程碑与交付物](#16-里程碑与交付物)
- [附录 A：关键代码片段](#附录-a关键代码片段)
- [附录 B：目录结构建议](#附录-b目录结构建议)

---

## 1. 背景与目标

构建一个**AI 翻译系统**，同时支持**字幕文件翻译**与**Jellyfin 媒体库自动补齐所需字幕**。系统要求：

- **前端**：React 19，科技简约现代风格，响应式、深色模式、进度可视化。
- **后端**：Python（FastAPI + Celery），**多数据库**（PostgreSQL / MySQL(MariaDB) / SQLite / SQL Server）可切换。
- **AI 能力**：集成 **Ollama**，若目标模型缺失则**自动下载**并缓存；无文本字幕时走 **ASR（faster‑whisper）**。
- **Jellyfin 集成**：读取媒体库，识别已有字幕语言；对缺失语言**批量自动翻译**并**回写**（优先调用 Jellyfin Subtitle API，上线后可选侧车写入）。
- **字幕文件**：支持 `.srt / .ass / .vtt`，保留时间轴与样式（ASS 标签）。

---

## 2. 整体架构总览

### 2.1 组件清单

- **React 19 前端**（Vite + TypeScript + Tailwind + Radix UI + TanStack Query）
- **FastAPI API 网关**（REST + SSE/WS）
- **Celery Workers**（翻译、转写、扫描、后处理）
- **Ollama Server**（本地/远程）
- **Jellyfin Server**（现有媒体库）
- **数据库**（Postgres / MySQL / SQLite / SQL Server）
- **Redis**（Celery broker & cache）

### 2.2 数据/控制流

```
┌───────────────────────┐     HTTPS      ┌──────────────────────────┐
│  React 19 Frontend    ├────────────────>  FastAPI (REST + SSE)    │
│  - Upload/Preview     │                │  · Orchestrator          │
│  - Library View       │                └───────────┬──────────────┘
└─────────┬─────────────┘                            │
          │ 进度/日志 (SSE/WS)                       │
          │                                          │
          │                      ┌───────────────────▼───────────────────┐
          │                      │         Celery Workers                │
          │                      │  · Translate · ASR · Scan · Writeback │
          │                      └───────────────┬─────────────┬────────┘
          │                                      │             │
     ┌────▼────┐                           ┌─────▼─────┐  ┌────▼──────┐
     │  Redis  │                           │  Ollama   │  │  Jellyfin │
     │ Broker  │                           │  Server   │  │  Server   │
     └────┬────┘                           └─────┬─────┘  └────┬──────┘
          │ DB/Cache                             │            │
     ┌────▼──────────────┐                       │            │
     │  Postgres/MySQL/  │                       │            │
     │  SQLite/SQLServer │                       │            │
     └───────────────────┘                模型拉取/生成   Items/Upload
```

---

## 3. 技术选型与理由

### 3.1 后端框架

- **FastAPI**：高性能异步框架，OpenAPI 自动化、依赖注入、Pydantic 模型友好。
- **SQLAlchemy 2.x（同步 Engine）**：跨数据库统一 ORM，配合线程池避免阻塞事件循环。
- **Alembic**：数据库迁移，保证各环境 schema 一致。
- **httpx**：异步 HTTP 客户端，对接 Ollama 与 Jellyfin。

### 3.2 任务队列

- **Celery + Redis**：成熟稳定的任务编排，支持重试/定时/并发控制；与 Python 生态良好。
- **Celery Beat**：定时任务（如定期扫描 Jellyfin 库、模型健康检查）。

### 3.3 多数据库支持与兼容策略

- 统一 ORM 层；**避免**方言专属类型（PG `ARRAY` 等）。
- **GUID → CHAR(36)**，自定义 TypeDecorator，跨库一致。
- **JSON 列**存储可变/数组数据（SQLite/MSSQL 退化为 TEXT + 序列化）。
- 高频过滤的数组/集合信息（如媒体已有语言）→ **子表**建模并索引。
- 统一 UTC 时间；应用层处理时区。

**可用数据库与驱动**：

| 数据库 | 驱动 | 连接 URL 示例 |
|---|---|---|
| PostgreSQL 13+ | `psycopg[binary]` | `postgresql+psycopg://user:pass@host:5432/ai_subs` |
| MySQL 8+/MariaDB 10.6+ | `pymysql`/`mysqlclient` | `mysql+pymysql://user:pass@host:3306/ai_subs` |
| SQLite 3.35+ | 内置 | `sqlite:///./ai_subs.db` |
| SQL Server 2019+ | `pyodbc` | `mssql+pyodbc:///?odbc_connect=DRIVER=ODBC+Driver+18+for+SQL+Server;SERVER=...` |

### 3.4 字幕/音视频处理

- **pysubs2**：读写 `.srt/.ass/.vtt`，保留 ASS 样式标签，适合“文本替换式”翻译。
- **FFmpeg / ffmpeg-python**：抽取音轨、转码为 ASR 友好格式（16kHz mono WAV）。
- **faster‑whisper**：ASR（CTranslate2 推理），速度与内存占用优于官方 Whisper 实现。

### 3.5 LLM 推理（Ollama）

- 统一通过 **Ollama HTTP API**：
  - `/api/tags` 列出本地模型；
  - `/api/pull` 动态下载模型（流式进度）；
  - `/api/generate` 或 `/api/chat` 进行翻译推理。
- 通过 **SSE** 将 `pull` 进度/翻译进度实时推送给前端。

### 3.6 前端栈（React 19）

- **Vite + React 19 + TypeScript**：开发体验与性能兼顾。
- **TanStack Query**：请求缓存与状态；**Zustand** 管理本地 UI 状态。
- **Tailwind CSS + Radix UI**：科技简约/可访问性；暗色模式与响应式。
- **react-hook-form + zod**：表单校验；**i18next**：界面国际化。

### 3.7 通信协议（REST + SSE/WS）

- REST：配置、浏览、任务提交、结果查询。
- **SSE**：任务进度/日志推送（更易穿透代理，服务端实现简单）。
- WS 作为备选（若需要双向交互）。

### 3.8 部署依赖

- **Docker Compose**：便于一体化启动（API/Worker/Beat/DB/Redis/Ollama）。
- GPU 可选：容器启用 NVIDIA 运行时或 K8s Device Plugin。

---

## 4. 技术路线（MVP → 迭代）

1. **MVP**：手动字幕上传 → 翻译 → 下载/预览；Ollama 自动拉取；SRT/ASS/VTT 支持。
2. **Jellyfin 只读**：读取库与 `MediaStreams`，识别缺失语言 → 生成外部字幕（侧车）。
3. **Jellyfin 回写**：调用 Subtitle API 上传字幕至指定 Item。
4. **无字幕链路**：音轨抽取 → faster‑whisper → SRT → 翻译 → 回写。
5. **体验增强**：术语表与禁译词、对照预览、任务队列/失败重试、批量/定时扫描。

---

## 5. 数据模型与数据库设计

### 5.1 关键建模与跨库策略

- **主键**：`GUID(CHAR(36))`；应用层 `uuid.UUID`；ORM 转换。
- **枚举**：`String(16/50)` + Pydantic 校验，避免方言 Enum 差异。
- **数组/集合**：媒体语言用**子表**；任务目标语言用 **JSON**。
- **时间**：`DateTime(timezone=True)`，统一存 UTC。
- **幂等**：业务层“先查后写”或 `UPDATE→INSERT`，避免不同数据库 UPSERT 语法差异。

### 5.2 表结构摘要

**translation_jobs**（任务表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | GUID | 主键 |
| item_id | String(64) | Jellyfin ItemId（可空） |
| source_type | String(16) | `subtitle|audio|media` |
| source_path | String(1024) | 本地手工路径（可空） |
| source_lang | String(20) | BCP‑47 或 `auto` |
| target_langs | JSON | 目标语言数组 |
| model | String(100) | 使用的 Ollama 模型名 |
| status | String(16) | `queued/running/success/failed/canceled` |
| progress | Float | 0–100 |
| error | Text | 失败原因 |
| created_at/started_at/finished_at | DateTime | UTC |

**media_assets**（媒体元数据）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | GUID | 主键 |
| jellyfin_item_id | String(64) | 唯一 |
| library_id | String(64) | 所属库 |
| path | String(1024) | 可选（仅 sidecar 模式需要） |
| duration | Integer | 秒 |
| has_pgs | Boolean | 是否存在图像字幕 |
| checksum | String(64) | 可选 |
| updated_at | DateTime | |

**media_audio_langs / media_subtitle_langs**（子表，语言集合）  
`asset_id(GUID, FK) + lang(String(20))` 带索引。

**subtitles**（生成/登记的字幕）  
`id, item_id, lang, format, storage(fs|s3|jellyfin), path_or_url, origin(asr|mt|manual), checksum, created_at`。

**settings/model_registry**：配置与模型本地状态。

### 5.3 索引与查询模式

- `translation_jobs(status, created_at)`：队列/监控常用。
- `media_assets(jellyfin_item_id)`：唯一检索。
- 子表 `media_*_langs(asset_id, lang)`：按语言过滤。
- 大规模“缺失语言”筛查：`NOT EXISTS` 子查询 + 覆盖索引。

### 5.4 迁移与版本控制

- **Alembic**：单线迁移。
- 迁移脚本禁止使用方言类型，必要时 `if DB_VENDOR == "mssql": ...` 分支处理索引名长度等差异。
- CI 做多数据库矩阵验证。

### 5.5 驱动矩阵与连接字符串

详见 [3.3](#33-多数据库支持与兼容策略)。

---

## 6. 核心服务设计与实现要点

### 6.1 JellyfinClient（媒体库集成）

**能力**：
- 列出库/Items，**请求字段包含 `MediaStreams`** 以便识别音轨与字幕的语言。
- 上传字幕到指定 Item：`Items/{itemId}/Subtitles`（体内含 `Data/Format/Language/IsForced/IsHearingImpaired`）。
- 侧车模式：当选择写入 FS 时按 `Title.<lang>.srt` 等约定命名。

**要点**：
- 采用 token（`X-Emby-Token`）鉴权。
- 超时与重试策略，429/5xx 退避。
- 抽象“库扫描器”：按库分页拉取 Items，构建 `media_assets` 与语言子表。

### 6.2 SubtitleService（字幕读写/格式）

**能力**：
- 加载与保存 `.srt/.ass/.vtt`；自动格式识别。
- 仅替换文本，保留时间轴与 ASS 标签（如 `{\i1}`、位置等）。
- 可选“合并/切分”策略（按时长/标点/最大行长）。

**要点**：
- 正规化：全角/半角、空白、标点。
- 中/日/英 **行长与换行** 规则不同，按目标语言选择策略。
- ASS 风格：仅变更 `line.text`，不触及样式定义。

### 6.3 ASRService（无字幕 → 语音转写）

**能力**：
- 使用 **FFmpeg** 抽取音轨（优选原语种音轨）。
- **faster‑whisper** 转写输出 SRT/VTT（含起止时间）。

**要点**：
- 推理参数：`compute_type="auto"`；多线程/批量段处理。
- 长音频分段：基于静音检测或固定窗口 + 重叠，确保时间轴稳定。
- 资源守护：CPU/GPU 占用上限；大文件分块。

### 6.4 MTService / OllamaClient（翻译/模型管理）

**能力**：
- **ensure_model**：若本地无指定模型，调用 `/api/pull` 下载并将**进度流**转发给 SSE。
- **generate/chat**：以系统提示 + 用户模板约束“仅翻译文本，不修改时间戳/不追加内容”。

**提示词原则**：
- 严格“只翻译，不解释”；
- 保留人名/术语（可选术语表）；
- 目标语言自然化标点。

### 6.5 WritebackService（回写 Jellyfin / 侧车）

- **首选**：Jellyfin Subtitle API 上传（返回码校验，异常回滚）。
- **备选**：同目录侧车写入（编码 UTF‑8-BOM 可选；文件事件触发 Jellyfin 扫描）。
- 上传后更新 `subtitles` 表并与 `media_subtitle_langs` 同步。

### 6.6 Detector（缺失语言检测）

算法纲要：
1. 获取目标语言集合 `required_langs`（全局或库覆盖）。
2. 对每个 `media_asset`：
   - `existing = {subtitle_langs} ∪ {ASR 可行条件}`
   - `missing = required_langs - existing`
3. 若 `missing` 非空：为每个目标语言创建 `translation_job`；优先选择源字幕（最近似语种），无则走 ASR 流。

### 6.7 Job Orchestrator（编排/进度）

- 队列：`scan`、`translate`、`asr_then_translate`。
- 阶段进度：`pull → asr → mt → post → writeback`，向 SSE 推送结构化事件：
```json
{ "phase": "pull", "status": "downloading", "completed": 123456, "total": 999999 }
```

---

## 7. API 契约（OpenAPI 摘要）

**模型管理**
- `GET /api/models` → 本地模型列表
- `POST /api/models/pull` `{ "name": "qwen2.5:7b-instruct" }`
- `DELETE /api/models/{name}`

**Jellyfin**
- `GET /api/jellyfin/items?parentId=&fields=MediaStreams&types=Movie,Episode&page=1`
- `POST /api/scan` `{ "libraryId": "...", "targets": ["zh-CN","en"] }`

**任务**
- `POST /api/jobs/translate`
```json
{
  "source": {"type":"subtitle|audio|media", "pathOrItemId":"..."},
  "sourceLang":"auto|en|zh-CN",
  "targets":["zh-CN"],
  "format":"srt|ass|vtt",
  "writeback":"upload|sidecar",
  "model":"llama3:8b"
}
```
- `GET /api/jobs/{id}` → 状态/日志
- **SSE** `GET /api/jobs/{id}/events` → 进度事件流

**上传（手动翻译）**
- `POST /api/upload/subtitle` → 返回文件句柄供后续翻译使用

---

## 8. 进程与队列拓扑

- **API**：Uvicorn 多 worker；DB 操作通过线程池执行同步 ORM。
- **Workers**：按类型分队列；可设置**并发与速率限制**（防止 GPU/CPU 争用）。
- **Beat**：定时扫描 Jellyfin、清理临时文件、模型健康检查。
- **Redis**：Broker；必要时启用持久化（AOF）。
- **Ollama**：独立容器，模型存储卷挂载。

Celery 关键配置：`acks_late=true`、`task_reject_on_worker_lost=true`、`worker_max_tasks_per_child` 防止内存膨胀。

---

## 9. 字幕质量保障与后处理

- **规范化**：空白/全角半角/引号/省略号统一。
- **断句/合并**：按标点/最大字符数/时间间隔智能切分。
- **行宽控制**：中日语 12–16 字/行、英语 ~42–50 字符/行（可配置）。
- **多语标点**：中英转译时切换 `，。！？` 与 `,.!?`。
- **术语表/禁译词**：可选 JSON 词典；翻译前/后规则校验。
- **质量度量**：段落级合规检查、正则规则、人工抽检清单。

---

## 10. Jellyfin 集成细节与安全

- **读取**：`Items` 接口请求 `Fields=MediaStreams`，以获取字幕/音轨语言（`Type=Subtitle/Audio`）。
- **回写**：`Items/{itemId}/Subtitles` 上传，包含 `Data/Format/Language` 等；由 Jellyfin 统一显示名与语言标识。
- **侧车**：写入 `Title.<lang>.srt`、`Title.<lang>.ass` 等；Jellyfin 自动识别（可能受客户端/版本影响）。
- **权限**：使用专用 API Key，最小权限原则；上传需写权限。
- **速率限制**：对 Jellyfin 请求加并发/速率阈值。

---

## 11. 前端对接说明（React 19）

**页面与功能**：
1. **仪表盘**：队列状态、GPU/CPU 使用、模型拉取进度。
2. **模型管理**：搜索/拉取/删除、默认模型设置；显示 `pull` 进度。
3. **媒体库**：按库/剧集/季/条目浏览，显示字幕语言矩阵；一键补齐缺失语言。
4. **手动翻译**：上传字幕文件 → 选择源/目标 → 预览对照（时间轴锁定）。
5. **任务页**：任务详情、日志、阶段进度条、失败重试。

**技术要点**：
- **TanStack Query**：缓存与轮询；结合 **SSE** 订阅实时进度（以 `EventSource` 实现）。
- **组件库**：Radix UI 原子组件 + Tailwind 语义化 class。
- **主题**：暗色为默认，系统主题跟随；组件支持 `prefers-color-scheme`。
- **错误处理**：全局 `ErrorBoundary`，Toast 告警重试。

---

## 12. 配置清单（.env）

```ini
# API / Infra
API_BASE_URL=http://0.0.0.0:8000
REDIS_URL=redis://redis:6379/0

# Database (choose one)
DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/ai_subs
DB_VENDOR=postgres            # postgres | mysql | sqlite | mssql
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10

# Jellyfin
JELLYFIN_BASE_URL=http://jellyfin:8096
JELLYFIN_API_KEY=xxxxxx

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
DEFAULT_MT_MODEL=qwen2.5:7b-instruct
OLLAMA_KEEP_ALIVE=30m

# ASR / Pipeline
ASR_MODEL=medium              # faster‑whisper 模型名
REQUIRED_LANGS=zh-CN,en,ja    # 逗号分隔
WRITEBACK_MODE=upload         # upload | sidecar
```

---

## 13. 部署与运维

**Docker Compose（摘要）**
```yaml
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    env_file: .env
    depends_on: [redis, ollama]
    volumes: ["./backend:/app"]
  worker:
    build: .
    command: celery -A app.workers.celery_app worker -Q default -l INFO
    env_file: .env
    depends_on: [redis, ollama]
  beat:
    build: .
    command: celery -A app.workers.celery_app beat -l INFO
    env_file: .env
    depends_on: [redis]
  redis:
    image: redis:7
  # Database 按需添加（postgres/mysql/mssql/sqlite）
  ollama:
    image: ollama/ollama:latest
    volumes: ["ollama:/root/.ollama"]
volumes: { ollama: {} }
```

**运维要点**：
- **日志**：结构化（JSON），包含 job_id、phase、latency。
- **监控**：Prometheus 指标（任务耗时、失败率、队列深度）；Grafana 面板。
- **备份**：数据库与字幕产物（若写入 FS/S3）。
- **扩缩容**：Workers 无状态横向扩展；Ollama 根据显存与模型大小评估副本数量。

---

## 14. 测试策略与覆盖

- **单元测试**：Subtitle 解析/保存、提示词生成、OllamaClient 拉取流解析、DB CRUD。
- **集成测试**：
  - 无字幕媒体 → ASR → 翻译 → 回写 Jellyfin。
  - 模型缺失 → 自动 pull → 翻译 → 回写。
- **跨库矩阵**：PG/MySQL/SQLite/MSSQL 各跑一遍迁移 + CRUD + 关键查询。
- **E2E**：前端提交流程（Cypress/Playwright） + SSE 进度显示。

---

## 15. 风险清单与缓解

| 风险 | 说明 | 缓解 |
|---|---|---|
| 模型体积/下载失败 | 大模型拉取耗时/易中断 | `pull` 断点续传；前端可暂停/恢复；镜像源 |
| GPU/内存不足 | 同时 ASR/LLM 争用 | 队列限流、按资源分队列；Ollama `keep_alive` |
| Jellyfin 版本差异 | 客户端/版本对侧车识别差异 | 优先使用 API 上传；回退侧车 |
| 多数据库差异 | JSON/Enum/UPSERT 差异 | 统一 String/JSON；服务层幂等；迁移分支 |
| ASS 样式破坏 | 机翻替换破坏标签 | 解析→剥离→回填；单元测试覆盖 |
| PGS 图像字幕 | 需要 OCR 才能翻译 | MVP 暂不支持；后续引入 OCR 管线 |

---

## 16. 里程碑与交付物

1. **M1（骨架）**：FastAPI/Alembic/Celery/Redis/DB 接入；模型管理 API。
2. **M2（字幕管线）**：SRT/ASS/VTT 翻译闭环；手动上传预览。
3. **M3（Jellyfin 只读）**：扫描库与缺失语言检测；批量建任务。
4. **M4（回写）**：Subtitle API 上传；任务重试/补偿。
5. **M5（ASR）**：无字幕媒体→ASR→翻译→回写。
6. **M6（多库验证）**：PG/MySQL/SQLite/MSSQL 矩阵稳定通过。
7. **M7（体验）**：术语表/禁译、质量校验、可观察性完善。

---

## 附录 A：关键代码片段

**GUID TypeDecorator（跨库 UUID）**
```python
# models/types.py
import uuid
import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator, CHAR

class GUID(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True
    def process_bind_param(self, value, dialect):
        if value is None: return None
        if isinstance(value, uuid.UUID): return str(value)
        return str(uuid.UUID(value))
    def process_result_value(self, value, dialect):
        return uuid.UUID(value) if value else None
```

**OllamaClient（拉取进度流 → SSE）**
```python
async def ensure_model(name: str, progress_cb=None):
    if name in await list_local(): return
    async with httpx.AsyncClient(timeout=None) as s:
        async with s.stream("POST", f"{BASE}/api/pull", json={"name": name}) as resp:
            async for line in resp.aiter_lines():
                if line and progress_cb:
                    progress_cb(line)  # 原样转发到 SSE
```

**Subtitle 翻译（保留时间轴/标签）**
```python
subs = pysubs2.load(in_path)
for line in subs:
    text_plain, tags = strip_ass_tags(line.text)
    translated = call_llm_translate(text_plain, src, tgt, model)
    line.text = restore_tags(tags, translated)
subs.save(out_path)
```

---

## 附录 B：目录结构建议

```
backend/
  app/
    main.py
    core/ (config, db, logging, events)
    api/routers/ (health, models, jellyfin, jobs, upload)
    services/ (jellyfin_client, ollama_client, subtitle_service, asr_service, writeback, detector, prompts)
    models/ (types, translation_job, media_asset, subtitle, model_registry, setting, base)
    schemas/
    workers/ (celery_app, tasks)
  migrations/ (alembic)
  tests/
  docker-compose.yml
  pyproject.toml / requirements.txt
  .env.example
```

---

**版权与授权**：内部使用设计文档，允许在项目中自由复制与修改。

