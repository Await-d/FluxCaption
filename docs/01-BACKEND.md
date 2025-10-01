# 后端开发指南（Python · FastAPI + Celery）

> 面向：后端工程师  
> 目标：可立即按文档搭建、开发、联调、扩展

---

## 1. 架构与进程拓扑

- **FastAPI API**：REST + SSE，处理鉴权、配置、任务创建与查询。
- **Celery Workers**：`scan` / `translate` / `asr_then_translate` 队列。
- **Redis**：Celery broker & 缓存；SSE 事件从 worker 转发。
- **数据库**：SQLAlchemy 2（同步 Engine）+ Alembic。
- **Ollama**：HTTP API（模型枚举/拉取/推理）。
- **Jellyfin**：Items（含 `MediaStreams`）与 `UploadSubtitle` 回写。

### 1.1 目录结构

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
```

---

## 2. 关键技术与框架说明

### 2.1 FastAPI（异步 + 同步 ORM）

- Web 层异步；DB 操作使用 **同步 SQLAlchemy**，通过 `run_in_threadpool` 包装，兼容多数据库驱动。
- 自动生成 OpenAPI；在 `app/main.py` 中挂载路由与中间件。

### 2.2 SQLAlchemy 2 + Alembic（多数据库）

- **GUID TypeDecorator** → `CHAR(36)`；跨库一致。
- **JSON 列**保存变长/数组（任务目标语言等）；媒体语言用**子表**利于查询。
- `alembic upgrade head` 统一迁移；迁移脚本避免方言类型。

### 2.3 Celery（队列与调度）

- 任务划分：  
  - `scan`：按库/筛查缺失语言 → 批量建 `translation_job`  
  - `translate`：字幕→翻译→后处理→写回  
  - `asr_then_translate`：无字幕媒体 → ASR → 翻译  
- 配置：`acks_late`, `task_reject_on_worker_lost`, `worker_max_tasks_per_child`，避免任务丢失与内存膨胀。

### 2.4 OllamaClient

- `/api/tags` → 检查本地模型是否存在。  
- `/api/pull` → **流式下载**，将 `status/completed/total` 原样转发到 SSE。  
- `/api/generate` → 翻译（可选 `/api/chat`）。

### 2.5 JellyfinClient

- `GET /Items?Fields=MediaStreams` → 读取字幕/音轨语言与基础元数据。  
- `POST /Items/{itemId}/Subtitles` → 上传字幕（`Data/Format/Language/...`）。  
- 侧车模式：写入媒体同目录（可选）。

### 2.6 字幕与 ASR

- **pysubs2**：读写 `.srt/.ass/.vtt`，保留时间轴与标签，仅替换 `line.text`。  
- **faster‑whisper**：抽音后转写；输出 SRT/VTT；作为上游输入。

---

## 3. 代码骨架（片段）

**DB 会话与健康检查**
```python
# app/core/db.py
engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s; s.commit()
    except: s.rollback(); raise
    finally: s.close()
```

**Ollama 拉取（SSE 进度）**
```python
async def ensure_model(name: str, cb):
    if name in await list_local(): return
    async with httpx.AsyncClient(timeout=None) as s:
        async with s.stream("POST", f"{BASE}/api/pull", json={"name": name}) as resp:
            async for line in resp.aiter_lines():
                if line: cb("pull", line)  # 推送到 SSE
```

**字幕翻译主循环**
```python
subs = pysubs2.load(in_path)
for line in subs:
    plain, tags = strip_ass_tags(line.text)
    out = llm_translate(plain, model, src, tgt)
    line.text = restore_tags(tags, out)
subs.save(out_path, format=fmt)
```

---

## 4. 配置与约定

- 统一 **UTC** 存储；Pydantic 层校验枚举与语言码（BCP‑47）。
- 术语表/禁译词（可选）：JSON 配置，翻译前/后规则应用。
- 进度阶段：`pull → asr → mt → post → writeback`。

---

## 5. 本地运行与调试

```bash
# 依赖
pip install -r requirements.txt
alembic upgrade head

# 服务
uvicorn app.main:app --reload
celery -A app.workers.celery_app worker -l INFO
celery -A app.workers.celery_app beat -l INFO

# 环境变量（示例）
export OLLAMA_BASE_URL=http://localhost:11434
export JELLYFIN_BASE_URL=http://localhost:8096
export JELLYFIN_API_KEY=xxxxx
```

---

## 6. 性能与稳定性建议

- Worker 并发与 `prefetch_multiplier` 调优，避免模型/ASR 资源争用。
- 大文件分段转写；逐段翻译并批量写回，降低内存峰值。
- 对 Jellyfin 加重试与速率限制；对 `/api/pull` 进度做心跳检测。
