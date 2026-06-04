"""Idempotent reference-data seeding (D3/D4).

Runs on every startup. Uses INSERT OR IGNORE keyed on each table's natural
unique constraint so re-seeding never duplicates rows or overwrites existing
values. Money is integer cents; ownership is integer per-mille.
"""
from __future__ import annotations

from .db import get_connection

# number -> ownership per-mille (0.117 -> 117)
UNITS: list[tuple[str, int]] = [
    ("101", 117), ("102", 104), ("103", 112),
    ("201", 117), ("202", 104), ("203", 112),
    ("301", 117), ("302", 104), ("303", 112),
]

# masked_number -> friendly name
ACCOUNTS: list[tuple[str, str]] = [
    ("****7145", "Savings"),
    ("****9242", "Checking"),
    ("****9226", "Reserve Fund"),
]

# name, type, default_account, timing
CATEGORIES: list[tuple[str, str, str, str]] = [
    ("Dues 101", "Income", "Savings", "monthly"),
    ("Dues 102", "Income", "Savings", "monthly"),
    ("Dues 103", "Income", "Savings", "monthly"),
    ("Dues 201", "Income", "Savings", "monthly"),
    ("Dues 202", "Income", "Savings", "monthly"),
    ("Dues 203", "Income", "Savings", "monthly"),
    ("Dues 301", "Income", "Savings", "monthly"),
    ("Dues 302", "Income", "Savings", "monthly"),
    ("Dues 303", "Income", "Savings", "monthly"),
    ("Interest income", "Income", "Any", "monthly"),
    ("Bulger Safe & Lock", "Expense", "Checking", "annual"),
    ("Cintas Fire Protection", "Expense", "Checking", "annual"),
    ("Common Area Cleaning", "Expense", "Checking", "monthly"),
    ("Fire Alarm", "Expense", "Checking", "monthly"),
    ("Grounds/Landscaping", "Expense", "Checking", "monthly"),
    ("Homeowners Club Dues", "Expense", "Checking", "annual"),
    ("Insurance Premiums", "Expense", "Checking", "monthly"),
    ("Seattle City Light", "Expense", "Checking", "monthly"),
    ("Other", "Expense", "Checking", "annual"),
    ("Reserve Contribution", "Transfer", "Savings", "monthly"),
    ("Reserve Expenses", "Expense", "Reserve Fund", "annual"),
    ("Transfers", "Internal", "Any", "annual"),
]

# 2025 annual budget, in integer cents, keyed by category name.
BUDGET_2025_CENTS: dict[str, int] = {
    "Dues 101": 595475, "Dues 201": 595475, "Dues 301": 595475,
    "Dues 102": 529311, "Dues 202": 529311, "Dues 302": 529311,
    "Dues 103": 570027, "Dues 203": 570027, "Dues 303": 570027,
    "Interest income": 2600,
    "Reserve Contribution": 1800000,
    "Bulger Safe & Lock": 40000,
    "Cintas Fire Protection": 150000,
    "Common Area Cleaning": 270000,
    "Fire Alarm": 330000,
    "Grounds/Landscaping": 1200000,
    "Other": 750000,
    "Insurance Premiums": 450000,
    "Seattle City Light": 600000,
}

# pattern -> category name. Base rule set from the reference data model.
CATEGORIZE_RULES: list[tuple[str, str]] = [
    ("BULGER SAFE", "Bulger Safe & Lock"),
    ("Cintas", "Cintas Fire Protection"),
    ("309 S CLOVERDALE ST", "Common Area Cleaning"),
    ("CENTURYLINK", "Fire Alarm"),
    ("LumenCenturyLink", "Fire Alarm"),
    ("WASHINGTON ALARM", "Fire Alarm"),
    ("MCCARY", "Grounds/Landscaping"),
    ("NWEDI-291390275", "Insurance Premiums"),
    ("SEATTLEUTILTIES", "Seattle City Light"),
    ("Dividend/Interest", "Interest income"),
    ("BOEING EMPLOYEES CREDIT UNION", "Dues 101"),
    ("Emma Landsman", "Dues 102"),
    ("JARED MOLTON", "Dues 103"),
    ("EVE HWANG ONLNE", "Dues 201"),
    ("WENLU CHENG", "Dues 203"),
    ("R Young ACH", "Dues 301"),
    ("ERNAST", "Dues 302"),
    ("Business Mobile Deposit", "Dues 303"),
]

APP_CONFIG: list[tuple[str, str]] = [
    ("current_year", "2025"),
    ("last_upload_at", ""),
]


def seed_reference_data(db_path: str) -> None:
    """Insert reference data when absent. Idempotent (safe on every startup)."""
    con = get_connection(db_path)
    try:
        con.executemany(
            "INSERT OR IGNORE INTO units (number, ownership_pct) VALUES (?, ?)",
            UNITS,
        )
        con.executemany(
            "INSERT OR IGNORE INTO accounts (masked_number, name) VALUES (?, ?)",
            ACCOUNTS,
        )
        con.executemany(
            "INSERT OR IGNORE INTO categories (name, type, default_account, timing) "
            "VALUES (?, ?, ?, ?)",
            CATEGORIES,
        )

        # Resolve category names -> ids for budgets and rules.
        cat_ids = {
            row["name"]: row["id"]
            for row in con.execute("SELECT id, name FROM categories")
        }

        budget_rows = [
            (2025, cat_ids[name], cents)
            for name, cents in BUDGET_2025_CENTS.items()
            if name in cat_ids
        ]
        con.executemany(
            "INSERT OR IGNORE INTO budgets (year, category_id, annual_amount) "
            "VALUES (?, ?, ?)",
            budget_rows,
        )

        # categorize_rules has no natural unique key; only seed when empty so a
        # treasurer's later edits are never clobbered by a re-seed.
        rule_count = con.execute("SELECT COUNT(*) FROM categorize_rules").fetchone()[0]
        if rule_count == 0:
            rule_rows = [
                (pattern, cat_ids[name], 100, 100, 1)
                for pattern, name in CATEGORIZE_RULES
                if name in cat_ids
            ]
            con.executemany(
                "INSERT INTO categorize_rules "
                "(pattern, category_id, confidence, priority, active) "
                "VALUES (?, ?, ?, ?, ?)",
                rule_rows,
            )

        con.executemany(
            "INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)",
            APP_CONFIG,
        )

        con.commit()
    finally:
        con.close()
