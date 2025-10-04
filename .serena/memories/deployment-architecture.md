# FluxCaption 部署架构

## 架构概述

FluxCaption 采用简化的容器化架构，所有服务通过 Docker Compose 编排。

### 服务组成

1. **postgres** - PostgreSQL 15 数据库
2. **redis** - Redis 7 消息队列和缓存
3. **ollama** - Ollama LLM 推理引擎
4. **backend** - FastAPI API + Celery Worker (合并服务)
5. **beat** - Celery Beat 调度器
6. **frontend** - Nginx + React 前端

### 关键架构决策

**Backend 服务合并**
- backend 容器同时运行 FastAPI API 和 Celery Worker
- 通过 `/app/start.sh` 脚本启动两个进程
- Worker 在后台运行，API 在前台运行
- 这种架构简化了部署，减少了容器数量

**内存优化配置**
- Celery Worker 并发度设置为 `1` (concurrency=1)
- 原因：ASR 模型(faster-whisper, FunASR)加载时内存占用较大
- 在内存有限的环境中(< 8GB RAM)，高并发会导致 OOM Killer 终止进程
- 并发度=1 确保同时只有一个任务在执行，避免内存溢出

## Backend 启动流程

文件：`backend/start.sh`

```bash
#!/bin/bash
set -e

# 后台启动 Celery worker (并发度=1)
celery -A app.workers.celery_app worker -l INFO -Q default,scan,translate,asr -c 1 &

# 前台启动 FastAPI 应用
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

关键点：
- Worker 监听 4 个队列：default, scan, translate, asr
- `&` 使 worker 在后台运行
- `exec` 确保 uvicorn 替换 shell 进程(PID=1)，正确处理 Docker 信号

## Docker Compose 配置要点

### Backend 服务卷挂载

```yaml
volumes:
  - ./backend/app:/app/app                    # 代码热重载
  - ./backend/migrations:/app/migrations      # 数据库迁移
  - ./backend/alembic.ini:/app/alembic.ini   # Alembic 配置
  - api_logs:/app/logs                        # 日志持久化
  - subtitle_output:/app/output/subtitles     # 字幕输出
  - whisper_models:/app/models/whisper        # Whisper 模型缓存
  - temp_files:/tmp/fluxcaption               # 临时文件
  - ${MEDIA_PATH:-/media}:/media:ro           # 媒体文件只读访问
```

**重要**: `MEDIA_PATH` 必须挂载才能访问本地媒体文件进行扫描和处理

### 环境变量

必需的环境变量：
```bash
DATABASE_URL=postgresql+psycopg://fluxcaption:fluxcaption@postgres:5432/fluxcaption
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
OLLAMA_BASE_URL=http://ollama:11434
JELLYFIN_BASE_URL=${JELLYFIN_BASE_URL}
JELLYFIN_API_KEY=${JELLYFIN_API_KEY}
```

## 部署步骤

### 首次部署

```bash
# 1. 克隆代码
git clone <repository> && cd FluxCaption

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入必需的值：JELLYFIN_API_KEY, MEDIA_PATH 等

# 3. 启动所有服务
docker compose up -d

# 4. 检查服务状态
docker compose ps
docker logs fluxcaption-backend --tail 50

# 5. 访问应用
# Frontend: http://localhost:80
# Backend API: http://localhost:80/api
```

### 更新部署

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建 backend 镜像(如果 Dockerfile 或 requirements.txt 有变更)
docker compose build backend

# 3. 重启服务
docker compose up -d backend --force-recreate

# 4. 运行数据库迁移(如果有)
docker exec fluxcaption-backend alembic upgrade head
```

## 内存管理

### 系统要求

- **最低配置**: 8GB RAM, 4GB Swap
- **推荐配置**: 16GB RAM, 8GB Swap
- **GPU**: 可选，用于加速 ASR 和 LLM 推理

### OOM 问题排查

如果任务失败并出现 "signal 9 (SIGKILL)" 错误：

1. 检查系统内存使用:
```bash
free -h
docker stats
```

2. 检查是否有进程被 OOM Killer 终止:
```bash
dmesg | grep -i kill
```

3. 解决方案:
   - 降低 worker 并发度(已设为 1)
   - 使用更小的 ASR 模型(base/small 替代 medium/large)
   - 增加系统内存
   - 增加 swap 空间

### 清理僵尸任务

如果有任务卡在 "running" 状态但实际已失败：

```python
from app.core.db import SessionLocal
from app.models.translation_job import TranslationJob
from datetime import datetime, timezone

db = SessionLocal()
try:
    stuck_jobs = db.query(TranslationJob).filter(
        TranslationJob.status == 'running',
        TranslationJob.error.isnot(None)
    ).all()
    
    for job in stuck_jobs:
        job.status = 'cancelled' if 'cancel' in job.error.lower() else 'failed'
        if not job.finished_at:
            job.finished_at = datetime.now(timezone.utc)
    
    db.commit()
finally:
    db.close()
```

## 监控和日志

### 查看日志

```bash
# Backend (API + Worker)
docker logs -f fluxcaption-backend

# Beat (调度器)
docker logs -f fluxcaption-beat

# Frontend
docker logs -f fluxcaption-frontend
```

### 健康检查

```bash
# 检查所有服务健康状态
docker compose ps

# 检查 API 健康端点
curl http://localhost:80/health

# 检查 Celery worker 状态
docker exec fluxcaption-backend celery -A app.workers.celery_app inspect active
```

## 故障排除

### Backend 无法启动

1. 检查数据库连接:
```bash
docker logs fluxcaption-postgres
docker exec fluxcaption-backend pg_isready -h postgres -U fluxcaption
```

2. 检查 Redis 连接:
```bash
docker logs fluxcaption-redis
docker exec fluxcaption-backend redis-cli -h redis ping
```

### Worker 不处理任务

1. 验证 worker 正在运行:
```bash
docker logs fluxcaption-backend | grep "celery@.*ready"
```

2. 检查 Redis 队列:
```bash
docker exec fluxcaption-redis redis-cli LLEN celery
```

3. 检查 worker 并发度:
```bash
docker logs fluxcaption-backend | grep "concurrency"
# 应该显示: concurrency: 1 (prefork)
```

## 性能调优

### Celery Worker 并发度调整

**当前配置**: concurrency=1 (内存受限环境)

如果系统内存充足(>16GB)，可以提高并发度:

编辑 `backend/start.sh`:
```bash
celery -A app.workers.celery_app worker -l INFO -Q default,scan,translate,asr -c 2 &
```

然后重新部署:
```bash
docker compose build backend
docker compose up -d backend --force-recreate
```

**注意**: 每增加 1 个并发，peak 内存使用可能增加 2-3GB(取决于 ASR 模型大小)

### ASR 模型选择

在 `.env` 中配置:
```bash
# 内存有限 (< 8GB)
ASR_MODEL=base

# 平衡 (8-16GB)
ASR_MODEL=small

# 高质量 (> 16GB)
ASR_MODEL=medium
```

## 安全建议

1. **生产环境禁用 --reload**:
   编辑 `backend/start.sh`，移除 uvicorn 的 `--reload` 参数

2. **使用非 root 用户运行**:
   当前 worker 以 root 运行，生产环境应创建专用用户

3. **限制 API 访问**:
   配置防火墙规则，仅允许信任的 IP 访问

4. **启用 HTTPS**:
   在 frontend nginx 配置中添加 SSL 证书

5. **API Key 保护**:
   在 `.env` 中使用强 API Key，定期轮换
