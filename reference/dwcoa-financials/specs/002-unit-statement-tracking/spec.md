# Feature Specification: Unit Statement Tracking ("My Account" Section)

**Feature Branch**: `feature/002-unit-statement-tracking`
**Created**: 2026-01-21
**Status**: Ready for Planning
**Input**: Requirements document `docs/statement-tracking-requirements.md`

## Overview

Add a "My Account" section to the dashboard that provides homeowners with visibility into their annual dues obligation, payment progress, and recommended monthly payment. This enables homeowners to self-manage their payment schedules without requiring treasurer intervention.

Key insight: Homeowners want to understand their financial obligations at a glance - what they owe, what they've paid, and what they need to pay each month to stay current. The treasurer wants carryover balances to calculate automatically when locking a new year's budget.

---

## User Scenarios & Testing

### User Story 1 - Select Unit and View Statement (Priority: P1)

A homeowner visits the dashboard and selects their unit from a dropdown. The page displays their personalized financial statement showing last year's summary, current year's dues, payments made, and remaining balance.

**Why this priority**: This is the core value - homeowners can self-serve their financial status without contacting the treasurer.

**Independent Test**: Select unit 201 from dropdown; see personalized statement with correct ownership percentage (10.4%), calculated dues, and payment history.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** user selects unit 201, **Then** the My Account section displays with that unit's financial data
2. **Given** a unit was previously selected, **When** user returns to the dashboard later, **Then** the same unit is pre-selected (persisted in localStorage)
3. **Given** no unit is selected, **When** viewing dashboard, **Then** display prompt "Select your unit to view your statement"
4. **Given** user is admin role, **When** selecting different units, **Then** can view any unit's statement (for support purposes)

---

### User Story 2 - View Last Year Summary (Priority: P2)

A homeowner sees their prior year's financial summary: what they were budgeted to pay, what they actually paid, and any balance (positive or negative) that carried forward to the current year.

**Why this priority**: Understanding the carryover balance is essential for homeowners to trust their current year's total.

**Independent Test**: For a unit that underpaid by $160 last year, statement shows: Annual dues budgeted $3,960, Total paid $3,800, Balance carried forward $160.

**Acceptance Scenarios**:

1. **Given** Unit 201 had $3,960 budgeted and paid $3,800 in 2025, **When** viewing 2026 statement, **Then** shows $160 carried forward
2. **Given** Unit 102 overpaid by $150 in 2025, **When** viewing statement, **Then** shows "($150.00) credit" carried forward
3. **Given** no budget existed for prior year, **When** viewing statement, **Then** shows "No data available for [year]"

---

### User Story 3 - View Current Year Summary (Priority: P1)

A homeowner sees their current year's total obligation: carryover balance plus annual dues, minus payments made, equals remaining balance.

**Why this priority**: This answers the fundamental question "How much do I owe?"

**Independent Test**: Unit with $160 carryover + $4,104 annual dues - $700 paid = $3,564 remaining balance displayed.

**Acceptance Scenarios**:

1. **Given** carryover of $160 and annual dues of $4,104, **When** viewing current year, **Then** total due shows $4,264
2. **Given** total due of $4,264 and $700 paid YTD, **When** viewing, **Then** remaining balance shows $3,564
3. **Given** budget is not yet locked, **When** viewing statement, **Then** displays notice "Budget for [year] is pending approval. Amounts shown are preliminary."
4. **Given** a credit carryover of -$150, **When** calculating total due, **Then** credit reduces total (e.g., $4,104 - $150 = $3,954 total due)

---

### User Story 4 - View Payment Guidance (Priority: P2)

A homeowner sees the standard monthly payment (annual dues / 12) and a suggested monthly payment (remaining balance / months remaining) to help them budget.

**Why this priority**: Proactive guidance helps homeowners stay current without treasurer reminders.

**Independent Test**: In March with $3,564 remaining and 10 months left, suggested payment shows $356.40/month.

**Acceptance Scenarios**:

1. **Given** annual dues of $4,104, **When** viewing guidance, **Then** standard monthly shows $342.00
2. **Given** remaining balance of $3,564 and 10 months remaining, **When** viewing guidance, **Then** suggested monthly shows $356.40
3. **Given** remaining balance is $0 or negative, **When** viewing guidance, **Then** shows "Paid in full" or "Credit balance" instead
4. **Given** it's December with $500 remaining, **When** viewing guidance, **Then** shows "Remaining balance: $500 due by Dec 31"

---

### User Story 5 - View Recent Payments (Priority: P3)

A homeowner sees their recent payments to verify checks have been received and processed correctly.

**Why this priority**: Provides confirmation that payments were recorded, reducing support questions.

**Independent Test**: Unit 201 sees last 5 payments with dates and amounts; can click to see full history.

**Acceptance Scenarios**:

1. **Given** Unit 201 made payments on Jan 5 and Feb 3, **When** viewing recent payments, **Then** both payments display with dates and amounts
2. **Given** no payments recorded for current year, **When** viewing, **Then** shows "No payments recorded for [year]"
3. **Given** user clicks "View full history", **When** clicked, **Then** shows all payments for current and prior year

---

### Edge Cases

