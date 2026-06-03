"""Transaction routes."""

import base64
import json
from datetime import datetime
from typing import Any

from app.services import database, csv_processor, categorizer


def is_duplicate(conn, post_date: str, account_number: str, description: str,
                 debit: float, credit: float, balance: float) -> bool:
    """Check if a transaction already exists.

    Args:
        conn: Database connection
        post_date: Transaction post date
        account_number: Account number
        description: Transaction description
        debit: Debit amount (may be None)
        credit: Credit amount (may be None)
        balance: Running balance

    Returns:
        True if duplicate exists
    """
    row = conn.execute("""
        SELECT id FROM transactions
        WHERE post_date = ?
        AND account_number = ?
        AND description = ?
        AND (debit = ? OR (debit IS NULL AND ? IS NULL))
        AND (credit = ? OR (credit IS NULL AND ? IS NULL))
        AND balance = ?
    """, (post_date, account_number, description, debit, debit, credit, credit, balance)).fetchone()
    return row is not None


def handle_list_transactions(query: dict) -> dict:
    """List transactions with optional filters.

    Args:
        query: Query parameters (year, account, category_id, needs_review, limit, offset, include_all)

    Returns:
        Response with transaction list
    """
    # Build query - exclude Transfer categories by default, unless include_all is set
    include_all = query.get('include_all') == 'true'

    if include_all:
        # Include all transactions (for Reserve Fund Activity)
        sql = """
            SELECT t.*,
                   c.name as category,
                   c.type as category_type,
                   ac.name as auto_category
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN categories ac ON t.auto_category_id = ac.id
            WHERE 1=1
        """
    else:
        # Exclude Transfer and Internal categories from normal display
        sql = """
            SELECT t.*,
                   c.name as category,
                   c.type as category_type,
                   ac.name as auto_category
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN categories ac ON t.auto_category_id = ac.id
            WHERE (c.type IS NULL OR c.type NOT IN ('Transfer', 'Internal'))
        """
    params: list = []

    # Apply filters
    if query.get('year'):
        sql += " AND strftime('%Y', t.post_date) = ?"
        params.append(str(query['year']))

    if query.get('account'):
        sql += " AND t.account_name = ?"
        params.append(query['account'])

    if query.get('category_id'):
        sql += " AND t.category_id = ?"
        params.append(int(query['category_id']))

    if query.get('needs_review') == 'true':
        sql += " AND t.needs_review = 1"

    # Count total (using same filters)
    if include_all:
        count_sql = """
            SELECT COUNT(*) as count
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
    else:
        count_sql = """
            SELECT COUNT(*) as count
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE (c.type IS NULL OR c.type NOT IN ('Transfer', 'Internal'))
        """
    if query.get('year'):
        count_sql += " AND strftime('%Y', t.post_date) = ?"
    if query.get('account'):
        count_sql += " AND t.account_name = ?"
    if query.get('category_id'):
        count_sql += " AND t.category_id = ?"
    if query.get('needs_review') == 'true':
        count_sql += " AND t.needs_review = 1"

    count_row = database.fetch_one(count_sql, tuple(params))
    total = count_row['count'] if count_row else 0

    # Add ordering and pagination
    sql += " ORDER BY t.post_date DESC, t.id DESC"

    limit = int(query.get('limit', 100))
    offset = int(query.get('offset', 0))
    sql += f" LIMIT {limit} OFFSET {offset}"

    rows = database.fetch_all(sql, tuple(params))
    transactions = database.rows_to_dicts(rows)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'transactions': transactions,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    }


def handle_upload(event_body: dict, raw_body: str = '') -> dict:
    """Handle CSV file upload.

    Args:
        event_body: Parsed request body
        raw_body: Raw body for multipart handling

    Returns:
        Response with upload stats
    """
    try:
        # Get CSV content
        # In Lambda, file may come as base64 or direct content
        csv_content = None

        if 'file' in event_body:
            # Direct file content
            csv_content = event_body['file']
        elif 'body' in event_body:
            # Base64 encoded
            try:
                csv_content = base64.b64decode(event_body['body']).decode('utf-8')
            except Exception:
                csv_content = event_body['body']
        elif raw_body:
            # Try to extract from multipart or use directly
            if 'Content-Disposition' in raw_body:
                # Multipart - extract content after headers
                parts = raw_body.split('\r\n\r\n', 1)
                if len(parts) > 1:
                    csv_content = parts[1].rsplit('\r\n--', 1)[0]
            else:
                csv_content = raw_body
        elif isinstance(event_body, str):
            csv_content = event_body

        if not csv_content:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': 'No file content provided'})
            }

        # Parse CSV
        result = csv_processor.parse_csv(csv_content)

        if result.errors:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'bad_request',
                    'message': 'CSV parsing errors',
                    'errors': result.errors
                })
            }

        # Check if replace_all mode is requested
        replace_all = event_body.get('replace_all', False)

        # Process transactions
        with database.transaction() as conn:
            # Only clear existing transactions if replace_all is True
            if replace_all:
                conn.execute("DELETE FROM transactions")

            # Get category mapping for pre-categorized items
            categories = {c['name']: c['id'] for c in database.get_categories()}

            # Stats
            stats = {
                'added': 0,
                'skipped': 0,
                'categorized': 0,
                'needs_review': 0
            }

            # Process each transaction
            for txn in result.transactions:
                # Check for duplicate (skip if already exists)
                if not replace_all and is_duplicate(
                    conn,
                    txn.post_date,
                    txn.account_number,
                    txn.description,
                    txn.debit,
                    txn.credit,
                    txn.balance
                ):
                    stats['skipped'] += 1
                    continue

                # Categorize new transaction
                category_id = None
                auto_category_id = None
                confidence = None
                needs_review = False

                # Check for pre-existing category in CSV
                if txn.category and txn.category in categories:
                    category_id = categories[txn.category]
                    confidence = 100
                    stats['categorized'] += 1
                else:
                    # Auto-categorize
                    cat_result = categorizer.categorize_transaction(
                        txn.description,
                        txn.account_name
                    )
                    auto_category_id = cat_result.category_id
                    confidence = cat_result.confidence
                    needs_review = cat_result.needs_review

                    if cat_result.category_id and not cat_result.needs_review:
                        category_id = cat_result.category_id
                        stats['categorized'] += 1
                    elif cat_result.needs_review:
                        stats['needs_review'] += 1

                # Insert transaction
                conn.execute("""
                    INSERT INTO transactions (
                        account_number, account_name, post_date, check_number,
                        description, debit, credit, status, balance,
                        category_id, auto_category_id, confidence, needs_review
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    txn.account_number,
                    txn.account_name,
                    txn.post_date,
                    txn.check_number,
                    txn.description,
                    txn.debit,
                    txn.credit,
                    txn.status,
                    txn.balance,
                    category_id,
                    auto_category_id,
                    confidence,
                    1 if needs_review else 0
                ))
                stats['added'] += 1

            # Update last upload timestamp
            database.set_config('last_upload_at', datetime.now().isoformat())

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Upload successful',
                'stats': stats,
                'warnings': result.warnings[:10]  # Limit warnings in response
            })
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'internal_error', 'message': str(e)})
        }


