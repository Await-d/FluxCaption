# FluxCaption Docker 部署脚本使用指南

本目录包含一系列便捷的 shell 脚本，用于管理 FluxCaption Docker 服务。

## 📋 可用脚本

### 1. `deploy.sh` - 完整部署脚本

**功能**：构建镜像并部署所有服务

**用法**：
```bash
./deploy.sh [选项]
```

**选项**：
- `--no-cache`：不使用 Docker 缓存构建（适用于需要完全重新构建的情况）
- `--cleanup`：部署前清理未使用的 Docker 镜像
- `--skip-build`：跳过构建步骤，直接启动现有镜像
- `--help, -h`：显示帮助信息

**示例**：
```bash
# 标准部署
./deploy.sh

# 完全重新构建
./deploy.sh --no-cache

# 清理旧镜像后部署
./deploy.sh --cleanup

# 跳过构建直接启动
./deploy.sh --skip-build
```

**首次部署注意事项**：
1. 确保已安装 Docker 和 Docker Compose
2. 确保存在 `.env` 文件（脚本会从 `.env.example` 自动创建）
3. 编辑 `.env` 文件，填入必需的配置值：
   - `JELLYFIN_API_KEY`
   - `OLLAMA_BASE_URL`
   - 其他自定义配置

---

### 2. `start.sh` - 启动服务

**功能**：启动所有 FluxCaption 服务

**用法**：
```bash
./start.sh
```

**行为**：
- 如果服务已在运行，会询问是否重启
- 如果服务未运行，直接启动所有服务

**输出**：
- 显示服务状态
- 提供访问地址

---

### 3. `stop.sh` - 停止服务

**功能**：停止所有 FluxCaption 服务

**用法**：
```bash
./stop.sh
```

**行为**：
- 停止所有容器
- 不删除数据卷（数据保留）
- 显示清理结果

---

### 4. `restart.sh` - 重启服务

**功能**：重启指定服务或所有服务

**用法**：
```bash
./restart.sh [服务名]
```

**服务名**（可选）：
- `backend` - 后端 API 服务
- `beat` - Celery Beat 调度器
- `postgres` - PostgreSQL 数据库
- `redis` - Redis 缓存
- `ollama` - Ollama AI 模型服务

**示例**：
```bash
# 重启所有服务
./restart.sh

# 仅重启后端服务
./restart.sh backend

# 仅重启 Ollama 服务
./restart.sh ollama
```

---

### 5. `logs.sh` - 查看日志

**功能**：查看服务日志，支持实时跟踪

**用法**：
```bash
./logs.sh [服务名] [选项]
```

**服务名**（可选）：
- `backend` - 后端 API 服务
- `beat` - Celery Beat 调度器
- `postgres` - PostgreSQL 数据库
- `redis` - Redis 缓存
- `ollama` - Ollama AI 模型服务
- 留空 - 所有服务

**选项**：
- `-f, --follow`：实时跟踪日志（Ctrl+C 退出）
- `-n <数量>`：显示最后 N 行日志（默认：100）
- `-h, --help`：显示帮助信息

**示例**：
```bash
# 查看所有服务最后 100 行日志
./logs.sh

# 实时跟踪 backend 日志
./logs.sh backend -f

# 查看 backend 最后 50 行日志
./logs.sh backend -n 50

# 实时跟踪所有服务日志
./logs.sh -f

# 查看 Ollama 最后 200 行日志
./logs.sh ollama -n 200
```

---

### 6. `cleanup.sh` - 清理资源

**功能**：清理 Docker 容器、卷、镜像等资源

**⚠️ 警告**：此脚本会删除数据，请谨慎使用！

**用法**：
```bash
./cleanup.sh [选项]
```

**选项**：
- `--all`：完全清理（容器 + 卷 + 镜像 + 网络）⚠️ 会删除所有数据
- `--containers`：仅清理容器
- `--volumes`：清理容器和卷 ⚠️ 会删除数据库数据
- `--images`：清理容器和镜像
- `--cache`：清理 Docker 构建缓存
- `--help, -h`：显示帮助信息

**示例**：
```bash
# 仅停止并删除容器（数据保留）
./cleanup.sh --containers

# 清理构建缓存
./cleanup.sh --cache

# 完全清理（会要求确认）
./cleanup.sh --all

# 删除数据卷（会要求确认）
./cleanup.sh --volumes
```

