"""Budget calculation service."""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.services import database

# Cutoff year: 2025+ uses calculated dues from operating budget
# Years before this use legacy per-unit budget entries
CALCULATED_DUES_START_YEAR = 2025


def get_total_operating_budget(year: int) -> float:
    """Calculate total annual operating budget including Reserve Contribution.

    This is the sum of all Expense category annual budgets.
    Used for calculating unit dues in 2025+.

    Args:
        year: Budget year

    Returns:
        Total annual operating budget
    """
    sql = """
        SELECT COALESCE(SUM(b.annual_amount), 0) as total
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.year = ? AND c.type = 'Expense' AND c.active = 1
    """
    row = database.fetch_one(sql, (year,))
    return row['total'] if row else 0.0


def get_ytd_actuals(year: int, as_of_date: Optional[date] = None) -> Dict[int, float]:
    """Get YTD actual amounts by category for budget comparison.

    NOTE: This ONLY includes Income and Expense categories.
    Transfers (type='Transfer' and type='Internal') are intentionally excluded
    because they are not income or expenses - they just move money between accounts.
    Transfers DO affect account balances (handled by get_account_balances()),
    but should NOT appear in income/expense budget summaries.

    Args:
        year: Year to calculate
        as_of_date: Only include transactions on or before this date

    Returns:
        Dict mapping category_id to actual amount (Income and Expense only)
    """
    if as_of_date is None:
        as_of_date = date.today()

    # Income = credits, Expenses = debits
    # Transfers excluded - they're not income or expenses
    # Filter by year AND on or before as_of_date
    sql = """
        SELECT
            t.category_id,
            c.type,
            SUM(CASE WHEN c.type = 'Income' THEN t.credit ELSE t.debit END) as amount
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE strftime('%Y', t.post_date) = ?
        AND t.post_date <= ?
        AND t.category_id IS NOT NULL
        AND c.type IN ('Income', 'Expense')
        GROUP BY t.category_id
    """
    rows = database.fetch_all(sql, (str(year), as_of_date.isoformat()))

    return {row['category_id']: row['amount'] or 0 for row in rows}


def get_budget_summary(year: int, as_of_date: Optional[date] = None) -> dict:
    """Get complete budget summary for dashboard.

    For 2025+, income budget equals total operating budget:
    - Unit dues cover 99.9% (distributed by ownership percentages)
    - Interest income covers 0.1% (calculated, not manually entered)

    Budget amounts are always the full annual amount (not prorated by month).

    Args:
        year: Budget year
        as_of_date: Date to calculate actuals through (defaults to today)

    Returns:
        Dict with income_summary, expense_summary, and category details.
        If no budget exists for the year, returns $0 for all budget amounts.
    """
    if as_of_date is None:
        as_of_date = date.today()

    # Get budgets for the year (may be empty if no budget set up)
    budgets = database.get_budgets(year)

    # Get actuals through as_of_date
    actuals = get_ytd_actuals(year, as_of_date=as_of_date)

    # Process income
    income_categories = []
    income_annual_budget = 0
    income_ytd_actual = 0

    # Process expenses
    expense_categories = []
    expense_annual_budget = 0
    expense_ytd_actual = 0

    # For 2025+, get operating budget upfront to calculate interest income
    total_operating_budget = None
    if year >= CALCULATED_DUES_START_YEAR:
        total_operating_budget = get_total_operating_budget(year)

    for budget in budgets:
        cat_type = budget['category_type']
        annual = budget['annual_amount'] or 0
        category_id = budget['category_id']
        category_name = budget['category_name']

        # For 2025+, Interest budget is calculated as 0.1% of operating budget
        if year >= CALCULATED_DUES_START_YEAR and category_name == 'Interest':
            annual = total_operating_budget * 0.001

        ytd_actual = actuals.get(category_id, 0)
        remaining = annual - ytd_actual

        # Skip categories with zero budget AND zero actual
        if annual == 0 and ytd_actual == 0:
            continue

        cat_data = {
            'id': category_id,
            'category': category_name,
            'type': cat_type,
            'annual_budget': round(annual, 2),
            'ytd_actual': round(ytd_actual, 2),
            'remaining': round(remaining, 2)
        }

        if cat_type == 'Income':
            income_categories.append(cat_data)
            income_ytd_actual += ytd_actual
            # For 2025+, we calculate dues from operating budget, not from category budgets
            if year < CALCULATED_DUES_START_YEAR:
                income_annual_budget += annual
        elif cat_type == 'Expense':
            expense_categories.append(cat_data)
            expense_annual_budget += annual
            expense_ytd_actual += ytd_actual

    # For 2025+, income budget equals operating budget (99.9% dues + 0.1% interest = 100%)
    calculated_income = False
    if year >= CALCULATED_DUES_START_YEAR:
        calculated_income = True
        income_annual_budget = total_operating_budget

    return {
        'year': year,
        'as_of_date': as_of_date.isoformat(),
        'income_summary': {
            'annual_budget': round(income_annual_budget, 2),
            'ytd_actual': round(income_ytd_actual, 2),
            'calculated': calculated_income,
            'total_operating_budget': round(total_operating_budget, 2) if total_operating_budget else None,
            'categories': income_categories
        },
        'expense_summary': {
            'annual_budget': round(expense_annual_budget, 2),
            'ytd_actual': round(expense_ytd_actual, 2),
            'remaining': round(expense_annual_budget - expense_ytd_actual, 2),
            'categories': expense_categories
        }
    }


