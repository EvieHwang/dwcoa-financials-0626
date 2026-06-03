"""Rules API routes for managing categorization rules."""

import json

from app.services import database


def handle_list() -> dict:
    """List all categorization rules.

    Returns:
        Response with rules list
    """
    rules = database.get_rules()

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'rules': rules})
    }


def handle_create(body: dict) -> dict:
    """Create a new categorization rule.

    Args:
        body: Request body with pattern and category_id

    Returns:
        Response with created rule
    """
    pattern = body.get('pattern', '').strip()
    category_id = body.get('category_id')

    # Validation
    if not pattern:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'Pattern is required'})
        }

    if len(pattern) < 1:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'Pattern must be at least 1 character'})
        }

    if not category_id:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'Category ID is required'})
        }

    # Check for duplicate pattern
    if database.rule_pattern_exists(pattern):
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'duplicate', 'message': 'A rule with this pattern already exists'})
        }

    # Verify category exists
    category = database.get_category_by_id(category_id)
    if not category:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'Invalid category ID'})
        }

    # Create rule
    rule = database.create_rule(pattern, category_id)

    return {
        'statusCode': 201,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'rule': rule})
    }


def handle_update(rule_id: int, body: dict) -> dict:
    """Update a categorization rule.

    Args:
        rule_id: Rule ID
        body: Request body with optional pattern, category_id, active

    Returns:
        Response with updated rule
    """
    # Check if rule exists
    existing = database.get_rule_by_id(rule_id)
    if not existing:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'not_found', 'message': 'Rule not found'})
        }

    # Validate pattern if provided
    pattern = body.get('pattern')
    if pattern is not None:
        pattern = pattern.strip()
        if len(pattern) < 1:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': 'Pattern must be at least 1 character'})
            }

        # Check for duplicate pattern (excluding current rule)
        if database.rule_pattern_exists(pattern, exclude_id=rule_id):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'duplicate', 'message': 'A rule with this pattern already exists'})
            }

    # Validate category if provided
    category_id = body.get('category_id')
    if category_id is not None:
        category = database.get_category_by_id(category_id)
        if not category:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': 'Invalid category ID'})
            }

    # Update rule
    active = body.get('active')
    rule = database.update_rule(rule_id, pattern=pattern, category_id=category_id, active=active)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'rule': rule})
    }


def handle_delete(rule_id: int) -> dict:
    """Delete a categorization rule.

    Note: Deleting a rule does NOT affect existing transactions.
    Rules only control auto-categorization of new transactions.
    Existing transactions retain their assigned categories.

    Args:
        rule_id: Rule ID

    Returns:
        Response with deletion result
    """
    deleted = database.delete_rule(rule_id)

    if not deleted:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'not_found', 'message': 'Rule not found'})
        }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'message': 'Rule deleted'})
    }
