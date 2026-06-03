# Data Model: DWCOA Financial Tracker

**Feature**: 001-financial-tracker
**Date**: 2026-01-02
**Storage**: SQLite (file stored in S3)

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│   Transaction   │──────▶│    Category     │
└─────────────────┘       └─────────────────┘
                                  │
                                  ▼
┌─────────────────┐       ┌─────────────────┐
│      Unit       │       │     Budget      │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│     Account     │       │ CategorizeRule  │
└─────────────────┘       └─────────────────┘

┌─────────────────┐
│    AppConfig    │
└─────────────────┘
```

---

## Tables

### transactions

Stores all financial transactions from bank CSV uploads.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key, auto-increment |
| account_number | TEXT | NO | Masked account from bank (e.g., "****7145") |
| account_name | TEXT | NO | Friendly name (Savings, Checking, Reserve Fund) |
| post_date | DATE | NO | Transaction date |
| check_number | TEXT | YES | Check number if applicable |
| description | TEXT | NO | Transaction description from bank |
| debit | DECIMAL(10,2) | YES | Debit amount (money out) |
| credit | DECIMAL(10,2) | YES | Credit amount (money in) |
| status | TEXT | NO | Transaction status (Posted, Pending) |
| balance | DECIMAL(10,2) | NO | Account balance after transaction |
| category_id | INTEGER | YES | FK to categories.id |
| auto_category_id | INTEGER | YES | AI-suggested category |
| confidence | INTEGER | YES | Categorization confidence (0-100) |
| needs_review | BOOLEAN | NO | Flag for manual review (default: false) |
| created_at | DATETIME | NO | When record was created |
| updated_at | DATETIME | NO | When record was last updated |

**Indexes**:
- `idx_transactions_date` on (post_date)
- `idx_transactions_account` on (account_name)
- `idx_transactions_category` on (category_id)
- `idx_transactions_review` on (needs_review) WHERE needs_review = true

**SQL**:
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    account_name TEXT NOT NULL,
    post_date DATE NOT NULL,
    check_number TEXT,
    description TEXT NOT NULL,
    debit DECIMAL(10,2),
    credit DECIMAL(10,2),
    status TEXT NOT NULL DEFAULT 'Posted',
    balance DECIMAL(10,2) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    auto_category_id INTEGER REFERENCES categories(id),
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    needs_review BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_date ON transactions(post_date);
CREATE INDEX idx_transactions_account ON transactions(account_name);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_review ON transactions(needs_review) WHERE needs_review = 1;
```

---

### categories

Defines income, expense, and transfer categories.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key, auto-increment |
| name | TEXT | NO | Category name (unique) |
| type | TEXT | NO | Income, Expense, Transfer, or Internal |
| default_account | TEXT | YES | Default account (Savings, Checking, Reserve Fund, Any) |
| timing | TEXT | NO | Budget timing pattern (monthly, quarterly, annual) |
| active | BOOLEAN | NO | Whether category is active (default: true) |
| created_at | DATETIME | NO | When record was created |

**Constraints**:
- `type` IN ('Income', 'Expense', 'Transfer', 'Internal')
- `timing` IN ('monthly', 'quarterly', 'annual')