def get_account_balances_at_year_start(year: int) -> List[dict]:
    """Get account balances at the end of prior year (Dec 31, year-1).

    This represents the beginning balance for the requested year.
    If no transactions exist before the year, returns 0 for that account.

    Args:
        year: The year to get beginning balances for

    Returns:
        List of account dicts with name and balance
    """
    prior_year_end = f"{year - 1}-12-31"

    sql = """
        SELECT t.account_name as name, t.balance
        FROM transactions t
        INNER JOIN (
            SELECT account_name, MAX(post_date) as max_date
            FROM transactions
            WHERE post_date <= ?
            GROUP BY account_name
        ) latest ON t.account_name = latest.account_name
                 AND t.post_date = latest.max_date
        WHERE t.id = (
            SELECT MAX(id) FROM transactions t2
            WHERE t2.account_name = t.account_name
            AND t2.post_date = latest.max_date
        )
        ORDER BY t.account_name
    """
    rows = database.fetch_all(sql, (prior_year_end,))

    # Return dict for easy lookup, include all expected accounts with 0 default
    account_names = ['Checking', 'Reserve Fund', 'Savings']
    balances = {row['name']: row['balance'] or 0 for row in rows}

    return [{'name': name, 'balance': balances.get(name, 0)} for name in account_names]


def get_account_balances(as_of_date: Optional[date] = None) -> List[dict]:
    """Get balance for each account as of a specific date.

    NOTE: Account balances include ALL transactions (including transfers).
    We use the balance column from the CSV which the bank calculates,
    not a calculated sum of debits/credits. This ensures transfers
    between accounts are properly reflected in each account's balance.

    Args:
        as_of_date: Get balance as of this date. Defaults to most recent.

    Returns:
        List of account dicts with name and balance
    """
    if as_of_date is None:
        # Get most recent balance for each account (no date filter)
        sql = """
            SELECT t.account_name as name, t.balance
            FROM transactions t
            INNER JOIN (
                SELECT account_name, MAX(post_date) as max_date
                FROM transactions
                GROUP BY account_name
            ) latest ON t.account_name = latest.account_name
                     AND t.post_date = latest.max_date
            WHERE t.id = (
                SELECT MAX(id) FROM transactions t2
                WHERE t2.account_name = t.account_name
                AND t2.post_date = latest.max_date
            )
            ORDER BY t.account_name
        """
        rows = database.fetch_all(sql)
    else:
        # Get balance as of specific date (most recent transaction on or before date)
        sql = """
            SELECT t.account_name as name, t.balance
            FROM transactions t
            INNER JOIN (
                SELECT account_name, MAX(post_date) as max_date
                FROM transactions
                WHERE post_date <= ?
                GROUP BY account_name
            ) latest ON t.account_name = latest.account_name
                     AND t.post_date = latest.max_date
            WHERE t.id = (
                SELECT MAX(id) FROM transactions t2
                WHERE t2.account_name = t.account_name
                AND t2.post_date = latest.max_date
            )
            ORDER BY t.account_name
        """
        rows = database.fetch_all(sql, (as_of_date.isoformat(),))

    balances = []
    for row in rows:
        balances.append({
            'name': row['name'],
            'balance': row['balance'] or 0
        })

    return balances


