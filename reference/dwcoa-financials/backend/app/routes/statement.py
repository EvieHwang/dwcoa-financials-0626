"""Unit statement routes."""

import json
from datetime import date
from typing import Optional

from app.services import database


# Valid unit numbers
VALID_UNITS = {'101', '102', '103', '201', '202', '203', '301', '302', '303'}


def handle_get_statement(unit_number: str, year: Optional[int] = None) -> dict:
    """Get financial statement for a unit.

    Calculates:
    - Prior year: budgeted dues, paid, carryover balance
    - Current year: carryover + annual dues - paid = remaining
    - Payment guidance: suggested monthly based on remaining balance

    Args:
        unit_number: Unit number (101-303)
        year: Statement year (defaults to current year)

    Returns:
        Response with complete statement data
    """
    # Validate unit number
    if unit_number not in VALID_UNITS:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'bad_request',
                'message': f'Invalid unit number: {unit_number}'
            })
        }

    # Get current year if not specified
    if not year:
        current_year_config = database.get_config('current_year')
        year = int(current_year_config) if current_year_config else date.today().year

    prior_year = year - 1
    today = date.today()
    current_month = today.month

    # Get unit info
    unit = database.get_unit(unit_number)
    if not unit:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'not_found',
                'message': f'Unit {unit_number} not found'
            })
        }

    ownership_pct = unit['ownership_pct']

    # ==========================================================================
    # Prior Year Summary
    # ==========================================================================
    prior_year_data = None
    prior_budget = database.get_total_operating_budget_annual(prior_year)

    if prior_budget > 0:
        # Calculate prior year values
        prior_budgeted = prior_budget * ownership_pct
        prior_historical_debt = database.get_unit_past_due(unit_number, prior_year)
        prior_paid = database.get_unit_payments_total(unit_number, prior_year)

        # Carryover = what was owed - what was paid
        # Positive = underpaid (owes money), Negative = overpaid (credit)
        balance_carried_forward = prior_budgeted + prior_historical_debt - prior_paid

        prior_year_data = {
            'year': prior_year,
            'annual_dues_budgeted': round(prior_budgeted, 2),
            'total_paid': round(prior_paid, 2),
            'balance_carried_forward': round(balance_carried_forward, 2)
        }
    else:
        # No prior year budget exists
        balance_carried_forward = 0.0

    # ==========================================================================
    # Current Year Summary
    # ==========================================================================
    current_budget = database.get_total_operating_budget_annual(year)
    budget_locked = database.is_budget_locked(year)

    # Calculate current year values
    annual_dues = current_budget * ownership_pct if current_budget > 0 else 0.0

    # Carryover is the balance from prior year (or 0 if no prior year data)
    carryover_balance = balance_carried_forward if prior_year_data else 0.0

    # For 2025, also add any historical debt that was seeded
    # (This handles the case where we're looking at year 2025 statement)
    if year == 2025 or (not prior_year_data and year > 2025):
        # Get any seeded historical debt for this year
        historical_debt_this_year = database.get_unit_past_due(unit_number, year)
        if historical_debt_this_year > 0:
            carryover_balance = historical_debt_this_year

    total_due = carryover_balance + annual_dues
    paid_ytd = database.get_unit_payments_total(unit_number, year)
    remaining_balance = total_due - paid_ytd

    # ==========================================================================
    # Payment Guidance
    # ==========================================================================
    # Original monthly dues = annual budget / 12 (what they'd pay if perfectly on schedule)
    original_monthly = annual_dues / 12 if annual_dues > 0 else 0.0

    # Months remaining calculation:
    # 1. Check if ANY payment made in current month
    #    - If yes: exclude current month from projection (month already "used")
    #    - If no: use 15th day cutoff for user convenience
    #      - Before 15th: include current month (still time to pay)
    #      - After 15th: exclude current month (too late for current month)
    # 2. Ensure minimum 1 month to avoid division by zero

    has_paid_this_month = database.has_unit_payment_in_current_month(
        unit_number, year, current_month
    )

    if has_paid_this_month:
        # Payment made this month - exclude current month from remaining months
        months_remaining = 12 - current_month
    else:
        # No payment this month - use 15th day cutoff
        if today.day < 15:
            months_remaining = 12 - current_month + 1  # Include current month
        else:
            months_remaining = 12 - current_month  # Exclude current month

    # Ensure at least 1 month (for December)
    months_remaining = max(1, months_remaining)

    if remaining_balance <= 0:
        suggested_monthly = 0.0
    else:
        suggested_monthly = remaining_balance / months_remaining

    current_year_data = {
        'year': year,
        'budget_locked': budget_locked,
        'carryover_balance': round(carryover_balance, 2),
        'annual_dues': round(annual_dues, 2),
        'total_due': round(total_due, 2),
        'paid_ytd': round(paid_ytd, 2),
        'remaining_balance': round(remaining_balance, 2),
        'original_monthly': round(original_monthly, 2),
        'months_remaining': months_remaining,
        'suggested_monthly': round(suggested_monthly, 2)
    }

    # ==========================================================================
    # Recent Payments
    # ==========================================================================
    recent_payments = database.get_unit_recent_payments(unit_number, year, limit=10)

    # Build response
    response_data = {
        'unit': unit_number,
        'ownership_pct': ownership_pct,
        'current_year': current_year_data,
        'prior_year': prior_year_data,
        'recent_payments': recent_payments
    }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response_data)
    }


def handle_get_payment_history(unit_number: str, year: Optional[int] = None) -> dict:
    """Get full payment history for a unit.

    Args:
        unit_number: Unit number (101-303)
        year: Filter by year (optional, returns all if not specified)

    Returns:
        Response with payment history
    """
    # Validate unit number
    if unit_number not in VALID_UNITS:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'bad_request',
                'message': f'Invalid unit number: {unit_number}'
            })
        }

    # Verify unit exists
    unit = database.get_unit(unit_number)
    if not unit:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'not_found',
                'message': f'Unit {unit_number} not found'
            })
        }

    # Get payments
    if year:
        # Get payments for specific year
        payments = database.get_unit_recent_payments(unit_number, year, limit=100)
        response_data = {
            'unit': unit_number,
            'year': year,
            'payments': payments
        }
    else:
        # Get payments for current and prior year
        current_year_config = database.get_config('current_year')
        current_year = int(current_year_config) if current_year_config else date.today().year
        prior_year = current_year - 1

        current_payments = database.get_unit_recent_payments(unit_number, current_year, limit=100)
        prior_payments = database.get_unit_recent_payments(unit_number, prior_year, limit=100)

        # Add year to each payment for clarity
        for p in current_payments:
            p['year'] = current_year
        for p in prior_payments:
            p['year'] = prior_year

        all_payments = current_payments + prior_payments
        # Sort by date descending
        all_payments.sort(key=lambda x: x['date'], reverse=True)

        response_data = {
            'unit': unit_number,
            'year': None,
            'payments': all_payments
        }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response_data)
    }
