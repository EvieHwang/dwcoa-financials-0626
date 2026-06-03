"""CSV processing for bank transaction imports."""

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from app.services import database


# Expected CSV columns from bank export
EXPECTED_COLUMNS = [
    'Account Number',
    'Post Date',
    'Check',
    'Description',
    'Debit',
    'Credit',
    'Status',
    'Balance'
]


@dataclass
class ParsedTransaction:
    """A parsed transaction from CSV."""
    account_number: str
    account_name: str
    post_date: str  # YYYY-MM-DD format
    check_number: Optional[str]
    description: str
    debit: Optional[float]
    credit: Optional[float]
    status: str
    balance: float
    category: Optional[str]  # If pre-categorized in CSV


@dataclass
class ParseResult:
    """Result of parsing a CSV file."""
    transactions: List[ParsedTransaction]
    errors: List[str]
    warnings: List[str]
    duplicate_count: int


def parse_csv(content: str) -> ParseResult:
    """Parse bank CSV content into transactions.

    Args:
        content: CSV file content as string

    Returns:
        ParseResult with transactions and any errors/warnings
    """
    transactions: List[ParsedTransaction] = []
    errors: List[str] = []
    warnings: List[str] = []
    seen_transactions: set = set()  # For duplicate detection
    duplicate_count = 0

    # Parse CSV
    reader = csv.DictReader(io.StringIO(content))

    # Validate columns
    if reader.fieldnames:
        missing = set(EXPECTED_COLUMNS) - set(reader.fieldnames)
        if missing:
            errors.append(f"Missing required columns: {', '.join(missing)}")
            return ParseResult([], errors, warnings, 0)

    # Get account mappings
    account_map = {a['masked_number']: a['name'] for a in database.get_accounts()}

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
        try:
            # Parse account
            account_number = row.get('Account Number', '').strip()
            account_name = account_map.get(account_number)

            if not account_name:
                warnings.append(f"Row {row_num}: Unknown account '{account_number}'")
                account_name = 'Unknown'

            # Parse date (handle various formats)
            date_str = row.get('Post Date', '').strip()
            post_date = parse_date(date_str)
            if not post_date:
                errors.append(f"Row {row_num}: Invalid date '{date_str}'")
                continue

            # Parse amounts
            debit = parse_amount(row.get('Debit', ''))
            credit = parse_amount(row.get('Credit', ''))
            balance = parse_amount(row.get('Balance', ''))

            if balance is None:
                errors.append(f"Row {row_num}: Invalid balance")
                continue

            description = row.get('Description', '').strip()

            # Check for duplicates (same date + amount + description)
            txn_key = (post_date, debit or 0, credit or 0, description)
            if txn_key in seen_transactions:
                duplicate_count += 1
                warnings.append(f"Row {row_num}: Potential duplicate transaction")
            seen_transactions.add(txn_key)

            # Check for pre-existing category (if column exists)
            category = row.get('Category', '').strip() or None

            transactions.append(ParsedTransaction(
                account_number=account_number,
                account_name=account_name,
                post_date=post_date,
                check_number=row.get('Check', '').strip() or None,
                description=description,
                debit=debit,
                credit=credit,
                status=row.get('Status', 'Posted').strip(),
                balance=balance,
                category=category
            ))

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    return ParseResult(transactions, errors, warnings, duplicate_count)


def parse_date(date_str: str) -> Optional[str]:
    """Parse date string to YYYY-MM-DD format.

    Args:
        date_str: Date string in various formats

    Returns:
        Date in YYYY-MM-DD format, or None if invalid
    """
    if not date_str:
        return None

    # Try various formats
    formats = [
        '%m/%d/%Y',  # 1/2/2026
        '%m/%d/%y',  # 1/2/26
        '%Y-%m-%d',  # 2026-01-02
        '%d/%m/%Y',  # 2/1/2026 (European)
        '%Y/%m/%d',  # 2026/01/02
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None


def parse_amount(amount_str: str) -> Optional[float]:
    """Parse amount string to float.

    Args:
        amount_str: Amount string (may have $, commas, etc.)

    Returns:
        Float amount, or None if empty/invalid
    """
    if not amount_str:
        return None

    # Remove currency symbols and commas
    cleaned = amount_str.strip().replace('$', '').replace(',', '')

    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def generate_csv(transactions: List[dict], include_app_columns: bool = True) -> str:
    """Generate CSV from transactions.

    Args:
        transactions: List of transaction dicts
        include_app_columns: Include app-added columns (Account, Category, etc.)

    Returns:
        CSV content as string
    """
    output = io.StringIO()

    # Define columns
    columns = list(EXPECTED_COLUMNS)
    if include_app_columns:
        columns.extend(['Account', 'Category', 'Auto_Category', 'Confidence', 'Needs_Review'])

    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()

    for txn in transactions:
        row = {
            'Account Number': txn.get('account_number', ''),
            'Post Date': format_date_for_csv(txn.get('post_date', '')),
            'Check': txn.get('check_number', ''),
            'Description': txn.get('description', ''),
            'Debit': format_amount_for_csv(txn.get('debit')),
            'Credit': format_amount_for_csv(txn.get('credit')),
            'Status': txn.get('status', 'Posted'),
            'Balance': format_amount_for_csv(txn.get('balance')),
        }

        if include_app_columns:
            row['Account'] = txn.get('account_name', '')
            row['Category'] = txn.get('category', '')
            row['Auto_Category'] = txn.get('auto_category', '')
            row['Confidence'] = txn.get('confidence', '')
            row['Needs_Review'] = 'true' if txn.get('needs_review') else ''

        writer.writerow(row)

    return output.getvalue()


def format_date_for_csv(date_val) -> str:
    """Format date for CSV output."""
    if not date_val:
        return ''
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%m/%d/%Y')
    # Assume string in YYYY-MM-DD format
    try:
        dt = datetime.strptime(str(date_val), '%Y-%m-%d')
        return dt.strftime('%m/%d/%Y')
    except ValueError:
        return str(date_val)


def format_amount_for_csv(amount) -> str:
    """Format amount for CSV output."""
    if amount is None:
        return ''
    return f"{float(amount):.2f}"