**SQL**:
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('Income', 'Expense', 'Transfer', 'Internal')),
    default_account TEXT CHECK (default_account IN ('Savings', 'Checking', 'Reserve Fund', 'Any', NULL)),
    timing TEXT NOT NULL DEFAULT 'monthly' CHECK (timing IN ('monthly', 'quarterly', 'annual')),
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Seed Data**:
```sql
INSERT INTO categories (name, type, default_account, timing) VALUES
-- Income (Dues)
('Dues 101', 'Income', 'Savings', 'monthly'),
('Dues 102', 'Income', 'Savings', 'monthly'),
('Dues 103', 'Income', 'Savings', 'monthly'),
('Dues 201', 'Income', 'Savings', 'monthly'),
('Dues 202', 'Income', 'Savings', 'monthly'),
('Dues 203', 'Income', 'Savings', 'monthly'),
('Dues 301', 'Income', 'Savings', 'monthly'),
('Dues 302', 'Income', 'Savings', 'monthly'),
('Dues 303', 'Income', 'Savings', 'monthly'),
('Interest income', 'Income', 'Any', 'monthly'),
-- Expenses
('Bulger Safe & Lock', 'Expense', 'Checking', 'annual'),
('Cintas Fire Protection', 'Expense', 'Checking', 'annual'),
('Common Area Cleaning', 'Expense', 'Checking', 'monthly'),
('Fire Alarm', 'Expense', 'Checking', 'monthly'),
('Grounds/Landscaping', 'Expense', 'Checking', 'monthly'),
('Homeowners Club Dues', 'Expense', 'Checking', 'annual'),
('Insurance Premiums', 'Expense', 'Checking', 'monthly'),
('Seattle City Light', 'Expense', 'Checking', 'monthly'),
('Other', 'Expense', 'Checking', 'annual'),
('Reserve Contribution', 'Transfer', 'Savings', 'monthly'),
('Reserve Expenses', 'Expense', 'Reserve Fund', 'annual'),
('Transfers', 'Internal', 'Any', 'annual');
```

---

### budgets

Stores annual budget amounts per category.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key, auto-increment |
| year | INTEGER | NO | Budget year |
| category_id | INTEGER | NO | FK to categories.id |
| annual_amount | DECIMAL(10,2) | NO | Annual budget amount |
| timing | TEXT | YES | Override timing (if different from category default) |

**Unique Constraint**: (year, category_id)

**SQL**:
```sql
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    annual_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    timing TEXT CHECK (timing IN ('monthly', 'quarterly', 'annual', NULL)),
    UNIQUE(year, category_id)
);
```

**2025 Seed Data**:
```sql
-- Income
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5954.75 FROM categories WHERE name = 'Dues 101';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5293.11 FROM categories WHERE name = 'Dues 102';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5700.27 FROM categories WHERE name = 'Dues 103';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5954.75 FROM categories WHERE name = 'Dues 201';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5293.11 FROM categories WHERE name = 'Dues 202';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5700.27 FROM categories WHERE name = 'Dues 203';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5954.75 FROM categories WHERE name = 'Dues 301';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5293.11 FROM categories WHERE name = 'Dues 302';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 5700.27 FROM categories WHERE name = 'Dues 303';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 26.00 FROM categories WHERE name = 'Interest income';

-- Expenses
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 18000.00 FROM categories WHERE name = 'Reserve Contribution';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 400.00 FROM categories WHERE name = 'Bulger Safe & Lock';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 1500.00 FROM categories WHERE name = 'Cintas Fire Protection';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 2700.00 FROM categories WHERE name = 'Common Area Cleaning';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 3300.00 FROM categories WHERE name = 'Fire Alarm';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 12000.00 FROM categories WHERE name = 'Grounds/Landscaping';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 7500.00 FROM categories WHERE name = 'Other';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 4500.00 FROM categories WHERE name = 'Insurance Premiums';
INSERT INTO budgets (year, category_id, annual_amount)
SELECT 2025, id, 6000.00 FROM categories WHERE name = 'Seattle City Light';
```

---

### units

Stores condo unit information and ownership percentages.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key, auto-increment |
| number | TEXT | NO | Unit number (101, 102, etc.) |
| ownership_pct | DECIMAL(5,3) | NO | Ownership percentage (e.g., 0.117) |

**SQL**:
```sql
CREATE TABLE units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL UNIQUE,
    ownership_pct DECIMAL(5,3) NOT NULL CHECK (ownership_pct > 0 AND ownership_pct <= 1)
);

INSERT INTO units (number, ownership_pct) VALUES
('101', 0.117),
('102', 0.104),
('103', 0.112),
('201', 0.117),
('202', 0.104),
('203', 0.112),
('301', 0.117),
('302', 0.104),
('303', 0.112);
```

