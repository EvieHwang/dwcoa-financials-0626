# @frozen — account-balance behavior: balance is the bank running-balance of the
# latest transaction on or before the as-of date, beginning balance is that rule
# at prior year-end, every seeded account is listed, total cash is their exact
# sum. Hand-verified; exercised through GET /api/dashboard.
"""US4 / AC4.* — account balances with year context."""
from conftest import ACCOUNT_NAMES, get_dashboard, insert_txn

YEAR = 2030


def _acct(data, name):
    for a in data["accounts"]:
        if a["name"] == name:
            return a
    return None


def test_balance_is_latest_on_or_before(app_env, viewer_client):
    db = app_env["db_path"]
    # Three Checking rows; the as-of date sits between the 2nd and 3rd.
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-01-10", balance=100000)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-03-15", balance=250000)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-09-01", balance=900000)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    # Latest on/before June 30 is the March 15 row.
    assert _acct(data, "Checking")["balance"] == 250000


def test_beginning_balance_prior_year_end(app_env, viewer_client):
    db = app_env["db_path"]
    insert_txn(db, account_name="Checking", post_date=f"{YEAR - 1}-11-20", balance=70000)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR - 1}-12-28", balance=88000)
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-02-01", balance=120000)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    acct = _acct(data, "Checking")
    # Beginning balance = latest on/before Dec 31 of the prior year.
    assert acct["beginning_balance"] == 88000
    assert acct["balance"] == 120000


def test_all_accounts_listed_and_total(app_env, viewer_client):
    db = app_env["db_path"]
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-02-01", balance=100000)
    insert_txn(db, account_name="Savings", post_date=f"{YEAR}-02-01", balance=300000)
    insert_txn(db, account_name="Reserve Fund", post_date=f"{YEAR}-02-01", balance=500000)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    names = {a["name"] for a in data["accounts"]}
    for expected in ACCOUNT_NAMES:
        assert expected in names, f"account {expected!r} not listed"
    # total_cash is the exact sum of the listed balances.
    assert data["total_cash"] == sum(a["balance"] for a in data["accounts"])
    assert data["total_cash"] == 900000


def test_account_without_txns_is_zero(app_env, viewer_client):
    db = app_env["db_path"]
    # Only Checking has activity; Savings / Reserve Fund have none.
    insert_txn(db, account_name="Checking", post_date=f"{YEAR}-02-01", balance=100000)
    data = get_dashboard(viewer_client, f"{YEAR}-06-30")
    savings = _acct(data, "Savings")
    assert savings is not None
    assert savings["balance"] == 0
    assert savings["beginning_balance"] == 0
