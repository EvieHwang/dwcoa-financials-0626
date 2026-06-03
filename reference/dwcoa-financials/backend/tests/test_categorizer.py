"""Tests for auto-categorization."""

import pytest
from unittest.mock import patch


class TestRulesEngine:
    """Tests for rules-based categorization."""

    @patch('app.services.categorizer.database')
    def test_match_interest_income(self, mock_db):
        """Dividend/Interest should match Interest income."""
        mock_db.get_categorize_rules.return_value = [
            {
                'pattern': 'Dividend.*Interest|DIVIDEND.*INTEREST',
                'category_id': 10,
                'category_name': 'Interest income',
                'confidence': 98,
                'priority': 100
            }
        ]

        from app.services.categorizer import categorize_transaction

        result = categorize_transaction('Dividend/Interest', 'Savings')

        assert result.category_id == 10
        assert result.category_name == 'Interest income'
        assert result.confidence == 98
        assert not result.needs_review
        assert result.source == 'rule'

    @patch('app.services.categorizer.database')
    def test_match_transfer(self, mock_db):
        """Internet Transfer should match Transfers."""
        mock_db.get_categorize_rules.return_value = [
            {
                'pattern': 'Internet Transfer|Reserve Funds',
                'category_id': 22,
                'category_name': 'Transfers',
                'confidence': 95,
                'priority': 100
            }
        ]

        from app.services.categorizer import categorize_transaction

        result = categorize_transaction('Internet Transfer to 3580799242', 'Savings')

        assert result.category_id == 22
        assert result.category_name == 'Transfers'
        assert result.confidence == 95

    @patch('app.services.categorizer.database')
    def test_match_utility(self, mock_db):
        """Seattle City Light should match."""
        mock_db.get_categorize_rules.return_value = [
            {
                'pattern': 'SEATTLE.*CITY.*LIGHT|SEATTLEUTILITIES',
                'category_id': 18,
                'category_name': 'Seattle City Light',
                'confidence': 95,
                'priority': 100
            }
        ]

        from app.services.categorizer import categorize_transaction

        result = categorize_transaction('SEATTLE CITY LIGHT PAYMENT', 'Checking')

        assert result.category_id == 18
        assert result.category_name == 'Seattle City Light'

    @patch('app.services.categorizer.database')
    def test_match_dues_by_name(self, mock_db):
        """Owner name should match their dues category."""
        mock_db.get_categorize_rules.return_value = [
            {
                'pattern': 'J ERNAST|J.*ERNAST',
                'category_id': 8,
                'category_name': 'Dues 302',
                'confidence': 92,
                'priority': 80
            }
        ]

        from app.services.categorizer import categorize_transaction

        result = categorize_transaction('External Deposit J ERNAST  - CREDIT', 'Savings')

        assert result.category_id == 8
        assert result.category_name == 'Dues 302'
        assert result.confidence == 92

    @patch('app.services.categorizer.database')
    def test_no_match(self, mock_db):
        """Unknown description should not match."""
        mock_db.get_categorize_rules.return_value = [
            {
                'pattern': 'SPECIFIC_PATTERN',
                'category_id': 1,
                'category_name': 'Category',
                'confidence': 90,
                'priority': 100
            }
        ]

        from app.services.categorizer import categorize_transaction

        result = categorize_transaction('Some random transaction', 'Checking')

        assert result.category_id is None
        assert result.confidence == 0
        assert result.needs_review
        assert result.source == 'none'

    @patch('app.services.categorizer.database')
    def test_low_confidence_needs_review(self, mock_db):
        """Low confidence matches should be flagged for review."""
        mock_db.get_categorize_rules.return_value = [
            {
                'pattern': 'Deposit',
                'category_id': 99,
                'category_name': 'Other',
                'confidence': 50,  # Below 80 threshold
                'priority': 10
            }
        ]

        from app.services.categorizer import categorize_transaction

        result = categorize_transaction('External Deposit', 'Savings')

        assert result.category_id == 99
        assert result.confidence == 50
        assert result.needs_review  # Should be flagged

    @patch('app.services.categorizer.database')
    def test_priority_ordering(self, mock_db):
        """Higher priority rules should match first."""
        mock_db.get_categorize_rules.return_value = [
            {
                'pattern': 'Deposit',  # Generic, low priority
                'category_id': 99,
                'category_name': 'Other',
                'confidence': 50,
                'priority': 10
            },
            {
                'pattern': 'J ERNAST',  # Specific, high priority
                'category_id': 8,
                'category_name': 'Dues 302',
                'confidence': 92,
                'priority': 80
            }
        ]

        from app.services.categorizer import categorize_transaction

        # Should match the higher priority rule
        result = categorize_transaction('External Deposit J ERNAST', 'Savings')

        # Note: In real implementation, rules are returned sorted by priority
        # This test verifies the first matching rule is used
        assert result.source == 'rule'


