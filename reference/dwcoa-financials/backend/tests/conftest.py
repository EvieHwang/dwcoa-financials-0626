"""Pytest configuration and fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Mock AWS dependencies before any imports
sys.modules['boto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()

# Mock AWS Lambda Powertools Logger
mock_logger = MagicMock()
mock_powertools = MagicMock()
mock_powertools.Logger.return_value = mock_logger
sys.modules['aws_lambda_powertools'] = mock_powertools

# Create a mock S3 module
mock_s3 = MagicMock()
mock_s3.get_bucket_name.return_value = 'test-bucket'
mock_s3.file_exists.return_value = False
mock_s3.get_temp_path.return_value = '/tmp/test.db'
sys.modules['app.utils.s3'] = mock_s3
