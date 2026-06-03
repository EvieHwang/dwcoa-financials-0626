"""Category management routes."""

import json
from typing import Any

from app.services import database


def handle_list(query: dict) -> dict:
    """List all categories.

    Args:
        query: Query parameters (active, type)

    Returns:
        Response with category list
    """
    active_only = query.get('active', 'true').lower() == 'true'
    category_type = query.get('type')

    categories = database.get_categories(
        active_only=active_only,
        category_type=category_type
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'categories': categories})
    }


def handle_create(body: dict) -> dict:
    """Create a new category.

    Args:
        body: Category data

    Returns:
        Response with created category
    """
    required = ['name', 'type']
    for field in required:
        if not body.get(field):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': f'{field} is required'})
            }

    # Check if name already exists
    existing = database.get_category_by_name(body['name'])
    if existing:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'bad_request', 'message': 'Category name already exists'})
        }

    # Insert category
    with database.transaction():
        database.execute("""
            INSERT INTO categories (name, type, default_account, active)
            VALUES (?, ?, ?, ?)
        """, (
            body['name'],
            body['type'],
            body.get('default_account'),
            1 if body.get('active', True) else 0
        ))

    # Fetch created category
    category = database.get_category_by_name(body['name'])

    return {
        'statusCode': 201,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(category)
    }


def handle_update(category_id: int, body: dict) -> dict:
    """Update a category.

    Args:
        category_id: Category ID
        body: Updated category data

    Returns:
        Response with updated category
    """
    # Verify category exists
    category = database.get_category_by_id(category_id)
    if not category:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'not_found', 'message': 'Category not found'})
        }

    # Build update
    updates = []
    params: list = []

    if 'name' in body:
        # Check for duplicate name
        existing = database.get_category_by_name(body['name'])
        if existing and existing['id'] != category_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'bad_request', 'message': 'Category name already exists'})
            }
        updates.append("name = ?")
        params.append(body['name'])

    if 'type' in body:
        updates.append("type = ?")
        params.append(body['type'])

    if 'default_account' in body:
        updates.append("default_account = ?")
        params.append(body['default_account'])

    if 'active' in body:
        updates.append("active = ?")
        params.append(1 if body['active'] else 0)

    if updates:
        params.append(category_id)
        with database.transaction():
            database.execute(
                f"UPDATE categories SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

    # Fetch updated category
    updated = database.get_category_by_id(category_id)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(updated)
    }
