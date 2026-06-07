"""Pure categorization engine (D1) — no FastAPI, no DB imports.

The router builds rule mappings from DB rows and passes them in; this module
never reads the database. It owns the two highest-value pure surfaces:

- `match` — pick the winning rule for a transaction by R1's ordering
  (priority desc, then pattern length desc, then rule id asc), applying the
  case-insensitive substring + optional account + optional amount conditions,
  skipping inactive rules; no match yields a "needs review" verdict.
- `suggest_pattern` — the R7 smart-stripping heuristic for a starting pattern.

A rule is any mapping with keys: id, pattern, category_id, account,
amount_min, amount_max, priority, confidence, active. (sqlite3.Row and plain
dicts both support the `rule["key"]` access used here.)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

# How many digit characters in a token make it "noise" (an id / invoice /
# date code) the suggestion heuristic drops (R7).
_DIGIT_NOISE_THRESHOLD = 3
# Minimum length of a useful suggested pattern before falling back (R7).
_MIN_PATTERN_LEN = 3


@dataclass
class MatchResult:
    """The engine's verdict for one transaction (the result shape is
    @scaffolding; the observable contract is category + needs_review, with
    confidence/source propagated to the DB layer)."""

    category_id: Optional[int]
    confidence: Optional[int]
    source: Optional[str]
    needs_review: bool


def signed_agnostic_amount(debit: Optional[int], credit: Optional[int]) -> Optional[int]:
    """The transaction's matchable money magnitude in integer cents.

    A bank row populates at most one of debit/credit; to stay deterministic in
    the atypical both-present case, debit takes precedence. A row with both
    NULL has no matchable amount.
    """
    if debit is not None:
        return debit
    if credit is not None:
        return credit
    return None


def _rule_matches(
    rule: Mapping[str, Any],
    description_lower: str,
    account_name: Optional[str],
    magnitude: Optional[int],
) -> bool:
    pattern = rule["pattern"]
    if not pattern:
        return False
    if pattern.lower() not in description_lower:
        return False

    account = rule["account"]
    if account:  # an empty/NULL account condition is "no condition"
        if account_name != account:
            return False

    amount_min = rule["amount_min"]
    amount_max = rule["amount_max"]
    if amount_min is not None or amount_max is not None:
        if magnitude is None:
            return False
        if amount_min is not None and magnitude < amount_min:
            return False
        if amount_max is not None and magnitude > amount_max:
            return False

    return True


def match(
    description: Optional[str],
    account_name: Optional[str],
    debit: Optional[int],
    credit: Optional[int],
    rules: Sequence[Mapping[str, Any]],
) -> MatchResult:
    """Return the winning active rule's verdict, or a needs-review result."""
    description_lower = (description or "").lower()
    magnitude = signed_agnostic_amount(debit, credit)

    candidates = [
        rule
        for rule in rules
        if rule["active"]
        and _rule_matches(rule, description_lower, account_name, magnitude)
    ]
    if not candidates:
        return MatchResult(
            category_id=None, confidence=None, source=None, needs_review=True
        )

    # Priority desc, then pattern length desc, then id asc — a total order, so
    # the winner is deterministic across builds (R1).
    winner = min(
        candidates,
        key=lambda r: (-int(r["priority"]), -len(r["pattern"]), int(r["id"])),
    )
    return MatchResult(
        category_id=winner["category_id"],
        confidence=winner["confidence"],
        source="auto",
        needs_review=False,
    )


def suggest_pattern(description: str) -> str:
    """Smart-strip a description into a reusable starting pattern (R7).

    Split on whitespace, drop any token with >=3 digit characters (ids /
    invoice numbers / long date codes), collapse the rest with single spaces.
    If the result is shorter than 3 characters, fall back to the trimmed input.
    """
    tokens = description.split()
    kept = [
        token
        for token in tokens
        if sum(ch.isdigit() for ch in token) < _DIGIT_NOISE_THRESHOLD
    ]
    result = " ".join(kept).strip()
    if len(result) < _MIN_PATTERN_LEN:
        return description.strip()
    return result
