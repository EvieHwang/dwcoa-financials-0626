# @frozen — the proration BEHAVIOR (the R7 worked-example table and the
# effective-timing rule) is the contract. The import path / function name is
# @scaffolding: /build may rename the module or signature, logging it in
# build-deviations.md, as long as these results hold. This is the constitution's
# centralized, unit-tested budget-timing math — a weak test here is worse than
# none, so every case is a hand-verified number.
"""R7: YTD proration stepped by period reached, in integer cents."""
from datetime import date

import pytest

# Scaffolding seam: the engine lives behind these names until /build may refine
# them. The behavior asserted below is what is frozen.
from app.proration import effective_timing, prorated_ytd

YEAR = 2025
ANNUAL = 120000  # $1,200.00 in cents


@pytest.mark.parametrize(
    "timing,as_of,expected",
    [
        # monthly accrues by month reached (whole month counts on entry)
        ("monthly", date(2025, 1, 15), 10000),
        ("monthly", date(2025, 6, 1), 60000),
        ("monthly", date(2025, 6, 30), 60000),
        ("monthly", date(2025, 12, 31), 120000),
        # quarterly steps at quarter boundaries (full quarter on entry)
        ("quarterly", date(2025, 1, 10), 30000),
        ("quarterly", date(2025, 4, 30), 60000),
        ("quarterly", date(2025, 7, 1), 90000),
        ("quarterly", date(2025, 12, 31), 120000),
        # annual is fully expected from January 1
        ("annual", date(2025, 1, 1), 120000),
        ("annual", date(2025, 12, 31), 120000),
    ],
)
def test_prorated_ytd_within_year(timing, as_of, expected):
    assert prorated_ytd(ANNUAL, timing, as_of, YEAR) == expected


@pytest.mark.parametrize("timing", ["monthly", "quarterly", "annual"])
def test_after_budget_year_is_full(timing):
    # A date in any later year means the whole year has elapsed -> full amount.
    assert prorated_ytd(ANNUAL, timing, date(2026, 2, 1), YEAR) == ANNUAL


@pytest.mark.parametrize("timing", ["monthly", "quarterly", "annual"])
def test_before_budget_year_is_zero(timing):
    # A date before the budget year -> nothing expected yet.
    assert prorated_ytd(ANNUAL, timing, date(2024, 12, 31), YEAR) == 0


def test_rounding_is_half_up_to_the_cent():
    # 100 cents over 12 months: 8.33.. -> 8 ; 16.66.. -> 17
    assert prorated_ytd(100, "monthly", date(2025, 1, 31), YEAR) == 8
    assert prorated_ytd(100, "monthly", date(2025, 2, 28), YEAR) == 17
    # 150 / 12 = 12.5 -> rounds up to 13
    assert prorated_ytd(150, "monthly", date(2025, 1, 15), YEAR) == 13


def test_returns_integer_cents_no_float():
    result = prorated_ytd(ANNUAL, "quarterly", date(2025, 5, 1), YEAR)
    assert isinstance(result, int)


def test_zero_budget_prorates_to_zero():
    for timing in ("monthly", "quarterly", "annual"):
        assert prorated_ytd(0, timing, date(2025, 6, 30), YEAR) == 0


def test_effective_timing_override_beats_default():
    # A per-line override wins; absent override falls back to category default.
    assert effective_timing("annual", "monthly") == "annual"
    assert effective_timing(None, "monthly") == "monthly"
    assert effective_timing(None, "quarterly") == "quarterly"


def test_override_drives_proration_not_category_default():
    # A line whose category default is monthly but whose override is annual must
    # prorate as annual (full from January), not as monthly (3/12). This pins the
    # resolve-then-prorate composition so a caller can't wire the default timing.
    eff = effective_timing("annual", "monthly")
    assert prorated_ytd(ANNUAL, eff, date(2025, 3, 1), YEAR) == ANNUAL  # not 30000
    # And the inverse: no override falls back to the monthly default's stepping.
    eff_default = effective_timing(None, "monthly")
    assert prorated_ytd(ANNUAL, eff_default, date(2025, 3, 1), YEAR) == 30000
