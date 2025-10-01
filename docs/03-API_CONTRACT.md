# API 契约（OpenAPI 摘要）

> Base URL 由环境决定，示例以 `/api` 为前缀。

---

## 1. 模型管理

### GET `/api/models`
- **200**：`{ models: string[] }`

### POST `/api/models/pull`
- **Body**：`{ "name": "qwen2.5:7b-instruct" }`
- **202**：创建拉取任务；进度通过 SSE 下发。

### DELETE `/api/models/{name}`
- **204**：删除成功

---

## 2. Jellyfin 集成

### GET `/api/jellyfin/items`
- **Query**：`parentId?`, `types?=Movie,Episode`, `page?=1`, `pageSize?=50`
- **Fields**：默认包含 `mediaStreams`
- **200**：
```json
{
  "page": 1,
  "pageSize": 50,
  "total": 1234,
  "items": [
    { "id": "JELLYFIN_ITEM_ID",
      "name": "Title",
      "libraryId": "LIB_ID",
      "mediaStreams": {
        "audio": ["en","ja"],
        "subtitles": ["en","zh-CN"]
      }
    }
  ]
}
```

### POST `/api/scan`
- **Body**：`{ "libraryId": "LIB_ID", "targets": ["zh-CN","en"] }`
- **202**：返回被创建的作业数量。

---

## 3. 任务

### POST `/api/jobs/translate`
```json
{
  "source": {"type":"subtitle|audio|media", "pathOrItemId":"..."},
  "sourceLang":"auto|en|zh-CN",
  "targets":["zh-CN"],
  "format":"srt|ass|vtt",
  "writeback":"upload|sidecar",
  "model":"llama3:8b"
}
```
- **202**：`{ "jobId": "..." }`

### GET `/api/jobs/{id}`
- **200**：
```json
{
  "id":"...",
  "status":"running",
  "progress":42.3,
  "phase":"mt",
  "createdAt":"...",
  "logs":[ "...recent messages..." ]
}
```

### SSE `GET /api/jobs/{id}/events`
- **Event**：`message`
- **Data**：`{ "phase": "pull|asr|mt|post|writeback", "status":"...", "completed": 123, "total": 456 }`

---

## 4. 上传（手动翻译）

### POST `/api/upload/subtitle`
- **multipart/form-data**：`file`
- **201**：`{ "handle": "/uploads/xxx.srt" }`
