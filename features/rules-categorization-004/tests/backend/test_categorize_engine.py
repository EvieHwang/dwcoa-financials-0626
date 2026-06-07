# @scaffolding — names the pure engine surface (`app.categorize.match` /
# `suggest_pattern`, and the rule mapping it consumes) ahead of implementation.
# /build may rename the functions or reshape the rule/result objects, logging it,
# as long as these BEHAVIORS hold: first-qualifying-rule-by-(priority, pattern
# length, id), case-insensitive substring + account + amount conditions, inactive
# rules skipped, no-match → needs review, and the suggest-pattern heuristic.
"""R1 (engine matching/ordering/conditions) and R7 (suggestion) — pure, no DB."""
import importlib

import pytest

categorize = importlib.import_module("app.categorize")


def rule(rid, pattern, category_id, *, account=None, amount_min=None,
         amount_max=None, priority=0, confidence=100, active=True):
    """Build a rule mapping the engine consumes (keys are the scaffolding seam)."""
    return {
        "id": rid, "pattern": pattern, "category_id": category_id,
        "account": account, "amount_min": amount_min, "amount_max": amount_max,
        "priority": priority, "confidence": confidence, "active": active,
    }


def _cat(result):
    return result["category_id"] if isinstance(result, dict) else result.category_id


def _needs_review(result):
    if isinstance(result, dict):
        return bool(result.get("needs_review"))
    return bool(getattr(result, "needs_review"))


def match(description, rules, *, account_name="Checking", debit=None, credit=None):
    return categorize.match(description, account_name, debit, credit, rules)


# --- R1 ordering -----------------------------------------------------------

def test_order_pattern_length():
    # Same priority: the longer matching pattern wins (more specific).
    rules = [
        rule(1, "BANK", 10, priority=0),
        rule(2, "BANK OF AMERICA", 20, priority=0),
    ]
    assert _cat(match("BANK OF AMERICA ACH", rules)) == 20


def test_order_priority():
    # Higher priority beats a longer lower-priority pattern.
    rules = [
        rule(1, "BANK", 10, priority=10),
        rule(2, "BANK OF AMERICA", 20, priority=0),
    ]
    assert _cat(match("BANK OF AMERICA ACH", rules)) == 10


def test_order_id_tiebreak():
    # Equal priority AND equal pattern length: lowest id wins (deterministic).
    rules = [
        rule(5, "AAAA", 50, priority=0),
        rule(3, "BBBB", 30, priority=0),
    ]
    assert _cat(match("AAAA BBBB", rules)) == 30


# --- R1 substring ----------------------------------------------------------

def test_substring_case_insensitive():
    rules = [rule(1, "electric", 10)]
    assert _cat(match("PUGET SOUND ELECTRIC CO", rules)) == 10
    assert _cat(match("puget sound electric co", rules)) == 10
    # Not a substring -> no match.
    assert _needs_review(match("WATER DISTRICT", rules)) is True


# --- R1 account condition --------------------------------------------------

def test_account_condition():
    rules = [rule(1, "DEPOSIT", 10, account="Savings")]
    assert _cat(match("MOBILE DEPOSIT", rules, account_name="Savings")) == 10
    # Same description, wrong account -> condition fails -> no match.
    assert _needs_review(match("MOBILE DEPOSIT", rules, account_name="Checking")) is True


# --- R1 amount condition ---------------------------------------------------

def test_amount_condition():
    rules = [rule(1, "MCCARY", 10, amount_min=10000, amount_max=20000)]
    # $150.00 debit -> 15000, inside the range.
    assert _cat(match("MCCARY LANDSCAPE", rules, debit=15000)) == 10
    # $5.00 debit -> 500, outside.
    assert _needs_review(match("MCCARY LANDSCAPE", rules, debit=500)) is True

    # min-only behaves as a one-sided floor; matches on a credit's magnitude.
    floor = [rule(2, "DUES", 20, amount_min=50000)]
    assert _cat(match("DUES PAYMENT", floor, credit=60000)) == 20
    assert _needs_review(match("DUES PAYMENT", floor, credit=40000)) is True

    # max-only behaves as a one-sided ceiling.
    ceil = [rule(3, "FEE", 30, amount_max=1000)]
    assert _cat(match("SERVICE FEE", ceil, debit=500)) == 30
    assert _needs_review(match("SERVICE FEE", ceil, debit=5000)) is True

    # A row with no debit and no credit cannot satisfy an amount-bounded rule.
    assert _needs_review(match("MCCARY LANDSCAPE", rules)) is True

    # Determinism when both are populated (atypical): debit takes precedence, so
    # the debit magnitude decides the match, not the credit.
    assert _cat(match("MCCARY LANDSCAPE", rules, debit=15000, credit=999)) == 10
    assert _needs_review(
        match("MCCARY LANDSCAPE", rules, debit=500, credit=15000)) is True


# --- R1 active flag / no match ---------------------------------------------

def test_inactive_skipped():
    rules = [rule(1, "ELECTRIC", 10, active=False)]
    assert _needs_review(match("SEATTLE ELECTRIC", rules)) is True


def test_no_match_needs_review():
    res = match("TOTALLY UNKNOWN VENDOR", [rule(1, "ELECTRIC", 10)])
    assert _needs_review(res) is True
    assert _cat(res) is None


def test_match_returns_category_not_flagged():
    # The engine's internal result shape is @scaffolding; the durable contract is
    # "matched -> category set, not flagged". Confidence *propagation* is pinned at
    # the DB/ingest layer (test_categorize_on_ingest.py) where it is observable.
    res = match("SEATTLE ELECTRIC", [rule(1, "ELECTRIC", 10, confidence=90)])
    assert _cat(res) == 10
    assert _needs_review(res) is False


# --- R7 suggested pattern --------------------------------------------------

@pytest.mark.parametrize("description,expected", [
    ("SEATTLE UTILITIES BILL 12345", "SEATTLE UTILITIES BILL"),
    ("ACH PYMT 0099283 R YOUNG", "ACH PYMT R YOUNG"),
    ("Check 1042", "Check"),
    ("NWEDI-291390275", "NWEDI-291390275"),  # whole token stripped -> fallback
    ("Visa 12", "Visa 12"),                   # only 2 digits -> token kept
])
def test_suggest_pattern(description, expected):
    assert categorize.suggest_pattern(description) == expected
