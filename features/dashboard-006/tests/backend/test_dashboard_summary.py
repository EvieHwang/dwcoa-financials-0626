# @frozen — the budget-vs-actual BEHAVIOR is the contract and every number here
# is hand-verified (constitution: "a weak test here is worse than none"). The
# aggregation is exercised through GET /api/dashboard so it stays decoupled from
# the internal function names (@scaffolding). Worked examples use year 2030, which
# carries no seeded budgets, so each case controls its own inputs exactly.
"""US2 / US3 — prorated budget vs. actual, income shown independently."""
from conftest import (
    category_id,
    first_category_of_type,
    get_dashboard,
    insert_budget,
    insert_txn,
)

YEAR = 2030


def _line(summary, name):
    for line in summary["categories"]:
        if line["name"] == name:
            return line
    return None


def test_prorated_uses_effective_timing_override(app_env, viewer_client):
    """A line whose category default is monthly but whose per-line override is
    annual must prorate FULL-from-January, not m/12 (AC2.2)."""
    db = app_env["db_path"]
    cat = category_id(db, "Common Area Cleaning")  # default timing 'monthly'
    insert_budget(db, year=YEAR, category_id=cat, annual_amount=120000,
                  timing="annual")
    # As of March: annual override -> full 120000, NOT monthly 3/12 = 30000.
    data = get_dashboard(viewer_client, f"{YEAR}-03-01")
    line = _line(data["expense_summary"], "Common Area Cleaning")
    assert line is not None
    assert line["prorated_budget"] == 120000  # not 30000


def test_remaining_is_prorated_minus_actual(app_env, viewer_client):
    db = app_env["db_path"]
    cat = category_id(db, "Insurance Premiums")  # default monthly
    insert_budget(db, year=YEAR, category_id=cat, annual_amount=120000)  # $1,200
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-02-10",
               debit=50000, category_id=cat)
    # As of June: prorated monthly = 120000 * 6/12 = 60000; actual = 50000.
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    line = _line(data["expense_summary"], "Insurance Premiums")
    assert line["annual_budget"] == 120000
    assert line["prorated_budget"] == 60000
    assert line["actual"] == 50000
    assert line["remaining"] == 10000  # 60000 - 50000


def test_actuals_by_type(app_env, viewer_client):
    """Income actual draws from credit; expense actual from debit (AC2.4)."""
    db = app_env["db_path"]
    dues = category_id(db, "Dues 101")        # Income
    ins = category_id(db, "Insurance Premiums")  # Expense
    insert_txn(db, account_name="Savings", post_date=f"{YEAR}-03-01",
               credit=30000, category_id=dues)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-03-01",
               debit=20000, category_id=ins)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    assert _line(data["income_summary"], "Dues 101")["actual"] == 30000
    assert _line(data["expense_summary"], "Insurance Premiums")["actual"] == 20000


def test_uncategorized_excluded(app_env, viewer_client):
    """Uncategorized rows (category_id NULL) never contribute to actuals."""
    db = app_env["db_path"]
    dues = category_id(db, "Dues 101")
    insert_txn(db, account_name="Savings", post_date=f"{YEAR}-03-01",
               credit=30000, category_id=dues)
    insert_txn(db, account_name="Savings", post_date=f"{YEAR}-03-02",
               credit=99999, category_id=None)  # uncategorized
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    assert data["income_summary"]["actual"] == 30000  # not 130000


def test_transfers_excluded_from_totals(app_env, viewer_client):
    """A Transfers (Internal) row is in neither income nor expense (AC6.2/US2)."""
    db = app_env["db_path"]
    transfers = category_id(db, "Transfers")  # type 'Internal'
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-03-01",
               credit=50000, debit=50000, category_id=transfers)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    assert data["income_summary"]["actual"] == 0
    assert data["expense_summary"]["actual"] == 0
    assert _line(data["income_summary"], "Transfers") is None
    assert _line(data["expense_summary"], "Transfers") is None


def test_income_budget_is_independent_sum(app_env, viewer_client):
    """Income budget = sum of entered income-category budgets, NOT derived from
    the operating (expense) budget total (decision #4 / AC3.*)."""
    db = app_env["db_path"]
    dues = category_id(db, "Dues 101")
    interest = category_id(db, "Interest")
    insert_budget(db, year=YEAR, category_id=dues, annual_amount=100000)
    insert_budget(db, year=YEAR, category_id=interest, annual_amount=5000)
    # A deliberately DIFFERENT expense total, to prove income isn't taken from it.
    ins = category_id(db, "Insurance Premiums")
    insert_budget(db, year=YEAR, category_id=ins, annual_amount=120000)
    data = get_dashboard(viewer_client, f"{YEAR}-12-31")
    assert data["income_summary"]["annual_budget"] == 105000      # 100000 + 5000
    assert data["expense_summary"]["annual_budget"] == 120000
    assert data["income_summary"]["annual_budget"] != data["expense_summary"]["annual_budget"]


def test_line_includes_category_id(app_env, viewer_client):
    """Each summary line carries its integer `category_id` (part of the frozen
    line contract / AC2.1), matching the real seeded category id."""
    db = app_env["db_path"]
    ins = category_id(db, "Insurance Premiums")
    insert_budget(db, year=YEAR, category_id=ins, annual_amount=120000)
    line = _line(
        get_dashboard(viewer_client, f"{YEAR}-06-30")["expense_summary"],
        "Insurance Premiums",
    )
    assert line["category_id"] == ins
    assert isinstance(line["category_id"], int)


def test_totals_are_sum_of_lines(app_env, viewer_client):
    """Each summary total is the exact integer-cent sum of its category lines."""
    db = app_env["db_path"]
    exp_id, exp_name = first_category_of_type(db, "Expense")
    inc_id, inc_name = first_category_of_type(db, "Income")
    insert_budget(db, year=YEAR, category_id=exp_id, annual_amount=240000)
    insert_budget(db, year=YEAR, category_id=inc_id, annual_amount=120000)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-04-01",
               debit=11111, category_id=exp_id)
    insert_txn(db, account_name="Savings", post_date=f"{YEAR}-04-01",
               credit=22222, category_id=inc_id)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    for summary in (data["income_summary"], data["expense_summary"]):
        for field in ("annual_budget", "prorated_budget", "actual", "remaining"):
            assert summary[field] == sum(c[field] for c in summary["categories"]), field
