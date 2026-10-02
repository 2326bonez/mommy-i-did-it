# Mommy I Did It 💀

**Build It • Tune It • Finish It.**

A real AI-powered application-building platform. Users describe an app idea,
AI generates a structured plan, and (Phase 1+) real agents build runnable code
with honest verification and full source ownership.

## Phase 0 — Foundation (current)

- Email/password auth (bcrypt + JWT)
- Project CRUD
- AI requirement generation via capability-based Model Provider Layer (OpenAI)
- Neon Postgres in production (fail-fast if `DATABASE_URL` missing — no silent SQLite fallback)
- React + Vite + TypeScript frontend, dark Bonez Labz theme

## Project layout

```
backend/        FastAPI app (auth, projects, requirements, provider layer)
frontend/       React + Vite + TS (built to frontend/dist, served by backend)
requirements.txt
render.yaml     Render blueprint
```

## Local dev

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
cd backend && ../.venv/bin/uvicorn main:app --port 8099
```

Without `DATABASE_URL` the app runs on a local SQLite file with a loud
warning banner (dev only). In production (`RENDER` set or `ENV=production`)
it refuses to boot without `DATABASE_URL`.

Set `OPENAI_API_KEY` to enable AI requirement generation; without it the
endpoint returns a clean 503.

## Deploy (Render)

1. Create the service from `render.yaml` (Blueprint) or manually as a Python web service:
   - Build: `pip install -r requirements.txt`
   - Start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
2. Set env vars: `DATABASE_URL` (Neon), `OPENAI_API_KEY`, `JWT_SECRET` (generate), `ENV=production`.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full platform blueprint
(agents, build protection, verification, connectors, phased plan).
