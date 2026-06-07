# @frozen — the public copy/lock contract: POST /api/budgets/copy and
# /api/budgets/lock, plus locked-year write enforcement (R5). The editor depends
# on these status codes and shapes.
"""R3 (copy), R4 (lock/unlock), R5 (locked enforcement)."""
from conftest import (
    category_id,
    count_budgets,
    get_budget_row,
    insert_budget,
    set_lock,
)

# Unseeded years (seed.py only seeds 2025) so copy/lock/count assertions hold
# against a clean slate rather than tripping over ~20 seeded 2025 rows.
SRC = 2029  # copy source
DST = 2030  # copy target / locked year


def _seed_two_lines(db, year):
    a = category_id(db, "Insurance Premiums")
    b = category_id(db, "Seattle City Light")
    insert_budget(db, year=year, category_id=a, annual_amount=450000,
                  timing="annual")
    insert_budget(db, year=year, category_id=b, annual_amount=600000)
    return a, b


# --- R3: copy ---------------------------------------------------------------

def test_copy_carries_amount_and_timing(admin_client, app_env):
    db = app_env["db_path"]
    a, _ = _seed_two_lines(db, SRC)
    r = admin_client.post("/api/budgets/copy", json={
        "from_year": SRC, "to_year": DST,
    })
    assert r.status_code == 200
    assert r.json()["count"] == 2
    # The annual-timed override is carried, not just the amount.
    copied = get_budget_row(db, year=DST, category_id=a)
    assert copied["annual_amount"] == 450000
    assert copied["timing"] == "annual"


def test_copy_rejects_same_year(admin_client, app_env):
    _seed_two_lines(app_env["db_path"], SRC)
    r = admin_client.post("/api/budgets/copy", json={
        "from_year": SRC, "to_year": SRC,
    })
    assert r.status_code == 400


def test_copy_rejects_empty_source(admin_client):
    # Both source and target are empty/unseeded, so only the empty-source rule
    # can produce the 400 (the target is not non-empty, so 409 cannot fire).
    r = admin_client.post("/api/budgets/copy", json={
        "from_year": 2019, "to_year": 2031,
    })
    assert r.status_code == 400


def test_copy_into_nonempty_target_requires_overwrite(admin_client, app_env):
    db = app_env["db_path"]
    _seed_two_lines(db, SRC)
    # Target already has a line.
    existing = category_id(db, "Fire Alarm")
    insert_budget(db, year=DST, category_id=existing, annual_amount=330000)

    r = admin_client.post("/api/budgets/copy", json={
        "from_year": SRC, "to_year": DST,
    })
    assert r.status_code == 409
    # Target untouched: still exactly the one pre-existing line.
    assert count_budgets(db, DST) == 1
    assert get_budget_row(db, year=DST, category_id=existing)["annual_amount"] == 330000


def test_copy_overwrite_replaces_target(admin_client, app_env):
    db = app_env["db_path"]
    a, b = _seed_two_lines(db, SRC)
    # A different pre-existing target line that should be gone after replace.
    stale = category_id(db, "Fire Alarm")
    insert_budget(db, year=DST, category_id=stale, annual_amount=330000)

    r = admin_client.post("/api/budgets/copy", json={
        "from_year": SRC, "to_year": DST, "overwrite": True,
    })
    assert r.status_code == 200
    # DST now matches SRC's set: the two source lines, and the stale line gone.
    assert count_budgets(db, DST) == 2
    assert get_budget_row(db, year=DST, category_id=stale) is None
    assert get_budget_row(db, year=DST, category_id=a)["annual_amount"] == 450000
    assert get_budget_row(db, year=DST, category_id=b)["annual_amount"] == 600000


# --- R4: lock / unlock ------------------------------------------------------

def test_lock_then_read_reflects_state(admin_client, app_env):
    r = admin_client.post("/api/budgets/lock", json={"year": DST, "locked": True})
    assert r.status_code == 200
    assert r.json()["locked"] is True
    assert r.json()["locked_at"]  # a timestamp is set
    body = admin_client.get(f"/api/budgets?year={DST}").json()
    assert body["locked"] is True


def test_unlock_restores_writeability(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Other")
    set_lock(db, year=DST, locked=True)
    # Locked -> write refused (R5).
    assert admin_client.post("/api/budgets", json={
        "year": DST, "category_id": cid, "annual_amount": 1000,
    }).status_code == 403
    # Unlock, then the same write succeeds.
    admin_client.post("/api/budgets/lock", json={"year": DST, "locked": False})
    assert admin_client.post("/api/budgets", json={
        "year": DST, "category_id": cid, "annual_amount": 1000,
    }).status_code == 200


# --- R5: locked-year write enforcement --------------------------------------

def test_locked_upsert_refused_and_unchanged(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Insurance Premiums")
    insert_budget(db, year=DST, category_id=cid, annual_amount=450000)
    set_lock(db, year=DST, locked=True)
    r = admin_client.post("/api/budgets", json={
        "year": DST, "category_id": cid, "annual_amount": 999999,
    })
    assert r.status_code == 403
    assert get_budget_row(db, year=DST, category_id=cid)["annual_amount"] == 450000


def test_locked_copy_into_refused_and_unchanged(admin_client, app_env):
    db = app_env["db_path"]
    _seed_two_lines(db, SRC)
    set_lock(db, year=DST, locked=True)
    r = admin_client.post("/api/budgets/copy", json={
        "from_year": SRC, "to_year": DST, "overwrite": True,
    })
    assert r.status_code == 403
    assert count_budgets(db, DST) == 0


def test_locked_delete_refused_and_unchanged(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Insurance Premiums")
    insert_budget(db, year=DST, category_id=cid, annual_amount=450000)
    set_lock(db, year=DST, locked=True)
    r = admin_client.delete(f"/api/budgets?year={DST}&category_id={cid}")
    assert r.status_code == 403
    assert get_budget_row(db, year=DST, category_id=cid) is not None
