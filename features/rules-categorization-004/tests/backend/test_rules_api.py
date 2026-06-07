# @frozen — the rules API + sweep contract: admin-only CRUD over /api/rules; a
# successful create/update re-categorizes the OPEN transactions (auto or flagged)
# while leaving manual and migrated-history rows alone; delete never alters
# transactions; /api/rules/suggest returns the smart-stripped pattern. The
# endpoint paths/verbs and the sweep BEHAVIOR are the contract the frontend and
# the treasurer rely on. (The exact /suggest spelling is @scaffolding; its
# returned pattern is frozen.)
"""R5 (CRUD/validation/authz), R6 (sweep), R7 (suggest endpoint)."""
from conftest import (
    bank_row, csv_text, upload, category_id_by_name, get_txn, insert_txn,
    row_by_desc,
)

EVIL = {"Origin": "https://evil.example"}


def _rule_of(res):
    body = res.json()
    return body.get("rule", body)


def _list_rules(admin_client):
    return admin_client.get("/api/rules").json()["rules"]


# --- R5 CRUD ---------------------------------------------------------------

def test_crud_lifecycle(admin_client, app_env):
    cat = category_id_by_name(app_env["db_path"], "Other")
    cat2 = category_id_by_name(app_env["db_path"], "Insurance Premiums")

    # Seeded rules are listable.
    assert len(_list_rules(admin_client)) >= 1

    created = admin_client.post("/api/rules",
                                json={"pattern": "WIDGET CO", "category_id": cat})
    assert created.status_code == 201
    rid = _rule_of(created)["id"]
    assert _rule_of(created)["pattern"] == "WIDGET CO"

    updated = admin_client.patch(f"/api/rules/{rid}",
                                 json={"category_id": cat2, "priority": 50})
    assert updated.status_code == 200
    after = next(r for r in _list_rules(admin_client) if r["id"] == rid)
    assert after["category_id"] == cat2
    assert after["priority"] == 50

    deleted = admin_client.delete(f"/api/rules/{rid}")
    assert deleted.status_code == 200
    assert all(r["id"] != rid for r in _list_rules(admin_client))


def test_create_validation(admin_client, app_env):
    cat = category_id_by_name(app_env["db_path"], "Other")

    # Empty pattern -> 400.
    assert admin_client.post("/api/rules",
                             json={"pattern": "   ", "category_id": cat}
                             ).status_code == 400
    # Bad category -> 400.
    assert admin_client.post("/api/rules",
                             json={"pattern": "GOODPAT", "category_id": 999999}
                             ).status_code == 400
    # Duplicate pattern -> 400.
    assert admin_client.post("/api/rules",
                             json={"pattern": "DUPME", "category_id": cat}
                             ).status_code == 201
    assert admin_client.post("/api/rules",
                             json={"pattern": "DUPME", "category_id": cat}
                             ).status_code == 400


def test_update_missing_404(admin_client):
    assert admin_client.patch("/api/rules/999999",
                              json={"priority": 1}).status_code == 404


def test_delete_preserves_transactions(admin_client, app_env):
    cat = category_id_by_name(app_env["db_path"], "Other")
    rid = _rule_of(admin_client.post(
        "/api/rules", json={"pattern": "WIDGETCO", "category_id": cat}))["id"]
    # Upload a row the rule auto-categorizes.
    upload(admin_client, csv_text([
        bank_row("****9242", "1/15/2026", "WIDGETCO INVOICE", debit="9.00",
                 balance="1.00"),
    ]))
    row = row_by_desc(app_env["db_path"], "WIDGETCO INVOICE")
    assert row["category_id"] == cat and row["needs_review"] == 0

    # Deleting the rule must NOT touch the already-categorized transaction.
    assert admin_client.delete(f"/api/rules/{rid}").status_code == 200
    after = get_txn(app_env["db_path"], row["id"])
    assert after["category_id"] == cat
    assert after["needs_review"] == 0


# --- R5/R10 authz ----------------------------------------------------------

def test_rules_authz(client, viewer_client, admin_client, app_env):
    cat = category_id_by_name(app_env["db_path"], "Other")
    # Admin-only list/suggest.
    assert viewer_client.get("/api/rules").status_code == 403
    assert client.get("/api/rules").status_code == 401
    assert viewer_client.get("/api/rules/suggest?description=ACME 123").status_code == 403
    # Admin-only mutations.
    assert viewer_client.post("/api/rules",
                              json={"pattern": "X", "category_id": cat}
                              ).status_code == 403
    assert client.post("/api/rules",
                       json={"pattern": "X", "category_id": cat}).status_code == 401


