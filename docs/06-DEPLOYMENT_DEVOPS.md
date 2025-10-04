# 部署与运维（DevOps）

> 面向：平台与运维工程师

---

## 1. 运行时依赖

- **Redis**：Celery broker；AOF 建议开启。
- **数据库**：PostgreSQL（默认）、或 MySQL/SQLite/MSSQL。
- **Ollama**：镜像 `ollama/ollama:latest`；模型卷 `/root/.ollama`。
- **FFmpeg**：worker 镜像内预装。

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
- **beat**：Celery Beat 调度器；定时扫描/清理/健康检查（单实例）。
- **ollama**：独立容器；根据显存选择模型大小。
- **postgres** / **redis**：数据库与消息队列服务。
- **frontend**：Nginx 静态文件服务 + React SPA。

**架构说明**：
- Backend 容器同时运行 API 和 Worker，简化了部署和资源管理
- Worker 在后台运行（`celery ... &`），API 在前台运行（`exec uvicorn ...`）
- 并发度=1 是为防止 ASR 模型加载时内存溢出导致进程被 OOM Killer 终止

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
