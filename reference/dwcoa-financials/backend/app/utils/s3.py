"""S3 utilities for data storage."""

import os
import tempfile
from typing import Optional

import boto3
from botocore.exceptions import ClientError

# S3 client (reused across Lambda invocations)
_s3_client = None

def get_s3_client():
    """Get or create S3 client."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def get_bucket_name() -> str:
    """Get the data bucket name from environment."""
    return os.environ.get('DATA_BUCKET', 'dwcoa-data-local')


def download_file(key: str, local_path: str) -> bool:
    """Download a file from S3 to local path.

    Args:
        key: S3 object key
        local_path: Local file path to save to

    Returns:
        True if successful, False if file doesn't exist
    """
    try:
        get_s3_client().download_file(get_bucket_name(), key, local_path)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def upload_file(local_path: str, key: str) -> None:
    """Upload a file from local path to S3.

    Args:
        local_path: Local file path to upload
        key: S3 object key
    """
    get_s3_client().upload_file(local_path, get_bucket_name(), key)


def download_bytes(key: str) -> Optional[bytes]:
    """Download file content as bytes.

    Args:
        key: S3 object key

    Returns:
        File content as bytes, or None if not found
    """
    try:
        response = get_s3_client().get_object(Bucket=get_bucket_name(), Key=key)
        return response['Body'].read()
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        raise


def upload_bytes(content: bytes, key: str, content_type: str = 'application/octet-stream') -> None:
    """Upload bytes to S3.

    Args:
        content: File content as bytes
        key: S3 object key
        content_type: MIME type
    """
    get_s3_client().put_object(
        Bucket=get_bucket_name(),
        Key=key,
        Body=content,
        ContentType=content_type
    )


def file_exists(key: str) -> bool:
    """Check if a file exists in S3.

    Args:
        key: S3 object key

    Returns:
        True if file exists
    """
    try:
        get_s3_client().head_object(Bucket=get_bucket_name(), Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def get_temp_path(filename: str = 'temp') -> str:
    """Get a temporary file path in Lambda's /tmp directory.

    Args:
        filename: Base filename

    Returns:
        Full path to temp file
    """
    return os.path.join(tempfile.gettempdir(), filename)
