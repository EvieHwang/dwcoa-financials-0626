# Constitution

## Standards
Interface:        Apple Human Interface Guidelines
                  developer.apple.com/design/human-interface-guidelines
Accessibility:    WCAG 2.1 AA
                  w3.org/WAI/WCAG21/quickref
Security:         OWASP Top 10
                  owasp.org/www-project-top-ten
API contracts:    OpenAPI Specification
                  spec.openapis.org

Extended (apply when relevant):
API design:       Microsoft REST API Guidelines
AI integration:   OWASP Top 10 for LLMs
Security depth:   OWASP ASVS

Agents follow these without deviation unless the declaration 
explicitly requires otherwise. Deviation must be surfaced as 
a decision, not made silently.

## Architectural principles
- The spec is the contract. Its requirements are never modified during implementation; if a requirement is wrong, `/build` stops and kicks back to `/spec` rather than patching it mid-build.
- No Docker for local development unless the project has multi-service dependencies that genuinely require it.
- All deployments run through GitHub Actions, triggered by push to `main`.
- Prefer self-hosted runners (Eviebot) over SSH-based deploy steps.

[Add app-specific principles below as they are decided.]

## Patterns in use
- **Frontend stack:** React + TypeScript + Tailwind + shadcn/ui. Vanilla JS is acceptable only for stateless single-page tools.
- **UI aesthetic:** information-dense, 14px base, tight line heights, dark mode as a first-class surface.
- **UX checklist:** apply Nielsen's 10 heuristics as a general sanity-check on any interface; Apple HIG (see Standards) is the authoritative reference for platform decisions.
- **Python service layout:** `pyproject.toml` with a console-script entry point (not `requirements.txt`); deployment plists live in `deploy/` (not `launchd/`).

[Add app-specific patterns below as they are established.]

## Quality gates
- All tests pass — and CI runs the same build the deploy runs. If the test runner doesn't type-check/compile (Vitest, esbuild, isolatedModules), CI also runs the production build (`tsc` / `pnpm build` / `mypy` / `go build`).
- `README.md` and `CLAUDE.md` exist and are current.
- `.env.example` lists every key the deploy workflow injects — no drift between the committed example and the actual required secrets.

[Add app-specific gates below as they are established.]

## Testing
Framework: [populated by /spec on first use]
Run: `[command — populated by /spec on first use]`

## Out of scope
[List what this codebase explicitly does not do. Populated per app.]

## Decision log
| Date | Decision | Rationale |
|------|----------|-----------|
[populated as significant decisions are made]

## Acknowledged risks
*Cross-feature accumulation surface. Each adversarial-gate finding the owner marks `acknowledged` gets one row here so the project never silently forgets that it knowingly took on risk. Severity is the unmitigated severity — an acknowledged HIGH stays HIGH. Populated by `/spec` when a finding is acknowledged.*

| Feature | Finding | Severity | Risk | Rationale | Mitigation |
|---------|---------|----------|------|-----------|------------|
[populated by the adversarial gate in /spec]
