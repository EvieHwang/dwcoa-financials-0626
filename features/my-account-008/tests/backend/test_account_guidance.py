# @frozen — payment guidance is the NEW integer-cent math this slice adds, and the
# constitution names financial calculations the highest-value test surface ("a weak
# test here is worse than none"). Every number is hand-verified. Divisible worked
# examples make the standard/suggested monthlies rounding-mode-independent; one
# dedicated case covers the (deliberately loose) suggested-monthly rounding
# tolerance, matching how 007 treats annual_dues rounding. Exercised through GET
# /api/account so it stays decoupled from internal function names.
"""US4 — standard monthly, the 15th-rule months_remaining, suggested monthly, and
the paid-in-full / credit / due-by-year-end statuses."""
import pytest

from conftest import clear_budgets, get_account, insert_budget, insert_payment


def _budget_only(db, *, op=10_000_000):
    """Unit 101 (117 per-mille), carryover 0: clear 2025 and 2026, set just a 2026
    operating budget so annual_dues(101) = op * 117 / 1000."""
    clear_budgets(db, 2025)
    clear_budgets(db, 2026)
    insert_budget(db, year=2026, category_name="Insurance Premiums",
                  annual_amount=op)


# --- standard monthly (AC4.1) ----------------------------------------------

def test_standard_monthly_divisible(app_env, viewer_client):
    """standard_monthly = annual_dues / 12. 1,170,000 / 12 = 97,500 (exact)."""
    db = app_env["db_path"]
    _budget_only(db)                                  # annual_dues(101) = 1,170,000
    g = get_account(viewer_client, unit="101", as_of="2026-06-30")["payment_guidance"]
    assert g["standard_monthly"] == 97_500


# --- months remaining: the "snap at the 15th" rule (AC4.2) ------------------

@pytest.mark.parametrize(
    "as_of,expected",
    [
        ("2026-01-01", 12),   # Jan, day <= 15 -> 12 - 1 + 1
        ("2026-01-15", 12),   # boundary day 15 still counts the current month
        ("2026-01-16", 11),   # past the 15th -> current month drops off
        ("2026-03-01", 10),
        ("2026-03-16", 9),
        ("2026-12-15", 1),
        ("2026-12-16", 0),    # after Dec 15 -> zero months remain
    ],
)
def test_months_remaining_15th_rule(app_env, viewer_client, as_of, expected):
    db = app_env["db_path"]
    _budget_only(db)
    g = get_account(viewer_client, unit="101", as_of=as_of)["payment_guidance"]
    assert g["months_remaining"] == expected


# --- suggested monthly when the unit owes (AC4.3) ---------------------------

def test_suggested_monthly_divisible(app_env, viewer_client):
    """remaining 1,000,000 over 10 months (as-of 2026-03-10, day <= 15) = 100,000
    per month, exact; status 'owes'."""
    db = app_env["db_path"]
    _budget_only(db)                                  # annual_dues = total_due = 1,170,000
    insert_payment(db, unit_number="101", post_date="2026-02-01", amount=170_000)
    g = get_account(viewer_client, unit="101", as_of="2026-03-10")["payment_guidance"]
    assert g["status"] == "owes"
    assert g["months_remaining"] == 10
    assert g["suggested_monthly"] == 100_000         # 1,000,000 / 10


def test_suggested_monthly_rounds_within_cent(app_env, viewer_client):
    """A non-divisible remaining still yields an integer-cent suggestion within one
    cent of the true share (rounding mode intentionally unspecified)."""
    db = app_env["db_path"]
    _budget_only(db)                                  # total_due = 1,170,000
    insert_payment(db, unit_number="101", post_date="2026-02-01", amount=170_000)
    g = get_account(viewer_client, unit="101", as_of="2026-06-10")["payment_guidance"]
    assert g["status"] == "owes"
    assert g["months_remaining"] == 7                 # June, day 10 -> 12 - 6 + 1
    remaining, months = 1_000_000, 7
    floor = remaining // months                       # 142,857
    assert isinstance(g["suggested_monthly"], int)
    assert g["suggested_monthly"] in (floor, floor + 1)


# --- paid in full / credit short-circuits (AC4.4) ---------------------------

def test_paid_in_full_status(app_env, viewer_client):
    """remaining == 0 -> status 'paid_in_full', suggested_monthly null;
    standard_monthly still present."""
    db = app_env["db_path"]
    _budget_only(db)                                  # total_due = 1,170,000
    insert_payment(db, unit_number="101", post_date="2026-02-01", amount=1_170_000)
    g = get_account(viewer_client, unit="101", as_of="2026-06-30")["payment_guidance"]
    assert g["status"] == "paid_in_full"
    assert g["suggested_monthly"] is None
    assert g["standard_monthly"] == 97_500


def test_credit_status(app_env, viewer_client):
    """remaining < 0 -> status 'credit', suggested_monthly null."""
    db = app_env["db_path"]
    _budget_only(db)                                  # total_due = 1,170,000
    insert_payment(db, unit_number="101", post_date="2026-02-01", amount=1_500_000)
    g = get_account(viewer_client, unit="101", as_of="2026-06-30")["payment_guidance"]
    assert g["status"] == "credit"
    assert g["suggested_monthly"] is None


# --- year-boundary: zero months remaining, no divide-by-zero (AC4.5) --------

def test_due_by_year_end_no_divzero(app_env, viewer_client):
    """After Dec 15, months_remaining is 0; with a balance owing, guidance returns
    status 'due_by_year_end' and a null suggested_monthly (never a divide-by-zero),
    HTTP 200 (get_account asserts the 200)."""
    db = app_env["db_path"]
    _budget_only(db)                                  # total_due = 1,170,000, unpaid
    g = get_account(viewer_client, unit="101", as_of="2026-12-16")["payment_guidance"]
    assert g["months_remaining"] == 0
    assert g["status"] == "due_by_year_end"
    assert g["suggested_monthly"] is None
    assert g["standard_monthly"] == 97_500
