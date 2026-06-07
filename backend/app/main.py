"""App factory (the testable seam).

`create_app()` reads config from the environment at call time, runs migrations
then seed against the configured database, wires the routers, and registers the
SPA fallback. `app = create_app()` is the uvicorn target.

Startup is idempotent and self-healing: against an empty *or* already-seeded
database it converges to the same ready state without duplication (BC4 / EC5).
"""
from __future__ import annotations

from fastapi import FastAPI

from .auth import RateLimiter
from .config import load_config
from .migrations import run_migrations
from .routers import admin, auth, health, reference, rules, transactions
from .seed import seed_reference_data
from .static import register_spa


def create_app() -> FastAPI:
    # Fails fast if a required secret is missing (EC1 / BC3).
    config = load_config()

    run_migrations(config.database_path)
    seed_reference_data(config.database_path)

    app = FastAPI(title="DWCOA Financials", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.config = config
    app.state.rate_limiter = RateLimiter(
        max_attempts=config.login_max_attempts,
        window_seconds=config.login_window_seconds,
    )

    # API routers first so the SPA catch-all never shadows them.
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(reference.router)
    app.include_router(admin.router)
    app.include_router(transactions.router)
    app.include_router(rules.router)

    # SPA fallback registered last.
    register_spa(app, config.static_dir)

    return app


# uvicorn target. Built at import time from the process environment; in
# production the required secrets are present, so this succeeds.
app = create_app()