def handle_download(query: dict) -> dict:
    """Download transactions as CSV.

    Args:
        query: Query parameters (year optional)

    Returns:
        Response with CSV content
    """
    sql = """
        SELECT t.*,
               c.name as category,
               ac.name as auto_category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories ac ON t.auto_category_id = ac.id
        WHERE 1=1
    """
    params: list = []

    if query.get('year'):
        sql += " AND strftime('%Y', t.post_date) = ?"
        params.append(str(query['year']))

    sql += " ORDER BY t.post_date DESC, t.id DESC"

    rows = database.fetch_all(sql, tuple(params))
    transactions = database.rows_to_dicts(rows)

    csv_content = csv_processor.generate_csv(transactions, include_app_columns=True)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename="dwcoa_transactions.csv"'
        },
        'body': csv_content
    }


def handle_update(transaction_id: int, body: dict) -> dict:
    """Update a transaction's category.

    Args:
        transaction_id: Transaction ID
        body: Request body with category_id and/or needs_review

    Returns:
        Response with updated transaction
    """
    # Verify transaction exists
    txn = database.fetch_one("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    if not txn:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'not_found', 'message': 'Transaction not found'})
        }

    # Build update
    updates = []
    params: list = []

    if 'category_id' in body:
        updates.append("category_id = ?")
        params.append(body['category_id'])

    if 'description' in body:
        description = body['description'].strip() if body['description'] else ''
        if description:
            updates.append("description = ?")
            params.append(description)

    if 'needs_review' in body:
        updates.append("needs_review = ?")
        params.append(1 if body['needs_review'] else 0)
    elif 'category_id' in body and body['category_id']:
        # Clear needs_review when category is set
        updates.append("needs_review = 0")

    updates.append("updated_at = datetime('now')")

    if updates:
        params.append(transaction_id)
        with database.transaction():
            database.execute(
                f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

    # Fetch updated transaction
    updated = database.fetch_one("""
        SELECT t.*,
               c.name as category,
               ac.name as auto_category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories ac ON t.auto_category_id = ac.id
        WHERE t.id = ?
    """, (transaction_id,))

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(database.row_to_dict(updated))
    }


def handle_review_queue() -> dict:
    """Get transactions needing review.

    Returns:
        Response with transactions needing review
    """
    rows = database.fetch_all("""
        SELECT t.*,
               c.name as category,
               ac.name as auto_category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories ac ON t.auto_category_id = ac.id
        WHERE t.needs_review = 1
        ORDER BY t.description ASC, t.post_date DESC
        LIMIT 100
    """)

    transactions = database.rows_to_dicts(rows)
    count = database.fetch_one("SELECT COUNT(*) as count FROM transactions WHERE needs_review = 1")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'transactions': transactions,
            'count': count['count'] if count else 0
        })
    }
