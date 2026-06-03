"""Tests for CSV processing."""

import pytest
from unittest.mock import patch

# Mock database.get_accounts
mock_accounts = [
    {'masked_number': '****7145', 'name': 'Savings'},
    {'masked_number': '****9242', 'name': 'Checking'},
    {'masked_number': '****9226', 'name': 'Reserve Fund'},
]


class TestParseDate:
    """Tests for date parsing."""

    def test_parse_date(self):
        from app.services.csv_processor import parse_date

        # US format
        assert parse_date('1/2/2026') == '2026-01-02'
        assert parse_date('12/31/2025') == '2025-12-31'

        # ISO format
        assert parse_date('2026-01-02') == '2026-01-02'

        # Invalid
        assert parse_date('') is None
        assert parse_date('invalid') is None


class TestParseAmount:
    """Tests for amount parsing."""

    def test_parse_amount(self):
        from app.services.csv_processor import parse_amount

        assert parse_amount('100.00') == 100.0
        assert parse_amount('$1,234.56') == 1234.56
        assert parse_amount('$100') == 100.0
        assert parse_amount('') is None
        assert parse_amount('   ') is None


class TestGenerateCsv:
    """Tests for CSV generation."""

    def test_generate_csv(self):
        from app.services.csv_processor import generate_csv

        transactions = [
            {
                'account_number': '****7145',
                'account_name': 'Savings',
                'post_date': '2025-12-31',
                'check_number': '',
                'description': 'Test deposit',
                'debit': None,
                'credit': 100.00,
                'status': 'Posted',
                'balance': 1000.00,
                'category': 'Interest income',
                'auto_category': 'Interest income',
                'confidence': 95,
                'needs_review': False
            }
        ]

        csv_content = generate_csv(transactions)

        assert 'Account Number' in csv_content
        assert '****7145' in csv_content
        assert 'Test deposit' in csv_content
        assert 'Interest income' in csv_content


class TestParseCsv:
    """Tests for CSV parsing."""

    @patch('app.services.csv_processor.database')
    def test_parse_csv_valid(self, mock_db):
        """Parse valid CSV content."""
        mock_db.get_accounts.return_value = mock_accounts

        from app.services.csv_processor import parse_csv

        csv_content = """Account Number,Post Date,Check,Description,Debit,Credit,Status,Balance
****7145,1/2/2026,,External Deposit Test,,100.00,Posted,1000.00
****9242,1/2/2026,1234,Check payment,50.00,,Posted,500.00"""

        result = parse_csv(csv_content)

        assert len(result.errors) == 0
        assert len(result.transactions) == 2
        assert result.transactions[0].account_name == 'Savings'
        assert result.transactions[0].credit == 100.0
        assert result.transactions[1].account_name == 'Checking'
        assert result.transactions[1].debit == 50.0

    @patch('app.services.csv_processor.database')
    def test_parse_csv_missing_columns(self, mock_db):
        """Missing required columns should error."""
        mock_db.get_accounts.return_value = mock_accounts

        from app.services.csv_processor import parse_csv

        csv_content = """Account Number,Description,Amount
****7145,Test,100"""

        result = parse_csv(csv_content)

        assert len(result.errors) > 0
        assert 'Missing required columns' in result.errors[0]

    @patch('app.services.csv_processor.database')
    def test_parse_csv_unknown_account(self, mock_db):
        """Unknown account should warn but continue."""
        mock_db.get_accounts.return_value = mock_accounts

        from app.services.csv_processor import parse_csv

        csv_content = """Account Number,Post Date,Check,Description,Debit,Credit,Status,Balance
****9999,1/2/2026,,Test,,100.00,Posted,1000.00"""

        result = parse_csv(csv_content)

        assert len(result.warnings) > 0
        assert 'Unknown account' in result.warnings[0]
        assert len(result.transactions) == 1
        assert result.transactions[0].account_name == 'Unknown'

    @patch('app.services.csv_processor.database')
    def test_parse_csv_duplicate_detection(self, mock_db):
        """Duplicate transactions should be warned."""
        mock_db.get_accounts.return_value = mock_accounts

        from app.services.csv_processor import parse_csv

        csv_content = """Account Number,Post Date,Check,Description,Debit,Credit,Status,Balance
****7145,1/2/2026,,Duplicate test,,100.00,Posted,1000.00
****7145,1/2/2026,,Duplicate test,,100.00,Posted,1100.00"""

        result = parse_csv(csv_content)

        assert result.duplicate_count == 1
        assert any('Potential duplicate' in w for w in result.warnings)
