# @frozen — monthly cashflow behavior: per-month income (credits, Income cats) vs
# expenses (debits, Expense cats), transfers excluded, months filled with zeros
# through the as-of month. Hand-verified; exercised through GET /api/dashboard.
"""US6 / AC6.* — the one simple monthly income-vs-expense series."""
from conftest import category_id, get_dashboard, insert_txn

YEAR = 2030


def _month(series, m):
    for entry in series:
        if entry["month"] == m:
            return entry
    return None


def test_monthly_income_expense(app_env, viewer_client):
    db = app_env["db_path"]
    dues = category_id(db, "Dues 101")            # Income
    ins = category_id(db, "Insurance Premiums")   # Expense
    insert_txn(db, account_name="Savings", post_date=f"{YEAR}-02-10",
               credit=30000, category_id=dues)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-02-20",
               debit=12000, category_id=ins)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-05-05",
               debit=8000, category_id=ins)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    series = data["monthly_cashflow"]
    feb = _month(series, 2)
    assert feb["income"] == 30000
    assert feb["expenses"] == 12000
    may = _month(series, 5)
    assert may["income"] == 0
    assert may["expenses"] == 8000


def test_cashflow_excludes_transfers(app_env, viewer_client):
    db = app_env["db_path"]
    transfers = category_id(db, "Transfers")  # type 'Internal'
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-02-10",
               credit=50000, debit=50000, category_id=transfers)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    feb = _month(data["monthly_cashflow"], 2)
    assert feb["income"] == 0
    assert feb["expenses"] == 0


def test_months_filled_through_as_of(app_env, viewer_client):
    # No transactions at all; the series still lists Jan..as-of-month with zeros.
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    series = data["monthly_cashflow"]
    months = [e["month"] for e in series]
    assert months == [1, 2, 3, 4, 5, 6]
    assert all(e["income"] == 0 and e["expenses"] == 0 for e in series)


def test_full_year_via_year_end_as_of(app_env, viewer_client):
    """Picking Dec 31 as the as-of date is how a past full year is viewed: the
    series spans all twelve months and December activity is included (AC6.1).
    `year` always equals the as-of date's year, so the series length is simply
    the as-of month — here, December = 12."""
    db = app_env["db_path"]
    dues = category_id(db, "Dues 101")  # Income
    insert_txn(db, account_name="Savings", post_date=f"{YEAR}-12-15",
               credit=44000, category_id=dues)
    data = get_dashboard(viewer_client, f"{YEAR}-12-31")
    series = data["monthly_cashflow"]
    months = [e["month"] for e in series]
    assert months == list(range(1, 13)), months  # full Jan..Dec
    assert _month(series, 12)["income"] == 44000
