# @frozen — the public ingestion contract: POST /api/transactions/upload, its
# dedup/idempotency/atomicity behavior, exact-cents storage, account mapping,
# authz, and the response summary. These survive any refactor of the internals.
# (One named knob — the INGEST_MAX_UPLOAD_BYTES env var in the oversize test — is
# scaffolding; /build may rename it, but the "oversize rejected, nothing
# inserted" behavior is frozen.)
"""R2, R4, R5, R6, R7, R8, R10 verified through the API against a real DB."""
from conftest import (
    ADMIN_PW, UNKNOWN_ACCT, bank_row, csv_text, upload, do_login,
    connect, count_transactions, first_category_id,
)


def _row_by_desc(db_path, description):
    con = connect(db_path)
    try:
        return con.execute(
            "SELECT * FROM transactions WHERE description = ?", (description,)
        ).fetchone()
    finally:
        con.close()


# --- R2: exact cents, NULL, sign (end-to-end) ------------------------------

def test_amounts_stored_as_exact_cents(admin_client, app_env):
    content = csv_text([
        bank_row("****9226", "1/27/2026", "Deposit Reserve Funds",
                 credit="3,326.00", balance="121243.17"),
        bank_row("****9226", "2/6/2026", "Overdraft Protection Withdraw",
                 debit="$538.07", balance="-50.00"),
    ])
    assert upload(admin_client, content).status_code == 200

    deposit = _row_by_desc(app_env["db_path"], "Deposit Reserve Funds")
    assert deposit["credit"] == 332600
    assert deposit["debit"] is None          # empty cell -> NULL, not 0
    assert deposit["balance"] == 12124317

    overdraft = _row_by_desc(app_env["db_path"], "Overdraft Protection Withdraw")
    assert overdraft["debit"] == 53807        # "$538.07" -> 53807
    assert overdraft["credit"] is None
    assert overdraft["balance"] == -5000       # negative preserved


# --- R7: account mapping ---------------------------------------------------

def test_mapped_account_name(admin_client, app_env):
    content = csv_text([
        bank_row("****9242", "1/15/2026", "Check Payment", debit="100.00",
                 balance="500.00"),
    ])
    assert upload(admin_client, content).status_code == 200
    row = _row_by_desc(app_env["db_path"], "Check Payment")
    assert row["account_name"] == "Checking"
    assert row["account_number"] == "****9242"


def test_unknown_account_imported_and_flagged(admin_client, app_env):
    content = csv_text([
        bank_row(UNKNOWN_ACCT, "1/10/2026", "Mystery Deposit", credit="42.00",
                 balance="42.00"),
    ])
    r = upload(admin_client, content)
    assert r.status_code == 200
    body = r.json()
    # imported (added), not dropped, not a hard error
    assert body["added"] == 1
    assert body["unknown_account_count"] == 1
    assert UNKNOWN_ACCT in body["unknown_accounts"]
    row = _row_by_desc(app_env["db_path"], "Mystery Deposit")
    assert row["account_name"] == "Unknown"
    assert row["account_number"] == UNKNOWN_ACCT


# --- R8: summary -----------------------------------------------------------

def test_summary_counts(admin_client):
    content = csv_text([
        bank_row("****9226", "1/1/2026", "A", credit="1.00", balance="1.00"),
        bank_row("****9226", "1/2/2026", "B", credit="2.00", balance="3.00"),
        bank_row("****9226", "1/2/2026", "B", credit="2.00", balance="3.00"),  # in-file dup
    ])
    body = upload(admin_client, content).json()
    assert body["added"] == 2
    assert body["skipped_duplicate"] == 1
    assert body["total"] == 3


# --- R4: idempotency / dedup ----------------------------------------------

def test_reupload_is_noop(admin_client, app_env):
    content = csv_text([
        bank_row("****9226", "1/31/2026", "Dividend/Interest", credit="25.15",
                 balance="121268.32"),
        bank_row("****9226", "1/27/2026", "Deposit Reserve Funds", credit="3326.00",
                 balance="121243.17"),
    ])
    assert upload(admin_client, content).json()["added"] == 2
    assert count_transactions(app_env["db_path"]) == 2

    second = upload(admin_client, content).json()
    assert second["added"] == 0
    assert second["skipped_duplicate"] == 2
    assert count_transactions(app_env["db_path"]) == 2  # no growth


def test_overlapping_upload_adds_only_new(admin_client, app_env):
    first = csv_text([
        bank_row("****9226", "1/1/2026", "A", credit="1.00", balance="1.00"),
    ])
    upload(admin_client, first)
    overlap = csv_text([
        bank_row("****9226", "1/1/2026", "A", credit="1.00", balance="1.00"),  # existing
        bank_row("****9226", "1/2/2026", "B", credit="2.00", balance="3.00"),  # new
    ])
    body = upload(admin_client, overlap).json()
    assert body["added"] == 1
    assert body["skipped_duplicate"] == 1
    assert count_transactions(app_env["db_path"]) == 2


