# 客户交付包说明

> 面向：把 FluxCaption 直接交给客户、测试人员、业务同事使用的交付人员。

---

## 1. 交付目标

本说明用于帮助你把当前项目整理成一个**可直接发给客户**的压缩包或共享目录。

客户收到后，只需要：

1. 解压
2. 双击首次配置
3. 双击启动系统
4. 在浏览器里登录使用

---

## 2. 建议交付给客户的文件

建议保留以下内容：

### 根目录必须保留

- `docker-compose.yml`
- `.env.example`
- `quick-client.ps1`
- `quick-setup.cmd`
- `quick-start.cmd`
- `quick-open.cmd`
- `quick-stop.cmd`
- `quick-status.cmd`
- `quick-logs.cmd`
- `01-首次配置.cmd`
- `02-启动系统.cmd`
- `03-打开系统.cmd`
- `04-查看状态.cmd`
- `05-查看日志.cmd`
- `06-停止系统.cmd`

### 文档建议保留

- `README.md`
- `docs/09-QUICK_START_NON_DEVELOPER.md`
- `docs/10-CUSTOMER_HANDOFF_PACKAGE.md`
- `docs/06-DEPLOYMENT_DEVOPS.md`（当客户需要 `.sup/PGS` OCR 时）

### 程序目录必须保留

- `backend/`
- `frontend/`

---

## 3. 不建议交给普通客户的内容

如果客户不需要开发源码协作，可不重点介绍这些内容：

- 测试目录
- CI/CD 目录
- 设计草稿文档
- 开发规范文档

但如果你只是简单打包整个项目目录，保留它们也没问题，只是不要让客户把这些当成主要入口。

---

## 4. 发给客户之前你应该先做什么

### 检查 1：确认 Docker Desktop 已要求客户安装

客户机器必须先有：

- Docker Desktop
- 并且使用前必须先打开 Docker Desktop，等待其完全启动

### 检查 2：确认你已经告诉客户准备这三项信息

- Jellyfin 地址
- Jellyfin API Key
- 媒体目录路径

### 检查 3：建议你预先设置管理员账号密码

建议在 `.env` 里提前设置：

- `INITIAL_ADMIN_USERNAME=admin`
- `INITIAL_ADMIN_PASSWORD=你准备好的密码`

这样客户首次登录不需要再去日志里查随机密码。

---

## 5. 建议的客户操作顺序

你可以直接把下面这段发给客户：

### 第一次使用

1. 双击 `01-首次配置.cmd`
2. 填写 Jellyfin 地址、API Key、媒体目录路径、管理员密码
3. 双击 `02-启动系统.cmd`
4. 等待首次构建完成（第一次会比较慢）
5. 浏览器打开 `http://localhost`
6. 用你刚才设置的管理员账号登录

### 平时使用

1. 双击 `02-启动系统.cmd`
2. 如果页面没自动打开，就双击 `03-打开系统.cmd`

### 关闭系统

1. 双击 `06-停止系统.cmd`

---

## 6. 推荐你发给客户的说明文字模板

你可以直接复制下面这段：

```text
请先安装 Docker Desktop。

收到项目后，请按以下顺序操作：

1. 双击 01-首次配置.cmd
2. 填写 Jellyfin 地址、API Key、媒体目录
3. 双击 02-启动系统.cmd
4. 浏览器访问 http://localhost
5. 使用你设置的管理员账号密码登录

如果打不开：
- 先双击 04-查看状态.cmd
- 再双击 05-查看日志.cmd

关闭系统时：
- 双击 06-停止系统.cmd
```

---

## 7. 如果客户需要 `.sup / PGS` 字幕翻译

需要额外说明：

- 普通文本字幕（`.srt/.ass/.vtt`）可直接用
- 图片字幕（`.sup/.pgs`）需要额外 OCR 运行环境

可参考：

- `docs/06-DEPLOYMENT_DEVOPS.md`

重点让客户或运维关注：

- `PGS_OCR_ENGINE`
- `Subtitle Edit`
- `pgsocr`

---

## 8. 最终建议

如果你的目标是“让客户少问问题，直接能用”，建议交付前就完成：

1. 预先写好 `.env`
2. 预先配置管理员密码
3. 把需要客户双击的文件按顺序编号
4. 把 `docs/09-QUICK_START_NON_DEVELOPER.md` 一起交付

这样客户基本只需要按数字顺序双击即可。
