# FluxCaption .agentdocs 知识中心

## 活跃工作流
- [260320-incomplete-tasks-plan.md](workflow/260320-incomplete-tasks-plan.md) — 项目未完成事项全面补全计划

## 架构决策
- [2026-03-20] FastAPI + Celery + Redis + SQLAlchemy 2 后端架构，多数据库（PG/MySQL/SQLite/MSSQL）
- [2026-03-20] 前端 React 19 + Vite + TanStack Query + Zustand + i18next
- [2026-03-20] AI 服务层通过 UnifiedAIClient 统一，后端 ai_providers/ 多提供商工厂模式

## 已知问题
- ASR 检查点未保存 auto-detect 语言，断点续传时需重跑 ASR（tasks.py:910）
- FunASR asr_factory 工厂分发逻辑存在 pass 占位，未完成
- 多处裸 `except: pass` 静默吞异常（tasks.py, ai_providers.py）
- MediaAsset 找不到时写入空占位数据（library_id="", type="Unknown"）
- 测试体系完全缺失，backend/tests/ 不存在

## 全局重要记忆
- 项目当前版本 v1.4.1，M1 基础已完成，M2-M5 待完成
- 前端 19 个页面均存在，但缺乏 E2E 测试验证
- CI/CD 管道已配置（GitHub Actions），但测试步骤无内容可运行