def test_in_file_duplicate_inserted_once(admin_client, app_env):
    row = bank_row("****9226", "1/2/2026", "B", credit="2.00", balance="3.00")
    upload(admin_client, csv_text([row, row]))
    con = connect(app_env["db_path"])
    try:
        n = con.execute("SELECT COUNT(*) FROM transactions WHERE description='B'").fetchone()[0]
    finally:
        con.close()
    assert n == 1


def test_distinct_account_or_balance_not_deduped(admin_client, app_env):
    # Same date/amount/description, but different account, and different balance:
    # both must survive because account_number and balance are in the identity.
    content = csv_text([
        bank_row("****9226", "1/5/2026", "Transfer", debit="100.00", balance="900.00"),
        bank_row("****9242", "1/5/2026", "Transfer", debit="100.00", balance="900.00"),
        bank_row("****9226", "1/5/2026", "Transfer", debit="100.00", balance="800.00"),
    ])
    body = upload(admin_client, content).json()
    assert body["added"] == 3
    assert count_transactions(app_env["db_path"]) == 3


# --- R5: category preservation --------------------------------------------

def test_reupload_preserves_category(admin_client, app_env):
    content = csv_text([
        bank_row("****9226", "1/9/2026", "Dues 101 Payment", credit="200.00",
                 balance="200.00"),
    ])
    upload(admin_client, content)
    db_path = app_env["db_path"]

    # treasurer categorizes the stored row
    cat_id = first_category_id(db_path)
    con = connect(db_path)
    try:
        con.execute("UPDATE transactions SET category_id = ? WHERE description = ?",
                    (cat_id, "Dues 101 Payment"))
        con.commit()
        original_id = con.execute(
            "SELECT id FROM transactions WHERE description='Dues 101 Payment'"
        ).fetchone()[0]
    finally:
        con.close()

    # re-upload the same file
    second = upload(admin_client, content).json()
    assert second["added"] == 0

    row = _row_by_desc(db_path, "Dues 101 Payment")
    assert row["category_id"] == cat_id      # category survived
    assert row["id"] == original_id          # same row, not replaced
    assert count_transactions(db_path) == 1


# --- R6: atomicity / structural + row errors ------------------------------

def test_structural_error_inserts_nothing(admin_client, app_env):
    header = ["Account Number", "Post Date", "Description", "Debit", "Credit"]  # no Balance
    bad = csv_text([["****9226", "1/1/2026", "x", "1.00", ""]], header=header)
    r = upload(admin_client, bad)
    assert r.status_code == 400
    assert count_transactions(app_env["db_path"]) == 0


def test_bad_amount_rejects_whole_file(admin_client, app_env):
    content = csv_text([
        bank_row("****9226", "1/1/2026", "Good", credit="1.00", balance="1.00"),
        bank_row("****9226", "1/2/2026", "Bad", credit="not-money", balance="3.00"),
    ])
    r = upload(admin_client, content)
    assert r.status_code == 400
    assert count_transactions(app_env["db_path"]) == 0  # the good row is NOT inserted


def test_bad_date_rejects_whole_file(admin_client, app_env):
    content = csv_text([
        bank_row("****9226", "13/45/2026", "Bad Date", credit="1.00", balance="1.00"),
    ])
    r = upload(admin_client, content)
    assert r.status_code == 400
    assert count_transactions(app_env["db_path"]) == 0


# --- R10: authz + CSRF + size ---------------------------------------------

def test_upload_requires_admin(viewer_client, client, app_env):
    content = csv_text([
        bank_row("****9226", "1/1/2026", "X", credit="1.00", balance="1.00"),
    ])
    assert upload(viewer_client, content).status_code == 403   # view-only forbidden
    assert upload(client, content).status_code == 401          # anonymous unauthorized
    assert count_transactions(app_env["db_path"]) == 0


def test_upload_cross_origin_rejected(admin_client, app_env):
    content = csv_text([
        bank_row("****9226", "1/1/2026", "X", credit="1.00", balance="1.00"),
    ])
    r = upload(admin_client, content, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert count_transactions(app_env["db_path"]) == 0


def test_oversize_upload_rejected(make_app, monkeypatch, app_env):
    # A clearly-oversize upload is refused without being fully ingested (R10).
    monkeypatch.setenv("INGEST_MAX_UPLOAD_BYTES", "2048")
    from fastapi.testclient import TestClient
    with TestClient(make_app(), base_url="https://testserver") as c:
        assert do_login(c, ADMIN_PW).status_code == 200
        big = csv_text([
            bank_row("****9226", "1/1/2026", "padding " * 8, credit="1.00",
                     balance=f"{i}.00")
            for i in range(200)
        ])
        assert len(big.encode()) > 2048
        r = upload(c, big)
        assert r.status_code in (400, 413)
    assert count_transactions(app_env["db_path"]) == 0
