# 测试与质量（QA）

> 面向：测试工程师与开发自测

---

## 1. 测试金字塔

- **单元**：Subtitle 解析/保存、提示词生成、OllamaClient `/api/pull` 流解析、DB CRUD。
- **集成**：Ollama + Jellyfin + Redis + DB 打通。
- **端到端（E2E）**：前端发起任务 → SSE 展示进度 → 回写成功 → 前端校验展示。

---

## 2. 多数据库矩阵

- PG / MySQL / SQLite / MSSQL 四套作业：
  - 迁移成功
  - CRUD 与分页一致
  - “缺失语言”筛查查询正确

---

## 3. 典型用例

1. 手动上传 SRT → 翻译 → 下载/预览 → 上传 Jellyfin
2. 媒体无字幕 → ASR 输出 SRT → 翻译 → 上传
3. 模型缺失 → 自动 `/api/pull` → 翻译 → 成功
4. 侧车写回 → Jellyfin 自动识别
5. 长音频 → 分段正确 → 时间轴连续

---

## 4. 质量规则检查

- 空字幕/重复字幕/超长行/标签破坏
- 术语表/禁译词命中情况
- 标点与空白规范化

---

## 5. CI 建议（GitHub Actions）

- Job 1：`pytest -m unit`
- Job 2（矩阵 PG/MySQL/SQLite）：启动服务 → `alembic upgrade head` → `pytest -m "integration and not slow"`
- Job 3：Playwright/Cypress E2E（可选）
