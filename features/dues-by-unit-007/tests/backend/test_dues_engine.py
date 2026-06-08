# @frozen — the dues MATH is the contract and every number here is hand-verified
# (constitution: "a weak test here is worse than none" names per-unit carryover and
# dues expected/paid/outstanding as required surfaces). The math is exercised
# through GET /api/dues so it stays decoupled from internal function names
# (@scaffolding). Worked examples clear the seeded 2025 budgets and set their own,
# so each case controls operating_budget exactly. annual_dues examples use operating
# budgets that are exact multiples of 1000 so the result is rounding-mode-independent;
# one dedicated test covers the (deliberately loose) rounding tolerance.
"""US2–US6 — operating-budget basis, ownership share, payments, carryover, totals."""
from conftest import (
    SEEDED_UNITS,
    clear_budgets,
    get_dues,
    insert_budget,
    insert_credit_to_category,
    insert_past_due,
    insert_payment,
    set_category_active,
    unit_row,
)


# --- operating budget basis (AC2.3) ----------------------------------------

def test_operating_budget_expense_only(app_env, viewer_client):
    """Operating budget = sum of active Expense budgets; income and inactive
    expense budgets never contribute."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # active Expense
    insert_budget(db, year=2025, category_name="Bulger Safe & Lock",
                  annual_amount=1_000_000)             # Expense, will deactivate
    insert_budget(db, year=2025, category_name="Dues 101",
                  annual_amount=5_000_000)             # Income — excluded
    set_category_active(db, "Bulger Safe & Lock", False)
    data = get_dues(viewer_client, "2025-06-30")
    # Only the active Insurance Premiums expense counts.
    assert data["operating_budget"] == 10_000_000


def test_income_budget_does_not_affect_dues(app_env, viewer_client):
    """Adding an income-category budget changes neither operating_budget nor any
    unit's annual_dues (hard separation from the income/interest side)."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    before = get_dues(viewer_client, "2025-06-30")
    insert_budget(db, year=2025, category_name="Interest", annual_amount=9_999_999)
    after = get_dues(viewer_client, "2025-06-30")
    assert after["operating_budget"] == before["operating_budget"] == 10_000_000
    assert unit_row(after, "101")["annual_dues"] == unit_row(before, "101")["annual_dues"]


# --- annual dues = ownership share, full annual (AC2.2) ---------------------

def test_annual_dues_is_ownership_share(app_env, viewer_client):
    """annual_dues = operating_budget * ownership_per_mille / 1000 (exact here)."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    data = get_dues(viewer_client, "2025-06-30")
    u101 = unit_row(data, "101")
    u102 = unit_row(data, "102")
    assert u101["ownership_per_mille"] == 117
    assert u101["annual_dues"] == 1_170_000      # 10,000,000 * 117 / 1000
    assert u102["annual_dues"] == 1_040_000      # 10,000,000 * 104 / 1000


def test_proportional_to_ownership(app_env, viewer_client):
    """A higher-ownership unit owes proportionally more from the same budget."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    data = get_dues(viewer_client, "2025-06-30")
    u101 = unit_row(data, "101")  # 117 per-mille
    u102 = unit_row(data, "102")  # 104 per-mille
    assert u101["annual_dues"] > u102["annual_dues"]
    # Shares track the per-mille ratio exactly for this exact budget.
    assert u101["annual_dues"] * 104 == u102["annual_dues"] * 117


def test_annual_dues_not_prorated(app_env, viewer_client):
    """Expected dues is the FULL annual amount regardless of the as-of date —
    the deliberate divergence from the dashboard's prorated budget math."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    early = get_dues(viewer_client, "2025-02-01")   # February
    late = get_dues(viewer_client, "2025-12-31")    # December
    assert unit_row(early, "101")["annual_dues"] == 1_170_000   # not 2/12
    assert unit_row(late, "101")["annual_dues"] == 1_170_000
    assert unit_row(early, "101")["expected_total"] == 1_170_000


def test_annual_dues_rounds_to_cents(app_env, viewer_client):
    """A non-divisible budget still yields an integer-cent share within one cent
    of the true share (rounding mode intentionally unspecified — not a priority)."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    op = 1_000_333
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=op)
    u101 = unit_row(get_dues(viewer_client, "2025-06-30"), "101")
    floor = op * 117 // 1000
    assert isinstance(u101["annual_dues"], int)
    assert u101["annual_dues"] in (floor, floor + 1)


