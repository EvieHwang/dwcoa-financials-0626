# @frozen — the statement MATH is the contract and every number here is
# hand-verified. The current-year figures must EQUAL the board's /api/dues row for
# the same unit/date (proving the 007 dues engine is reused, not re-derived —
# constitution names per-unit carryover and dues expected/paid/outstanding as
# required surfaces). Exercised through GET /api/account so it stays decoupled from
# internal function names (@scaffolding). Worked examples clear the seeded 2025
# budgets and set their own, so each case controls operating_budget exactly.
"""US2/US3/US5 — current-year reuse, prior-year wrap-up, recent payments."""
from conftest import (
    clear_budgets,
    dues_unit_row,
    get_account,
    get_dues,
    insert_budget,
    insert_credit_to_category,
    insert_past_due,
    insert_payment,
)


def _setup_two_year(db):
    """The contract's worked example: unit 101 (117 per-mille).

    2025: baseline 100,000; operating budget 10,000,000 -> annual_dues 1,170,000;
          one full-year payment of 500,000 (2025-06-01).
    2026: operating budget 20,000,000 -> annual_dues 2,340,000;
          one payment of 1,000,000 (2026-05-01).
    carry_in(2026) = 100,000 + 1,170,000 - 500,000 = 770,000.
    """
    clear_budgets(db, 2025)
    clear_budgets(db, 2026)
    insert_past_due(db, unit_number="101", year=2025, past_due_balance=100_000)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    insert_payment(db, unit_number="101", post_date="2025-06-01", amount=500_000)
    insert_budget(db, year=2026, category_name="Insurance Premiums",
                  annual_amount=20_000_000)
    insert_payment(db, unit_number="101", post_date="2026-05-01", amount=1_000_000)


# --- current year equals the dues row (engine reuse) (AC2.2) ----------------

def test_current_year_matches_dues_row(app_env, viewer_client):
    """For the same unit and date, the statement's current-year figures equal the
    board's /api/dues row exactly — the reuse contract.

    Checked for TWO units with different ownership (101 @ 117, 102 @ 104) and
    distinct carryover/payment histories, so a re-derivation that happened to
    reproduce one unit's simple accumulation cannot pass for both."""
    db = app_env["db_path"]
    _setup_two_year(db)  # gives unit 101 a baseline + multi-year history
    # Give unit 102 (104 per-mille) its own distinct history: a 2025 overpayment
    # that becomes a 2026 credit carried forward.
    insert_payment(db, unit_number="102", post_date="2025-04-01", amount=3_000_000)
    insert_payment(db, unit_number="102", post_date="2026-04-01", amount=250_000)

    dues = get_dues(viewer_client, "2026-06-30")
    for number in ("101", "102"):
        cy = get_account(viewer_client, unit=number, as_of="2026-06-30")["current_year"]
        row = dues_unit_row(dues, number)
        assert cy["carryover"] == row["carryover"], number
        assert cy["annual_dues"] == row["annual_dues"], number
        assert cy["total_due"] == row["expected_total"], number
        assert cy["paid_ytd"] == row["paid"], number
        assert cy["remaining_balance"] == row["outstanding"], number

    # Unit 101's figures are also pinned to hand-verified absolutes (the contract's
    # worked example), so the cross-check isn't only relative.
    cy101 = get_account(viewer_client, unit="101", as_of="2026-06-30")["current_year"]
    assert cy101["carryover"] == 770_000
    assert cy101["annual_dues"] == 2_340_000
    assert cy101["total_due"] == 3_110_000
    assert cy101["paid_ytd"] == 1_000_000
    assert cy101["remaining_balance"] == 2_110_000
    # And unit 102 carries a credit (negative remaining) — a different sign path.
    cy102 = get_account(viewer_client, unit="102", as_of="2026-06-30")["current_year"]
    assert cy102["remaining_balance"] < 0


def test_annual_dues_not_prorated(app_env, viewer_client):
    """Annual dues is the FULL annual amount regardless of the as-of date within a
    year (the deliberate divergence from the dashboard's prorated budget math)."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # annual_dues(101)=1,170,000
    early = get_account(viewer_client, unit="101", as_of="2025-02-01")
    late = get_account(viewer_client, unit="101", as_of="2025-12-31")
    assert early["current_year"]["annual_dues"] == 1_170_000
    assert late["current_year"]["annual_dues"] == 1_170_000


def test_remaining_is_total_minus_paid(app_env, viewer_client):
    """remaining_balance == total_due - paid_ytd exactly, in integer cents."""
    db = app_env["db_path"]
    _setup_two_year(db)
    cy = get_account(viewer_client, unit="101", as_of="2026-06-30")["current_year"]
    assert isinstance(cy["remaining_balance"], int)
    assert cy["remaining_balance"] == cy["total_due"] - cy["paid_ytd"]
    assert cy["total_due"] == cy["carryover"] + cy["annual_dues"]


def test_overpayment_is_credit(app_env, viewer_client):
    """Paying more than expected yields a negative remaining_balance (a credit),
    not clamped to zero."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # annual_dues(101)=1,170,000
    insert_payment(db, unit_number="101", post_date="2025-03-01", amount=1_500_000)
    cy = get_account(viewer_client, unit="101", as_of="2025-06-30")["current_year"]
    assert cy["total_due"] == 1_170_000
    assert cy["paid_ytd"] == 1_500_000
    assert cy["remaining_balance"] == -330_000


