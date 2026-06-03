# Technical Plan: Unit Statement Tracking

**Feature**: Unit Statement Tracking ("My Account" Section)
**Branch**: `feature/002-unit-statement-tracking`
**Created**: 2026-01-21
**Updated**: 2026-01-21 - Simplified (dynamic carryover calculation, no schema changes)

---

## Technical Context

| Aspect | Value |
|--------|-------|
| **Language** | Python 3.12 (backend), Vanilla JavaScript (frontend) |
| **Framework** | AWS Lambda + API Gateway |
| **Database** | SQLite (stored in S3) |
| **Frontend** | Static HTML/CSS/JS hosted on S3 + CloudFront |
| **Auth** | JWT tokens, shared passwords (board/admin roles) |
| **Build Tool** | AWS SAM |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ Unit Selector │  │         My Account Section           │ │
│  │   Dropdown    │  │  ┌────────────┬───────────────────┐  │ │
│  │               │  │  │Last Year   │ Current Year      │  │ │
│  │ localStorage  │  │  │Summary     │ Summary           │  │ │
│  │ persistence   │  │  ├────────────┼───────────────────┤  │ │
│  └──────────────┘  │  │Payment     │ Payment Guidance  │  │ │
│                     │  │History     │ Suggested Monthly │  │ │
│                     │  └────────────┴───────────────────┘  │ │
│                     └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway                              │
│  GET /api/statement/{unit}      (NEW)                       │
│  GET /api/statement/{unit}/payments  (NEW)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Lambda Function                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ routes/statement.py (NEW)                              │ │
│  │  - handle_get_statement(unit, year)                    │ │
│  │  - handle_get_payment_history(unit, year)              │ │
│  │  - Dynamic carryover calculation (not stored)          │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ services/database.py (EXTENDED)                        │ │
│  │  - get_total_operating_budget_annual()                 │ │
│  │  - get_unit_payments_total()                           │ │
│  │  - get_unit_recent_payments()                          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      SQLite (S3)                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ unit_past_dues (UNCHANGED - seed 2025 historical debt) │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ transactions, budgets, units, categories (unchanged)   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Key Design Decision**: Carryovers are calculated dynamically from transaction data, not stored. This matches how `get_dues_status()` already works. The `unit_past_dues` table only stores historical debt predating the transaction data (2025 seed values).

---

## Constitution Alignment

| Principle | How This Feature Complies |
|-----------|--------------------------|
| **Simplicity First** | Single new API endpoint, NO schema changes, vanilla JS frontend |
| **Serverless When Dynamic** | Uses existing Lambda, no new infrastructure |
| **Password-Protected Access** | Leverages existing JWT auth, no new auth required |
| **Data Portability** | Statement data derived from existing transactions/budgets |
| **Cost Guardrails** | No new compute resources, trivial query cost |

---

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `backend/app/routes/statement.py` | Statement API endpoints with dynamic carryover calc |

### Modified Files

| File | Changes |
|------|---------|
| `backend/app/services/database.py` | Add statement query helper functions |
| `backend/app/main.py` | Add statement route handlers |
| `frontend/index.html` | Add unit selector, My Account section |
| `frontend/app.js` | Add statement fetch/render logic |
| `frontend/styles.css` | Add My Account section styles |

### NOT Modified

| File | Why |
|------|-----|
| `backend/sql/schema.sql` | No schema changes needed |
| `backend/app/routes/budgets.py` | Budget lock unchanged - remains simple flag |

---

## Implementation Phases

### Phase 1: Seed Data (Low Risk)

**Objective**: Seed 2025 historical debt (pre-transaction-data balances)

**Changes**:
1. Insert historical debt into `unit_past_dues` table:
   - Unit 101: $3,981.85
   - Unit 201: $529.00
   - Unit 203: $371.40
   - Unit 303: $625.44

**Verification**: Query `unit_past_dues WHERE year = 2025` shows seed values

---

### Phase 2: Backend - Statement Endpoint (Medium Risk)

**Objective**: Create API to return statement data with dynamic carryover calculation

**Changes**:
1. Create `routes/statement.py` with:
   - `handle_get_statement(unit, year)` - calculates carryover dynamically
   - `handle_get_payment_history(unit, year)` - full payment list
2. Add to `database.py`:
   - `get_total_operating_budget_annual(year)` - full year budget (not YTD)
   - `get_unit_payments_total(unit, year)` - sum of dues payments
   - `get_unit_recent_payments(unit, year, limit)` - payment list
3. Wire routes in `main.py`

**Carryover Logic**:
```python
carryover = prior_budgeted + prior_historical_debt - prior_paid
```
Where `prior_historical_debt` comes from `unit_past_dues` (only for 2025 seed data).

**Verification**: cURL requests return expected JSON structure

---

### Phase 3: Frontend - Unit Selector (Low Risk)

**Objective**: Add dropdown to select unit, persist in localStorage

**Changes**:
1. Add `<select id="unit-selector">` to `index.html` header area
2. Add JavaScript:
   - Populate dropdown with 9 units
   - On change, save to localStorage, trigger statement load
   - On page load, restore selection from localStorage

**Verification**: Select unit, refresh page, selection persists

---

### Phase 4: Frontend - My Account Section (Medium Risk)

**Objective**: Display statement data in new dashboard section

**Changes**:
1. Add HTML section structure to `index.html`:
   - Prior year summary card
   - Current year summary card
   - Payment guidance card
   - Recent payments table
2. Add `renderMyAccount(data)` to `app.js`
3. Add `loadStatement(unit)` to fetch from API
4. Add CSS for new section layout

**Verification**: Statement displays correctly with all fields populated

---

### Phase 5: Edge Cases & Polish (Low Risk)

**Objective**: Handle special cases and improve UX

**Changes**:
1. Handle "no prior year data" state
2. Handle "budget not locked" warning
3. Handle "paid in full" / "credit balance" states
4. December special message
5. Loading/skeleton states
6. Responsive styling for mobile

**Verification**: All edge case scenarios display appropriate messages

---

## Testing Strategy

### Unit Tests (Backend)

```python
def test_carryover_calculation():
    """Verify carryover formula: budget × ownership% + historical_debt - paid"""
    # Unit 101 with $3981.85 historical debt, paid full 2025 dues
    # should show carryover = $3981.85

def test_statement_response_structure():
    """Verify all required fields present in API response"""

def test_months_remaining_calculation():
    """January=12, December=1"""
```

### Manual Testing

1. **Happy path**: Select unit, see correct statement
2. **Carryover accuracy**: Verify Unit 101 shows $3981.85 historical debt in carryover
3. **Credit balance**: Test unit that overpaid shows credit correctly
4. **No prior data**: Unit with no 2025 transactions shows appropriate message
5. **Budget not locked**: Preliminary warning displays

---

## Deployment Plan

1. **Seed data**: Insert 2025 historical debt values
2. **Build**: `sam build`
3. **Deploy**: `sam deploy`
4. **Smoke test**: Verify API responds, frontend loads
5. **Functional test**: Test each user story

---

## Rollback Plan

If issues are discovered:

1. **Backend**: Revert to previous Lambda version via AWS Console
2. **Frontend**: Revert S3 files from previous commit
3. **Database**: Seed data can remain (no harm if feature reverted)

---

## Success Metrics

- [ ] Statement loads in < 3 seconds
- [ ] Carryover calculations include 2025 historical debt correctly
- [ ] Dynamic calculation matches what treasurer would compute manually
- [ ] No console errors in frontend
- [ ] Works on mobile viewport
