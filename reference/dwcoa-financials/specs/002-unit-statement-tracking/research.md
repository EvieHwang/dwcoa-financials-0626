# Technical Research: Unit Statement Tracking

## Overview

This document captures technical decisions and rationale for the Unit Statement Tracking feature.

---

## Key Technical Decisions

### TD-1: API Design - Single Endpoint vs Multiple

**Decision**: Single composite endpoint `GET /api/statement/{unit}`

**Rationale**:
- Frontend needs all statement data in one render cycle
- Reduces HTTP round trips (single request vs 4-5 separate calls)
- Simplifies frontend logic - one API call, one data structure
- Follows existing pattern where `/api/dashboard` returns composite data

**Alternative Considered**: Separate endpoints for prior year, current year, payments
- Rejected: More complex frontend orchestration, race conditions possible

---

### TD-2: Carryover Calculation Strategy

**Decision**: Calculate carryovers dynamically at query time (NOT stored)

**Rationale**:
- The existing dues system (`get_dues_status`) already calculates everything dynamically
- Budget lock is just a flag to prevent accidental edits - not a data finalization step
- Storing carryovers would duplicate data that can be computed from transactions
- Dynamic calculation is always accurate and self-correcting

**Implementation**:
```python
def get_statement(unit, year):
    prior_year = year - 1
    # Calculate carryover dynamically from prior year data
    prior_budgeted = get_total_operating_budget_annual(prior_year) * ownership_pct
    prior_paid = get_unit_payments_total(unit, prior_year)
    prior_past_due = get_unit_past_due(unit, prior_year)  # Historical debt only
    carryover = prior_budgeted + prior_past_due - prior_paid
    ...
```

**What `unit_past_dues` is for**:
- Historical debt that predates the transaction data (e.g., pre-2025 balances)
- NOT for year-to-year carryover (that's calculated dynamically)
- The 2025 seed values are this kind of historical debt

---

### TD-3: Payment History Query Strategy

**Decision**: Query transactions table directly by category pattern

**Rationale**:
- Existing pattern: `WHERE c.name LIKE 'Dues %'` already used in `dues.py`
- Generic "Dues" category exists for payments not assigned to specific unit
- Need to handle both `Dues` (generic) and `Dues 201` (specific) categories

**Payment Attribution**:
- `Dues 201` → Unit 201
- `Dues` (generic) → Not attributed to specific unit (show in history but exclude from balance calc)

**Query Pattern**:
```sql
SELECT t.post_date, t.credit as amount
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE c.name = 'Dues {unit}' OR c.name = 'Dues'
AND strftime('%Y', t.post_date) = ?
ORDER BY t.post_date DESC
```

---

### TD-4: No Schema Changes Required

**Decision**: No changes to `unit_past_dues` table needed

**Rationale**:
- Carryovers are calculated dynamically, not stored
- `unit_past_dues` only stores historical pre-transaction-data debt
- The 2025 seed values go here; future carryovers are computed
- No `auto_calculated` column needed since we don't auto-populate

**Existing Schema (unchanged)**:
```sql
CREATE TABLE unit_past_dues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_number TEXT NOT NULL,
    year INTEGER NOT NULL,
    past_due_balance REAL NOT NULL DEFAULT 0,
    UNIQUE(unit_number, year)
);
```

---

### TD-5: Months Remaining Calculation

**Decision**: Use calendar-based calculation from current date

**Rationale**:
- Simple: `months_remaining = 12 - current_month + 1`
- January = 12 months, December = 1 month
- Matches homeowner mental model (fiscal year = calendar year)

**Edge Case**: December suggested payment
- If December, show "Remaining balance: $X due by Dec 31" instead of monthly
- Prevents divide-by-one giving same number

---

### TD-6: Frontend State Management

**Decision**: localStorage for unit selection, no global state library

**Rationale**:
- Single piece of persistent state (selected unit)
- Vanilla JS codebase - no React/Redux/Vuex
- localStorage is browser-native, no dependencies
- Existing patterns: app uses localStorage for auth token

**Implementation**:
```javascript
// Save
localStorage.setItem('selectedUnit', unitNumber);

// Load
const selectedUnit = localStorage.getItem('selectedUnit');
```

---

### TD-7: UI Section Placement

**Decision**: New section below "Income & Dues", above "Operating Expenses"

**Rationale**:
- Contextually follows income/dues overview
- Homeowner's primary interest (My Account) is elevated vs admin-focused sections
- Maintains logical flow: Balances → Income → My Account → Expenses → History

**Alternative Considered**: Separate tab or page
- Rejected: Requirement FR-005 specifies "new section in existing dashboard"

---

## Existing Code Integration Points

### Backend

| File | Integration |
|------|-------------|
| `backend/app/main.py` | Add routes for `/api/statement/{unit}` |
| `backend/app/routes/statement.py` | **NEW** - Statement endpoint with dynamic carryover calc |
| `backend/app/services/database.py` | Add statement query helper functions |

**No changes needed to**:
- `budgets.py` - Lock remains a simple flag
- `schema.sql` - No schema changes required

### Frontend

| File | Integration |
|------|-------------|
| `frontend/index.html` | Add unit selector dropdown, My Account section HTML |
| `frontend/app.js` | Add statement fetching, rendering, localStorage handling |
| `frontend/styles.css` | Add My Account section styles |

---

## Data Flow Diagram

```
User selects unit → localStorage.setItem('selectedUnit')
                  ↓
              fetch('/api/statement/{unit}')
                  ↓
Backend calculates:
  1. Prior year: budgeted dues, paid, carryover
  2. Current year: carryover + annual dues - paid = remaining
  3. Payment guidance: remaining / months_remaining
  4. Recent payments: last 10 from transactions
                  ↓
Frontend renders My Account section with all data
```

---

## Risk Assessment

### Low Risk
- Database migration (adding column) - straightforward SQLite ALTER
- API endpoint addition - follows existing patterns exactly
- Frontend section - vanilla JS, well-established patterns

### Medium Risk
- Carryover calculation accuracy - needs thorough testing against manual verification
- Edge cases in payment guidance (December, credits, exactly on track)

### Mitigation
- Unit tests for carryover formula with known test data
- Manual verification with real 2025 data before release
- Edge case tests for payment guidance logic

---

## Performance Considerations

- Statement query should be < 100ms (small dataset, indexed queries)
- No caching needed (data changes infrequently, always needs fresh)
- Carryover calculation for 9 units is negligible (< 10ms)
