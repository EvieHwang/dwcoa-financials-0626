"""Dashboard routes."""

import json
from datetime import date, datetime
from typing import Optional

from app.services import database, budget_calc
from app.routes import dues


def _is_budget_locked(year: int) -> bool:
    """Check if budget is locked for a given year."""
    return database.is_budget_locked(year)


def handle_get_dashboard(as_of_date: Optional[str] = None) -> dict:
    """Get dashboard data as of a specific date.

    Args:
        as_of_date: Date string (YYYY-MM-DD) to view snapshot. Defaults to today.

    Returns:
        Response with complete dashboard data as of the specified date
    """
    # Parse date or default to today
    if as_of_date:
        try:
            snapshot_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        except ValueError:
            snapshot_date = date.today()
    else:
        snapshot_date = date.today()

    year = snapshot_date.year

    # Get last upload timestamp
    last_updated = database.get_config('last_upload_at')

    # Get account balances as of date
    accounts = budget_calc.get_account_balances(as_of_date=snapshot_date)
    total_cash = sum(a['balance'] for a in accounts)

    # Get beginning balances for the year (as of Dec 31 prior year)
    beginning_balances = budget_calc.get_account_balances_at_year_start(year)

    # Merge starting_balance into each account object
    starting_balance_map = {b['name']: b['balance'] for b in beginning_balances}
    for account in accounts:
        account['starting_balance'] = starting_balance_map.get(account['name'], 0)

    # Get budget summary as of date
    budget_summary = budget_calc.get_budget_summary(year, as_of_date=snapshot_date)

    # Get dues status as of date
    dues_data = dues.get_dues_status(year, as_of_date=snapshot_date)

    # Get reserve fund status
    reserve_fund = budget_calc.get_reserve_fund_status(year, as_of_date=snapshot_date)

    # Get monthly cashflow for charts
    monthly_cashflow = budget_calc.get_monthly_cashflow(year, as_of_date=snapshot_date)

    # Get review count (always current, not date-filtered)
    review_row = database.fetch_one(
        "SELECT COUNT(*) as count FROM transactions WHERE needs_review = 1"
    )
    review_count = review_row['count'] if review_row else 0

    # Check if budget is locked for the displayed year
    budget_locked = _is_budget_locked(year)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'last_updated': last_updated or None,
            'as_of_date': snapshot_date.isoformat(),
            'year': year,
            'budget_locked': budget_locked,
            'accounts': accounts,
            'beginning_balances': beginning_balances,
            'total_cash': round(total_cash, 2),
            'income_summary': budget_summary['income_summary'],
            'expense_summary': budget_summary['expense_summary'],
            'dues_status': dues_data['units'],
            'reserve_fund': reserve_fund,
            'monthly_cashflow': monthly_cashflow,
            'review_count': review_count
        })
    }
