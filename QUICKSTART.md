# FluxCaption 快速开始指南

5 分钟快速部署和使用 FluxCaption AI 字幕翻译系统。

---

## 📦 前置要求

确保已安装以下软件：

- **Docker** (24.0+) 和 **Docker Compose** (2.20+)
- **Jellyfin 媒体服务器**（已配置并运行）

---

## 🚀 快速开始（5 分钟）

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/FluxCaption.git
cd FluxCaption
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件（必须修改以下两项）
nano .env
```

**最小化必需配置：**

```ini
# Jellyfin 集成（必填）
JELLYFIN_BASE_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_jellyfin_api_key_here

# 其他配置保持默认值即可
```

**获取 Jellyfin API Key：**

1. 登录 Jellyfin Web 界面
2. 进入 **控制台 → 高级 → API 密钥**
3. 点击 **新建 API 密钥**
4. 输入应用名称：`FluxCaption`
5. 复制生成的 API 密钥

### 3. 启动服务

```bash
# 启动所有容器
docker compose up -d

# 查看启动状态
docker compose ps
```

**预期输出：**

```
NAME                     STATUS          PORTS
fluxcaption-backend      Up 30 seconds   0.0.0.0:8000->8000/tcp
fluxcaption-frontend     Up 30 seconds   0.0.0.0:80->80/tcp
fluxcaption-worker       Up 30 seconds
fluxcaption-postgres     Up 30 seconds   5432/tcp
fluxcaption-redis        Up 30 seconds   6379/tcp
fluxcaption-ollama       Up 30 seconds   11434/tcp
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker compose exec backend alembic upgrade head
```

### 5. 拉取翻译模型

```bash
# 拉取默认翻译模型（约 4.7 GB）
docker compose exec ollama ollama pull qwen2.5:7b-instruct

# 查看已安装模型
docker compose exec ollama ollama list
```

**可选：通过 Web 界面拉取**

访问 http://localhost → **模型管理** → 输入 `qwen2.5:7b-instruct` → **拉取模型**

### 6. 访问应用

打开浏览器访问：

- **前端界面**: http://localhost
- **API 文档**: http://localhost/docs

---

## 🎬 第一次翻译

### 方式 1：手动上传字幕文件翻译

1. 访问 http://localhost
2. 点击 **翻译** 标签页
3. 上传 `.srt` 或 `.ass` 字幕文件
4. 选择源语言和目标语言
5. 点击 **开始翻译**
6. 实时查看翻译进度
7. 完成后下载翻译好的字幕

### 方式 2：从 Jellyfin 扫描缺失字幕

1. 访问 http://localhost
2. 点击 **媒体库** 标签页
3. 选择要扫描的 Jellyfin 媒体库
4. 点击 **扫描媒体库**
5. 系统自动检测缺失的字幕语言
6. 自动创建翻译任务
7. 在 **任务** 标签页查看进度

### 方式 3：为无字幕视频生成字幕

1. 上传视频文件到 Jellyfin
2. 在 FluxCaption 中扫描媒体库
3. 系统检测到视频无字幕后：
   - 自动提取音频
   - 使用 Whisper ASR 生成源语言字幕
   - 翻译到目标语言
   - 上传回 Jellyfin

---

## ⚙️ 常用配置

### 设置必需字幕语言

编辑 `.env` 文件：

```ini
# 设置必需的字幕语言（BCP-47 格式）
REQUIRED_LANGS=zh-CN,en,ja

# 示例：只需要中文和英文
REQUIRED_LANGS=zh-CN,en
```

重启服务：

```bash
docker compose restart backend worker
```

### 更换翻译模型

```bash
# 拉取新模型（例如更小的 1.5B 模型）
docker compose exec ollama ollama pull qwen2.5:1.5b-instruct

