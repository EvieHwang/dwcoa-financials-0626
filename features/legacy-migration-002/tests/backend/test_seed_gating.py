"""R9 / R10 — seed is an empty-DB bootstrap that matches production naming.

R9: a true no-op against any DB that already holds reference data (migrated or
already-seeded), so deploying the migrated production DB is never polluted by a
startup seed. R10: the dev/test seed reflects production canonical names/types.
"""
import sqlite3


def _migrated_empty_db(tmp_path):
    from app.migrations import run_migrations

    db = tmp_path / "seed.db"
    run_migrations(str(db))
    return db


def _all_table_counts(db):
    con = sqlite3.connect(str(db))
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        con.close()


# --- R9 ---------------------------------------------------------------------

def test_seed_complete_when_empty(tmp_path):
    from app.seed import seed_reference_data

    db = _migrated_empty_db(tmp_path)
    seed_reference_data(str(db))
    con = sqlite3.connect(str(db))
    try:
        assert con.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 9
        assert con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 3
        assert con.execute("SELECT COUNT(*) FROM categories").fetchone()[0] >= 22
        assert con.execute("SELECT COUNT(*) FROM categorize_rules").fetchone()[0] > 0
    finally:
        con.close()


def test_seed_noop_when_populated(tmp_path):
    from app.seed import seed_reference_data

    db = _migrated_empty_db(tmp_path)
    # Simulate migrated production data: a category already present, with a name
    # the seed would never produce.
    con = sqlite3.connect(str(db))
    try:
        con.execute(
            "INSERT INTO categories (name, type, default_account, timing) "
            "VALUES ('PB Replacement', 'Expense', NULL, 'monthly')"
        )
        con.commit()
    finally:
        con.close()

    before = _all_table_counts(db)
    seed_reference_data(str(db))  # must be a true no-op
    after = _all_table_counts(db)
    assert after == before
    # the pre-existing category is untouched and not duplicated
    con = sqlite3.connect(str(db))
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM categories WHERE name='PB Replacement'"
        ).fetchone()[0] == 1
    finally:
        con.close()


# --- R10 --------------------------------------------------------------------

def test_seed_canonical_names_and_types(tmp_path):
    from app.seed import seed_reference_data

    db = _migrated_empty_db(tmp_path)
    seed_reference_data(str(db))
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        names = {r["name"] for r in con.execute("SELECT name FROM categories")}
        types = {r["name"]: r["type"] for r in con.execute("SELECT name, type FROM categories")}
    finally:
        con.close()

    # corrected names
    assert "Interest" in names and "Interest income" not in names
    assert "Reserve Fund" in names and "Reserve Expenses" not in names
    # corrected type
    assert types["Reserve Contribution"] == "Expense"
    # the five treasurer-added categories are present
    assert {
        "Membership & License",
        "Reserve Income",
        "202 & 302 Balcony Repairs",
        "102 & 103 Leak Repairs",
        "PB Replacement",
    } <= names


def test_seed_budgets_and_rules_reference_corrected_names(tmp_path):
    """A rename that didn't propagate would silently drop the Interest budget/rule."""
    from app.seed import seed_reference_data

    db = _migrated_empty_db(tmp_path)
    seed_reference_data(str(db))
    con = sqlite3.connect(str(db))
    try:
        # no seeded budget or rule dangles off a missing category
        dangling_budget = con.execute(
            "SELECT COUNT(*) FROM budgets WHERE category_id NOT IN (SELECT id FROM categories)"
        ).fetchone()[0]
        dangling_rule = con.execute(
            "SELECT COUNT(*) FROM categorize_rules WHERE category_id NOT IN (SELECT id FROM categories)"
        ).fetchone()[0]
        # the Interest budget survived the rename (resolves to category 'Interest')
        interest_budget = con.execute(
            "SELECT COUNT(*) FROM budgets b JOIN categories c ON b.category_id=c.id "
            "WHERE c.name='Interest'"
        ).fetchone()[0]
        # a rule resolves to 'Interest' (the Dividend/Interest rule)
        interest_rule = con.execute(
            "SELECT COUNT(*) FROM categorize_rules r JOIN categories c ON r.category_id=c.id "
            "WHERE c.name='Interest'"
        ).fetchone()[0]
    finally:
        con.close()
    assert (dangling_budget, dangling_rule) == (0, 0)
    assert interest_budget == 1
    assert interest_rule == 1
