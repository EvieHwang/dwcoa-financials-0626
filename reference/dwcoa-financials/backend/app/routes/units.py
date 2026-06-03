"""Unit management routes."""

import json
from datetime import date

from app.services import database


def handle_get_units(query: dict) -> dict:
    """Get all units with year-specific past due balances.

    Args:
        query: Query parameters (year required)

    Returns:
        Response with units list including past_due_balance for the year
    """
    year = query.get('year')
    if not year:
        year = date.today().year
    else:
        try:
            year = int(year)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': 'year must be an integer'})
            }

    # Get base units
    units = database.get_units()

    # Get year-specific past dues
    past_dues = {pd['unit_number']: pd['past_due_balance'] for pd in database.get_unit_past_dues(year)}

    # Merge past dues into units
    result = []
    for unit in units:
        result.append({
            'number': unit['number'],
            'ownership_pct': unit['ownership_pct'],
            'past_due_balance': past_dues.get(unit['number'], 0)
        })

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'units': result, 'year': year})
    }
