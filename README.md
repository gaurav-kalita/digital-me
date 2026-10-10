# Digital Me

A personal **retrieval-augmented generation (RAG)** stack: chat with an AI grounded in your own knowledge, plus a Chrome extension that plans and fills web forms from the same data.

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│  Next.js    │────▶│  ai-service  │────▶│  Ollama / OpenAI        │
│  frontend   │     │  (FastAPI)   │     │  (generation)           │
└─────────────┘     └──────┬───────┘     └─────────────────────────┘
                           │
┌─────────────┐            │  FAISS + optional Redis cache
│  Chrome     │────────────┤
│  extension  │            ▼
└─────────────┘     ┌──────────────┐
                    │  data/       │  profile, skills, projects, …
                    └──────────────┘
```

## Why this repo

| Piece | Role |
|--------|------|
| **`ai-service/`** | FastAPI backend: offline indexing, LlamaIndex-first retrieval, chat, health, form-fill planning |
| **`frontend/`** | Next.js UI that proxies `/api/chat` and `/api/health` to the backend |
| **`browser-extension/`** | Manifest V3 extension: scan forms → `POST /forms/plan` → autofill |
| **`data/`** | Curated JSON/Markdown knowledge (sample personal corpus included) |

The backend uses **clean architecture** (application use cases, ports, infrastructure adapters) with a single composition root in `app/bootstrap/composition.py`.

## Prerequisites

- **Python 3.11+** (3.8 may work locally but CI targets 3.11)
- **Node.js 20+** for the frontend
- **[Ollama](https://ollama.com/)** (default LLM) or OpenAI-compatible API
- **Redis** (optional; improves retrieval caching — service runs degraded without it)

## Quick start

### 1. Backend

```powershell
cd ai-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env if needed (Ollama URL, models, paths)

python scripts\rebuild_index.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Frontend

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app talks to the backend via `AI_SERVICE_URL` (default `http://127.0.0.1:8000`).

### 3. Chrome extension (optional)

1. Open `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select `browser-extension/`
3. In extension options, set the backend URL if not using port 8000

See [browser-extension/README.md](browser-extension/README.md) for the form-fill flow.

## Knowledge base

- Source files live under `data/` (`profile.json`, `skills.json`, `projects/`, etc.).
- Generated indexes are written to `data/.index/` (gitignored). Rebuild after changing sources:

```powershell
cd ai-service
python scripts\rebuild_index.py
```

Replace the sample JSON with your own content; keep the same structure or extend loaders in `ai-service/app/data_layer/`.

## Configuration

Copy `ai-service/.env.example` to `ai-service/.env`. Important knobs:

| Variable | Purpose |
|----------|---------|
| `LLM_TYPE` | `ollama` or `openai` |
| `OLLAMA_MODEL` / `OPENAI_MODEL` | Generation model |
| `RETRIEVAL_BACKEND` | `llamaindex` (default) or native FAISS path |
| `REDIS_CACHE_ENABLED` | Toggle retrieval cache |
| `GUARDRAIL_ENABLED` | Restrict off-topic prompts |

Full reference: [ai-service/README.md](ai-service/README.md).

## Development

```powershell
# Backend tests (uses hashing embedder in CI; local may use sentence-transformers)
cd ai-service
pytest -q

# Frontend production build
cd frontend
npm run build
```

GitHub Actions runs both jobs on push/PR (see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health/` | Readiness: `healthy`, `degraded`, or `503` |
| `POST` | `/chat/` | RAG chat with sources |
| `POST` | `/forms/plan` | Structured fill plan for browser automation |

## Project layout

```text
digital-me/
  ai-service/          # FastAPI RAG + form planning
  frontend/            # Next.js chat UI
  browser-extension/   # Chrome MV3 autofill
  data/                # Knowledge corpus + local index output
  .github/workflows/   # CI
```

## License

[MIT](LICENSE) — Copyright (c) 2026 Gaurav Kalita

## Contributing

Issues and pull requests are welcome. Run `pytest` and `npm run build` before opening a PR.
