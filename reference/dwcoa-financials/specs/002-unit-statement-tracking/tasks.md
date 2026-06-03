# Tasks: Unit Statement Tracking

**Feature**: Unit Statement Tracking ("My Account" Section)
**Branch**: `feature/002-unit-statement-tracking`
**Generated**: 2026-01-21
**Updated**: 2026-01-21 - Simplified (carryovers calculated dynamically, no schema changes)

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Seed Data | 1 | Complete |
| Phase 2: Backend Statement API | 6 | Complete |
| Phase 3: Frontend UI | 6 | Complete |
| Phase 4: Integration & Polish | 4 | Complete |
| **Total** | **17** | **Complete** |

---

## Phase 1: Seed Data

**Objective**: Seed 2025 historical debt (pre-transaction-data balances)

- [x] T001 [US2] Seed 2025 historical debt into `unit_past_dues` table:
  - Unit 101: $3,981.85
  - Unit 201: $529.00
  - Unit 203: $371.40
  - Unit 303: $625.44
  - (Units with $0 don't need entries - defaults to 0)

**Dependencies**: None (foundational)

**Note**: This is historical debt predating the transaction data. Future carryovers are calculated dynamically from transactions - no need to store them.

---

## Phase 2: Backend Statement API

**Objective**: Create API endpoints to return statement data with dynamic carryover calculation

### Database Layer

- [x] T002 [US1] Add `get_total_operating_budget_annual(year)` function to `backend/app/services/database.py` - returns full annual operating budget (not YTD)
- [x] T003 [P] [US3] Add `get_unit_payments_total(unit_number, year)` function to `database.py` - sum of dues payments for unit in year
- [x] T004 [P] [US5] Add `get_unit_recent_payments(unit_number, year, limit=10)` function to `database.py` - list of recent payment transactions

### Route Handler

- [x] T005 [US1] Create new file `backend/app/routes/statement.py` with `handle_get_statement(unit, year)` function:
  - Calculate carryover dynamically: `prior_budgeted + prior_historical_debt - prior_paid`
  - Calculate current year totals: `carryover + annual_dues - paid_ytd`
  - Calculate payment guidance: `remaining / months_remaining`
  - Return complete statement response structure
- [x] T006 [US5] Add `handle_get_payment_history(unit, year)` function to `statement.py` for full payment history endpoint

### Router Integration

- [x] T007 [US1] Add statement routes to `backend/app/main.py`:
  - `GET /api/statement/{unit}` → `statement.handle_get_statement`
  - `GET /api/statement/{unit}/payments` → `statement.handle_get_payment_history`

**Dependencies**: T001 should complete before T005 for accurate testing

---

## Phase 3: Frontend UI

**Objective**: Add unit selector and My Account section to dashboard

### Unit Selector

- [x] T008 [US1] Add unit selector dropdown HTML to `frontend/index.html` in the header/controls area, with all 9 unit options
- [x] T009 [US1] Add unit selector JavaScript to `frontend/app.js`:
  - Populate dropdown
  - Save selection to `localStorage.setItem('selectedUnit', ...)`
  - Restore selection on page load
  - Trigger statement load on change

### My Account Section Structure

- [x] T010 [US1] Add "My Account" section HTML to `frontend/index.html` below Income & Dues section with:
  - Section container with id `my-account-section`
  - Prior year summary card placeholder
  - Current year summary card placeholder
  - Payment guidance card placeholder
  - Recent payments table placeholder

### Statement Rendering

- [x] T011 [US2][US3] Add `renderMyAccount(data)` function to `app.js` to populate:
  - Prior year: annual dues budgeted, total paid, balance carried forward
  - Current year: carryover, annual dues, total due, paid YTD, remaining balance
  - Payment guidance: standard monthly, suggested monthly, months remaining
  - Recent payments table

- [x] T012 [US1] Add `loadStatement(unit)` function to `app.js` to fetch from `/api/statement/{unit}` and call `renderMyAccount()`

### Styling

- [x] T013 [P] [US1] Add My Account section CSS to `frontend/styles.css`:
  - Card layout matching existing dashboard style
  - Highlight colors for key numbers (remaining balance, suggested monthly)
  - Color coding: green for paid/credit, amber for on-track, red for behind
  - Responsive styles for mobile

**Dependencies**: T007 must complete before T012 can be tested

---

## Phase 4: Integration & Polish

**Objective**: Handle edge cases and finalize the feature

- [x] T014 [US2] Add handling for "no prior year data" state - display "No data available for [year]" message in prior year section
- [x] T015 [US3] Add handling for unlocked budget state - display "Budget for [year] is pending approval. Amounts shown are preliminary." notice
- [x] T016 [US4] Add edge case handling in payment guidance:
  - If `remaining_balance <= 0`: show "Paid in full" or "Credit balance: $X"
  - If December: show "Remaining balance: $X due by Dec 31"
  - Credit display format: "($150.00) credit"
- [x] T017 [US5] Add "View full payment history" link/button that calls `/api/statement/{unit}/payments` and displays in modal or expanded section

**Dependencies**: T011 must complete before T014-T017

---

## Dependency Graph

```
T001 ─────────────────────┐
                          │
T002 ─┬─► T003 ───────────┼─► T005 ─► T007 ─► T012
      │                   │
      └─► T004 ───────────┘

T008 ─► T009 ─► T010 ─► T011 ─► T013
                          │
                          └─► T014 ─► T015 ─► T016 ─► T017
```

**Parallel Work Streams**:
- Stream A: Backend API (T001-T007)
- Stream B: Frontend UI (T008-T013) - can start in parallel with backend

---

## User Story Coverage

| User Story | Tasks | Priority |
|------------|-------|----------|
| US1: Select Unit and View Statement | T002-T013 | P1 |
| US2: View Last Year Summary | T001, T005, T011, T014 | P2 |
| US3: View Current Year Summary | T003, T005, T011, T015 | P1 |
| US4: View Payment Guidance | T005, T011, T016 | P2 |
| US5: View Recent Payments | T004, T006, T011, T017 | P3 |

**Note**: US6 (Automatic Carryover on Budget Lock) has been **removed** - carryovers are calculated dynamically, matching existing system behavior.

---

## Verification Checklist

After all tasks complete:

- [ ] Unit selector dropdown shows all 9 units
- [ ] Selected unit persists across page refresh (localStorage)
- [ ] Statement loads within 3 seconds
- [ ] Prior year shows: budgeted, paid, carryover (calculated dynamically)
- [ ] Current year shows: total due, paid YTD, remaining
- [ ] Payment guidance shows suggested monthly
- [ ] Recent payments table displays
- [ ] 2025 historical debt reflected in calculations
- [ ] Credit balances display correctly
- [ ] "No data" states display appropriate messages
- [ ] Responsive on mobile viewport

---

## What Changed (Simplification)

**Removed**:
- Schema changes (`auto_calculated` column) - not needed
- Carryover-on-lock feature (T010-T012) - redundant
- US6 user story - doesn't apply

**Why**: The existing system already calculates dues dynamically. Carryovers can be computed the same way - no need to store them or trigger on budget lock. Budget lock remains a simple flag to prevent accidental edits.

**Task count**: 22 → 17
