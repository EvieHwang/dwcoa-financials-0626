"""A8 / BC8 — same-origin guard on state-changing POST endpoints (CSRF defense)."""
from conftest import ADMIN_PW, do_login


def test_cross_origin_post_rejected(client):
    # A request carrying a foreign Origin must be refused and establish no session.
    r = client.post(
        "/api/auth/login",
        json={"password": ADMIN_PW},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403
    assert client.get("/api/auth/me").status_code == 401


def test_matching_origin_allowed(client):
    # Same-origin Origin (the app's own host) is allowed — the SPA still works.
    r = client.post(
        "/api/auth/login",
        json={"password": ADMIN_PW},
        headers={"Origin": "https://testserver"},
    )
    assert r.status_code == 200


def test_no_origin_allowed(client):
    # No Origin header (non-browser / same-origin navigation) is allowed.
    assert do_login(client, ADMIN_PW).status_code == 200


def test_cross_origin_logout_rejected(admin_client):
    r = admin_client.post("/api/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    # session remains valid because the malicious logout was refused
    assert admin_client.get("/api/auth/me").status_code == 200
