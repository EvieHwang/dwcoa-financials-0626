"""Dues tracking routes."""

import json
from datetime import date
from decimal import Decimal
from typing import Optional

from app.services import database, budget_calc
from app.services.budget_calc import CALCULATED_DUES_START_YEAR

# First year with transaction data
BASE_YEAR = 2025


def calculate_unit_carryover(unit: dict, target_year: int) -> Decimal:
    """Calculate cumulative unpaid balance carried forward to target_year.

    For years > BASE_YEAR, this iterates through all prior years and calculates:
    carryover = (historical_debt + annual_dues - payments) accumulated over time.

    Carryover can be negative (credit balance) if a unit overpays.

    Args:
        unit: Unit dict with 'number' and 'ownership_pct'
        target_year: The year to calculate carryover for

    Returns:
        Cumulative balance (positive = owes money, negative = credit)
    """
    if target_year <= BASE_YEAR:
        # For base year, use seeded historical debt only
        return Decimal(str(database.get_unit_past_due(unit['number'], target_year) or 0))

    carryover = Decimal('0')

    for year in range(BASE_YEAR, target_year):
        # Get historical debt for this year (typically only applies to 2025)
        historical_debt = Decimal(str(database.get_unit_past_due(unit['number'], year) or 0))

        # Get annual budget for this year
        total_budget = budget_calc.get_total_operating_budget(year)
        annual_dues = Decimal(str(total_budget)) * Decimal(str(unit['ownership_pct']))

        # Get payments made during this year
        paid = Decimal(str(database.get_unit_payments_total(unit['number'], year) or 0))

        # Add to running carryover (can be negative for credits)
        year_owed = carryover + historical_debt + annual_dues
        carryover = year_owed - paid

    return carryover


def get_dues_status(year: Optional[int] = None, as_of_date: Optional[date] = None) -> dict:
    """Calculate dues status for all units as of a specific date.

    For 2025+: Dues are calculated from Total Operating Budget × Ownership %
    For < 2025: Uses legacy per-unit Dues category budgets

    Budget amounts are always the full annual amount (not prorated by month).

    Args:
        year: Budget year (defaults to current year)
        as_of_date: Only include payments on or before this date

    Returns:
        Dict with year, total_budget (annual), and units list
    """
    if not year:
        current_year = database.get_config('current_year')
        year = int(current_year) if current_year else date.today().year

    if as_of_date is None:
        as_of_date = date.today()

    # Get units
    units = database.get_units()

    # Get dues payments by unit through as_of_date
    dues_sql = """
        SELECT c.name as category, SUM(t.credit) as paid
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name LIKE 'Dues %'
        AND strftime('%Y', t.post_date) = ?
        AND t.post_date <= ?
        GROUP BY c.name
    """
    dues_rows = database.fetch_all(dues_sql, (str(year), as_of_date.isoformat()))
    dues_by_unit = {}
    for row in dues_rows:
        unit_num = row['category'].replace('Dues ', '')
        dues_by_unit[unit_num] = row['paid'] or 0

    # Calculate status for each unit
    total_annual_budget = 0
    total_operating_budget = None
    unit_status = []

    if year >= CALCULATED_DUES_START_YEAR:
        # NEW: Calculate dues from total operating budget
        total_operating_budget = budget_calc.get_total_operating_budget(year)

        for unit in units:
            # Calculate carryover from all prior years (including credits)
            carryover = float(calculate_unit_carryover(unit, year))
            # Unit's share = Total Operating Budget × Ownership %
            annual_budget = total_operating_budget * unit['ownership_pct']
            expected_total = carryover + annual_budget
            total_annual_budget += expected_total
            paid = dues_by_unit.get(unit['number'], 0)
            outstanding = expected_total - paid

            unit_status.append({
                'unit': unit['number'],
                'ownership_pct': unit['ownership_pct'],
                'past_due_balance': round(carryover, 2),
                'annual_budget': round(annual_budget, 2),
                'expected_total': round(expected_total, 2),
                'paid_ytd': round(paid, 2),
                'outstanding': round(outstanding, 2)
            })
    else:
        # LEGACY: Use per-unit Dues category budgets (annual amounts)
        dues_budget_sql = """
            SELECT c.name as category, b.annual_amount
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            WHERE b.year = ? AND c.name LIKE 'Dues %'
        """
        budget_rows = database.fetch_all(dues_budget_sql, (year,))
        dues_budgets = {}
        for row in budget_rows:
            unit_num = row['category'].replace('Dues ', '')
            dues_budgets[unit_num] = row['annual_amount'] or 0

        for unit in units:
            # For legacy years, carryover is just the seeded historical debt
            carryover = float(calculate_unit_carryover(unit, year))
            annual_budget = dues_budgets.get(unit['number'], 0)
            expected_total = carryover + annual_budget
            total_annual_budget += expected_total
            paid = dues_by_unit.get(unit['number'], 0)
            outstanding = expected_total - paid

            unit_status.append({
                'unit': unit['number'],
                'ownership_pct': unit['ownership_pct'],
                'past_due_balance': round(carryover, 2),
                'annual_budget': round(annual_budget, 2),
                'expected_total': round(expected_total, 2),
                'paid_ytd': round(paid, 2),
                'outstanding': round(outstanding, 2)
            })

    return {
        'year': year,
        'total_annual_budget': round(total_annual_budget, 2),
        'total_operating_budget': round(total_operating_budget, 2) if total_operating_budget else None,
        'calculated': year >= CALCULATED_DUES_START_YEAR,
        'units': unit_status
    }


def handle_get_dues(year: Optional[int] = None) -> dict:
    """Handle GET /api/dues request.

    Args:
        year: Budget year

    Returns:
        Response with dues status
    """
    data = get_dues_status(year)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data)
    }
