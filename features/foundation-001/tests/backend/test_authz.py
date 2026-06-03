"""Story B — role is server-authoritative; client cannot assert privilege."""
import datetime as dt

import jwt

from conftest import COOKIE, SESSION_SECRET


def _token(role, secret=SESSION_SECRET, exp_delta=dt.timedelta(hours=1)):
    payload = {"role": role, "exp": dt.datetime.now(dt.timezone.utc) + exp_delta}
    return jwt.encode(payload, secret, algorithm="HS256")


def test_admin_config_admin_200(admin_client):
    assert admin_client.get("/api/admin/config").status_code == 200


def test_admin_config_viewer_403(viewer_client):
    assert viewer_client.get("/api/admin/config").status_code == 403


def test_admin_config_anon_401(client):
    assert client.get("/api/admin/config").status_code == 401


def test_reference_allows_both_roles(admin_client, viewer_client):
    assert admin_client.get("/api/reference").status_code == 200
    assert viewer_client.get("/api/reference").status_code == 200


def test_role_header_ignored(viewer_client):
    # A viewer that injects an admin role via header/body must stay a viewer.
    r = viewer_client.get("/api/admin/config", headers={"X-Role": "admin", "Role": "admin"})
    assert r.status_code == 403


def test_tampered_cookie_rejected(client):
    # Valid-looking JWT signed with the WRONG secret must not grant access.
    forged = _token("admin", secret="attacker-guessed-secret")
    r = client.get("/api/admin/config", cookies={COOKIE: forged})
    assert r.status_code in (401, 403)
    # garbage cookie -> treated as no session, not a 500
    r2 = client.get("/api/auth/me", cookies={COOKIE: "not-a-jwt"})
    assert r2.status_code == 401


def test_expired_token_401(client):
    expired = _token("admin", exp_delta=dt.timedelta(seconds=-10))
    r = client.get("/api/auth/me", cookies={COOKIE: expired})
    assert r.status_code == 401
