"""Auto-categorization service using simple string matching."""

from typing import Optional

from aws_lambda_powertools import Logger

from app.services import database
from app.models.entities import CategorizationResult


# Initialize structured logger
logger = Logger(service="dwcoa-categorizer")

# Account numbers for transfer detection
INTERNAL_ACCOUNT_NUMBERS = ['7145', '9242', '9226']


def get_transfers_category_id() -> Optional[int]:
    """Get the Transfers category ID."""
    cat = database.get_category_by_name('Transfers')
    return cat['id'] if cat else None


def categorize_transaction(description: str, account_name: str) -> CategorizationResult:
    """Categorize a single transaction using simple string matching.

    Args:
        description: Transaction description
        account_name: Account name (Savings, Checking, Reserve Fund)

    Returns:
        CategorizationResult with category and confidence
    """
    desc_upper = description.upper()

    # Check for internal transfers first
    # Pattern: description contains 'Transfer' AND any internal account number
    if 'TRANSFER' in desc_upper:
        if any(acc in description for acc in INTERNAL_ACCOUNT_NUMBERS):
            transfers_id = get_transfers_category_id()
            if transfers_id:
                logger.info(
                    "Transfer auto-detected",
                    extra={
                        "categorization_source": "transfer_detection",
                        "category_id": transfers_id,
                        "description_preview": description[:50],
                        "account": account_name
                    }
                )
                return CategorizationResult(
                    category_id=transfers_id,
                    category_name='Transfers',
                    confidence=100,
                    needs_review=False,
                    source='rule'
                )

    # Check rules (case-insensitive substring match)
    rules = database.get_categorize_rules()

    for rule in rules:
        pattern_upper = rule['pattern'].upper()
        if pattern_upper in desc_upper:
            logger.info(
                "Rule match",
                extra={
                    "categorization_source": "rule",
                    "pattern": rule['pattern'],
                    "category_id": rule['category_id'],
                    "category_name": rule['category_name'],
                    "description_preview": description[:50],
                    "account": account_name
                }
            )
            return CategorizationResult(
                category_id=rule['category_id'],
                category_name=rule['category_name'],
                confidence=100,
                needs_review=False,
                source='rule'
            )

    # No match - flag for review
    logger.debug(
        "No rule match",
        extra={
            "categorization_source": "none",
            "description_preview": description[:50],
            "account": account_name
        }
    )
    return CategorizationResult(
        category_id=None,
        category_name=None,
        confidence=0,
        needs_review=True,
        source='none'
    )


def learn_pattern(description: str, category_id: int) -> None:
    """Learn a new categorization pattern from manual categorization.

    Creates a simple substring rule based on the transaction description.
    Future transactions containing this pattern will be auto-categorized.

    Args:
        description: Transaction description (used as pattern)
        category_id: Category ID assigned
    """
    # Use the full description as the pattern (simple substring matching)
    # The admin can edit this in the Rules UI to make it more specific
    pattern = description.strip()

    if not pattern or len(pattern) < 3:
        logger.warning(
            "Pattern learning failed - pattern too short",
            extra={
                "description_preview": description[:50],
                "category_id": category_id
            }
        )
        return

    # Get category name for logging
    cat = database.get_category_by_id(category_id)
    cat_name = cat['name'] if cat else f'ID:{category_id}'

    # Check if pattern already exists
    if database.rule_pattern_exists(pattern):
        logger.info(
            "Pattern learning skipped - pattern exists",
            extra={
                "pattern": pattern[:50],
                "category_id": category_id,
                "category_name": cat_name
            }
        )
        return

    # Create new rule
    database.create_rule(pattern, category_id)
    logger.info(
        "Pattern learned",
        extra={
            "pattern_learning": True,
            "pattern": pattern[:50],
            "category_id": category_id,
            "category_name": cat_name
        }
    )
