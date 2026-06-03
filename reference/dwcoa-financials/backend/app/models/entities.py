"""Data model entities."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class CategoryType(Enum):
    """Category types."""
    INCOME = "Income"
    EXPENSE = "Expense"
    TRANSFER = "Transfer"
    INTERNAL = "Internal"


@dataclass
class Account:
    """Bank account."""
    id: int
    masked_number: str
    name: str


@dataclass
class Category:
    """Transaction category."""
    id: int
    name: str
    type: CategoryType
    default_account: Optional[str] = None
    active: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> 'Category':
        """Create from database row dict."""
        return cls(
            id=d['id'],
            name=d['name'],
            type=CategoryType(d['type']),
            default_account=d.get('default_account'),
            active=bool(d.get('active', 1))
        )


@dataclass
class Transaction:
    """Financial transaction."""
    id: Optional[int]
    account_number: str
    account_name: str
    post_date: date
    description: str
    debit: Optional[Decimal]
    credit: Optional[Decimal]
    status: str
    balance: Decimal
    category_id: Optional[int] = None
    auto_category_id: Optional[int] = None
    confidence: Optional[int] = None
    needs_review: bool = False
    check_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, d: dict) -> 'Transaction':
        """Create from database row dict."""
        post_date = d['post_date']
        if isinstance(post_date, str):
            post_date = datetime.strptime(post_date, '%Y-%m-%d').date()

        return cls(
            id=d.get('id'),
            account_number=d['account_number'],
            account_name=d['account_name'],
            post_date=post_date,
            description=d['description'],
            debit=Decimal(str(d['debit'])) if d.get('debit') else None,
            credit=Decimal(str(d['credit'])) if d.get('credit') else None,
            status=d.get('status', 'Posted'),
            balance=Decimal(str(d['balance'])),
            category_id=d.get('category_id'),
            auto_category_id=d.get('auto_category_id'),
            confidence=d.get('confidence'),
            needs_review=bool(d.get('needs_review', 0)),
            check_number=d.get('check_number'),
            created_at=d.get('created_at'),
            updated_at=d.get('updated_at')
        )


@dataclass
class Budget:
    """Budget entry."""
    id: int
    year: int
    category_id: int
    annual_amount: Decimal
    # Computed fields for display
    category_name: Optional[str] = None
    category_type: Optional[str] = None
    annual_budget: Optional[Decimal] = None
    ytd_actual: Optional[Decimal] = None
    remaining: Optional[Decimal] = None


@dataclass
class Unit:
    """Condo unit."""
    id: int
    number: str
    ownership_pct: Decimal


@dataclass
class CategorizeRule:
    """Auto-categorization rule."""
    id: int
    pattern: str
    category_id: int
    confidence: int
    priority: int
    active: bool = True
    category_name: Optional[str] = None


@dataclass
class CategorizationResult:
    """Result of auto-categorization."""
    category_id: Optional[int]
    category_name: Optional[str]
    confidence: int
    needs_review: bool
    source: str  # 'rule', 'claude', 'manual', 'none'
