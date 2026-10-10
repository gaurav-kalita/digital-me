# Frontend

Next.js chat UI for the `ai-service` backend. Override the backend with `AI_SERVICE_URL` in `.env.local`.

## Run

```powershell
cd frontend
npm ci
copy .env.example .env.local
npm run dev
```

The app talks to the backend through Next.js route handlers:

- `GET /api/health` -> `ai-service /health/`
- `POST /api/chat` -> `ai-service /chat/`

Default backend URL:

```text
http://127.0.0.1:8000
```