---

### accounts

Stores account mapping from masked numbers to friendly names.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key, auto-increment |
| masked_number | TEXT | NO | Masked account number from bank (****7145) |
| name | TEXT | NO | Friendly name (Savings, Checking, Reserve Fund) |

**SQL**:
```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    masked_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE
);

INSERT INTO accounts (masked_number, name) VALUES
('****7145', 'Savings'),
('****9242', 'Checking'),
('****9226', 'Reserve Fund');
```

---

### categorize_rules

Stores pattern-matching rules for auto-categorization.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | NO | Primary key, auto-increment |
| pattern | TEXT | NO | Regex pattern to match on description |
| category_id | INTEGER | NO | FK to categories.id |
| confidence | INTEGER | NO | Confidence score (0-100) |
| priority | INTEGER | NO | Rule priority (higher = checked first) |
| active | BOOLEAN | NO | Whether rule is active |
| created_at | DATETIME | NO | When rule was created |

**SQL**:
```sql
CREATE TABLE categorize_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    confidence INTEGER NOT NULL DEFAULT 90 CHECK (confidence >= 0 AND confidence <= 100),
    priority INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rules_active ON categorize_rules(active, priority DESC);
```

**Initial Rules** (from training data):
```sql
INSERT INTO categorize_rules (pattern, category_id, confidence, priority) VALUES
-- Utility patterns
('WASHINGTON.*ALARM', (SELECT id FROM categories WHERE name = 'Fire Alarm'), 95, 100),
('SEATTLE.*CITY.*LIGHT|SEATTLEUTILITIES', (SELECT id FROM categories WHERE name = 'Seattle City Light'), 95, 100),
('CINTAS', (SELECT id FROM categories WHERE name = 'Cintas Fire Protection'), 95, 100),
('NWEDI.*EDI|NWEDI-291390275', (SELECT id FROM categories WHERE name = 'Insurance Premiums'), 90, 90),
('BULGER', (SELECT id FROM categories WHERE name = 'Bulger Safe & Lock'), 95, 100),
-- Interest
('Dividend/Interest', (SELECT id FROM categories WHERE name = 'Interest income'), 95, 100),
-- Transfers (internal)
('Internet Transfer|Reserve Funds', (SELECT id FROM categories WHERE name = 'Transfers'), 95, 100),
-- Dues by owner name (examples - should be expanded based on actual data)
('J ERNAST', (SELECT id FROM categories WHERE name = 'Dues 302'), 90, 80),
('EVE HWANG', (SELECT id FROM categories WHERE name = 'Dues 203'), 90, 80),
('WENLU CHENG', (SELECT id FROM categories WHERE name = 'Dues 101'), 90, 80),
('JARED MOLTON', (SELECT id FROM categories WHERE name = 'Dues 301'), 90, 80),
('Emma Landsman', (SELECT id FROM categories WHERE name = 'Dues 102'), 90, 80),
('R Young', (SELECT id FROM categories WHERE name = 'Dues 201'), 90, 80),
('BOEING EMPLOYEES.*CREDIT UNION', (SELECT id FROM categories WHERE name = 'Dues 103'), 85, 70);
```

---

### app_config

Stores application configuration and state.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| key | TEXT | NO | Config key (primary key) |
| value | TEXT | NO | Config value (JSON for complex values) |
| updated_at | DATETIME | NO | When config was last updated |

**SQL**:
```sql
CREATE TABLE app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO app_config (key, value) VALUES
('last_upload_at', ''),
('admin_password_hash', ''),
('board_password_hash', ''),
('current_year', '2025');
```

---

## Views

### v_transaction_summary

Provides transaction data with category names for display.

```sql
CREATE VIEW v_transaction_summary AS
SELECT
    t.id,
    t.account_name,
    t.post_date,
    t.description,
    t.debit,
    t.credit,
    c.name as category,
    c.type as category_type,
    ac.name as auto_category,
    t.confidence,
    t.needs_review
FROM transactions t
LEFT JOIN categories c ON t.category_id = c.id
LEFT JOIN categories ac ON t.auto_category_id = ac.id
ORDER BY t.post_date DESC;
```