**清理级别说明**：
1. `--containers`：最安全，仅删除容器，数据完全保留
2. `--cache`：清理构建缓存，释放磁盘空间
3. `--images`：删除容器和镜像，数据保留
4. `--volumes`：⚠️ 删除数据库等持久化数据
5. `--all`：⚠️ 完全清理，所有数据丢失

---

## 🚀 常见使用场景

### 首次部署

```bash
# 1. 检查并编辑配置
cp .env.example .env
vim .env  # 填入必需的配置

# 2. 执行部署
./deploy.sh

# 3. 查看服务状态
docker compose ps

# 4. 访问应用
# 浏览器打开: http://localhost
```

### 日常维护

```bash
# 查看服务状态
docker compose ps

# 查看最新日志
./logs.sh

# 重启某个服务
./restart.sh backend

# 查看特定服务的实时日志
./logs.sh backend -f
```

### 更新代码后重新部署

```bash
# 方法 1: 快速重启（使用缓存）
./deploy.sh

# 方法 2: 完全重新构建
./deploy.sh --no-cache

# 方法 3: 仅重启服务（代码已在镜像中）
./restart.sh
```

### 问题排查

```bash
# 1. 查看所有服务日志
./logs.sh

# 2. 实时跟踪问题服务
./logs.sh backend -f

# 3. 查看更多历史日志
./logs.sh backend -n 500

# 4. 检查容器状态
docker compose ps

# 5. 重启问题服务
./restart.sh backend
```

### 清理磁盘空间

```bash
# 清理 Docker 缓存
./cleanup.sh --cache

# 查看磁盘使用
docker system df

# 清理未使用的镜像
docker image prune -a
```

### 完全重置（删除所有数据）

```bash
# ⚠️ 警告：这会删除所有数据！

# 1. 停止服务
./stop.sh

# 2. 完全清理
./cleanup.sh --all

# 3. 重新部署
./deploy.sh
```

---

## 📊 服务说明

| 服务名 | 说明 | 端口 |
|--------|------|------|
| `backend` | FastAPI 后端 API + 前端静态文件 | 80 |
| `beat` | Celery Beat 调度器 + Worker | - |
| `postgres` | PostgreSQL 数据库 | 5432 (内部) |
| `redis` | Redis 缓存和消息队列 | 6379 (内部) |
| `ollama` | Ollama AI 模型服务 | 11434 (内部) |

---

## 🔧 故障排除

### 脚本无法执行

**问题**：`permission denied`

**解决**：
```bash
chmod +x *.sh
```

### Docker 命令需要 sudo

**问题**：需要 sudo 权限运行 docker 命令

**解决**：
```bash
# 将用户加入 docker 组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker
```

### 端口冲突

**问题**：端口 80 已被占用

**解决**：
```bash
# 方法 1: 停止占用端口的服务
sudo lsof -i :80
sudo systemctl stop nginx  # 例如

# 方法 2: 修改 docker-compose.yml 中的端口映射
# 将 "80:8000" 改为 "8080:8000"
```

### 磁盘空间不足

**问题**：构建或运行时磁盘空间不足

**解决**：
```bash
# 清理 Docker 资源
./cleanup.sh --cache
docker system prune -a

# 查看磁盘使用
docker system df
df -h
```

### 服务无法启动

**问题**：容器启动后立即退出

**解决**：
```bash
# 查看详细日志
./logs.sh [服务名] -n 200

# 检查配置文件
cat .env

# 检查容器状态
docker compose ps -a
```

---

## 📝 注意事项

1. **首次部署前**：务必检查并修改 `.env` 文件
2. **数据备份**：定期备份 PostgreSQL 数据库
3. **日志监控**：使用 `./logs.sh -f` 监控服务运行状态
4. **资源清理**：定期使用 `./cleanup.sh --cache` 释放磁盘空间
5. **版本更新**：更新代码后使用 `./deploy.sh --no-cache` 重新构建

---

## 🆘 获取帮助

- **脚本帮助**：运行 `./[脚本名].sh --help`
- **Docker 文档**：https://docs.docker.com
- **项目文档**：查看 `docs/` 目录
- **问题反馈**：https://github.com/anthropics/FluxCaption/issues
