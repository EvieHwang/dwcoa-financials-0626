"""Authentication routes."""

import json
from typing import Any

from app.utils.auth import authenticate, require_auth


def handle_login(body: dict) -> dict:
    """Handle login request.

    Args:
        body: Request body with 'password' field

    Returns:
        Response dict with token or error
    """
    password = body.get('password', '')

    if not password:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'bad_request', 'message': 'Password required'})
        }

    result = authenticate(password)

    if result is None:
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'unauthorized', 'message': 'Invalid password'})
        }

    token, role, expires_at = result

    return {
        'statusCode': 200,
        'body': json.dumps({
            'token': token,
            'role': role,
            'expires_at': expires_at.isoformat()
        })
    }


def handle_verify(headers: dict) -> dict:
    """Handle token verification request.

    Args:
        headers: Request headers

    Returns:
        Response dict with validity status
    """
    payload = require_auth(headers)

    if payload is None:
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'unauthorized', 'message': 'Invalid or expired token'})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({
            'valid': True,
            'role': payload.get('role'),
            'expires_at': payload.get('exp')
        })
    }
