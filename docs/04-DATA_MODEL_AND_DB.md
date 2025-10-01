# 数据模型与多数据库策略

> 面向：后端/DBA/DevOps

---

## 1. 统一建模原则

- **主键**：`GUID → CHAR(36)`；TypeDecorator 透明转换。
- **枚举**：`String` + Pydantic 校验，避免方言差异。
- **集合**：媒体语言集合用**子表**；任务目标语言用 **JSON**。
- **时间**：存 UTC（`DateTime(timezone=True)`）。
- **幂等**：服务层“先查后写”或 `UPDATE→INSERT`，不使用方言 UPSERT。

---

## 2. 表设计（摘要）

### 2.1 translation_jobs
- `id GUID PK`
- `item_id String(64)`
- `source_type String(16)` (`subtitle|audio|media`)
- `source_path String(1024)`
- `source_lang String(20)`
- `target_langs JSON`
- `model String(100)`
- `status String(16)`（`queued/running/success/failed/canceled`）
- `progress Float`
- `error Text`
- `created_at/started_at/finished_at DateTime(tz=True)`
- **索引**：`(status, created_at)`

### 2.2 media_assets
- `id GUID PK`
- `jellyfin_item_id String(64) UNIQUE`
- `library_id String(64)`
- `path String(1024)`
- `duration Integer`
- `has_pgs Boolean`
- `checksum String(64)`
- `updated_at DateTime(tz=True)`

### 2.3 media_audio_langs / media_subtitle_langs
- `id GUID PK`
- `asset_id GUID FK`
- `lang String(20)`
- **索引**：`asset_id`, `lang`

### 2.4 subtitles
- `id GUID PK`
- `item_id String(64)`
- `lang String(20)`
- `format String(8)`（srt/ass/vtt）
- `storage String(16)`（fs/s3/jellyfin）
- `path_or_url String(1024)`
- `origin String(16)`（asr/mt/manual）
- `checksum String(64)`
- `created_at DateTime(tz=True)`

---

## 3. 连接字符串与驱动

| 数据库 | 驱动 | URL |
|---|---|---|
| PostgreSQL | psycopg | `postgresql+psycopg://user:pass@host:5432/ai_subs` |
| MySQL/MariaDB | pymysql/mysqlclient | `mysql+pymysql://user:pass@host:3306/ai_subs` |
| SQLite | 内置 | `sqlite:///./ai_subs.db` |
| SQL Server | pyodbc | `mssql+pyodbc:///?odbc_connect=...` |

---

## 4. 迁移与 CI 矩阵

- `alembic upgrade head` 统一迁移。
- CI 对 PG/MySQL/SQLite/MSSQL 跑：建表 → CRUD → 关键查询。
- 如需 JSON 复杂过滤：优先“冗余列 + 索引”而非方言 JSON 索引。

---

## 5. 查询模式建议

- **Keyset 分页**优先，避免大偏移。
- 大规模“缺失语言”筛查示例：
```sql
SELECT a.*
FROM media_assets a
WHERE NOT EXISTS (
  SELECT 1 FROM media_subtitle_langs s
  WHERE s.asset_id = a.id AND s.lang = :target
)
```
