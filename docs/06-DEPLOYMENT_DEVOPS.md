# 部署与运维（DevOps）

> 面向：平台与运维工程师

如果你要给**非开发人员**快速交付可双击使用的本地版本，请同时参考：

- `docs/09-QUICK_START_NON_DEVELOPER.md`
- 根目录快捷脚本：`quick-setup.cmd`、`quick-start.cmd`、`quick-open.cmd`、`quick-stop.cmd`

---

## 1. 运行时依赖

- **Redis**：Celery broker；AOF 建议开启。
- **数据库**：PostgreSQL（默认）、或 MySQL/SQLite/MSSQL。
- **Ollama**：镜像 `ollama/ollama:latest`；模型卷 `/root/.ollama`。
- **FFmpeg**：worker 镜像内预装。
- **PGS OCR 引擎**（可选，但启用 `.sup` 翻译时必需）：
  - 优先推荐 `Subtitle Edit` 可执行文件
  - 次选 `python -m pgsocr` 或 `pgsocr` 命令行（前提是已具备 Tesseract 运行时）

---

## 2. 环境变量（.env 摘要）

```ini
DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/ai_subs
DB_VENDOR=postgres
REDIS_URL=redis://redis:6379/0
JELLYFIN_BASE_URL=http://jellyfin:8096
JELLYFIN_API_KEY=xxxx
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_KEEP_ALIVE=30m
DEFAULT_MT_MODEL=qwen2.5:7b-instruct
AI_MODELS_CATALOG_URL=https://models.dev
AI_MODELS_AUTO_SYNC_ENABLED=true
AI_MODELS_AUTO_SYNC_INTERVAL_SECONDS=3600
PGS_OCR_ENGINE=auto
PGS_OCR_OUTPUT_FORMAT=srt
PGS_OCR_TIMEOUT_SECONDS=1800
PGSOCR_EXECUTABLE=pgsocr
PGSOCR_MODULE_COMMAND=python -m pgsocr
SUBTITLE_EDIT_EXECUTABLE=SubtitleEdit
ASR_MODEL=medium
REQUIRED_LANGS=zh-CN,en,ja
WRITEBACK_MODE=upload
```

---

## 3. Compose 与进程

- **backend**：FastAPI (Uvicorn) + Celery Worker 合并服务；通过 `/app/start.sh` 同时启动 API 和 Worker。
  - Worker 并发度设为 `1`（内存受限环境优化，避免 OOM）
  - Worker 监听队列：`default, scan, translate, asr`
  - 如系统内存充足（>16GB），可在 `start.sh` 中提高并发度（`-c 2` 或更高）
  - Windows 本地开发请使用 `backend/start.ps1`；该脚本会以 PowerShell 后台进程启动 Worker，并使用 `--pool=solo`
- **beat**：Celery Beat 调度器；定时扫描/清理/健康检查（单实例）。
- **ollama**：独立容器；根据显存选择模型大小。
- **postgres** / **redis**：数据库与消息队列服务。
- **frontend**：Nginx 静态文件服务 + React SPA。

AI 模型目录自动同步会在启动时和后台定时访问 `AI_MODELS_CATALOG_URL`（默认 `https://models.dev`）。如果部署环境不能访问外网，建议设置 `AI_MODELS_AUTO_SYNC_ENABLED=false`，再通过 API 或管理界面手动同步。

### PGS / SUP OCR 运行要求

- 如果要翻译 Blu-ray 图片字幕（`.sup` / PGS），部署环境必须额外提供 OCR 引擎。
- 推荐优先级：
  1. `Subtitle Edit`（最稳定，适合手动/半自动处理）
  2. `python -m pgsocr` / `pgsocr`（适合具备完整 Tesseract 运行时的自动化环境）
- `PGS_OCR_ENGINE=auto` 时，后端会按上述顺序自动探测。
- 如果一个引擎都没有：
  - `.sup` 上传仍然会进入任务流
  - 但任务会在 OCR 阶段失败，并明确报缺少 OCR 引擎

### Windows 主机建议

- 安装 `Subtitle Edit` 并确保 `SubtitleEdit.exe` 在 PATH 中，或
- 安装 Tesseract OCR（推荐 `UB-Mannheim.TesseractOCR`）并确保 Python 环境可构建 `tesserocr`，然后使用 `python -m pgsocr`

### Linux / Docker 建议

- 在 worker 镜像中额外安装：
  - `tesseract-ocr`
  - 对应语言包（如 `tesseract-ocr-eng`、`tesseract-ocr-chi-sim`、`tesseract-ocr-jpn`）
- 再安装或挂载：
  - `pgsocr` 命令行，或
  - 可调用的 `python -m pgsocr`

**架构说明**：
- Backend 容器同时运行 API 和 Worker，简化了部署和资源管理
- Worker 在后台运行（`celery ... &`），API 在前台运行（`exec uvicorn ...`）
- 并发度=1 是为防止 ASR 模型加载时内存溢出导致进程被 OOM Killer 终止
- `start.sh` 仅用于 Linux/容器环境；Windows 原生环境需使用 `start.ps1`
- Windows `start.ps1` 默认关闭 Uvicorn reload，以避免 reload 监督进程在 Ctrl+C 时输出取消异常；需要热重载时设置 `FLUXCAPTION_RELOAD=1`

---

## 4. 监控与日志

- **日志**：结构化（JSON），关键字段：`job_id, phase, duration, media_id, model`。
- **指标**（Prometheus）：
  - 任务吞吐/时延/失败率
  - 模型拉取耗时与成功率
  - ASR/MT 阶段用时分布
- **告警**：失败率阈值、队列积压、Ollama 不可用、Jellyfin 超时。

---

## 5. 安全

- Jellyfin 使用**最小权限** API Key；生产环境走内网。
- API 鉴权（可选）：JWT/Key；CORS 仅允许前端域名。
- 上传存储目录隔离；病毒/脚本扫描（可选）。

---

## 6. 灰度与回滚

- Worker 支持**逐步放量**；新模型先小流量验证。
- 失败作业重试策略：指数退避 + 最大次数；超过阈值进入死信队列。
- 版本回滚：镜像打 tag；数据库迁移支持 `downgrade`（谨慎）。
