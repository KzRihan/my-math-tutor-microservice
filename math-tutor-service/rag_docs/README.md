# RAG Documents

Drop your tutoring notes, examples, and syllabus content here.

Supported formats:
- `.md`, `.txt` (plain text)
- `.json` (list of objects with `text` + optional `metadata`)
- `.jsonl` (one JSON object per line)

After adding files, ingest with:

```bash
curl -X POST http://localhost:8000/api/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"rebuild": true}'
```
