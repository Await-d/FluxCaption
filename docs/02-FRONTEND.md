# 前端开发指南（React 19 · Vite + TS）

> 面向：前端工程师  
> 风格：科技简约 · 深色优先 · 响应式

---

## 1. 技术栈

- **React 19 + TypeScript + Vite**
- **UI**：Tailwind CSS + Radix UI（无障碍 + 原子化）
- **数据**：TanStack Query（请求缓存/重试/轮询）
- **状态**：Zustand（轻量全局 UI 状态）
- **表单**：react-hook-form + zod
- **国际化**：i18next
- **实时**：SSE（`EventSource`）订阅任务进度

---

## 2. 页面结构 & 路由

- `/` 仪表盘：系统概览、正在运行的任务、Ollama 拉取进度。
- `/models` 模型管理：列出本地模型、搜索/拉取、设默认。
- `/library` 媒体库：按库/条目浏览，显示字幕语言矩阵，支持“一键补齐”。
- `/jobs` 任务队列：筛选（状态/时间）、详情、重试。
- `/translate` 手动翻译：上传字幕 → 选择源/目标 → 对照预览 → 提交。
- `/settings` 设置：required_langs、写回模式、并发/资源阈值、术语表。

组件层级示意：
```
App
 ├─ Layout (Header/Sidebar/Theme)
 ├─ DashboardPage
 ├─ ModelsPage
 ├─ LibraryPage
 ├─ JobsPage
 ├─ TranslatePage
 └─ SettingsPage
```

---

## 3. 交互细节

- **进度显示**：SSE 事件按阶段渲染进度条（Resolve/Download/Verify/ASR/MT/Post/Writeback）。
- **对照预览**：左侧原文（锁定时间轴），右侧译文（可编辑微调）。
- **错误处理**：请求层统一 toast；SSE 断线自动重连 + 指数退避。

---

## 4. API 对接示例

**拉取模型**
```ts
await api.post('/api/models/pull', { name: 'qwen2.5:7b-instruct' })
```

**订阅任务进度**
```ts
const es = new EventSource(`/api/jobs/${jobId}/events`)
es.onmessage = (e) => {
  const msg = JSON.parse(e.data) // { phase, status, completed, total }
  setProgress(msg)
}
```

**提交翻译任务**
```ts
await api.post('/api/jobs/translate', {
  source: { type: 'subtitle', pathOrItemId: fileHandle },
  sourceLang: 'auto',
  targets: ['zh-CN'],
  format: 'srt',
  writeback: 'upload',
  model: 'llama3:8b'
})
```

---

## 5. 设计语言与规范

- **排版**：网格布局、10–12px 圆角、弱阴影；重点用中性灰 + 少量品牌强调色。
- **深色主题**：跟随系统，提供开关；Tailwind `dark:` 前缀样式。
- **可访问性**：Radix 组件 + aria 属性；对比度达到 WCAG AA。

---

## 6. 本地开发

```bash
pnpm i
pnpm dev
# .env.local: VITE_API_BASE_URL=http://localhost:8000
```

---

## 7. 性能优化

- 路由级代码分割；TanStack Query 智能缓存与后台刷新。
- 列表虚拟化（媒体库、任务队列）。
- 避免大对象重复渲染（使用 memo/selector）。
