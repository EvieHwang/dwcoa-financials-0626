# @frozen — auth and CSRF on the budgets surface: reads need any session, writes
# need admin and same-origin. Role is server-side only (never client-asserted).
"""R1/R2/R3/R4/R6 auth + CSRF (Reuses pattern: foundation auth + same-origin)."""
from conftest import category_id, get_budget_row, insert_budget

YEAR = 2025

# A cross-origin Origin header to trip the same-origin (CSRF) guard on writes.
CROSS = {"Origin": "https://evil.example"}


# --- reads ------------------------------------------------------------------

def test_read_allowed_for_viewer(viewer_client):
    assert viewer_client.get(f"/api/budgets?year={YEAR}").status_code == 200


def test_read_rejects_anonymous(client):
    assert client.get(f"/api/budgets?year={YEAR}").status_code == 401


# --- writes require admin ---------------------------------------------------

def _cid(app_env):
    return category_id(app_env["db_path"], "Other")


def test_upsert_forbidden_for_viewer(viewer_client, app_env):
    r = viewer_client.post("/api/budgets", json={
        "year": YEAR, "category_id": _cid(app_env), "annual_amount": 1000,
    })
    assert r.status_code == 403
    assert get_budget_row(app_env["db_path"], year=YEAR,
                          category_id=_cid(app_env)) is None


def test_upsert_unauthenticated(client, app_env):
    r = client.post("/api/budgets", json={
        "year": YEAR, "category_id": _cid(app_env), "annual_amount": 1000,
    })
    assert r.status_code == 401


def test_copy_forbidden_for_viewer(viewer_client):
    r = viewer_client.post("/api/budgets/copy", json={
        "from_year": 2024, "to_year": 2025,
    })
    assert r.status_code == 403


def test_lock_forbidden_for_viewer(viewer_client):
    r = viewer_client.post("/api/budgets/lock", json={"year": YEAR, "locked": True})
    assert r.status_code == 403


def test_delete_forbidden_for_viewer(viewer_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Other")
    insert_budget(db, year=YEAR, category_id=cid, annual_amount=1000)
    r = viewer_client.delete(f"/api/budgets?year={YEAR}&category_id={cid}")
    assert r.status_code == 403
    assert get_budget_row(db, year=YEAR, category_id=cid) is not None


# --- CSRF: cross-origin writes refused before any change --------------------

def test_upsert_rejects_cross_origin(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Other")
    r = admin_client.post("/api/budgets", headers=CROSS, json={
        "year": YEAR, "category_id": cid, "annual_amount": 1000,
    })
    assert r.status_code == 403
    assert get_budget_row(db, year=YEAR, category_id=cid) is None


def test_copy_rejects_cross_origin(admin_client):
    r = admin_client.post("/api/budgets/copy", headers=CROSS, json={
        "from_year": 2024, "to_year": 2025,
    })
    assert r.status_code == 403


def test_lock_rejects_cross_origin(admin_client):
    r = admin_client.post("/api/budgets/lock", headers=CROSS,
                          json={"year": YEAR, "locked": True})
    assert r.status_code == 403


def test_delete_rejects_cross_origin(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Other")
    insert_budget(db, year=YEAR, category_id=cid, annual_amount=1000)
    r = admin_client.delete(f"/api/budgets?year={YEAR}&category_id={cid}",
                            headers=CROSS)
    assert r.status_code == 403
    assert get_budget_row(db, year=YEAR, category_id=cid) is not None