def get_total_cash() -> float:
    """Get total cash across all accounts.

    Returns:
        Sum of all account balances
    """
    balances = get_account_balances()
    return sum(b['balance'] for b in balances)


def get_reserve_fund_status(year: int, as_of_date: Optional[date] = None) -> dict:
    """Get reserve fund status showing contributions, expenses, and net.

    Reserve Contribution is a Transfer category - money moved from Checking
    to Reserve Fund. Reserve Expenses are paid from the Reserve Fund account.
    This section shows the net activity vs the contribution budget.

    Args:
        year: Budget year
        as_of_date: Date to calculate through

    Returns:
        Dict with budget, contributions_in, expenses_out, and net
    """
    if as_of_date is None:
        as_of_date = date.today()

    # Get budget for Reserve Contribution category
    budget_sql = """
        SELECT b.annual_amount
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE c.name = 'Reserve Contribution'
        AND b.year = ?
    """
    budget_row = database.fetch_one(budget_sql, (year,))

    annual_budget = budget_row['annual_amount'] if budget_row else 0

    # Get contributions IN to Reserve Fund
    contributions_sql = """
        SELECT COALESCE(SUM(t.credit), 0) as amount
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name = 'Reserve Contribution'
        AND strftime('%Y', t.post_date) = ?
        AND t.post_date <= ?
    """
    contrib_row = database.fetch_one(contributions_sql, (str(year), as_of_date.isoformat()))
    contributions = contrib_row['amount'] if contrib_row else 0

    # Get expenses OUT of Reserve Fund (debits from Reserve Fund account)
    expenses_sql = """
        SELECT COALESCE(SUM(t.debit), 0) as amount
        FROM transactions t
        WHERE t.account_name = 'Reserve Fund'
        AND strftime('%Y', t.post_date) = ?
        AND t.post_date <= ?
    """
    expense_row = database.fetch_one(expenses_sql, (str(year), as_of_date.isoformat()))
    expenses = expense_row['amount'] if expense_row else 0

    net = contributions - expenses

    return {
        'budget': round(annual_budget, 2),
        'contributions': round(contributions, 2),
        'expenses': round(expenses, 2),
        'net': round(net, 2)
    }


def get_monthly_cashflow(year: int, as_of_date: Optional[date] = None) -> List[dict]:
    """Get monthly income and expenses for cash flow chart.

    Args:
        year: Year to get data for
        as_of_date: Only include transactions on or before this date

    Returns:
        List of monthly data with income and expenses
    """
    if as_of_date is None:
        as_of_date = date.today()

    # Get monthly totals for income and expenses
    sql = """
        SELECT
            CAST(strftime('%m', t.post_date) AS INTEGER) as month,
            SUM(CASE WHEN c.type = 'Income' THEN t.credit ELSE 0 END) as income,
            SUM(CASE WHEN c.type = 'Expense' THEN t.debit ELSE 0 END) as expenses
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE strftime('%Y', t.post_date) = ?
        AND t.post_date <= ?
        GROUP BY strftime('%m', t.post_date)
        ORDER BY month
    """
    rows = database.fetch_all(sql, (str(year), as_of_date.isoformat()))

    # Create a list for all 12 months, filling in zeros for missing months
    monthly_data = []
    month_map = {row['month']: row for row in rows}

    # Only include months up to as_of_date
    max_month = as_of_date.month if as_of_date.year == year else 12

    for month in range(1, max_month + 1):
        row = month_map.get(month)
        if row:
            income = row['income'] or 0
            expenses = row['expenses'] or 0
        else:
            income = 0
            expenses = 0
        monthly_data.append({
            'month': month,
            'income': round(income, 2),
            'expenses': round(expenses, 2)
        })

    return monthly_data
