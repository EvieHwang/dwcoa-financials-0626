# [Project Name]

[One-line description of what this app is. Replace when this template is copied.]

## Repo map
- `declaration.md` — what this project is and why it exists
- `constitution.md` — principles, standards, decisions, and project conventions (testing framework, acknowledged risks)
- `features/[feature-name]-[number]/` — per-feature artifacts (`declaration.md`, `spec.md`, `tests/`), produced by `/spec` and `/build` at runtime

## Precedent repos to consult before building
*Other repos that encode patterns this project inherits or replaces. List them here so a fresh build agent knows what to read for ground truth before assuming a precedent.*

- `<owner>/<repo>` — what pattern it provides and how this project relates. [Replace or delete per project. Delete the section entirely if there are no precedent repos.]

If access to a listed repo is scoped out of the current session, ask the user before guessing — earlier specs from precedent repos are not always current and may have been superseded.

## Development environment
Development runs in Claude Code cloud sandboxes attached to this GitHub repo.

- The container is ephemeral and re-cloned each session. Anything not committed and pushed is lost.
- No `~/.claude/CLAUDE.md` exists in the sandbox — user-global preferences are carried at the bottom of this file.
- GitHub access is via the GitHub MCP server (tools prefixed `mcp__github__`). The `gh` CLI is not available.
- **Cloud vs. local for deployment debugging.** Use the cloud session for code-level work; use a local Claude Code session for runtime issues on Eviebot (service not starting, launchd state, live logs, injected env vars) where it can observe the running environment directly. Switch signal: two code-level fixes that should have moved the symptom but didn't usually means the problem is environmental, not in the code.
- Development branch pattern: `claude/<short-task-name>-<suffix>`. The sandbox provisions this branch per session — commit to it, never create a new one. Open a PR to `main` when work is complete. Do not add reviewers or assignees — the repo owner is the sole maintainer and the PR author, so GitHub rejects requesting their review and there is no clean assignee path in this setup.

## Run, test, deps
Pick the block that matches your project's stack. Uncomment it and delete the others. The header on each block describes when to use it.

<!--
### Python service (a backend program or MCP server, typically deployed to Eviebot)
- Install: `python3.11 -m venv .venv && .venv/bin/pip install -e .`
  Creates an isolated Python environment in `.venv/` (a hidden folder) and installs this project into it. The `-e` flag means "editable" — code changes take effect without reinstalling.
- Run locally: `.venv/bin/<script-name>` where `<script-name>` is defined in `pyproject.toml` under `[project.scripts]`.
- Tests: `.venv/bin/pytest` — pytest is the standard Python testing framework.
- Package manager / lockfile: `pyproject.toml` describes dependencies. To add one, edit `pyproject.toml` and re-run the install command.
-->

<!--
### Web frontend (React + Vite + Tailwind + shadcn/ui — the constitution's default frontend stack)
- Install: `pnpm install`
  pnpm is a JavaScript package manager (an alternative to npm). Installs everything listed in `package.json`.
- Run locally: `pnpm dev` — starts the Vite dev server. Open http://localhost:5173 in a browser.
- Tests: `pnpm test` — runs Vitest (the test runner that pairs with Vite).
- Package manager / lockfile: `pnpm` with `pnpm-lock.yaml`. To add a dependency: `pnpm add <package-name>`.
-->

<!--
### Next.js web app (React with built-in routing and server-side rendering)
- Install: `pnpm install`
- Run locally: `pnpm dev` — opens http://localhost:3000.
- Tests: `pnpm test`
- Package manager / lockfile: `pnpm` with `pnpm-lock.yaml`. To add a dependency: `pnpm add <package-name>`.
-->

<!--
### iOS or macOS app (Xcode + Swift)
- Install: open `<ProjectName>.xcodeproj` in Xcode. Swift Package Manager (SwiftPM) resolves dependencies automatically on open. No separate install command.
- Run locally: in Xcode, press Run (⌘R) to launch in the chosen simulator or device.
- Tests: in Xcode, press Test (⌘U). Or from the command line:
  `xcodebuild test -scheme <SchemeName> -destination 'platform=iOS Simulator,name=iPhone 15'`
- Package manager / lockfile: Swift Package Manager (`Package.resolved` — committed automatically by Xcode).
-->


## Deployment target
Pick one. Uncomment the matching block and delete the others.

<!--
### Eviebot (headless always-on Mac mini)
- Service path: `/Users/eviebot/services/<repo-name>/` (must exist before first deploy)
- Venv: `.venv/` inside the service path
- Process management: `launchd`; plists live in `deploy/`
- First load is manual on Eviebot (the runner's non-Aqua session can't bootstrap):
  `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<plist>`
- Subsequent deploys: `launchctl kickstart -k gui/$(id -u)/<label>`
- Deploy via GitHub Actions on push to `main`, on this repo's own Eviebot self-hosted runner (`runs-on: [self-hosted, macOS, ARM64]`).
  Workflow: rsync → create venv → pip install → write `.env` from secrets → kickstart → **post-deploy health check**.
- A deploy is "successful" only if the post-deploy health check against the live service passes — a zero exit from `launchctl kickstart` confirms the kick was sent, not that the service is reachable. The workflow must curl a health endpoint (or equivalent) and fail the job if it doesn't return 2xx within a bounded retry window.
- Before choosing a launchctl label: `launchctl list | grep eviebot` to avoid collisions.
-->

<!--
### AWS (public-facing)
- Account: `070840362692` (user: `eve-hwang`)
- Region: `us-east-1` (confirm per project)
- Credentials: named profiles only; never hardcode keys
- Deploy via GitHub Actions on push to `main`
- A deploy is "successful" only if a post-deploy health check against the live service passes — CloudFormation/ECS/Lambda success codes confirm provisioning, not reachability. The workflow must hit a health endpoint (ALB target check, function invocation, etc.) and fail the job if it doesn't return healthy within a bounded retry window.
-->

<!--
### Apple platform (iOS / macOS via the Xcode Claude extension)
- Specs live in this repo; build runs in Xcode locally
- No CI deploy path; release is a manual Xcode build and submission
- "Deploy success" for an Apple build means the archive builds, signs, and uploads cleanly. There is no live-service health check; treat App Store / TestFlight acceptance as the equivalent gate.
-->

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
