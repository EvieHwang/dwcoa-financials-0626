# @frozen — the review-queue + manual-fix contract: GET /api/transactions
# ?needs_review=true lists/counts only flagged rows; PATCH /api/transactions/{id}
# sets a sticky manual category and clears the flag; manual rows survive a later
# matching rule; authz + CSRF reuse foundation. The PATCH path/verb/body and the
# needs_review filter are the public contract the review UI consumes.
"""R3 (review filter + count) and R4 (single-transaction fix, sticky, authz)."""
from conftest import (
    bank_row, csv_text, upload, category_id_by_name, get_txn, insert_txn,
)

EVIL = {"Origin": "https://evil.example"}


def _seed_one_flagged(admin_client, app_env, desc="ZZQ SPECIAL VENDOR"):
    """Upload one unmatched row; return its id (it lands flagged needs_review)."""
    content = csv_text([
        bank_row("****9242", "1/16/2026", desc, debit="42.00", balance="458.00"),
    ])
    assert upload(admin_client, content).status_code == 200
    from conftest import row_by_desc
    return row_by_desc(app_env["db_path"], desc)["id"]


# --- R3 review filter + count ----------------------------------------------

def test_review_filter_and_count(admin_client, app_env):
    # Self-contained: our own rule categorizes the first row (don't depend on which
    # rules the seed ships); the two ZZQ rows match nothing and stay flagged.
    cat = category_id_by_name(app_env["db_path"], "Other")
    assert admin_client.post(
        "/api/rules", json={"pattern": "DELTA MATCHED", "category_id": cat}
    ).status_code == 201
    content = csv_text([
        bank_row("****9242", "1/15/2026", "DELTA MATCHED VENDOR",  # matched -> not flagged
                 debit="150.00", balance="500.00"),
        bank_row("****9242", "1/16/2026", "ZZQ UNRECOGNIZED ONE",  # flagged
                 debit="42.00", balance="458.00"),
        bank_row("****9242", "1/17/2026", "ZZQ UNRECOGNIZED TWO",  # flagged
                 debit="43.00", balance="415.00"),
    ])
    assert upload(admin_client, content).status_code == 200

    body = admin_client.get("/api/transactions?needs_review=true").json()
    descs = {t["description"] for t in body["transactions"]}
    assert descs == {"ZZQ UNRECOGNIZED ONE", "ZZQ UNRECOGNIZED TWO"}
    assert body["total"] == 2
    # The needs_review flag is exposed per row so the UI can render queue state.
    assert all(t["needs_review"] in (1, True) for t in body["transactions"])


def test_review_list_auth(client, viewer_client, app_env):
    # Unauthenticated cannot read; a viewer can (read is any-role, like the
    # base list). Only the *fix* is admin-only (below).
    assert client.get("/api/transactions?needs_review=true").status_code == 401
    assert viewer_client.get("/api/transactions?needs_review=true").status_code == 200


# --- R4 manual fix: sets, clears flag, sticky ------------------------------

def test_manual_fix_sets_and_sticks(admin_client, app_env):
    txn_id = _seed_one_flagged(admin_client, app_env, "ZZQ SPECIAL VENDOR")
    cat_x = category_id_by_name(app_env["db_path"], "Other")

    res = admin_client.patch(f"/api/transactions/{txn_id}",
                             json={"category_id": cat_x})
    assert res.status_code == 200

    row = get_txn(app_env["db_path"], txn_id)
    assert row["category_id"] == cat_x
    assert row["needs_review"] == 0

    # Now create a rule that MATCHES this description but targets a different
    # category. The manual categorization must survive the sweep untouched (R6).
    cat_y = category_id_by_name(app_env["db_path"], "Insurance Premiums")
    assert cat_y != cat_x
    created = admin_client.post("/api/rules",
                                json={"pattern": "ZZQ SPECIAL", "category_id": cat_y})
    assert created.status_code == 201

    row_after = get_txn(app_env["db_path"], txn_id)
    assert row_after["category_id"] == cat_x      # human choice preserved
    assert row_after["needs_review"] == 0


def test_fix_validation(admin_client, app_env):
    txn_id = _seed_one_flagged(admin_client, app_env, "ZZQ VALIDATION ROW")

    # Non-existent category -> 400, no write.
    bad = admin_client.patch(f"/api/transactions/{txn_id}",
                             json={"category_id": 999999})
    assert bad.status_code == 400
    assert get_txn(app_env["db_path"], txn_id)["category_id"] is None
    assert get_txn(app_env["db_path"], txn_id)["needs_review"] == 1

    # Non-existent transaction -> 404.
    cat = category_id_by_name(app_env["db_path"], "Other")
    missing = admin_client.patch("/api/transactions/888888",
                                 json={"category_id": cat})
    assert missing.status_code == 404


def test_fix_authz(client, viewer_client, admin_client, app_env):
    txn_id = _seed_one_flagged(admin_client, app_env, "ZZQ AUTHZ ROW")
    cat = category_id_by_name(app_env["db_path"], "Other")

    assert viewer_client.patch(f"/api/transactions/{txn_id}",
                               json={"category_id": cat}).status_code == 403
    assert client.patch(f"/api/transactions/{txn_id}",
                        json={"category_id": cat}).status_code == 401
    # Neither rejected request wrote anything.
    assert get_txn(app_env["db_path"], txn_id)["category_id"] is None


def test_fix_cross_origin(admin_client, app_env):
    txn_id = _seed_one_flagged(admin_client, app_env, "ZZQ CSRF ROW")
    cat = category_id_by_name(app_env["db_path"], "Other")
    res = admin_client.patch(f"/api/transactions/{txn_id}",
                             json={"category_id": cat}, headers=EVIL)
    assert res.status_code == 403
    assert get_txn(app_env["db_path"], txn_id)["category_id"] is None