### v_budget_status

Calculates YTD budget vs actual for dashboard.

```sql
CREATE VIEW v_budget_status AS
SELECT
    b.year,
    c.name as category,
    c.type as category_type,
    b.annual_amount,
    COALESCE(b.timing, c.timing) as timing,
    -- YTD budget calculation (simplified, actual logic in Python)
    b.annual_amount as ytd_budget,
    -- Actual calculation
    COALESCE(SUM(
        CASE WHEN c.type = 'Income' THEN t.credit ELSE t.debit END
    ), 0) as ytd_actual
FROM budgets b
JOIN categories c ON b.category_id = c.id
LEFT JOIN transactions t ON t.category_id = c.id
    AND strftime('%Y', t.post_date) = CAST(b.year AS TEXT)
WHERE c.type IN ('Income', 'Expense')
    AND c.name != 'Transfers'
GROUP BY b.id, c.id;
```

### v_dues_status

Shows dues status by unit.

```sql
CREATE VIEW v_dues_status AS
SELECT
    u.number as unit,
    u.ownership_pct,
    -- Expected dues = total expense budget * ownership %
    (SELECT SUM(annual_amount) FROM budgets b
     JOIN categories c ON b.category_id = c.id
     WHERE b.year = (SELECT value FROM app_config WHERE key = 'current_year')
     AND c.type = 'Expense') * u.ownership_pct as expected_annual,
    -- Payments received
    COALESCE((
        SELECT SUM(t.credit)
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name = 'Dues ' || u.number
        AND strftime('%Y', t.post_date) = (SELECT value FROM app_config WHERE key = 'current_year')
    ), 0) as paid_ytd,
    -- Outstanding = expected - paid
    (SELECT SUM(annual_amount) FROM budgets b
     JOIN categories c ON b.category_id = c.id
     WHERE b.year = (SELECT value FROM app_config WHERE key = 'current_year')
     AND c.type = 'Expense') * u.ownership_pct
    - COALESCE((
        SELECT SUM(t.credit)
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name = 'Dues ' || u.number
        AND strftime('%Y', t.post_date) = (SELECT value FROM app_config WHERE key = 'current_year')
    ), 0) as outstanding
FROM units u
ORDER BY u.number;
```

---

## Data Types (Python)

```python
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

class CategoryType(Enum):
    INCOME = "Income"
    EXPENSE = "Expense"
    TRANSFER = "Transfer"
    INTERNAL = "Internal"

class TimingPattern(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

@dataclass
class Transaction:
    id: int
    account_number: str
    account_name: str
    post_date: date
    description: str
    debit: Optional[Decimal]
    credit: Optional[Decimal]
    status: str
    balance: Decimal
    category_id: Optional[int]
    auto_category_id: Optional[int]
    confidence: Optional[int]
    needs_review: bool
    check_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Category:
    id: int
    name: str
    type: CategoryType
    timing: TimingPattern
    default_account: Optional[str] = None
    active: bool = True

@dataclass
class Budget:
    id: int
    year: int
    category_id: int
    annual_amount: Decimal
    timing: Optional[TimingPattern] = None

@dataclass
class Unit:
    id: int
    number: str
    ownership_pct: Decimal

@dataclass
class Account:
    id: int
    masked_number: str
    name: str

@dataclass
class CategorizeRule:
    id: int
    pattern: str
    category_id: int
    confidence: int
    priority: int
    active: bool = True
```

---

## Migration Strategy

Since this is a new application with no existing data:

1. **Initial Setup**: Run `schema.sql` to create all tables
2. **Seed Data**: Run `seed.sql` to populate categories, units, accounts, budgets
3. **Rules**: Run `rules.sql` to populate initial categorization rules
4. **Version**: Store schema version in `app_config` for future migrations

All SQL files will be packaged with the Lambda function.
