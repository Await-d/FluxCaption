# Test Data

This directory contains sample subtitle files for testing.

## Files

- `sample.srt` - Simple SRT subtitle file (5 lines)
- `sample.ass` - ASS subtitle file with formatting tags (5 lines)

## Usage

These files can be used to test:
- File upload (`POST /api/upload/subtitle`)
- Translation pipeline
- ASS tag preservation
- Subtitle parsing and saving
- Format conversion

## API Testing Examples

### Upload subtitle file

```bash
curl -X POST http://localhost:8000/api/upload/subtitle \
  -F "file=@tests/test_data/sample.srt"
```

### Create translation job

```bash
curl -X POST http://localhost:8000/api/jobs/translate \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "subtitle",
    "source_path": "/tmp/fluxcaption/xxx.srt",
    "source_lang": "en",
    "target_langs": ["zh-CN"],
    "model": "qwen2.5:7b-instruct",
    "writeback_mode": "upload"
  }'
```

### Stream progress

```bash
curl -N http://localhost:8000/api/jobs/{job_id}/events
```
