"""R3-R7 — the importer transforms the legacy DB into the new schema exactly.

Expected cent values are computed here independently (via Decimal) rather than
through the importer's own converter, so the importer is checked against a
parallel implementation, not against itself.
"""
from decimal import ROUND_HALF_UP, Decimal

import pytest

from conftest import (
    LEGACY_BUDGETS,
    LEGACY_TRANSACTIONS,
    LEGACY_UNIT_PAST_DUES,
    connect,
)


def cents(dollars):
    if dollars is None:
        return None
    return int((Decimal(str(dollars)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


# --- R3: primary keys, foreign keys, counts ---------------------------------

def test_primary_keys_preserved(imported_db):
    con = connect(imported_db)
    try:
        cat_ids = {r["id"] for r in con.execute("SELECT id FROM categories")}
        txn_ids = {r["id"] for r in con.execute("SELECT id FROM transactions")}
        unit_numbers = {r["number"] for r in con.execute("SELECT number FROM units")}
    finally:
        con.close()
    assert cat_ids == {1, 2, 3, 4, 5}
    assert txn_ids == {100, 101, 102, 103}
    assert unit_numbers == {"101", "102", "103", "302"}


def test_foreign_keys_resolve(imported_db):
    con = connect(imported_db)
    try:
        # PRAGMA foreign_key_check returns a row per violation; empty == clean.
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        # Belt and suspenders: no transaction/budget/rule points at a missing category.
        dangling_txn = con.execute(
            "SELECT COUNT(*) FROM transactions t "
            "WHERE t.category_id IS NOT NULL "
            "AND t.category_id NOT IN (SELECT id FROM categories)"
        ).fetchone()[0]
        dangling_auto = con.execute(
            "SELECT COUNT(*) FROM transactions t "
            "WHERE t.auto_category_id IS NOT NULL "
            "AND t.auto_category_id NOT IN (SELECT id FROM categories)"
        ).fetchone()[0]
        dangling_budget = con.execute(
            "SELECT COUNT(*) FROM budgets b "
            "WHERE b.category_id NOT IN (SELECT id FROM categories)"
        ).fetchone()[0]
        dangling_rule = con.execute(
            "SELECT COUNT(*) FROM categorize_rules r "
            "WHERE r.category_id NOT IN (SELECT id FROM categories)"
        ).fetchone()[0]
        dangling_pastdue = con.execute(
            "SELECT COUNT(*) FROM unit_past_dues p "
            "WHERE p.unit_number NOT IN (SELECT number FROM units)"
        ).fetchone()[0]
    finally:
        con.close()
    assert violations == []
    assert (dangling_txn, dangling_auto, dangling_budget, dangling_rule, dangling_pastdue) == (0, 0, 0, 0, 0)


def test_counts_and_year_aggregates_match(imported_db):
    con = connect(imported_db)
    try:
        assert con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == len(LEGACY_TRANSACTIONS)
        assert con.execute("SELECT COUNT(*) FROM budgets").fetchone()[0] == len(LEGACY_BUDGETS)

        # per-year transaction counts
        per_year = {
            r["yr"]: r["n"]
            for r in con.execute(
                "SELECT substr(post_date,1,4) AS yr, COUNT(*) AS n "
                "FROM transactions GROUP BY yr"
            )
        }
        assert per_year == {"2024": 3, "2025": 1}

        # per-year budget cent-totals equal the source totals to the cent
        out_budget_totals = {
            r["yr"]: r["total"]
            for r in con.execute(
                "SELECT year AS yr, SUM(annual_amount) AS total FROM budgets GROUP BY year"
            )
        }
    finally:
        con.close()

    expected = {}
    for _id, year, _cat, amount, _timing in LEGACY_BUDGETS:
        expected[year] = expected.get(year, 0) + cents(amount)
    assert out_budget_totals == expected


# --- R1 applied across real rows --------------------------------------------

def test_transaction_money_converted_exactly(imported_db):
    con = connect(imported_db)
    try:
        rows = {r["id"]: r for r in con.execute(
            "SELECT id, debit, credit, balance FROM transactions"
        )}
    finally:
        con.close()
    for tid, _an, _ac, _pd, _cn, _d, debit, credit, _s, balance, *_ in LEGACY_TRANSACTIONS:
        out = rows[tid]
        assert out["debit"] == cents(debit)
        assert out["credit"] == cents(credit)
        assert out["balance"] == cents(balance)
    # explicit edge rows: credit-only -> debit NULL; debit-only -> credit NULL; negative balance
    assert rows[100]["debit"] is None and rows[100]["credit"] == 83206
    assert rows[101]["credit"] is None and rows[101]["debit"] == 33600
    assert rows[102]["balance"] == -5025


def test_past_dues_converted_exactly(imported_db):
    con = connect(imported_db)
    try:
        rows = {(r["unit_number"], r["year"]): r["past_due_balance"]
                for r in con.execute("SELECT unit_number, year, past_due_balance FROM unit_past_dues")}
    finally:
        con.close()
    for _id, unit, year, amount in LEGACY_UNIT_PAST_DUES:
        assert rows[(unit, year)] == cents(amount)
    assert rows[("302", 2025)] == 62544


def test_ownership_converted_to_permille(imported_db):
    con = connect(imported_db)
    try:
        rows = {r["number"]: r["ownership_pct"]
                for r in con.execute("SELECT number, ownership_pct FROM units")}
    finally:
        con.close()
    assert rows == {"101": 117, "102": 104, "103": 112, "302": 104}


# --- R4: passthrough fields --------------------------------------------------

def test_passthrough_fields_preserved(imported_db):
    con = connect(imported_db)
    try:
        # category name carried verbatim (legacy "Interest", not seed "Interest income")
        names = {r["name"] for r in con.execute("SELECT name FROM categories")}
        assert "Interest" in names and "Interest income" not in names
        assert "Reserve Fund" in names

        # budgets.timing NULL passthrough (budget id 2 had NULL timing)
        timing = con.execute("SELECT timing FROM budgets WHERE id = 2").fetchone()["timing"]
        assert timing is None

        # app_config carried verbatim
        cfg = {r["key"]: r["value"] for r in con.execute("SELECT key, value FROM app_config")}
        assert cfg["current_year"] == "2026"
        assert cfg["last_upload_at"] == "2026-05-19T00:54:07.162920"

        # transaction confidence / needs_review carried
        row = con.execute("SELECT confidence, needs_review FROM transactions WHERE id = 103").fetchone()
        assert row["confidence"] == 90 and row["needs_review"] == 0
    finally:
        con.close()


# --- R5: budget locks (drop locked_by) --------------------------------------

def test_budget_locks_migrated(imported_db):
    con = connect(imported_db)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(budget_locks)")}
        rows = {r["year"]: (r["locked"], r["locked_at"])
                for r in con.execute("SELECT year, locked, locked_at FROM budget_locks")}
    finally:
        con.close()
    assert "locked_by" not in cols
    assert rows == {
        2024: (1, "2026-02-01 03:47:07"),
        2025: (1, "2026-02-12 02:45:35"),
    }


# --- R6: legacy-only artifacts dropped --------------------------------------

def test_legacy_artifacts_dropped(imported_db):
    con = connect(imported_db)
    try:
        views = con.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
        unit_cols = {r["name"] for r in con.execute("PRAGMA table_info(units)")}
    finally:
        con.close()
    assert views == []
    assert "past_due_balance" not in unit_cols


# --- R7: safety guards ------------------------------------------------------

def test_refuses_existing_target(legacy_db, tmp_path):
    from app.legacy_import import build_target

    out = tmp_path / "out.db"
    build_target(str(legacy_db), str(out))
    before = out.read_bytes()
    with pytest.raises(Exception):
        build_target(str(legacy_db), str(out))  # occupied target, no force
    assert out.read_bytes() == before  # unchanged


def test_force_rebuilds_existing_target(legacy_db, tmp_path):
    from app.legacy_import import build_target

    out = tmp_path / "out.db"
    build_target(str(legacy_db), str(out))
    build_target(str(legacy_db), str(out), force=True)  # must not raise
    con = connect(out)
    try:
        assert con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == len(LEGACY_TRANSACTIONS)
    finally:
        con.close()


def test_missing_source_aborts(tmp_path):
    from app.legacy_import import build_target

    out = tmp_path / "out.db"
    with pytest.raises(Exception):
        build_target(str(tmp_path / "does-not-exist.db"), str(out))
    assert not out.exists()  # no partial target
