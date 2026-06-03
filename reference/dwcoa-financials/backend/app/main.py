"""Main Lambda handler for DWCOA Financial Tracker API."""

import json
import traceback
from typing import Any

from app.routes import auth
from app.utils.auth import require_auth, require_admin


def make_response(status_code: int, body: Any, content_type: str = 'application/json') -> dict:
    """Create API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body (will be JSON-encoded if dict/list)
        content_type: Content-Type header

    Returns:
        API Gateway response dict
    """
    headers = {
        'Content-Type': content_type,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
    }

    if isinstance(body, (dict, list)):
        body = json.dumps(body)

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': body
    }


def error_response(status_code: int, error: str, message: str) -> dict:
    """Create error response.

    Args:
        status_code: HTTP status code
        error: Error code
        message: Error message

    Returns:
        API Gateway response dict
    """
    return make_response(status_code, {'error': error, 'message': message})


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for API Gateway events.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Parse request
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        path = event.get('rawPath', event.get('path', '/'))
        headers = event.get('headers', {})
        body_str = event.get('body', '{}')

        # Handle CORS preflight
        if http_method == 'OPTIONS':
            return make_response(200, '')

        # Parse body
        try:
            body = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            body = {}

        # Query parameters
        query_params = event.get('queryStringParameters', {}) or {}

        # Route request
        return route_request(http_method, path, headers, body, query_params)

    except Exception as e:
        traceback.print_exc()
        return error_response(500, 'internal_error', str(e))


def route_request(method: str, path: str, headers: dict, body: dict, query: dict) -> dict:
    """Route request to appropriate handler.

    Args:
        method: HTTP method
        path: Request path
        headers: Request headers
        body: Request body
        query: Query parameters

    Returns:
        API Gateway response
    """
    # Remove /prod prefix if present (API Gateway stage)
    if path.startswith('/prod'):
        path = path[5:]

    # Auth routes (no authentication required)
    if path == '/api/auth/login' and method == 'POST':
        return auth.handle_login(body)

    if path == '/api/auth/verify' and method == 'GET':
        return auth.handle_verify(headers)

    # All other routes require authentication
    auth_payload = require_auth(headers)
    if auth_payload is None:
        return error_response(401, 'unauthorized', 'Authentication required')

    role = auth_payload.get('role', 'board')
    is_admin = role == 'admin'

    # Import route handlers (lazy to avoid circular imports)
    from app.routes import dashboard, transactions, categories, budgets, dues, reports, rules, units, statement

    # Dashboard
    if path == '/api/dashboard' and method == 'GET':
        as_of_date = query.get('as_of_date') or None
        return dashboard.handle_get_dashboard(as_of_date)

    # Transactions
    if path == '/api/transactions' and method == 'GET':
        return transactions.handle_list_transactions(query)

    if path == '/api/transactions/upload' and method == 'POST':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        return transactions.handle_upload(event_body=body, raw_body=body.get('_raw_body', ''))

    if path == '/api/transactions/download' and method == 'GET':
        return transactions.handle_download(query)

    if path.startswith('/api/transactions/') and method == 'PATCH':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        transaction_id = int(path.split('/')[-1])
        return transactions.handle_update(transaction_id, body)

    # Categories
    if path == '/api/categories' and method == 'GET':
        return categories.handle_list(query)

    if path == '/api/categories' and method == 'POST':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        return categories.handle_create(body)

    if path.startswith('/api/categories/') and method == 'PATCH':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        category_id = int(path.split('/')[-1])
        return categories.handle_update(category_id, body)

    # Budgets
    if path == '/api/budgets' and method == 'GET':
        year = int(query.get('year', 0))
        if not year:
            return error_response(400, 'bad_request', 'Year parameter required')
        return budgets.handle_list(year)

    if path == '/api/budgets' and method == 'POST':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        return budgets.handle_upsert(body)

    if path == '/api/budgets/copy' and method == 'POST':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        return budgets.handle_copy(body)

    if path.startswith('/api/budgets/lock/') and method == 'POST':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        year = int(path.split('/')[-1])
        return budgets.handle_lock(year, body)

    # Dues
    if path == '/api/dues' and method == 'GET':
        year = int(query.get('year', 0)) or None
        return dues.handle_get_dues(year)

    # Statements (unit financial statements)
    if path.startswith('/api/statement/') and method == 'GET':
        parts = path.split('/')
        unit_number = parts[3]  # /api/statement/{unit}
        year = int(query.get('year', 0)) or None

        # Check if this is the payments sub-route
        if len(parts) > 4 and parts[4] == 'payments':
            return statement.handle_get_payment_history(unit_number, year)
        else:
            return statement.handle_get_statement(unit_number, year)

    # Reports
    if path == '/api/reports/pdf' and method == 'GET':
        as_of_date = query.get('as_of_date')
        return reports.handle_generate_pdf(as_of_date)

    # Review queue
    if path == '/api/review' and method == 'GET':
        return transactions.handle_review_queue()

    # Rules
    if path == '/api/rules' and method == 'GET':
        return rules.handle_list()

    if path == '/api/rules' and method == 'POST':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        return rules.handle_create(body)

    if path.startswith('/api/rules/') and method == 'PATCH':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        rule_id = int(path.split('/')[-1])
        return rules.handle_update(rule_id, body)

    if path.startswith('/api/rules/') and method == 'DELETE':
        if not is_admin:
            return error_response(403, 'forbidden', 'Admin access required')
        rule_id = int(path.split('/')[-1])
        return rules.handle_delete(rule_id)

    # Units
    if path == '/api/units' and method == 'GET':
        return units.handle_get_units(query)

    # Not found
    return error_response(404, 'not_found', f'Route not found: {method} {path}')
