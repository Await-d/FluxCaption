# FluxCaption 未完成事项补全计划

## 任务概览
基于代码库全面分析，整理项目中未完成、半完成、有缺陷的内容，制定优先级补全方案。

## 当前分析
项目 v1.4.1，M1 基础完成，M2-M5 标记未完成。
代码层面：核心业务逻辑已实现，主要缺口为：测试体系、部分 ASR 逻辑、代码健壮性。

---

## 问题清单

### P0 — 阻断级（影响核心功能正确性）

- [x] T-01: ASR 检查点未保存 auto-detect 语言 (`tasks.py:906-910`) ✅
- [x] T-02: FunASR 工厂分发逻辑（完整实现已存在，确认正常）✅
- [x] T-03: MediaAsset 占位数据写入 DB (`tasks.py`) ✅ 改为 warning+skip
- [x] T-04: `audio_extractor.py` video_file possibly unbound + None 可迭代 ✅
- [x] T-05: `ai_quota_service.py` UTC import 错误 + float|None 类型错误 + None 作为异常类 ✅

### P1 — 质量级（影响稳定性/可维护性）

- [x] T-06: 多处裸 `except: pass` 改为具名异常+日志 (`tasks.py`, `ai_providers.py`) ✅
- [x] T-07: `ai_providers.py:579-586` None 属性访问（usage stats）✅
- [x] T-08: `subtitle_service.py` session 类型注解 object→Session；`unified_ai_client.py` UTC import + None session guard ✅

### P2 — 完备级（功能缺失但有替代路径）

- [x] T-09: 测试体系建设（`backend/tests/` conftest + 3个单元测试模块）✅
- [x] T-10: `jellyfin_client.py:659` user_id 返回空字符串 → 抛出 JellyfinAuthError ✅
- [x] T-11: `custom_openai_provider.py` 硬编码 `dummy` → `no-key-required` ✅

### P3 — 优化级（按需）

- [ ] T-12: `frontend/src/lib/api.ts` 854 行单文件模块化拆分
- [ ] T-13: E2E 测试（Playwright）覆盖主流程

---

## 执行状态

- **P0 全部完成** (2026-03-20)
- **P1 全部完成** (2026-03-20)
- **P2 全部完成** (2026-03-20)
- **P3 可选优化，按需执行**

## 备注
- LSP 诊断中 celery/pysubs2/faster_whisper unresolved import 为虚拟环境未安装的假阳性，不影响运行
- `tasks.py` 中其余 LSP 错误（current_phase/result_paths 等）属于 Pyright 无法推断 query().first() 返回类型，为虚假报错
- 前端 19 个页面功能均已实现，无 stub 页面
