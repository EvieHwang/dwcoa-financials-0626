# Data Model: Unit Statement Tracking

## Schema: No Changes Required

The existing `unit_past_dues` table is sufficient. It stores **historical debt that predates the transaction data** (e.g., pre-2025 balances), not year-to-year carryovers.

**Existing Schema (unchanged)**:
```sql
CREATE TABLE unit_past_dues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_number TEXT NOT NULL,
    year INTEGER NOT NULL,
    past_due_balance REAL NOT NULL DEFAULT 0,
    UNIQUE(unit_number, year),
    FOREIGN KEY (unit_number) REFERENCES units(number)
);
```

**Purpose**: Store historical debt from before transaction data exists. Year-to-year carryovers are calculated dynamically from transaction data.

---

## API Response Structures

### Statement Response

**Endpoint**: `GET /api/statement/{unit}?year={year}`

```typescript
interface StatementResponse {
  unit: string;                    // "201"
  ownership_pct: number;           // 0.104 (10.4%)

  current_year: {
    year: number;                  // 2026
    budget_locked: boolean;        // true
    carryover_balance: number;     // 160.00 (positive = owes, negative = credit)
    annual_dues: number;           // 4104.00
    total_due: number;             // 4264.00 (carryover + annual_dues)
    paid_ytd: number;              // 700.00
    remaining_balance: number;     // 3564.00 (total_due - paid_ytd)
    standard_monthly: number;      // 342.00 (annual_dues / 12)
    months_remaining: number;      // 10 (in March)
    suggested_monthly: number;     // 356.40 (remaining / months_remaining)
  };

  prior_year: {
    year: number;                  // 2025
    annual_dues_budgeted: number;  // 3960.00
    total_paid: number;            // 3800.00
    balance_carried_forward: number; // 160.00
  } | null;                        // null if no prior year data

  recent_payments: Array<{
    date: string;                  // "2026-02-03"
    amount: number;                // 350.00
  }>;
}
```

### Payment History Response

**Endpoint**: `GET /api/statement/{unit}/payments?year={year}`

```typescript
interface PaymentHistoryResponse {
  unit: string;
  year: number;
  payments: Array<{
    date: string;
    amount: number;
    description: string;           // From transaction description
  }>;
}
```

---

## Calculation Formulas

### Prior Year Balance Carried Forward

```
balance_carried_forward = annual_dues_budgeted - total_paid
```

Where:
- `annual_dues_budgeted` = Total Operating Budget × Ownership %
- `total_paid` = SUM(transactions.credit) WHERE category = 'Dues {unit}' AND year = prior_year

**Sign Convention**:
- Positive = owes money (underpaid)
- Negative = credit (overpaid)

### Current Year Total Due

```
total_due = carryover_balance + annual_dues
```

Where:
- `carryover_balance` = unit_past_dues.past_due_balance for current year (or calculated from prior year)
- `annual_dues` = Total Operating Budget × Ownership %

### Remaining Balance

```
remaining_balance = total_due - paid_ytd
```

### Suggested Monthly Payment

```
if remaining_balance <= 0:
    suggested_monthly = 0  # Display "Paid in full" or "Credit balance"
elif current_month == 12:
    suggested_monthly = remaining_balance  # Display "Due by Dec 31"
else:
    months_remaining = 12 - current_month + 1
    suggested_monthly = remaining_balance / months_remaining
```

### Standard Monthly Payment

```
standard_monthly = annual_dues / 12
```

---

## Carryover Calculation Logic (Dynamic)

**Calculated at query time** - not stored, not triggered by budget lock.

**Formula**:
```
carryover = prior_year_budgeted + prior_year_historical_debt - prior_year_paid
```

Where:
- `prior_year_budgeted` = Total Operating Budget (annual) × Ownership %
- `prior_year_historical_debt` = `unit_past_dues.past_due_balance` for prior year (0 if none)
- `prior_year_paid` = SUM(transactions.credit) WHERE category = 'Dues {unit}' AND year = prior_year

**Pseudocode**:
```python
def get_carryover(unit_number: str, year: int) -> float:
    """Calculate carryover dynamically from prior year data."""
    prior_year = year - 1

    # Get prior year budget
    prior_budget = get_total_operating_budget_annual(prior_year)
    ownership_pct = get_unit(unit_number)['ownership_pct']
    budgeted = prior_budget * ownership_pct

    # Get prior year historical debt (pre-transaction-data debt only)
    historical_debt = get_unit_past_due(unit_number, prior_year)

    # Get prior year payments
    paid = get_unit_payments_total(unit_number, prior_year)

    return budgeted + historical_debt - paid
```

**Why dynamic calculation?**
- Always accurate - no stale data
- Self-correcting if transactions are recategorized
- Matches how `get_dues_status()` already works
- No need to modify budget lock behavior

---

## Query Templates

### Get Unit Statement Data

```sql
-- Get ownership percentage
SELECT number, ownership_pct FROM units WHERE number = ?;

-- Get current year budget lock status
SELECT locked FROM budget_locks WHERE year = ?;

-- Get total operating budget for year (annual amount)
SELECT SUM(b.annual_amount) as total
FROM budgets b
JOIN categories c ON b.category_id = c.id
WHERE b.year = ? AND c.type = 'Expense' AND c.name != 'Reserve Expenses';

-- Get carryover (past due) for unit/year
SELECT past_due_balance, auto_calculated
FROM unit_past_dues
WHERE unit_number = ? AND year = ?;

-- Get payments for unit in year
SELECT SUM(t.credit) as total_paid
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE c.name = ? AND strftime('%Y', t.post_date) = ?;
-- Where c.name = 'Dues 201' for unit 201

-- Get recent payments
SELECT t.post_date as date, t.credit as amount
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE c.name = ? AND strftime('%Y', t.post_date) = ?
ORDER BY t.post_date DESC
LIMIT 10;
```

---

## Seed Data: 2025 Historical Debt

The `unit_past_dues` table stores **historical debt that predates the transaction data**. Bank statements only go back so far, so any debt from before that must be manually entered.

**2025 Historical Debt** (debt from before transaction data begins):

| Unit | Historical Debt | Notes |
|------|-----------------|-------|
| 101 | $3,981.85 | Pre-2025 debt |
| 102 | $0.00 | No historical debt |
| 103 | $0.00 | No historical debt |
| 201 | $529.00 | Pre-2025 debt |
| 202 | $0.00 | No historical debt |
| 203 | $371.40 | Pre-2025 debt |
| 301 | $0.00 | No historical debt |
| 302 | $0.00 | No historical debt |
| 303 | $625.44 | Pre-2025 debt |

**Seed SQL**:
```sql
-- Insert 2025 historical debt (debt predating transaction data)
INSERT OR REPLACE INTO unit_past_dues (unit_number, year, past_due_balance)
VALUES
    ('101', 2025, 3981.85),
    ('201', 2025, 529.00),
    ('203', 2025, 371.40),
    ('303', 2025, 625.44);
-- Units with $0 historical debt don't need entries (defaults to 0)
```

**Important**: This is a one-time seed. Future years don't need entries because carryovers are calculated dynamically from transaction data.

---

## Data Validation Rules

1. **Unit number**: Must be one of: 101, 102, 103, 201, 202, 203, 301, 302, 303
2. **Year**: Must be positive integer, reasonable range (2020-2030)
3. **Ownership percentage**: Must be > 0 and <= 1 (already enforced by schema)
4. **Past due balance**: Can be positive (owes) or negative (credit)
5. **Payments**: Must be positive amounts (credits to account)
