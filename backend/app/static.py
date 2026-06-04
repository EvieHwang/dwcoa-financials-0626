"""Static-asset serving with SPA fallback (E2 / BC6).

Unknown non-`/api` routes resolve to the SPA `index.html` for client-side
routing; real asset files are served directly; `/api/*` is never shadowed —
an unknown API path 404s as JSON rather than being swallowed as HTML.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response


def register_spa(app: FastAPI, static_dir: str) -> None:
    base = Path(static_dir)

    @app.get("/{full_path:path}")
    def spa(full_path: str, request: Request) -> Response:
        # Never let the SPA catch-all answer for the API namespace.
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        # Serve a real static file when it exists (and stays within base).
        if full_path:
            candidate = (base / full_path).resolve()
            try:
                candidate.relative_to(base.resolve())
            except ValueError:
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            if candidate.is_file():
                return FileResponse(candidate)

        index = base / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
