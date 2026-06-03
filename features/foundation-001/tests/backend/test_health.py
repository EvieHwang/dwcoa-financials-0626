"""Story E1 / EC4 — health endpoint reflects real DB readiness, no auth."""


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_health_no_auth_required(client):
    # no login performed; still reachable
    assert client.get("/api/health").status_code == 200


def test_health_unhealthy_when_db_unreachable(client, monkeypatch):
    # EC4: when the DB probe fails, health must report non-2xx so the deploy
    # gate fails loudly instead of shipping a broken app.
    import app.db as db
    monkeypatch.setattr(db, "check_connection", lambda *a, **k: False)
    r = client.get("/api/health")
    assert r.status_code == 503
