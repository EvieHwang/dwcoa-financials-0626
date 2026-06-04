# DWCOA Financials

Financial management dashboard for the Denny Way Condo Owners Association — tracks transactions, budgets, and dues for its 9 units, and generates board-ready reports.

A single always-on Fly app: a FastAPI backend serves the built React frontend
as static assets and exposes a small JSON API backed by SQLite on a mounted volume.

## Layout
- `backend/` — Python + FastAPI service (`app.main:create_app`), SQLite migrations + reference seed, auth, and the API.
- `frontend/` — React + TypeScript + Vite + Tailwind SPA; built assets are served by the backend in production.
- `Dockerfile` / `fly.toml` — multi-stage build and single-app Fly deploy.
- `.github/workflows/deploy.yml` — deploy on push to `main`, gated on a live `/api/health` check.
- `features/` — per-feature spec + test artifacts.

## Develop

### Backend (FastAPI)
```bash
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
# required config (see backend/.env.example):
export ADMIN_PASSWORD_HASH=... BOARD_PASSWORD_HASH=... SESSION_SECRET=... DATABASE_PATH=./dev.db
.venv/bin/uvicorn app.main:app --reload
.venv/bin/pytest        # run the test suite
```

### Frontend (React + Vite)
```bash
cd frontend
pnpm install
pnpm dev                # Vite dev server on http://localhost:5173
pnpm test               # Vitest
pnpm build              # production build + tsc type-check
```

## Configuration
The backend requires `ADMIN_PASSWORD_HASH`, `BOARD_PASSWORD_HASH`, and
`SESSION_SECRET` (it fails fast without them). `DATABASE_PATH` defaults to the
mounted Fly volume path in production. See `backend/.env.example` for the full
list; `FLY_API_TOKEN` is the CI/deploy secret. Passwords are bcrypt hashes;
sessions are HS256 JWTs carried in an `HttpOnly; Secure; SameSite=Lax` cookie.