# 或使用更大的 14B 模型（需要更多内存）
docker compose exec ollama ollama pull qwen2.5:14b-instruct
```

修改 `.env` 文件：

```ini
DEFAULT_MT_MODEL=qwen2.5:1.5b-instruct
```

重启服务：

```bash
docker compose restart backend worker
```

### 调整并发任务数

编辑 `.env` 文件：

```ini
# 最大并发翻译任务数（根据 CPU/GPU 性能调整）
MAX_CONCURRENT_TRANSLATE_TASKS=5

# 最大并发 ASR 任务数（消耗更多资源）
MAX_CONCURRENT_ASR_TASKS=2
```

---

## 🔍 健康检查

### 检查服务状态

```bash
# 查看所有服务状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 查看 worker 日志
docker compose logs -f worker

# 检查健康状态
curl http://localhost/health
```

### 验证 Jellyfin 连接

访问 http://localhost/docs

找到 **GET /api/jellyfin/health** 端点，点击 **Try it out** → **Execute**

预期响应：

```json
{
  "status": "ok",
  "server_name": "My Jellyfin Server",
  "version": "10.8.13",
  "connection_time_ms": 45
}
```

### 验证 Ollama 连接

```bash
# 列出已安装模型
docker compose exec ollama ollama list

# 测试模型推理
docker compose exec ollama ollama run qwen2.5:7b-instruct "Hello"
```

---

## 🐛 常见问题

### 问题 1：容器启动失败

```bash
# 查看详细日志
docker compose logs

# 检查端口占用
sudo lsof -i :80    # 前端
sudo lsof -i :8000  # 后端

# 强制重建容器
docker compose down -v
docker compose up -d --build
```

### 问题 2：无法连接 Jellyfin

- 检查 `JELLYFIN_BASE_URL` 是否正确
- 确保 Jellyfin 服务器正在运行
- 验证 API Key 是否有效
- 如果 Jellyfin 在 Docker 中，使用容器名称而不是 `localhost`

```ini
# 错误示例（Docker 内网络）
JELLYFIN_BASE_URL=http://localhost:8096

# 正确示例
JELLYFIN_BASE_URL=http://jellyfin:8096
# 或使用宿主机 IP
JELLYFIN_BASE_URL=http://192.168.1.100:8096
```

### 问题 3：翻译模型下载失败

```bash
# 检查 Ollama 日志
docker compose logs ollama

# 手动拉取模型
docker compose exec ollama ollama pull qwen2.5:7b-instruct

# 使用国内镜像（可选）
docker compose exec -e OLLAMA_MODELS_DIR=/root/.ollama/models \
  ollama ollama pull qwen2.5:7b-instruct
```

### 问题 4：翻译任务卡住不动

```bash
# 查看 worker 状态
docker compose logs worker

# 重启 worker
docker compose restart worker

# 检查 Redis 连接
docker compose exec redis redis-cli ping
```

### 问题 5：前端无法访问

```bash
# 检查 nginx 配置
docker compose exec frontend nginx -t

# 重启前端容器
docker compose restart frontend

# 检查后端 API 可达性
curl http://localhost/api/health
```

---

## 📚 下一步

恭喜！你已经成功部署 FluxCaption。接下来可以：

1. **阅读完整文档**：查看 `DEPLOYMENT.md` 了解生产环境部署
2. **配置高级功能**：
   - GPU 加速（ASR 和 LLM 推理）
   - 定时自动扫描
   - Sidecar 字幕文件模式
   - 自定义翻译提示词
3. **监控和维护**：
   - 设置日志收集
   - 配置备份策略
   - 启用 Prometheus 监控

**完整文档索引：**

- `DEPLOYMENT.md` - 完整部署指南
- `docs/` - 详细技术文档
- `CLAUDE.md` - 开发者指南

---

## 🆘 获取帮助

遇到问题？

- **GitHub Issues**: https://github.com/yourusername/FluxCaption/issues
- **查看日志**: `docker compose logs -f`
- **健康检查**: http://localhost/health
- **API 文档**: http://localhost/docs

---

**项目主页**: https://github.com/yourusername/FluxCaption
**最后更新**: 2025-10-01
