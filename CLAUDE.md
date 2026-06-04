# DWCOA Financials

<!-- Financial management dashboard for the Denny Way Condo Owners Association — tracks transactions, budgets, and dues for its 9 units, and generates board-ready reports. -->

## Repo map
- `declaration.md` — what this project is and why it exists
- `constitution.md` — principles, standards, decisions, and project conventions (testing framework, acknowledged risks)
- `features/[feature-name]-[number]/` — per-feature artifacts (`declaration.md`, `spec.md`, `tests/`), produced by `/spec` and `/build` at runtime

## Precedent repos to consult before building
*Other repos that encode patterns this project inherits or replaces. List them here so a fresh build agent knows what to read for ground truth before assuming a precedent.*

- `EvieHwang/dwcoa-financials` (also vendored at `reference/dwcoa-financials/`) — the legacy AWS-serverless app this project rebuilds; source of the data model, categorize rules, and the legacy SQLite schema. **Caveat: the vendored snapshot is stale relative to live production.** The production `dwcoa.db` (in S3) has been migrated past it — e.g. it has `timing` columns on `categories` and `budgets` that `reference/.../sql/schema.sql` and `services/database.py` never add. Trust an empirical dump of the live DB over the vendored schema when they disagree.

If access to a listed repo is scoped out of the current session, ask the user before guessing — earlier specs from precedent repos are not always current and may have been superseded.

## Development environment
Development runs in Claude Code cloud sandboxes attached to this GitHub repo.

- The container is ephemeral and re-cloned each session. Anything not committed and pushed is lost.
- No `~/.claude/CLAUDE.md` exists in the sandbox — user-global preferences are carried at the bottom of this file.
- GitHub access is via the GitHub MCP server (tools prefixed `mcp__github__`). The `gh` CLI is not available.
- **Cloud vs. local for deployment debugging.** Use the cloud session for code-level work; use a local Claude Code session for runtime issues on Eviebot (service not starting, launchd state, live logs, injected env vars) where it can observe the running environment directly. Switch signal: two code-level fixes that should have moved the symptom but didn't usually means the problem is environmental, not in the code.
- Development branch pattern: `claude/<short-task-name>-<suffix>`. The sandbox provisions this branch per session — commit to it, never create a new one. Open a PR to `main` when work is complete. Do not add reviewers or assignees — the repo owner is the sole maintainer and the PR author, so GitHub rejects requesting their review and there is no clean assignee path in this setup.

## Run, test, deps
Two-part repo: a Python/FastAPI backend and a React/Vite frontend. The backend serves the built frontend as static assets in production (single Fly app).

### Backend (Python — FastAPI, `pyproject.toml`)
- Install: `cd backend && python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
  Creates an isolated Python environment in `.venv/` and installs the project (with dev/test extras) in editable mode — code changes take effect without reinstalling.
- Run locally: `.venv/bin/uvicorn app.main:app --reload` — starts the dev API server with auto-reload.
- Tests: `.venv/bin/pytest`
- Package manager / lockfile: `pyproject.toml` describes dependencies. To add one, edit `pyproject.toml` and re-run the install command.

### Frontend (React + TypeScript + Vite + Tailwind + shadcn/ui)
- Install: `cd frontend && pnpm install`
  pnpm is a JavaScript package manager (an alternative to npm). Installs everything listed in `package.json`.
- Run locally: `pnpm dev` — starts the Vite dev server. Open http://localhost:5173 in a browser.
- Tests: `pnpm test` — runs Vitest.
- Production build: `pnpm build` — emits static assets and serves as the CI type-check (`tsc`).
- Package manager / lockfile: `pnpm` with `pnpm-lock.yaml`. To add a dependency: `pnpm add <package-name>`.


## Deployment target

### Fly.io (single always-on app)
- App + config: `fly.toml` at repo root; a Dockerfile builds the backend image and bundles the built frontend, which the backend serves as static assets (one deployable, no separate origin / CORS setup).
- Persistence: SQLite on a mounted Fly volume; periodic backup (e.g. Litestream or scheduled volume snapshot).
- Region: primary `sjc` (San Jose — nearest available Fly region to the HOA in Seattle; `sea` is not offered to this org).
- Secrets: set via `fly secrets set` (mirror of the repo's GitHub Actions secrets); the deploy workflow authenticates with `FLY_API_TOKEN`.
- Deploy via GitHub Actions on push to `main`, on a GitHub-hosted runner: `flyctl deploy --remote-only`. No self-hosted runner needed.
- A deploy is "successful" only if a post-deploy health check against the live app passes — a zero exit from `flyctl deploy` confirms the release was created, not that the app is reachable. The workflow must curl a health endpoint and fail the job if it doesn't return 2xx within a bounded retry window.

## Secrets
- Canonical source: the **1Password "Eviebot" vault**, one item per service (item name matches the repo), each secret a custom field named exactly for its env var.
- Workflows read secrets from **repository-level GitHub Actions secrets**, which are a manual mirror of 1Password. 1Password is authoritative — on any conflict, 1Password wins.
- Commit a `.env.example` listing every required key with no values.
- Never commit `.env` or any file containing secret values.
- On deploy, the workflow injects secrets into the chosen target (writes `.env` on Eviebot, sets env vars on AWS, configures the Xcode build). Anything on the target is an artifact of deployment, not a source of truth — if the target is rebuilt, the next deploy recreates it.
- Adding a new secret: add the field to the 1Password item → sync it into the repo's GitHub Actions secrets → add the key to `.env.example` → add the inject step to the deploy workflow.

---

## User globals — Evie Hwang
*Carried in this file because Claude Code cloud sandboxes have no `~/.claude/CLAUDE.md`. These coordinates apply to every project, not just this one.*

### GitHub
- One account: `EvieHwang` (personal). All repos, secrets, and runners live here.
- Deployment target is a per-project choice — AWS, Eviebot, or Apple platform — driven by the workload, not by which account hosts the repo.
- Self-hosted runners are **per repository** (a personal account can't host an org-level runner). Each Eviebot-deployed repo gets its own runner registered to it.

### AWS
- Account: `070840362692` (user: `eve-hwang`)
- Default region: `us-east-1`

### Eviebot — runtime server
- Mac mini, headless, always-on. macOS — use `launchd`, not systemd.
- Runner user: `eviebot`. All paths under `/Users/eviebot/`.
- Services live at `/Users/eviebot/services/<repo-name>/` with a venv at `.venv/`.
- Use `python3.11` (Homebrew) when 3.10+ is needed; otherwise confirm `python3 --version` before assuming.

#### Self-hosted runners (per repo)
- One runner per Eviebot-deployed repo, each installed at `~/actions-runner-<repo>/`.
- Labels: `[self-hosted, macOS, ARM64]`; workflows target it with `runs-on: [self-hosted, macOS, ARM64]`.
- Managed via `launchd` through the runner's own script: `cd ~/actions-runner-<repo>/ && ./svc.sh start|stop|status|restart`.
- Adding a runner to a new repo: generate a registration token for the repo, then on Eviebot `mkdir -p ~/actions-runner-<repo> && cd ~/actions-runner-<repo>`, download and extract the runner, `./config.sh --url https://github.com/EvieHwang/<repo> --token <TOKEN>`, then `./svc.sh install && ./svc.sh start`.

### Gateway integration
- Gateway repo: `eviebot-mcp-gateway`, running on port 8080.
- To add a new MCP backend, follow the gateway repo's `CLAUDE.md` exactly. Port allocation, auth patterns (A/B), and the `gateway.py` block are defined there — read it first.
- Check existing service labels with `launchctl list | grep eviebot` before choosing a new one.
