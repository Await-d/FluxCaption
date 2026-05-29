# 非开发人员快速启动与使用指南

> 面向：需要快速启动 FluxCaption 并开始使用的普通用户、测试人员、运维协助人员。

---

## 1. 这套快捷方式适合谁

如果你：

- 不想手工输入很多命令
- 只想快速把系统启动起来
- 主要通过网页界面使用系统

请直接使用仓库根目录这几个文件：

- `quick-setup.cmd`
- `quick-start.cmd`
- `quick-open.cmd`
- `quick-stop.cmd`
- `quick-status.cmd`
- `quick-logs.cmd`

如果你希望使用**中文编号版入口**，也可以直接双击：

- `01-首次配置.cmd`
- `02-启动系统.cmd`
- `03-打开系统.cmd`
- `04-查看状态.cmd`
- `05-查看日志.cmd`
- `06-停止系统.cmd`

---

## 2. 使用前准备

请先安装以下软件：

- **Docker Desktop**
- **Git**（如果你还没有把项目下载到本地）

并且在双击启动前请先确认：

- Docker Desktop 已经启动完成
- Docker 图标状态正常，不是在启动中

建议环境：

- Windows 10 / 11
- 内存 16 GB 或以上
- 系统盘和模型盘有足够空间

---

## 3. 第一次使用

### 步骤 1：打开项目目录

确认你已经进入 FluxCaption 项目根目录，并且能看到这些文件：

- `docker-compose.yml`
- `.env.example`
- `quick-setup.cmd`
- `quick-start.cmd`

### 步骤 2：运行首次配置

双击：

- `quick-setup.cmd`

它会帮你准备 `.env` 并提示你填写：

- Jellyfin 地址
- Jellyfin API Key
- 媒体目录路径（给 Docker 用）
- 初始管理员用户名
- 初始管理员密码

建议：

- Jellyfin 地址示例：`http://192.168.1.10:8096`
- 媒体目录示例：`D:/Media`
- 初始管理员密码请自己设置，避免系统自动随机生成

### 步骤 3：启动系统

双击：

- `quick-start.cmd`

它会自动执行：

- `docker compose up -d --build`

首次启动请预期：

- 可能需要几分钟到十几分钟
- 会下载 Docker 镜像
- 会构建前端与后端环境
- 第一次通常明显比第二次慢

并自动打开浏览器：

- `http://localhost`

---

## 4. 登录系统

默认登录页会要求输入用户名和密码。

如果你在 `quick-setup.cmd` 中填写了：

- `INITIAL_ADMIN_USERNAME`
- `INITIAL_ADMIN_PASSWORD`

请使用你设置的账号密码登录。

如果你没有设置初始密码，系统会随机生成一个管理员密码。
此时请双击：

- `quick-logs.cmd`

然后在日志里搜索：

- `INITIAL ADMIN CREDENTIALS`

你会看到系统首次生成的登录账号密码。

---

## 5. 启动后从哪里进入

网页地址：

- 主界面：`http://localhost`
- API 文档：`http://localhost/docs`

说明：

- Docker 快速启动模式下，**前端已经集成在后端容器里**
- 不需要再单独打开 `5173` 端口

---

## 6. 日常使用顺序

推荐顺序：

1. 打开系统并登录
2. 进入设置或相关页面，检查 Jellyfin 连接配置
3. 进入 AI Provider / AI Models 页面，确认模型可用
4. 进入翻译页或媒体库页，创建字幕翻译任务
5. 进入 Jobs / Live Progress 页面观察任务进度
6. 回到 Jellyfin 或输出目录确认结果

---

## 7. 常用快捷脚本说明

### `quick-setup.cmd`

用途：

- 首次配置 `.env`
- 修改 Jellyfin 地址、API Key、媒体路径、管理员密码

### `quick-start.cmd`

用途：

- 启动全部 Docker 服务
- 自动构建最新镜像
- 自动打开系统页面

### `quick-open.cmd`

用途：

- 只打开浏览器访问系统

### `quick-stop.cmd`

用途：

- 停止当前 Docker 服务

### `quick-status.cmd`

用途：

- 查看服务是否正在运行

### `quick-logs.cmd`

用途：

- 查看后端最近日志
- 排查首次密码、Jellyfin 连接、模型拉取、任务失败等问题

---

## 8. 非开发人员最常见问题

### 1）双击启动后网页打不开

处理方式：

- 先运行 `quick-status.cmd`
- 确认 `backend / postgres / redis / ollama` 服务都在运行
- 如果没启动成功，再看 `quick-logs.cmd`
- 先确认 Docker Desktop 已经完全启动

### 2）登录不上

处理方式：

- 确认你在 `quick-setup.cmd` 中设置了固定管理员密码
- 如果没设置，去 `quick-logs.cmd` 查 `INITIAL ADMIN CREDENTIALS`

### 3）Jellyfin 连不上

请检查：

- Jellyfin URL 是否正确
- Jellyfin API Key 是否有效
- Jellyfin 是否允许当前机器访问

### 4）模型下载很慢

这是正常现象，尤其是第一次启动时。

请查看：

- `quick-logs.cmd`

观察 Ollama / 模型拉取日志。

### 5）上传 `.sup` 字幕后任务失败

原因通常是没有安装 OCR 运行环境。

请参考：

- `docs/06-DEPLOYMENT_DEVOPS.md`

重点查看：

- `PGS_OCR_ENGINE`
- `Subtitle Edit`
- `pgsocr`

---

## 9. 推荐的最简单操作方式

首次：

1. 双击 `quick-setup.cmd`
2. 双击 `quick-start.cmd`

以后每天：

1. 双击 `quick-start.cmd`
2. 如果浏览器没自动打开，就双击 `quick-open.cmd`

不用时：

1. 双击 `quick-stop.cmd`

---

## 10. 面向开发人员的文档

如果你需要更详细的技术部署说明，请看：

- `README.md`
- `docs/06-DEPLOYMENT_DEVOPS.md`
- `docs/01-BACKEND.md`
- `docs/02-FRONTEND.md`
- `docs/10-CUSTOMER_HANDOFF_PACKAGE.md`
