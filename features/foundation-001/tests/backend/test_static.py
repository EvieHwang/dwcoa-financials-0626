"""Story E2 / BC6 — backend serves the SPA without shadowing the API."""
from fastapi.testclient import TestClient


def test_spa_fallback(make_app, tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<!doctype html><title>DWCOA</title>", encoding="utf-8")
    monkeypatch.setenv("STATIC_DIR", str(static_dir))
    with TestClient(make_app(), base_url="https://testserver") as c:
        # an unknown, non-/api client route resolves to the SPA entry
        r = c.get("/dashboard/some/deep/link")
        assert r.status_code == 200
        assert "DWCOA" in r.text


def test_api_routes_not_shadowed(make_app, tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<!doctype html><title>DWCOA</title>", encoding="utf-8")
    monkeypatch.setenv("STATIC_DIR", str(static_dir))
    with TestClient(make_app(), base_url="https://testserver") as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")


def test_unknown_api_route_not_shadowed(make_app, tmp_path, monkeypatch):
    # An unknown /api/* path must 404 — not be swallowed by the SPA catch-all
    # and returned as index.html with 200.
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<!doctype html><title>DWCOA</title>", encoding="utf-8")
    monkeypatch.setenv("STATIC_DIR", str(static_dir))
    with TestClient(make_app(), base_url="https://testserver") as c:
        r = c.get("/api/does-not-exist")
        assert r.status_code == 404
        assert "text/html" not in r.headers.get("content-type", "")
