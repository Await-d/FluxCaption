# FluxCaption 部署指南

完整的 FluxCaption 开发和生产环境部署指南。

---

## 📋 快速导航

1. [前置要求](#前置要求)
2. [开发环境部署](#开发环境部署)
3. [生产环境部署](#生产环境部署)
4. [配置说明](#配置说明)
5. [服务管理](#服务管理)
6. [故障排查](#故障排查)

---

## 🔧 前置要求

### 系统要求

**最低配置：**
- CPU: 4 核心
- 内存: 8 GB
- 存储: 50 GB
- 操作系统: Linux (推荐 Ubuntu 20.04+), macOS, Windows + WSL2

**推荐配置（生产环境）：**
- CPU: 8+ 核心
- 内存: 16+ GB
- 存储: 100+ GB SSD
- GPU: NVIDIA GPU + CUDA（可选，用于加速 ASR/LLM）

### 必需软件

- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Git**: 2.30+

---

## 🚀 开发环境部署

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/FluxCaption.git
cd FluxCaption
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**必需的环境变量：**

```ini
# Jellyfin 集成
JELLYFIN_BASE_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_jellyfin_api_key_here

# 数据库（开发环境默认值即可）
DATABASE_URL=postgresql+psycopg://fluxcaption:fluxcaption@postgres:5432/fluxcaption

# Redis（开发环境默认值即可）
REDIS_URL=redis://redis:6379/0

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
DEFAULT_MT_MODEL=qwen2.5:7b-instruct
```

### 3. 启动所有服务

```bash
# 启动全部容器
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker compose exec backend alembic upgrade head
```

### 5. 拉取翻译模型

```bash
# 方式1：在容器内执行
docker compose exec ollama ollama pull qwen2.5:7b-instruct

# 方式2：通过 API（推荐）
curl -X POST http://localhost/api/models/pull \
  -H "Content-Type: application/json" \
  -d '{"model_name": "qwen2.5:7b-instruct"}'
```

### 6. 访问应用

- **前端界面**: http://localhost
- **后端 API**: http://localhost/api
- **API 文档**: http://localhost/docs
- **健康检查**: http://localhost/health

---

## 🏭 生产环境部署

### 1. 准备生产环境

```bash
# 创建数据持久化目录
sudo mkdir -p /var/lib/fluxcaption
cd /var/lib/fluxcaption

# 创建子目录
mkdir -p postgres redis ollama whisper_models subtitle_output
```

### 2. 配置生产设置

```bash
# 复制生产环境配置
cp .env.example .env.prod

# 编辑生产配置
nano .env.prod
```

**生产环境重要变量：**

```ini
# 环境设置
ENVIRONMENT=production
DEBUG=false

# 安全配置
POSTGRES_PASSWORD=<强随机密码>
REDIS_PASSWORD=<强随机密码>

# Jellyfin
JELLYFIN_BASE_URL=https://jellyfin.yourdomain.com
JELLYFIN_API_KEY=<你的API密钥>

# 存储路径
DATA_DIR=/var/lib/fluxcaption

# 日志
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3. 启动生产环境

```bash
# 使用生产配置启动
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  --env-file .env.prod \
  up -d
```

### 4. 启用 GPU 支持（可选）

在 docker-compose 文件中取消注释 GPU 配置：

```yaml
# Ollama 服务
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

# Worker 服务（ASR）
worker:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

---

## ⚙️ 配置说明

### 数据库迁移

```bash
# 创建新迁移
docker compose exec backend alembic revision --autogenerate -m "描述"

# 应用迁移
docker compose exec backend alembic upgrade head

# 回滚一个版本
docker compose exec backend alembic downgrade -1

# 查看当前版本
docker compose exec backend alembic current
```

### Worker 扩展

```bash
# 扩展 worker 到 3 个实例
docker compose up -d --scale worker=3
```

### 资源限制

在 `docker-compose.prod.yml` 中调整：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## 🔨 服务管理

### 启动/停止服务

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose stop

# 停止并删除容器
docker compose down

# 停止并删除所有（包括数据卷）
docker compose down -v
```

### 查看日志

```bash
# 所有服务日志
docker compose logs -f

# 特定服务日志
docker compose logs -f backend

# 最近 100 行
docker compose logs --tail=100 backend
```

### 重启服务

```bash
# 重启所有
docker compose restart

# 重启特定服务
docker compose restart backend
```

### 执行命令

```bash
# 进入后端容器 shell
docker compose exec backend bash

# 运行 Python 脚本
docker compose exec backend python -m app.scripts.cleanup

# 执行数据库查询
docker compose exec postgres psql -U fluxcaption -d fluxcaption -c "SELECT COUNT(*) FROM translation_jobs;"
```

---

## 🐛 故障排查

### 服务健康检查

```bash
# 检查所有服务状态
docker compose ps

# 检查后端健康
docker compose exec backend curl -f http://localhost:8000/health

# 检查数据库连接
docker compose exec backend python -c "from app.core.db import engine; engine.connect()"
```

### 常见问题

#### 1. 服务无法启动

```bash
# 查看日志
docker compose logs

# 检查磁盘空间
df -h

# 检查 Docker 资源
docker system df
```

#### 2. 数据库连接错误

```bash
# 验证数据库运行状态
docker compose ps postgres

# 查看数据库日志
docker compose logs postgres

# 测试连接
docker compose exec postgres pg_isready -U fluxcaption
```

#### 3. Ollama 模型未找到

```bash
# 列出已安装模型
docker compose exec ollama ollama list

# 手动拉取模型
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

#### 4. 前端无法访问后端

```bash
# 检查 nginx 配置
docker compose exec frontend nginx -t

# 重启 nginx
docker compose restart frontend

# 检查后端可访问性
curl http://localhost/api/health
```

### 性能问题

```bash
# 查看资源使用
docker stats

# 查看 worker 队列
docker compose exec backend celery -A app.workers.celery_app inspect active

# 查看 Redis 内存使用
docker compose exec redis redis-cli INFO memory
```

---

## 💾 备份与恢复

### 备份

#### 1. 数据库备份

```bash
# 创建备份
docker compose exec postgres pg_dump -U fluxcaption fluxcaption > backup_$(date +%Y%m%d).sql

# 或使用 Docker 卷备份
docker run --rm \
  -v fluxcaption_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz /data
```

#### 2. 完整系统备份

```bash
# 备份所有卷
docker compose down
tar czf fluxcaption_backup_$(date +%Y%m%d).tar.gz \
  /var/lib/fluxcaption/ \
  .env.prod
docker compose up -d
```

### 恢复

#### 1. 恢复数据库

```bash
# 停止服务
docker compose down

# 从 SQL 导入恢复
cat backup_20240101.sql | docker compose exec -T postgres psql -U fluxcaption fluxcaption

# 启动服务
docker compose up -d
```

#### 2. 恢复完整系统

```bash
# 解压备份
tar xzf fluxcaption_backup_20240101.tar.gz -C /

# 恢复权限
sudo chown -R 999:999 /var/lib/fluxcaption/postgres
sudo chown -R 999:999 /var/lib/fluxcaption/redis

# 启动服务
docker compose up -d
```

---

## 🔐 安全最佳实践

1. **使用强密码** - PostgreSQL 和 Redis
2. **启用 SSL/TLS** - 生产环境使用反向代理
3. **限制网络访问** - 防火墙规则
4. **定期更新** - Docker 镜像和依赖
5. **定期备份** - 自动化备份脚本
6. **监控日志** - 异常活动检测
7. **API 认证** - 公网暴露时启用

---

## 📊 监控（可选）

### Prometheus + Grafana

在 `docker-compose.prod.yml` 中添加：

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## 📞 支持

遇到问题？
- **GitHub Issues**: https://github.com/yourusername/FluxCaption/issues
- **项目文档**: 查看 `docs/` 目录

---

**最后更新:** 2025-10-01
