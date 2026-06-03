"""EC1 / EC5 — fail-fast on missing secrets; fresh boot is self-initializing."""
import pytest

from conftest import bcrypt_hash

REQUIRED = ["ADMIN_PASSWORD_HASH", "BOARD_PASSWORD_HASH", "SESSION_SECRET"]


def _set_all(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "d.db"))
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", bcrypt_hash("a"))
    monkeypatch.setenv("BOARD_PASSWORD_HASH", bcrypt_hash("b"))
    monkeypatch.setenv("SESSION_SECRET", "signing-secret")


def test_missing_secret_fails_fast(tmp_path, monkeypatch):
    _set_all(monkeypatch, tmp_path)
    from app.main import create_app

    for var in REQUIRED:
        _set_all(monkeypatch, tmp_path)
        monkeypatch.delenv(var, raising=False)
        with pytest.raises(Exception):
            # must refuse to build rather than boot with an insecure default
            create_app()


def test_fresh_boot_ready(client, viewer_client):
    # app_env gave a fresh tmp DB; startup must migrate + seed with no manual step
    assert client.get("/api/health").json().get("status") == "ok"
    data = viewer_client.get("/api/reference").json()
    assert len(data["units"]) == 9
