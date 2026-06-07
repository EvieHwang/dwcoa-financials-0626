# @frozen — the migration's observable guarantees: the schema gains usable
# rule-condition columns and a per-transaction categorization-source marker;
# startup is idempotent (no duplicate transfer rule); existing categorized data is
# preserved while uncategorized rows are flagged into the review queue. Asserted
# through the app/API and DB state, not against raw column names (those are an
# implementation detail /build owns).
#
# `test_migrated_db_branch` drives `app.migrations.run_migrations` directly and
# stages the MIGRATIONS list to reach the migrated-production precondition (a
# populated rules table with NO transfer rule, plus pre-existing transactions)
# that a fresh test DB cannot otherwise reproduce. The list-staging is a
# @scaffolding mechanism; the asserted outcomes are the frozen contract.
"""R9 (additive, idempotent migration) + R8 (single transfer rule, both paths)."""
import importlib

from conftest import (
    bank_row, csv_text, upload, connect, category_id_by_name, get_txn,
    insert_txn, row_by_desc,
)


def _rules_targeting(db_path, category_name):
    cat = category_id_by_name(db_path, category_name)
    con = connect(db_path)
    try:
        return con.execute(
            "SELECT COUNT(*) FROM categorize_rules WHERE category_id = ?", (cat,)
        ).fetchone()[0]
    finally:
        con.close()


def test_migration_idempotent_no_dup_transfer(make_app, app_env):
    # First startup seeds (fresh DB) -> exactly one transfer rule.
    make_app()
    assert _rules_targeting(app_env["db_path"], "Transfers") == 1
    # A second startup re-runs migrations + seed; both are no-ops -> still one.
    make_app()
    assert _rules_targeting(app_env["db_path"], "Transfers") == 1


def test_conditions_and_source_usable(admin_client, app_env):
    # Create a rule carrying BOTH an account and an amount condition; if the
    # migration didn't add the columns, this round-trip + match cannot work.
    cat = category_id_by_name(app_env["db_path"], "Other")
    res = admin_client.post("/api/rules", json={
        "pattern": "OMEGA", "category_id": cat,
        "account": "Savings", "amount_min": 10000, "amount_max": 20000,
    })
    assert res.status_code == 201

    upload(admin_client, csv_text([
        bank_row("****7145", "1/15/2026", "OMEGA ON SAVINGS",   # right acct+amount
                 debit="150.00", balance="500.00"),
        bank_row("****9242", "1/15/2026", "OMEGA ON CHECKING",  # wrong account
                 debit="150.00", balance="500.00"),
    ]))
    on_savings = row_by_desc(app_env["db_path"], "OMEGA ON SAVINGS")
    on_checking = row_by_desc(app_env["db_path"], "OMEGA ON CHECKING")
    assert on_savings["category_id"] == cat and on_savings["needs_review"] == 0
    assert on_checking["category_id"] is None and on_checking["needs_review"] == 1


def _transfer_rules(db_path):
    """(count of rules targeting Transfers, that count's patterns)."""
    cat = category_id_by_name(db_path, "Transfers")
    con = connect(db_path)
    try:
        rows = con.execute(
            "SELECT pattern FROM categorize_rules WHERE category_id = ?", (cat,)
        ).fetchall()
        return [r["pattern"] for r in rows]
    finally:
        con.close()


def test_migrated_db_branch(app_env):
    """The migrated-production path: a populated rules table lacking a transfer
    rule, with pre-existing transactions. v3 must insert exactly one transfer
    rule, flag the uncategorized backlog, freeze categorized rows, and be
    idempotent on re-run."""
    M = importlib.import_module("app.migrations")
    db = str(app_env["db_path"])
    saved = M.MIGRATIONS
    try:
        # 1) Bring the DB up to *before* v3 (versions 1 and 2 only).
        M.MIGRATIONS = [m for m in saved if m[0] <= 2]
        M.run_migrations(db)

        # 2) Populate a migrated-production-like state: categories, a NON-transfer
        #    rule (so categorize_rules is non-empty), and two pre-existing txns.
        con = connect(db)
        try:
            con.execute("INSERT INTO categories (name, type) VALUES ('Transfers', 'Internal')")
            con.execute("INSERT INTO categories (name, type) VALUES ('Other', 'Expense')")
            other_id = con.execute(
                "SELECT id FROM categories WHERE name='Other'").fetchone()["id"]
            transfers_id = con.execute(
                "SELECT id FROM categories WHERE name='Transfers'").fetchone()["id"]
            con.execute(
                "INSERT INTO categorize_rules (pattern, category_id, confidence, "
                "priority, active) VALUES ('DUMMY', ?, 100, 100, 1)", (other_id,))
            # A categorized historical row (must stay frozen)...
            con.execute(
                "INSERT INTO transactions (account_number, account_name, post_date, "
                "description, balance, category_id, needs_review) "
                "VALUES ('****9242', 'Checking', '2022-01-01', 'OLD CATEGORIZED', "
                "0, ?, 0)", (transfers_id,))
            # ...and an uncategorized historical row (must be flagged for review).
            con.execute(
                "INSERT INTO transactions (account_number, account_name, post_date, "
                "description, balance, category_id, needs_review) "
                "VALUES ('****9242', 'Checking', '2022-02-01', 'OLD UNCATEGORIZED', "
                "0, NULL, 0)")
            con.commit()
        finally:
            con.close()

        # 3) Apply v3.
        M.MIGRATIONS = saved
        M.run_migrations(db)

        # Exactly one transfer rule, with the pinned pattern.
        assert _transfer_rules(db) == ["Transfer"]
        # Uncategorized backlog flagged; categorized history frozen.
        flagged = row_by_desc(db, "OLD UNCATEGORIZED")
        frozen = row_by_desc(db, "OLD CATEGORIZED")
        assert flagged["needs_review"] == 1 and flagged["category_id"] is None
        assert frozen["needs_review"] == 0 and frozen["category_id"] == transfers_id

        # 4) Idempotent re-run: no duplicate transfer rule, no re-flagging churn.
        M.run_migrations(db)
        assert _transfer_rules(db) == ["Transfer"]
        assert row_by_desc(db, "OLD CATEGORIZED")["needs_review"] == 0
    finally:
        M.MIGRATIONS = saved


def test_existing_categories_preserved(make_app, app_env):
    # A pre-existing categorized row (models migrated history) survives a
    # subsequent startup that re-runs migrations + seed.
    make_app()
    cat = category_id_by_name(app_env["db_path"], "Other")
    txn_id = insert_txn(
        app_env["db_path"], account_number="****9242", account_name="Checking",
        post_date="2023-07-01", description="HISTORICAL ROW", debit=5000,
        balance=0, category_id=cat, needs_review=0,
    )
    make_app()  # re-run migrations + seed
    after = get_txn(app_env["db_path"], txn_id)
    assert after["category_id"] == cat
    assert after["needs_review"] == 0