# --- prior year wrap-up (AC3.*) --------------------------------------------

def test_prior_year_block(app_env, viewer_client):
    """For 2026 the prior-year block carries 2025's own budgeted/paid and the
    balance carried forward."""
    db = app_env["db_path"]
    _setup_two_year(db)
    py = get_account(viewer_client, unit="101", as_of="2026-06-30")["prior_year"]
    assert py["year"] == 2025
    assert py["data_available"] is True
    assert py["annual_dues_budgeted"] == 1_170_000   # 2025 op 10,000,000 * 117/1000
    assert py["total_paid"] == 500_000               # 2025 full-year payment
    assert py["balance_carried_forward"] == 770_000  # == current carryover


def test_carried_forward_equals_carryover(app_env, viewer_client):
    """The prior-year balance_carried_forward is the same number as the current
    year's carryover (surfaced in both blocks)."""
    db = app_env["db_path"]
    _setup_two_year(db)
    acct = get_account(viewer_client, unit="101", as_of="2026-06-30")
    assert (
        acct["prior_year"]["balance_carried_forward"]
        == acct["current_year"]["carryover"]
    )


def test_2025_prior_year_not_available(app_env, viewer_client):
    """For 2025 (the first tracked year) the prior year is 2024, which predates
    tracking: data_available false, breakdown null, but the carried-forward
    baseline still surfaces and equals the current carryover."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    insert_past_due(db, unit_number="101", year=2025, past_due_balance=250_000)
    acct = get_account(viewer_client, unit="101", as_of="2025-06-30")
    py = acct["prior_year"]
    assert py["year"] == 2024
    assert py["data_available"] is False
    assert py["annual_dues_budgeted"] is None
    assert py["total_paid"] is None
    assert py["balance_carried_forward"] == 250_000
    assert acct["current_year"]["carryover"] == 250_000


# --- recent payments (AC5.*) -----------------------------------------------

def test_recent_payments_window_and_order(app_env, viewer_client):
    """Recent payments are the unit's dues credits in the current and prior
    calendar year, capped at the as-of date, newest first."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    clear_budgets(db, 2026)
    insert_payment(db, unit_number="101", post_date="2024-12-01", amount=111_111)  # prior-prior year: out
    insert_payment(db, unit_number="101", post_date="2025-03-01", amount=100_000)
    insert_payment(db, unit_number="101", post_date="2025-11-01", amount=200_000)
    insert_payment(db, unit_number="101", post_date="2026-02-01", amount=300_000)
    insert_payment(db, unit_number="101", post_date="2026-09-01", amount=400_000)  # after as-of: out
    payments = get_account(viewer_client, unit="101", as_of="2026-06-30")["recent_payments"]
    assert [(p["date"], p["amount"]) for p in payments] == [
        ("2026-02-01", 300_000),
        ("2025-11-01", 200_000),
        ("2025-03-01", 100_000),
    ]


def test_recent_payments_excludes_others(app_env, viewer_client):
    """Another unit's dues, a non-dues category credit, and this unit's
    out-of-window/after-as-of payments never appear."""
    db = app_env["db_path"]
    clear_budgets(db, 2026)
    insert_payment(db, unit_number="101", post_date="2026-03-01", amount=100_000)  # the only one expected
    insert_payment(db, unit_number="102", post_date="2026-03-01", amount=555_000)  # other unit
    insert_credit_to_category(db, category_name="Interest",
                              post_date="2026-03-01", amount=777_000)              # non-dues
    insert_payment(db, unit_number="101", post_date="2026-08-01", amount=999_000)  # after as-of
    payments = get_account(viewer_client, unit="101", as_of="2026-06-30")["recent_payments"]
    assert [(p["date"], p["amount"]) for p in payments] == [("2026-03-01", 100_000)]


def test_recent_payments_same_date_both_appear(app_env, viewer_client):
    """Two payments on the same date both appear (their relative order is not a
    contract); they sit in the right newest-first position relative to other
    dates."""
    db = app_env["db_path"]
    clear_budgets(db, 2026)
    insert_payment(db, unit_number="101", post_date="2026-01-10", amount=100_000)
    insert_payment(db, unit_number="101", post_date="2026-03-15", amount=200_000)
    insert_payment(db, unit_number="101", post_date="2026-03-15", amount=300_000)  # same date
    payments = get_account(viewer_client, unit="101", as_of="2026-06-30")["recent_payments"]
    dates = [p["date"] for p in payments]
    # All three appear; both same-date entries are present (order between them free).
    assert len(payments) == 3
    assert dates == ["2026-03-15", "2026-03-15", "2026-01-10"]
    assert sorted(p["amount"] for p in payments if p["date"] == "2026-03-15") == [
        200_000, 300_000,
    ]


def test_recent_payments_empty(app_env, viewer_client):
    """No payments in the window -> empty list, not an error."""
    db = app_env["db_path"]
    clear_budgets(db, 2026)
    payments = get_account(viewer_client, unit="101", as_of="2026-06-30")["recent_payments"]
    assert payments == []