- **New unit/owner mid-year**: Historical debt can be manually set in unit_past_dues to reflect prorated obligation
- **Year boundary in January**: Last year = previous calendar year, This year = current calendar year
- **Exactly on track**: When suggested monthly equals standard monthly, display encouraging message
- **All units paid in full**: Payment guidance section still renders but shows positive status

---

## Requirements

### Functional Requirements

**Unit Selection**

- **FR-001**: System MUST provide a unit selector dropdown visible to both homeowner and admin roles
- **FR-002**: Dropdown MUST display all 9 units: 101, 102, 103, 201, 202, 203, 301, 302, 303
- **FR-003**: Selected unit MUST persist in browser localStorage across sessions
- **FR-004**: When no unit selected, MUST display prompt "Select your unit to view your statement"

**My Account Section Display**

- **FR-005**: My Account section MUST display as a new section in existing dashboard (no separate page/tab)
- **FR-006**: Section MUST only be visible when a unit is selected
- **FR-007**: Section MUST be visible to both homeowner and admin roles
- **FR-008**: Section MUST update dynamically when unit selection changes (no page reload)

**Last Year Summary**

- **FR-009**: MUST display prior year's annual dues budgeted (operating budget × unit ownership %)
- **FR-010**: MUST display prior year's total payments made (sum of Dues category transactions)
- **FR-011**: MUST display balance carried forward (budgeted - paid; positive = past due, negative = credit)
- **FR-012**: If prior year budget never existed, MUST display "No data available for [year]"
- **FR-013**: Negative balance (credit) MUST display clearly, e.g., "($150.00) credit"

**Current Year Summary**

- **FR-014**: MUST display carryover balance from prior year
- **FR-015**: MUST display current year annual dues (operating budget × unit ownership %)
- **FR-016**: MUST display total due for year (carryover + annual dues)
- **FR-017**: MUST display payments made YTD (sum of current year Dues transactions)
- **FR-018**: MUST display remaining balance (total due - payments YTD)
- **FR-019**: If current year budget not locked, MUST display notice about preliminary amounts
- **FR-020**: Credits (negative carryover) MUST reduce total due

**Payment Guidance**

- **FR-021**: MUST display standard monthly payment (annual dues ÷ 12)
- **FR-022**: MUST calculate months remaining (12 - current month + 1)
- **FR-023**: MUST display suggested monthly payment (remaining balance ÷ months remaining)
- **FR-024**: If remaining balance ≤ 0, MUST display "Paid in full" or "Credit balance"
- **FR-025**: In December with remaining balance, MUST display "Remaining balance: $X due by Dec 31"
- **FR-026**: Suggested monthly MUST be rounded to nearest cent

**Payment History**

- **FR-027**: MUST display recent payments (last 5-10) for selected unit in current year
- **FR-028**: Each payment MUST show date and amount
- **FR-029**: MUST provide way to view full payment history (current and prior year)
- **FR-030**: If no payments, MUST display "No payments recorded for [year]"

**Carryover Calculation**

- **FR-031**: Carryover MUST be calculated dynamically: Prior year (Budgeted + Historical Debt - Paid)
- **FR-032**: Historical debt (pre-transaction-data balances) stored in existing `unit_past_dues` table
- **FR-033**: No schema changes required - existing table structure is sufficient

---

### Key Entities

**Statement Response** (new API response structure)
- unit (string: unit number)
- ownership_pct (decimal: ownership percentage)
- current_year (object: year, budget_locked, carryover_balance, annual_dues, total_due, paid_ytd, remaining_balance, standard_monthly, months_remaining, suggested_monthly)
- prior_year (object: year, annual_dues_budgeted, total_paid, balance_carried_forward)
- recent_payments (array: date, amount)

**Unit Past Dues** (existing table, NO changes needed)
- id (integer, primary key)
- unit_number (string, foreign key to units)
- year (integer)
- past_due_balance (decimal) - stores historical debt predating transaction data only

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Homeowner can view their statement within 3 seconds of selecting their unit
- **SC-002**: Carryover calculations match manual verification for all 9 units
- **SC-003**: Selected unit persists across browser sessions via localStorage
- **SC-004**: Payment guidance correctly handles edge cases (paid in full, December, credits)
- **SC-005**: Auto-carryover on budget lock completes for all units without errors
- **SC-006**: Admin can distinguish auto-calculated vs manually-set past dues

---

## Assumptions

- Dues payments are identified by the existing "Dues" category (generic) mapped to specific units
- Unit ownership percentages are already stored in the units table
- The budget lock mechanism already exists and functions correctly
- Prior year budget data is available for carryover calculation
- Browser localStorage is available and not blocked

---

## Out of Scope (Future Considerations)

- Email notification when statement is ready (budget locked)
- PDF export of individual unit statement
- Payment reminders / alerts when falling behind
- Individual unit login credentials (currently shared passwords)
- Online payment integration

---

## Dependencies

- Existing budget locking mechanism (already implemented)
- Existing unit_past_dues table (already exists, needs column addition)
- Existing dues calculation logic in /api/dues endpoint
- Dashboard rendering framework (vanilla JS, Chart.js, Tabulator)
