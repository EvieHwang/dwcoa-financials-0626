"""Database service for SQLite operations."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Optional

from app.utils import s3

# Database file locations
DB_KEY = 'dwcoa.db'
_db_connection: Optional[sqlite3.Connection] = None
_db_path: Optional[str] = None


def get_sql_path(filename: str) -> str:
    """Get path to SQL file in package."""
    # When running in Lambda, files are in /var/task
    base_path = Path(__file__).parent.parent.parent / 'sql'
    return str(base_path / filename)


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database with schema and seed data.

    Args:
        conn: SQLite connection
    """
    # Run schema
    with open(get_sql_path('schema.sql'), 'r') as f:
        conn.executescript(f.read())

    # Run migrations for existing databases
    run_migrations(conn)

    # Run seed data
    with open(get_sql_path('seed.sql'), 'r') as f:
        conn.executescript(f.read())

    # Run categorization rules
    with open(get_sql_path('rules.sql'), 'r') as f:
        conn.executescript(f.read())

    conn.commit()


def run_migrations(conn: sqlite3.Connection) -> None:
    """Run database migrations for schema updates.

    Args:
        conn: SQLite connection
    """
    # Check if past_due_balance column exists in units table
    cursor = conn.execute("PRAGMA table_info(units)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'past_due_balance' not in columns:
        conn.execute("ALTER TABLE units ADD COLUMN past_due_balance REAL NOT NULL DEFAULT 0")

    # Create unit_past_dues table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS unit_past_dues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_number TEXT NOT NULL,
            year INTEGER NOT NULL,
            past_due_balance REAL NOT NULL DEFAULT 0,
            UNIQUE(unit_number, year),
            FOREIGN KEY (unit_number) REFERENCES units(number)
        )
    """)

    # Create budget_locks table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budget_locks (
            year INTEGER PRIMARY KEY,
            locked INTEGER NOT NULL DEFAULT 0,
            locked_at TEXT,
            locked_by TEXT
        )
    """)

    # Change Reserve Contribution from Transfer to Expense (for calculated dues)
    conn.execute("UPDATE categories SET type = 'Expense' WHERE name = 'Reserve Contribution'")

    # Update ownership percentages (99.9% total; 0.1% is calculated interest income)
    conn.execute("UPDATE units SET ownership_pct = 0.117 WHERE number IN ('101', '201', '301')")
    conn.execute("UPDATE units SET ownership_pct = 0.104 WHERE number IN ('102', '202', '302')")
    conn.execute("UPDATE units SET ownership_pct = 0.112 WHERE number IN ('103', '203', '303')")


def get_connection() -> sqlite3.Connection:
    """Get database connection, downloading from S3 if needed.

    Returns:
        SQLite connection with row factory set
    """
    global _db_connection, _db_path

    if _db_connection is not None:
        return _db_connection

    # Download database from S3 or create new
    _db_path = s3.get_temp_path('dwcoa.db')

    if s3.file_exists(DB_KEY):
        s3.download_file(DB_KEY, _db_path)
        _db_connection = sqlite3.connect(_db_path)
        _db_connection.row_factory = sqlite3.Row
        # Run migrations on existing database
        run_migrations(_db_connection)
        _db_connection.commit()
        # Don't save here - only save when actual user data changes
        # This prevents race conditions where concurrent Lambda instances
        # overwrite each other's changes with stale data
    else:
        # Create new database
        _db_connection = sqlite3.connect(_db_path)
        _db_connection.row_factory = sqlite3.Row
        init_db(_db_connection)
        # Upload initial database
        save_db()

    return _db_connection


def save_db() -> None:
    """Save database to S3."""
    global _db_connection, _db_path

    if _db_connection is not None and _db_path is not None:
        _db_connection.commit()
        s3.upload_file(_db_path, DB_KEY)


def close_db() -> None:
    """Close database connection."""
    global _db_connection, _db_path

    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
        _db_path = None


@contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions.

    Yields:
        SQLite connection

    Commits on success, rolls back on exception, saves to S3.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
        save_db()
    except Exception:
        conn.rollback()
        raise


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Execute SQL and return cursor.

    Args:
        sql: SQL statement
        params: Query parameters

    Returns:
        Cursor with results
    """
    conn = get_connection()
    return conn.execute(sql, params)


def execute_many(sql: str, params_list: List[tuple]) -> None:
    """Execute SQL with multiple parameter sets.

    Args:
        sql: SQL statement
        params_list: List of parameter tuples
    """
    conn = get_connection()
    conn.executemany(sql, params_list)


def fetch_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """Fetch a single row.

    Args:
        sql: SQL query
        params: Query parameters

    Returns:
        Row or None
    """
    cursor = execute(sql, params)
    return cursor.fetchone()


def fetch_all(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    """Fetch all rows.

    Args:
        sql: SQL query
        params: Query parameters

    Returns:
        List of rows
    """
    cursor = execute(sql, params)
    return cursor.fetchall()


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict]:
    """Convert a Row to a dict.

    Args:
        row: SQLite Row object

    Returns:
        Dict or None
    """
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: List[sqlite3.Row]) -> List[dict]:
    """Convert Rows to list of dicts.

    Args:
        rows: List of SQLite Row objects

    Returns:
        List of dicts
    """
    return [dict(row) for row in rows]


# Convenience functions for common queries

def get_categories(active_only: bool = True, category_type: Optional[str] = None) -> List[dict]:
    """Get all categories.

    Args:
        active_only: Only return active categories
        category_type: Filter by type (Income, Expense, Transfer, Internal)

    Returns:
        List of category dicts
    """
    sql = "SELECT * FROM categories WHERE 1=1"
    params: List[Any] = []

    if active_only:
        sql += " AND active = 1"

    if category_type:
        sql += " AND type = ?"
        params.append(category_type)

    sql += " ORDER BY type, name"
    return rows_to_dicts(fetch_all(sql, tuple(params)))


def get_category_by_id(category_id: int) -> Optional[dict]:
    """Get a category by ID."""
    return row_to_dict(fetch_one("SELECT * FROM categories WHERE id = ?", (category_id,)))


def get_category_by_name(name: str) -> Optional[dict]:
    """Get a category by name."""
    return row_to_dict(fetch_one("SELECT * FROM categories WHERE name = ?", (name,)))


def get_accounts() -> List[dict]:
    """Get all account mappings."""
    return rows_to_dicts(fetch_all("SELECT * FROM accounts ORDER BY name"))


def get_account_name(masked_number: str) -> Optional[str]:
    """Get friendly account name from masked number."""
    row = fetch_one("SELECT name FROM accounts WHERE masked_number = ?", (masked_number,))
    return row['name'] if row else None


def get_units() -> List[dict]:
    """Get all units with ownership percentages."""
    return rows_to_dicts(fetch_all("SELECT * FROM units ORDER BY number"))


def get_budgets(year: int) -> List[dict]:
    """Get all active categories with their budgets for a year.

    Returns ALL active categories, not just ones with existing budgets.
    Categories without a budget entry will show annual_amount=0.
    """
    sql = """
        SELECT
            c.id as category_id,
            c.name as category_name,
            c.type as category_type,
            COALESCE(b.annual_amount, 0) as annual_amount,
            b.id as budget_id,
            ? as year
        FROM categories c
        LEFT JOIN budgets b ON b.category_id = c.id AND b.year = ?
        WHERE c.active = 1
        ORDER BY c.type, c.name
    """
    return rows_to_dicts(fetch_all(sql, (year, year)))


def get_config(key: str) -> Optional[str]:
    """Get a config value."""
    row = fetch_one("SELECT value FROM app_config WHERE key = ?", (key,))
    return row['value'] if row else None


def set_config(key: str, value: str) -> None:
    """Set a config value."""
    execute(
        "INSERT OR REPLACE INTO app_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value)
    )


def get_categorize_rules() -> List[dict]:
    """Get all active categorization rules, ordered by priority."""
    sql = """
        SELECT r.*, c.name as category_name
        FROM categorize_rules r
        JOIN categories c ON r.category_id = c.id
        WHERE r.active = 1
        ORDER BY r.priority DESC, r.id
    """
    return rows_to_dicts(fetch_all(sql))


def get_rules() -> List[dict]:
    """Get all rules with category names for admin UI."""
    sql = """
        SELECT r.id, r.pattern, r.category_id, r.active, c.name as category_name
        FROM categorize_rules r
        JOIN categories c ON r.category_id = c.id
        ORDER BY c.name, r.pattern
    """
    return rows_to_dicts(fetch_all(sql))


def get_rule_by_id(rule_id: int) -> Optional[dict]:
    """Get a rule by ID."""
    sql = """
        SELECT r.*, c.name as category_name
        FROM categorize_rules r
        JOIN categories c ON r.category_id = c.id
        WHERE r.id = ?
    """
    return row_to_dict(fetch_one(sql, (rule_id,)))


def rule_pattern_exists(pattern: str, exclude_id: Optional[int] = None) -> bool:
    """Check if a pattern already exists (case-insensitive).

    Args:
        pattern: Pattern to check
        exclude_id: Rule ID to exclude from check (for updates)

    Returns:
        True if pattern exists
    """
    sql = "SELECT id FROM categorize_rules WHERE UPPER(pattern) = UPPER(?)"
    params: List[Any] = [pattern]

    if exclude_id:
        sql += " AND id != ?"
        params.append(exclude_id)

    return fetch_one(sql, tuple(params)) is not None


def create_rule(pattern: str, category_id: int) -> dict:
    """Create a new categorization rule.

    Args:
        pattern: Match pattern (case-insensitive substring)
        category_id: Category ID to assign

    Returns:
        Created rule dict
    """
    with transaction():
        execute(
            """INSERT INTO categorize_rules (pattern, category_id, confidence, priority, active)
               VALUES (?, ?, 100, 100, 1)""",
            (pattern, category_id)
        )
        # Get the created rule
        cursor = execute("SELECT last_insert_rowid()")
        rule_id = cursor.fetchone()[0]

    return get_rule_by_id(rule_id)


def update_rule(rule_id: int, pattern: Optional[str] = None,
                category_id: Optional[int] = None, active: Optional[bool] = None) -> Optional[dict]:
    """Update a categorization rule.

    Args:
        rule_id: Rule ID
        pattern: New pattern (optional)
        category_id: New category ID (optional)
        active: New active status (optional)

    Returns:
        Updated rule dict or None if not found
    """
    updates = []
    params: List[Any] = []

    if pattern is not None:
        updates.append("pattern = ?")
        params.append(pattern)

    if category_id is not None:
        updates.append("category_id = ?")
        params.append(category_id)

    if active is not None:
        updates.append("active = ?")
        params.append(1 if active else 0)

    if not updates:
        return get_rule_by_id(rule_id)

    params.append(rule_id)

    with transaction():
        execute(f"UPDATE categorize_rules SET {', '.join(updates)} WHERE id = ?", tuple(params))

    return get_rule_by_id(rule_id)


def delete_rule(rule_id: int) -> bool:
    """Delete a categorization rule.

    Rules only affect auto-categorization of NEW transactions.
    Deleting a rule does NOT affect existing transactions - they retain
    their assigned categories.

    Args:
        rule_id: Rule ID to delete

    Returns:
        True if rule was deleted, False if not found
    """
    rule = get_rule_by_id(rule_id)
    if not rule:
        return False

    with transaction():
        execute("DELETE FROM categorize_rules WHERE id = ?", (rule_id,))

    return True


def get_unit(unit_number: str) -> Optional[dict]:
    """Get a single unit by number.

    Args:
        unit_number: Unit number (e.g., '101')

    Returns:
        Unit dict or None if not found
    """
    row = fetch_one("SELECT * FROM units WHERE number = ?", (unit_number,))
    return row_to_dict(row) if row else None


def update_unit(unit_number: str, past_due_balance: float) -> Optional[dict]:
    """Update a unit's past due balance (deprecated - use update_unit_past_due).

    Args:
        unit_number: Unit number (e.g., '101')
        past_due_balance: New past due balance amount

    Returns:
        Updated unit dict or None if not found
    """
    # Verify unit exists
    unit = get_unit(unit_number)
    if not unit:
        return None

    with transaction():
        execute(
            "UPDATE units SET past_due_balance = ? WHERE number = ?",
            (past_due_balance, unit_number)
        )

    return get_unit(unit_number)


def get_unit_past_dues(year: int) -> List[dict]:
    """Get past due balances for all units for a specific year.

    Args:
        year: Budget year

    Returns:
        List of dicts with unit_number and past_due_balance
    """
    # Get all units with their year-specific past due (or 0 if not set)
    sql = """
        SELECT u.number as unit_number, COALESCE(upd.past_due_balance, 0) as past_due_balance
        FROM units u
        LEFT JOIN unit_past_dues upd ON u.number = upd.unit_number AND upd.year = ?
        ORDER BY u.number
    """
    return rows_to_dicts(fetch_all(sql, (year,)))


def get_unit_past_due(unit_number: str, year: int) -> float:
    """Get past due balance for a specific unit and year.

    Args:
        unit_number: Unit number (e.g., '101')
        year: Budget year

    Returns:
        Past due balance (0 if not set)
    """
    row = fetch_one(
        "SELECT past_due_balance FROM unit_past_dues WHERE unit_number = ? AND year = ?",
        (unit_number, year)
    )
    return row['past_due_balance'] if row else 0.0


def update_unit_past_due(unit_number: str, year: int, past_due_balance: float) -> Optional[dict]:
    """Update a unit's past due balance for a specific year.

    Args:
        unit_number: Unit number (e.g., '101')
        year: Budget year
        past_due_balance: New past due balance amount

    Returns:
        Dict with unit_number, year, past_due_balance or None if unit not found
    """
    # Verify unit exists
    unit = get_unit(unit_number)
    if not unit:
        return None

    with transaction():
        execute(
            """INSERT INTO unit_past_dues (unit_number, year, past_due_balance)
               VALUES (?, ?, ?)
               ON CONFLICT(unit_number, year) DO UPDATE SET past_due_balance = ?""",
            (unit_number, year, past_due_balance, past_due_balance)
        )

    return {
        'unit_number': unit_number,
        'year': year,
        'past_due_balance': past_due_balance
    }


def is_budget_locked(year: int) -> bool:
    """Check if a budget year is locked.

    Args:
        year: Budget year

    Returns:
        True if budget is locked
    """
    row = fetch_one("SELECT locked FROM budget_locks WHERE year = ?", (year,))
    return row['locked'] == 1 if row else False


def get_budget_lock(year: int) -> Optional[dict]:
    """Get budget lock status for a year.

    Args:
        year: Budget year

    Returns:
        Dict with year, locked, locked_at or None if not set
    """
    row = fetch_one("SELECT * FROM budget_locks WHERE year = ?", (year,))
    return row_to_dict(row) if row else {'year': year, 'locked': False, 'locked_at': None}


def set_budget_lock(year: int, locked: bool) -> dict:
    """Lock or unlock a budget year.

    Args:
        year: Budget year
        locked: Whether to lock or unlock

    Returns:
        Dict with year, locked, locked_at
    """
    with transaction():
        execute("""
            INSERT INTO budget_locks (year, locked, locked_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(year) DO UPDATE SET locked = ?, locked_at = datetime('now')
        """, (year, 1 if locked else 0, 1 if locked else 0))

    return get_budget_lock(year)


# =============================================================================
# Statement API Functions
# =============================================================================

def get_total_operating_budget_annual(year: int) -> float:
    """Get total annual operating budget for a year (not YTD).

    Operating budget excludes Reserve Contribution and Reserve Expenses.

    Args:
        year: Budget year

    Returns:
        Total annual operating budget amount
    """
    sql = """
        SELECT SUM(b.annual_amount) as total
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.year = ?
        AND c.type = 'Expense'
        AND c.name NOT IN ('Reserve Contribution', 'Reserve Expenses')
    """
    row = fetch_one(sql, (year,))
    return row['total'] if row and row['total'] else 0.0


def get_unit_payments_total(unit_number: str, year: int) -> float:
    """Get total dues payments for a unit in a specific year.

    Args:
        unit_number: Unit number (e.g., '101')
        year: Payment year

    Returns:
        Total payments amount
    """
    sql = """
        SELECT SUM(t.credit) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name = ?
        AND strftime('%Y', t.post_date) = ?
    """
    category_name = f'Dues {unit_number}'
    row = fetch_one(sql, (category_name, str(year)))
    return row['total'] if row and row['total'] else 0.0


def get_unit_recent_payments(unit_number: str, year: int, limit: int = 10) -> List[dict]:
    """Get recent dues payments for a unit in a specific year.

    Args:
        unit_number: Unit number (e.g., '101')
        year: Payment year
        limit: Maximum number of payments to return

    Returns:
        List of payment dicts with date and amount
    """
    sql = """
        SELECT t.post_date as date, t.credit as amount, t.description
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name = ?
        AND strftime('%Y', t.post_date) = ?
        AND t.credit IS NOT NULL
        AND t.credit > 0
        ORDER BY t.post_date DESC
        LIMIT ?
    """
    category_name = f'Dues {unit_number}'
    rows = fetch_all(sql, (category_name, str(year), limit))
    return [{'date': row['date'], 'amount': row['amount'], 'description': row['description']} for row in rows]


def has_unit_payment_in_current_month(unit_number: str, year: int, current_month: int) -> bool:
    """Check if unit has made ANY payment in the current month.

    Args:
        unit_number: Unit number (e.g., '101')
        year: Payment year
        current_month: Current month (1-12)

    Returns:
        True if any payment exists in current month, False otherwise
    """
    sql = """
        SELECT COUNT(*) as count
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name = ?
        AND strftime('%Y', t.post_date) = ?
        AND CAST(strftime('%m', t.post_date) AS INTEGER) = ?
        AND t.credit IS NOT NULL
        AND t.credit > 0
    """
    category_name = f'Dues {unit_number}'
    row = fetch_one(sql, (category_name, str(year), current_month))
    return row['count'] > 0 if row else False