def test_no_budget_year_zero_dues(app_env, viewer_client):
    """No budgets for the year -> operating_budget 0, every annual_dues 0, but all
    nine units are still listed."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    data = get_dues(viewer_client, "2025-06-30")
    assert data["operating_budget"] == 0
    assert len(data["units"]) == len(SEEDED_UNITS)
    assert all(u["annual_dues"] == 0 for u in data["units"])


# --- payments (AC3.*) ------------------------------------------------------

def test_paid_capped_at_as_of(app_env, viewer_client):
    """paid counts only the unit's dues credits with post_date <= as_of."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_payment(db, unit_number="101", post_date="2025-02-01", amount=300_000)
    insert_payment(db, unit_number="101", post_date="2025-09-01", amount=400_000)
    data = get_dues(viewer_client, "2025-06-30")
    assert unit_row(data, "101")["paid"] == 300_000   # September excluded


def test_paid_only_current_year(app_env, viewer_client):
    """A payment in a different calendar year never counts toward this year."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_payment(db, unit_number="101", post_date="2024-05-01", amount=999_999)
    insert_payment(db, unit_number="101", post_date="2025-05-01", amount=200_000)
    data = get_dues(viewer_client, "2025-12-31")
    assert unit_row(data, "101")["paid"] == 200_000   # 2024 excluded


def test_paid_ignores_other_categories(app_env, viewer_client):
    """Only the unit's own `Dues <n>` credits count; interest and other units'
    dues never do."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_credit_to_category(db, category_name="Interest",
                              post_date="2025-03-01", amount=500_000)
    insert_payment(db, unit_number="102", post_date="2025-03-01", amount=600_000)
    insert_payment(db, unit_number="101", post_date="2025-03-01", amount=100_000)
    data = get_dues(viewer_client, "2025-06-30")
    assert unit_row(data, "101")["paid"] == 100_000
    assert unit_row(data, "102")["paid"] == 600_000


def test_overpayment_is_credit(app_env, viewer_client):
    """Paying more than expected yields a negative outstanding (a credit), not
    clamped to zero."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # annual_dues(101) = 1,170,000
    insert_payment(db, unit_number="101", post_date="2025-03-01", amount=1_500_000)
    u101 = unit_row(get_dues(viewer_client, "2025-06-30"), "101")
    assert u101["expected_total"] == 1_170_000
    assert u101["paid"] == 1_500_000
    assert u101["outstanding"] == -330_000


# --- carryover (AC4.*) -----------------------------------------------------

def test_2025_carryover_is_baseline(app_env, viewer_client):
    """For 2025, carryover is exactly the unit_past_dues baseline row."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # annual_dues(101) = 1,170,000
    insert_past_due(db, unit_number="101", year=2025, past_due_balance=250_000)
    u101 = unit_row(get_dues(viewer_client, "2025-06-30"), "101")
    assert u101["carryover"] == 250_000
    assert u101["expected_total"] == 1_420_000        # 250,000 + 1,170,000


