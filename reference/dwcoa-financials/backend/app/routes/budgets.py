"""Budget management routes."""

import json
from typing import Any

from app.services import database


def handle_list(year: int) -> dict:
    """List all budgets for a year.

    Args:
        year: Budget year

    Returns:
        Response with budget list including transaction counts and lock status
    """
    budgets = database.get_budgets(year)

    # Add transaction count for each category
    for budget in budgets:
        count_row = database.fetch_one(
            "SELECT COUNT(*) as count FROM transactions WHERE category_id = ?",
            (budget['category_id'],)
        )
        budget['transaction_count'] = count_row['count'] if count_row else 0

    # Get lock status for this year
    lock_info = database.get_budget_lock(year)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'year': year,
            'locked': lock_info.get('locked', False) if lock_info else False,
            'locked_at': lock_info.get('locked_at') if lock_info else None,
            'budgets': budgets
        })
    }


def handle_upsert(body: dict) -> dict:
    """Create or update a budget entry.

    Args:
        body: Budget data (year, category_id, annual_amount)

    Returns:
        Response with budget entry
    """
    required = ['year', 'category_id', 'annual_amount']
    for field in required:
        if body.get(field) is None:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': f'{field} is required'})
            }

    year = int(body['year'])
    category_id = int(body['category_id'])
    annual_amount = float(body['annual_amount'])

    # Check if budget is locked
    if database.is_budget_locked(year):
        return {
            'statusCode': 403,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'locked', 'message': 'Budget is locked for this year'})
        }

    # Verify category exists
    category = database.get_category_by_id(category_id)
    if not category:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'Category not found'})
        }

    # Upsert budget
    with database.transaction():
        database.execute("""
            INSERT INTO budgets (year, category_id, annual_amount)
            VALUES (?, ?, ?)
            ON CONFLICT(year, category_id) DO UPDATE SET
                annual_amount = excluded.annual_amount
        """, (year, category_id, annual_amount))

    # Fetch the budget entry
    row = database.fetch_one("""
        SELECT b.*, c.name as category_name, c.type as category_type
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.year = ? AND b.category_id = ?
    """, (year, category_id))

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(database.row_to_dict(row))
    }


def handle_copy(body: dict) -> dict:
    """Copy budgets from one year to another.

    Args:
        body: Copy parameters (from_year, to_year)

    Returns:
        Response with count of copied budgets
    """
    from_year = body.get('from_year')
    to_year = body.get('to_year')

    if not from_year or not to_year:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'from_year and to_year are required'})
        }

    from_year = int(from_year)
    to_year = int(to_year)

    if from_year == to_year:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'from_year and to_year must be different'})
        }

    # Check if target year is locked
    if database.is_budget_locked(to_year):
        return {
            'statusCode': 403,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'locked', 'message': f'Budget is locked for {to_year}'})
        }

    # Check source budgets exist
    source_budgets = database.get_budgets(from_year)
    if not source_budgets:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': f'No budgets found for {from_year}'})
        }

    # Copy budgets
    with database.transaction():
        database.execute("""
            INSERT OR REPLACE INTO budgets (year, category_id, annual_amount)
            SELECT ?, category_id, annual_amount
            FROM budgets
            WHERE year = ?
        """, (to_year, from_year))

    # Count copied
    count_row = database.fetch_one(
        "SELECT COUNT(*) as count FROM budgets WHERE year = ?",
        (to_year,)
    )
    count = count_row['count'] if count_row else 0

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': f'Copied {count} budgets from {from_year} to {to_year}',
            'count': count
        })
    }


def handle_lock(year: int, body: dict) -> dict:
    """Lock or unlock a budget year.

    Args:
        year: Budget year
        body: Request body with 'locked' boolean

    Returns:
        Response with lock status
    """
    locked = body.get('locked', True)

    lock_info = database.set_budget_lock(year, locked)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'year': year,
            'locked': lock_info.get('locked', False),
            'locked_at': lock_info.get('locked_at')
        })
    }
