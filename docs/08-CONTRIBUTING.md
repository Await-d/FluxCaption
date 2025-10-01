# 协作规范（Contributing）

---

## 1. 分支与提交

- `main`：稳定分支；受保护。
- `feat/*`、`fix/*`：功能/修复分支。
- Commit：遵循 Conventional Commits（`feat: xxx` / `fix: yyy` / `docs: zzz`）。

## 2. 代码风格

- **Python**：ruff + black；mypy（重要模块）。
- **TypeScript**：eslint + prettier。
- **文档**：Markdown + 中文标点规范。

## 3. PR 约定

- 关联 issue；附变更说明与风险评估。
- 新增/修改的 API：更新 `03-API_CONTRACT.md`。
- 涉及 DB：附 Alembic 脚本与回滚评估。