def test_rules_cross_origin(admin_client, app_env):
    cat = category_id_by_name(app_env["db_path"], "Other")
    before = len(_list_rules(admin_client))
    res = admin_client.post("/api/rules",
                            json={"pattern": "EVILPAT", "category_id": cat},
                            headers=EVIL)
    assert res.status_code == 403
    assert len(_list_rules(admin_client)) == before  # nothing written


# --- R6 sweep --------------------------------------------------------------

def test_create_rule_sweeps_open_rows(admin_client, app_env):
    # A flagged (needs_review) row already in the store...
    upload(admin_client, csv_text([
        bank_row("****9242", "1/16/2026", "ACME PLUMBING 5571", debit="42.00",
                 balance="458.00"),
    ]))
    row = row_by_desc(app_env["db_path"], "ACME PLUMBING 5571")
    assert row["needs_review"] == 1 and row["category_id"] is None

    cat = category_id_by_name(app_env["db_path"], "Other")
    before_count = admin_client.get(
        "/api/transactions?needs_review=true").json()["total"]

    # ...is caught by a newly created rule, WITHOUT re-upload.
    assert admin_client.post("/api/rules",
                             json={"pattern": "ACME PLUMBING", "category_id": cat}
                             ).status_code == 201

    after = get_txn(app_env["db_path"], row["id"])
    assert after["category_id"] == cat
    assert after["needs_review"] == 0
    after_count = admin_client.get(
        "/api/transactions?needs_review=true").json()["total"]
    assert after_count == before_count - 1


def test_sweep_skips_migrated_categorized(admin_client, app_env):
    # A migrated row: category set, source unset (insert_txn leaves source NULL).
    cat_x = category_id_by_name(app_env["db_path"], "Other")
    cat_y = category_id_by_name(app_env["db_path"], "Insurance Premiums")
    txn_id = insert_txn(
        app_env["db_path"], account_number="****9242", account_name="Checking",
        post_date="2024-05-01", description="MIGRATED ACME ROW", debit=1000,
        balance=0, category_id=cat_x, needs_review=0,
    )
    # A rule that matches it but targets a different category must NOT move it.
    assert admin_client.post("/api/rules",
                             json={"pattern": "MIGRATED ACME", "category_id": cat_y}
                             ).status_code == 201
    after = get_txn(app_env["db_path"], txn_id)
    assert after["category_id"] == cat_x


def test_sweep_corrects_auto(admin_client, app_env):
    cat_x = category_id_by_name(app_env["db_path"], "Other")
    cat_y = category_id_by_name(app_env["db_path"], "Insurance Premiums")

    # Rule A categorizes the upload row to X (auto).
    ra = _rule_of(admin_client.post(
        "/api/rules", json={"pattern": "BETA", "category_id": cat_x}))["id"]
    upload(admin_client, csv_text([
        bank_row("****9242", "1/15/2026", "BETA SERVICE CO", debit="9.00",
                 balance="1.00"),
    ]))
    row = row_by_desc(app_env["db_path"], "BETA SERVICE CO")
    assert row["category_id"] == cat_x

    # A higher-specificity rule B reroutes the auto row to Y on save (sweep).
    rb = _rule_of(admin_client.post(
        "/api/rules", json={"pattern": "BETA SERVICE", "category_id": cat_y}))["id"]
    assert get_txn(app_env["db_path"], row["id"])["category_id"] == cat_y

    # Disabling B re-sweeps the auto row back to A's verdict (X).
    assert admin_client.patch(f"/api/rules/{rb}",
                              json={"active": False}).status_code == 200
    assert get_txn(app_env["db_path"], row["id"])["category_id"] == cat_x


def test_sweep_idempotent(admin_client, app_env):
    cat = category_id_by_name(app_env["db_path"], "Other")
    upload(admin_client, csv_text([
        bank_row("****9242", "1/16/2026", "GAMMA VENDOR 9", debit="42.00",
                 balance="458.00"),
    ]))
    row = row_by_desc(app_env["db_path"], "GAMMA VENDOR 9")
    rid = _rule_of(admin_client.post(
        "/api/rules", json={"pattern": "GAMMA VENDOR", "category_id": cat}))["id"]
    once = get_txn(app_env["db_path"], row["id"])
    assert once["category_id"] == cat and once["needs_review"] == 0

    # A second sweep (re-saving the same rule, unchanged) yields the same state.
    assert admin_client.patch(f"/api/rules/{rid}",
                              json={"category_id": cat}).status_code == 200
    twice = get_txn(app_env["db_path"], row["id"])
    assert twice["category_id"] == cat
    assert twice["needs_review"] == 0


# --- R7 suggest endpoint ---------------------------------------------------

def test_suggest_endpoint(admin_client):
    res = admin_client.get(
        "/api/rules/suggest?description=SEATTLE UTILITIES BILL 12345")
    assert res.status_code == 200
    assert res.json()["pattern"] == "SEATTLE UTILITIES BILL"