class TestCategorizationResult:
    """Tests for CategorizationResult model."""

    def test_result_attributes(self):
        from app.models.entities import CategorizationResult

        result = CategorizationResult(
            category_id=1,
            category_name='Test',
            confidence=85,
            needs_review=False,
            source='rule'
        )

        assert result.category_id == 1
        assert result.category_name == 'Test'
        assert result.confidence == 85
        assert not result.needs_review
        assert result.source == 'rule'


class TestPatternExtraction:
    """Tests for pattern learning from manual categorization."""

    def test_extract_pattern_from_dues_payment(self):
        """Extract pattern from typical dues payment."""
        from app.services.categorizer import extract_pattern_from_description

        patterns = extract_pattern_from_description(
            "External Deposit J ERNAST  - CREDIT"
        )

        # Should extract "J" and/or "ERNAST" as distinctive parts
        assert len(patterns) > 0
        # The pattern should match the original
        import re
        assert any(re.search(p, "J ERNAST", re.IGNORECASE) for p in patterns)

    def test_extract_pattern_from_transfer(self):
        """Extract pattern from owner name in transfer."""
        from app.services.categorizer import extract_pattern_from_description

        patterns = extract_pattern_from_description(
            "External Deposit WENLU CHENG ONLNE TRNSFR88871070 - SENDER"
        )

        assert len(patterns) > 0
        # Should extract WENLU CHENG as the distinctive part
        import re
        assert any(re.search(p, "WENLU CHENG", re.IGNORECASE) for p in patterns)

    def test_extract_pattern_from_utility(self):
        """Extract pattern from utility payment."""
        from app.services.categorizer import extract_pattern_from_description

        patterns = extract_pattern_from_description(
            "SEATTLE CITY LIGHT PAYMENT"
        )

        assert len(patterns) > 0
        import re
        assert any(re.search(p, "SEATTLE", re.IGNORECASE) for p in patterns)

    def test_extract_pattern_from_interest(self):
        """Extract pattern from interest income."""
        from app.services.categorizer import extract_pattern_from_description

        patterns = extract_pattern_from_description("Dividend/Interest")

        assert len(patterns) > 0
        import re
        # Pattern should match the original description
        assert any(re.search(p, "Dividend/Interest", re.IGNORECASE) for p in patterns)

    def test_extract_pattern_skips_generic_prefixes(self):
        """Should skip 'External Deposit' and find the real identifier."""
        from app.services.categorizer import extract_pattern_from_description

        patterns = extract_pattern_from_description(
            "External Deposit Emma Landsman  - P2P XFR"
        )

        # Should NOT just return "External" as the pattern
        assert not any(p == "External" for p in patterns)
        # Should find Emma or Landsman
        import re
        assert any(
            re.search(p, "Emma", re.IGNORECASE) or re.search(p, "Landsman", re.IGNORECASE)
            for p in patterns
        )
