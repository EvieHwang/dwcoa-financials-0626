"""Story A — shared-password login, sessions, logout, secret handling."""
import logging

from fastapi.testclient import TestClient

from conftest import ADMIN_PW, BOARD_PW, COOKIE, do_login


def test_login_admin_role(client):
    r = do_login(client, ADMIN_PW)
    assert r.status_code == 200
    assert r.json().get("role") == "admin"


def test_login_viewer_role(client):
    r = do_login(client, BOARD_PW)
    assert r.status_code == 200
    assert r.json().get("role") == "viewer"


def test_login_bad_password_401(client):
    r = do_login(client, "not-the-password")
    assert r.status_code == 401
    # no session established
    assert client.get("/api/auth/me").status_code == 401


def test_login_sets_secure_httponly_cookie(client):
    r = do_login(client, ADMIN_PW)
    set_cookie = r.headers.get("set-cookie", "")
    assert COOKIE in set_cookie
    lowered = set_cookie.lower()
    assert "httponly" in lowered
    assert "secure" in lowered
    assert "samesite=lax" in lowered


def test_login_body_has_no_secrets(client):
    r = do_login(client, ADMIN_PW)
    body = r.text
    # neither the raw password, the bcrypt hash, nor a bare JWT should be echoed
    assert ADMIN_PW not in body
    assert "$2b$" not in body and "$2a$" not in body
    assert "eyJ" not in body  # base64url JWT header prefix


def test_me_returns_role(admin_client):
    r = admin_client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json().get("role") == "admin"


def test_me_no_session_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(admin_client):
    assert admin_client.post("/api/auth/logout").status_code in (200, 204)
    assert admin_client.get("/api/auth/me").status_code == 401


def test_passwords_verified_against_env_hashes(client, monkeypatch):
    # Rotating the env hash to a different password invalidates the old one.
    from conftest import bcrypt_hash
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", bcrypt_hash("rotated-pw"))
    # a freshly built app must honor the new hash and reject the old password
    from app.main import create_app
    from fastapi.testclient import TestClient
    with TestClient(create_app(), base_url="https://testserver") as c2:
        assert do_login(c2, ADMIN_PW).status_code == 401
        assert do_login(c2, "rotated-pw").status_code == 200


def test_login_rate_limited(client):
    # EC2: repeated failures eventually return 429 (bounded attempts per window).
    statuses = [do_login(client, "wrong").status_code for _ in range(25)]
    assert 429 in statuses, f"expected throttling, got {set(statuses)}"


def test_successful_logins_not_throttled(client):
    # EC2: the limiter counts FAILED attempts; a correct password is never throttled.
    statuses = [do_login(client, ADMIN_PW).status_code for _ in range(20)]
    assert all(s == 200 for s in statuses), f"correct password got throttled: {set(statuses)}"


def test_correct_password_succeeds_under_threshold(make_app, monkeypatch):
    # EC2 anti-lockout: a handful of failures (below threshold) must not block the
    # correct password.
    monkeypatch.setenv("LOGIN_MAX_ATTEMPTS", "5")
    with TestClient(make_app(), base_url="https://testserver") as c:
        for _ in range(4):
            assert do_login(c, "wrong").status_code == 401
        assert do_login(c, ADMIN_PW).status_code == 200


def test_no_secret_in_logs(client, caplog):
    # A7 / BC9: neither the submitted password nor any hash leaks into logs.
    secret_pw = "totally-unique-wrong-pw-9173"
    with caplog.at_level(logging.DEBUG):
        do_login(client, secret_pw)
        do_login(client, ADMIN_PW)
    text = caplog.text
    assert secret_pw not in text
    assert ADMIN_PW not in text
    assert "$2b$" not in text and "$2a$" not in text
