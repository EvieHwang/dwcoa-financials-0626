"""Dashboard aggregation logic (slice 6), as plain testable functions.

Joins the tables and engines built by earlier slices into one read-only,
association-level financial picture for a given **as-of date**. Business logic
lives here, not in the route handler (constitution). Every function takes an open
`sqlite3.Connection` and a `datetime.date`, and returns integer-cent Python
structures — no floats anywhere (constitution: "Money").

It *consumes* the budgets-005 proration engine (`app.proration`) for every
budget-to-date figure; it never re-implements the timing stepping. Transfers
(`Transfer`/`Internal` categories) never count as income or expense — they move
money between accounts and are already reflected in each account's running
`balance`.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from .proration import effective_timing, prorated_ytd

# Only these category types contribute to income/expense aggregation; the rest
# (`Transfer`/`Internal`) are the excluded "transfers".
INCOME = "Income"
EXPENSE = "Expense"

RESERVE_ACCOUNT = "Reserve Fund"
RESERVE_BUDGET_CATEGORY = "Reserve Contribution"


def _iso(d: date) -> str:
    return d.isoformat()


def _prior_year_end(year: int) -> str:
    """Dec 31 of the year before `year`, as an ISO date string."""
    return f"{year - 1}-12-31"


def _latest_balance(con: sqlite3.Connection, account_name: str, on_or_before: str) -> int:
    """The bank running `balance` of an account's latest transaction with
    `post_date <= on_or_before`, or 0 when there is none. Not a recomputed sum —
    transfers between accounts are already reflected in the stored balance."""
    row = con.execute(
        """
        SELECT balance
        FROM transactions
        WHERE account_name = ? AND post_date <= ?
        ORDER BY post_date DESC, id DESC
        LIMIT 1
        """,
        (account_name, on_or_before),
    ).fetchone()
    return int(row["balance"]) if row is not None else 0


def account_balances(con: sqlite3.Connection, as_of: date) -> list[dict]:
    """Every seeded account with its balance as of the date and its
    beginning-of-year balance (AC4.1-4.4). Drives off the `accounts` table, so an
    account with no transactions is still listed with zeros."""
    as_of_iso = _iso(as_of)
    boy_iso = _prior_year_end(as_of.year)
    rows = con.execute("SELECT name FROM accounts ORDER BY name").fetchall()
    return [
        {
            "name": row["name"],
            "balance": _latest_balance(con, row["name"], as_of_iso),
            "beginning_balance": _latest_balance(con, row["name"], boy_iso),
        }
        for row in rows
    ]


def _actuals_by_category(
    con: sqlite3.Connection, type_: str, year: int, as_of: date
) -> dict[int, int]:
    """Per-category actual-to-date, in integer cents, for categorized rows of the
    given type within `year` and `post_date <= as_of`. Income draws from `credit`,
    expense from `debit` (AC2.4). Uncategorized rows (`category_id IS NULL`) are
    excluded by the join."""
    amount_col = "credit" if type_ == INCOME else "debit"
    rows = con.execute(
        f"""
        SELECT t.category_id AS category_id,
               COALESCE(SUM(t.{amount_col}), 0) AS actual
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE c.type = ?
          AND t.post_date >= ?
          AND t.post_date <= ?
        GROUP BY t.category_id
        """,
        (type_, f"{year}-01-01", _iso(as_of)),
    ).fetchall()
    return {row["category_id"]: int(row["actual"]) for row in rows}


def _budgets_by_category(
    con: sqlite3.Connection, type_: str, year: int
) -> dict[int, tuple[int, str | None]]:
    """Per-category (annual_amount, timing-override) for the year's budget rows on
    categories of the given type."""
    rows = con.execute(
        """
        SELECT b.category_id AS category_id,
               b.annual_amount AS annual_amount,
               b.timing AS timing
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        WHERE b.year = ? AND c.type = ?
        """,
        (year, type_),
    ).fetchall()
    return {
        row["category_id"]: (int(row["annual_amount"]), row["timing"])
        for row in rows
    }


def category_summary(
    con: sqlite3.Connection, type_: str, year: int, as_of: date
) -> dict:
    """A type's summary: per-category lines (each with annual/prorated budget,
    actual, remaining) plus exact integer-cent rolled-up totals (AC2.*, AC3.*).

    A category appears as a line when it has a budget row for the year OR actual
    activity in the year; purely zero-budget-and-zero-actual categories are
    suppressed (the frozen-shape note). Income budget is summed from income
    categories only — never derived from the operating (expense) budget."""
    defaults = {
        row["id"]: row["timing"]
        for row in con.execute(
            "SELECT id, timing FROM categories WHERE type = ?", (type_,)
        )
    }
    budgets = _budgets_by_category(con, type_, year)
    actuals = _actuals_by_category(con, type_, year, as_of)

    names = {
        row["id"]: row["name"]
        for row in con.execute(
            "SELECT id, name FROM categories WHERE type = ?", (type_,)
        )
    }

    lines: list[dict] = []
    for cat_id in sorted(set(budgets) | set(actuals)):
        annual_budget, timing_override = budgets.get(cat_id, (0, None))
        actual = actuals.get(cat_id, 0)
        if annual_budget == 0 and actual == 0:
            continue
        timing = effective_timing(timing_override, defaults.get(cat_id, "monthly"))
        prorated = prorated_ytd(annual_budget, timing, as_of, year)
        lines.append(
            {
                "category_id": cat_id,
                "name": names.get(cat_id, ""),
                "annual_budget": annual_budget,
                "prorated_budget": prorated,
                "actual": actual,
                "remaining": prorated - actual,
            }
        )

    return {
        "annual_budget": sum(l["annual_budget"] for l in lines),
        "prorated_budget": sum(l["prorated_budget"] for l in lines),
        "actual": sum(l["actual"] for l in lines),
        "remaining": sum(l["remaining"] for l in lines),
        "categories": lines,
    }


def reserve_fund_status(con: sqlite3.Connection, year: int, as_of: date) -> dict:
    """Reserve-fund activity for the year against its contribution budget (AC5.*).

    Contributions/expenses are measured by *account* (money in/out of the
    `Reserve Fund` account), independent of how those rows are categorized; the
    budget is the prorated-to-date `Reserve Contribution` category budget."""
    row = con.execute(
        """
        SELECT COALESCE(SUM(credit), 0) AS contributions,
               COALESCE(SUM(debit), 0) AS expenses
        FROM transactions
        WHERE account_name = ? AND post_date >= ? AND post_date <= ?
        """,
        (RESERVE_ACCOUNT, f"{year}-01-01", _iso(as_of)),
    ).fetchone()
    contributions = int(row["contributions"])
    expenses = int(row["expenses"])

    budget_row = con.execute(
        """
        SELECT b.annual_amount AS annual_amount, b.timing AS timing,
               c.timing AS category_default
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        WHERE b.year = ? AND c.name = ?
        """,
        (year, RESERVE_BUDGET_CATEGORY),
    ).fetchone()
    if budget_row is not None:
        timing = effective_timing(budget_row["timing"], budget_row["category_default"])
        budget = prorated_ytd(int(budget_row["annual_amount"]), timing, as_of, year)
    else:
        budget = 0

    return {
        "budget": budget,
        "contributions": contributions,
        "expenses": expenses,
        "net": contributions - expenses,
        "beginning_balance": _latest_balance(
            con, RESERVE_ACCOUNT, _prior_year_end(year)
        ),
    }


def monthly_cashflow(con: sqlite3.Connection, year: int, as_of: date) -> list[dict]:
    """One {month, income, expenses} entry per month from January through the
    as-of month, in integer cents (AC6.*). Income = credits on Income categories,
    expenses = debits on Expense categories; transfers and uncategorized rows are
    excluded. Months with no activity report zeros — never gaps."""
    rows = con.execute(
        """
        SELECT CAST(strftime('%m', t.post_date) AS INTEGER) AS month,
               c.type AS ctype,
               COALESCE(SUM(t.credit), 0) AS credit,
               COALESCE(SUM(t.debit), 0) AS debit
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE c.type IN (?, ?)
          AND t.post_date >= ? AND t.post_date <= ?
        GROUP BY month, c.type
        """,
        (INCOME, EXPENSE, f"{year}-01-01", _iso(as_of)),
    ).fetchall()

    income: dict[int, int] = {}
    expenses: dict[int, int] = {}
    for row in rows:
        if row["ctype"] == INCOME:
            income[row["month"]] = int(row["credit"])
        else:
            expenses[row["month"]] = int(row["debit"])

    return [
        {"month": m, "income": income.get(m, 0), "expenses": expenses.get(m, 0)}
        for m in range(1, as_of.month + 1)
    ]


def build_dashboard(con: sqlite3.Connection, as_of: date) -> dict:
    """Assemble the full dashboard payload for `as_of` (the frozen API shape)."""
    year = as_of.year
    accounts = account_balances(con, as_of)
    return {
        "as_of_date": _iso(as_of),
        "year": year,
        "accounts": accounts,
        "total_cash": sum(a["balance"] for a in accounts),
        "income_summary": category_summary(con, INCOME, year, as_of),
        "expense_summary": category_summary(con, EXPENSE, year, as_of),
        "reserve_fund": reserve_fund_status(con, year, as_of),
        "monthly_cashflow": monthly_cashflow(con, year, as_of),
    }