def test_carryover_accumulates_forward(app_env, viewer_client):
    """For 2026, carryover = baseline + 2025 annual dues - 2025 full-year payments;
    this year's dues and payments stack on top of it."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    clear_budgets(db, 2026)
    insert_past_due(db, unit_number="101", year=2025, past_due_balance=100_000)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # 2025 annual_dues(101)=1,170,000
    insert_payment(db, unit_number="101", post_date="2025-06-01", amount=500_000)
    insert_budget(db, year=2026, category_name="Insurance Premiums",
                  annual_amount=20_000_000)            # 2026 annual_dues(101)=2,340,000
    insert_payment(db, unit_number="101", post_date="2026-05-01", amount=1_000_000)
    u101 = unit_row(get_dues(viewer_client, "2026-12-31"), "101")
    # carry_in(2026) = 100,000 + 1,170,000 - 500,000 = 770,000
    assert u101["carryover"] == 770_000
    assert u101["annual_dues"] == 2_340_000
    assert u101["expected_total"] == 3_110_000        # 770,000 + 2,340,000
    assert u101["paid"] == 1_000_000
    assert u101["outstanding"] == 2_110_000


def test_carryover_three_years(app_env, viewer_client):
    """A 2027 query iterates two prior years (2025, 2026) in the carryover loop —
    catching off-by-one loop bounds or per-iteration baseline double-counting that a
    single-iteration (2026) example cannot distinguish."""
    db = app_env["db_path"]
    for y in (2025, 2026, 2027):
        clear_budgets(db, y)
    insert_past_due(db, unit_number="101", year=2025, past_due_balance=100_000)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # 2025 annual_dues(101)=1,170,000
    insert_payment(db, unit_number="101", post_date="2025-06-01", amount=400_000)
    insert_budget(db, year=2026, category_name="Insurance Premiums",
                  annual_amount=20_000_000)            # 2026 annual_dues(101)=2,340,000
    insert_payment(db, unit_number="101", post_date="2026-06-01", amount=1_000_000)
    insert_budget(db, year=2027, category_name="Insurance Premiums",
                  annual_amount=30_000_000)            # 2027 annual_dues(101)=3,510,000
    insert_payment(db, unit_number="101", post_date="2027-03-01", amount=500_000)
    insert_payment(db, unit_number="101", post_date="2027-09-01", amount=999_999)  # after as-of
    u101 = unit_row(get_dues(viewer_client, "2027-06-30"), "101")
    # carry_in(2027): y=2025 -> 100,000 + 1,170,000 - 400,000 = 870,000;
    #                 y=2026 -> +0 + 2,340,000 - 1,000,000 = 2,210,000
    assert u101["carryover"] == 2_210_000
    assert u101["annual_dues"] == 3_510_000
    assert u101["expected_total"] == 5_720_000        # 2,210,000 + 3,510,000
    assert u101["paid"] == 500_000                     # September excluded
    assert u101["outstanding"] == 5_220_000


def test_carryover_uses_full_prior_year_payments(app_env, viewer_client):
    """A prior year's full-year payment reduces this year's carryover even when the
    requested as-of date is early in the current year, while the current year's
    own payments are still capped at that as-of date."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    clear_budgets(db, 2026)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # 2025 annual_dues(101)=1,170,000
    insert_payment(db, unit_number="101", post_date="2025-12-20", amount=1_170_000)
    insert_budget(db, year=2026, category_name="Insurance Premiums",
                  annual_amount=10_000_000)            # 2026 annual_dues(101)=1,170,000
    insert_payment(db, unit_number="101", post_date="2026-02-01", amount=200_000)
    insert_payment(db, unit_number="101", post_date="2026-06-01", amount=900_000)
    u101 = unit_row(get_dues(viewer_client, "2026-03-01"), "101")
    # 2025 fully paid -> carry_in(2026) = 0 even though as_of is early 2026.
    assert u101["carryover"] == 0
    # Current-year payment after the as-of date (June) is excluded.
    assert u101["paid"] == 200_000
    assert u101["expected_total"] == 1_170_000
    assert u101["outstanding"] == 970_000


# --- totals (AC6.*) --------------------------------------------------------

def test_totals_are_sums(app_env, viewer_client):
    """Each total is the exact integer-cent sum of the corresponding unit field."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=9_990_000)
    insert_past_due(db, unit_number="201", year=2025, past_due_balance=123_400)
    insert_payment(db, unit_number="101", post_date="2025-04-01", amount=250_000)
    insert_payment(db, unit_number="303", post_date="2025-04-01", amount=777_000)
    data = get_dues(viewer_client, "2025-06-30")
    assert len(data["units"]) == len(SEEDED_UNITS)
    for field in ("carryover", "annual_dues", "expected_total", "paid", "outstanding"):
        assert data["totals"][field] == sum(u[field] for u in data["units"]), field
