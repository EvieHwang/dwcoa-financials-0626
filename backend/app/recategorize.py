"""DB-facing categorization helpers: loading rules and the re-categorization
sweep (D4). Kept out of `app.categorize` so that module stays pure (no DB).

The sweep (R6) re-evaluates the active rule set against every *open*
transaction — source `auto` OR flagged `needs_review` — and writes each new
verdict. Manual rows (source `manual`) and migrated *categorized* history
(category set, source unset, not flagged) are excluded by the open-set query,
so they are never clobbered. Idempotent by construction: each verdict is
recomputed from the rules, not from prior state.
"""
from __future__ import annotations

import sqlite3

from . import categorize

# Columns aliased to the keys the pure engine consumes.
_RULE_COLUMNS = (
    "id, pattern, category_id, account, amount_min, amount_max, "
    "priority, confidence, active"
)


def load_active_rules(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        f"SELECT {_RULE_COLUMNS} FROM categorize_rules WHERE active = 1"
    ).fetchall()
    return [dict(row) for row in rows]


def apply_verdict(
    con: sqlite3.Connection, txn_id: int, result: categorize.MatchResult
) -> None:
    """Write one engine verdict onto a transaction row."""
    if result.needs_review:
        con.execute(
            "UPDATE transactions SET category_id = NULL, auto_category_id = NULL, "
            "category_source = NULL, confidence = NULL, needs_review = 1, "
            "updated_at = datetime('now') WHERE id = ?",
            (txn_id,),
        )
    else:
        con.execute(
            "UPDATE transactions SET category_id = ?, auto_category_id = ?, "
            "category_source = 'auto', confidence = ?, needs_review = 0, "
            "updated_at = datetime('now') WHERE id = ?",
            (result.category_id, result.category_id, result.confidence, txn_id),
        )


def sweep(con: sqlite3.Connection) -> None:
    """Re-categorize every open transaction against the current active rules.

    Runs on the caller's connection inside the caller's transaction, so the
    whole rule-save-plus-sweep is atomic (R6).
    """
    rules = load_active_rules(con)
    open_rows = con.execute(
        "SELECT id, account_name, description, debit, credit FROM transactions "
        "WHERE category_source = 'auto' OR needs_review = 1"
    ).fetchall()
    for row in open_rows:
        result = categorize.match(
            row["description"], row["account_name"], row["debit"], row["credit"],
            rules,
        )
        apply_verdict(con, row["id"], result)
