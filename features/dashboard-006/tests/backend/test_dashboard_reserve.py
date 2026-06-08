# @frozen — reserve-fund behavior: contributions in / expenses out / net measured
# on the Reserve Fund account, budget = prorated Reserve Contribution. Hand-
# verified; exercised through GET /api/dashboard.
"""US5 / AC5.* — reserve fund status."""
from conftest import category_id, get_dashboard, insert_budget, insert_txn

YEAR = 2030


def test_reserve_contributions_expenses_net(app_env, viewer_client):
    db = app_env["db_path"]
    # Money INTO Reserve Fund (credits) and OUT of it (debits), within the year.
    insert_txn(db, account_name="Reserve Fund", post_date=f"{YEAR}-02-01",
               credit=150000)
    insert_txn(db, account_name="Reserve Fund", post_date=f"{YEAR}-04-01",
               credit=150000)
    insert_txn(db, account_name="Reserve Fund", post_date=f"{YEAR}-05-01",
               debit=40000)
    # A row AFTER the as-of date must not count.
    insert_txn(db, account_name="Reserve Fund", post_date=f"{YEAR}-08-01",
               credit=999999)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    rf = data["reserve_fund"]
    assert rf["contributions"] == 300000   # 150000 + 150000
    assert rf["expenses"] == 40000
    assert rf["net"] == 260000             # 300000 - 40000


def test_reserve_budget_is_prorated(app_env, viewer_client):
    db = app_env["db_path"]
    rc = category_id(db, "Reserve Contribution")  # default timing 'monthly'
    insert_budget(db, year=YEAR, category_id=rc, annual_amount=1200000)  # $12,000
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    # Monthly proration through June = 1200000 * 6/12 = 600000.
    assert data["reserve_fund"]["budget"] == 600000


def test_reserve_beginning_balance(app_env, viewer_client):
    db = app_env["db_path"]
    insert_txn(db, account_name="Reserve Fund", post_date=f"{YEAR - 1}-12-15",
               balance=4500000)
    insert_txn(db, account_name="Reserve Fund", post_date=f"{YEAR}-03-01",
               balance=4650000)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    assert data["reserve_fund"]["beginning_balance"] == 4500000
