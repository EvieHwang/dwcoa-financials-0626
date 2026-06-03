# Feature: Unit Statement Tracking ("My Account" Section)

## Overview

Add a "My Account" section to the dashboard that provides homeowners with visibility into their annual dues obligation, payment progress, and recommended monthly payment. This enables homeowners to self-manage their payment schedules without requiring treasurer intervention.

## User Stories

1. **As a homeowner**, I want to select my unit and see my personalized financial statement so I can understand my total obligation for the year.

2. **As a homeowner**, I want to see what I paid last year, what I was budgeted to pay, and any balance that carried over so I understand how my current balance was calculated.

3. **As a homeowner**, I want to see my remaining balance and a recommended monthly payment so I can ensure I pay my full dues by year-end.

4. **As a homeowner**, I want to see my recent payments so I can verify my checks have been received and processed.

5. **As a treasurer**, I want carryover balances to calculate automatically when I lock a new year's budget so I don't have to manually calculate and enter past due amounts.

6. **As a treasurer**, I want visibility into all units' statement views so I can help homeowners who have questions.

---

## Functional Requirements

### FR-1: Unit Selection

- **FR-1.1**: Add a unit selector dropdown to the dashboard, visible to both homeowner and admin roles
- **FR-1.2**: Dropdown displays all 9 units (101, 102, 103, 201, 202, 203, 301, 302, 303)
- **FR-1.3**: Selection persists in browser session (localStorage)
- **FR-1.4**: Default to no selection; prompt user to "Select your unit to view your statement"

### FR-2: My Account Section

- **FR-2.1**: Display as a new section in the existing dashboard (below current content, no new tabs)
- **FR-2.2**: Section only visible when a unit is selected
- **FR-2.3**: Section displays for both homeowner and admin roles

### FR-3: Last Year Summary

Display the following for the prior fiscal year:

| Field | Calculation |
|-------|-------------|
| Annual dues budgeted | Prior year's operating budget × unit ownership % |
| Total payments made | Sum of all payments to unit's Dues category in prior year |
| Balance carried forward | Budgeted − Paid (positive = past due, negative = credit) |

- **FR-3.1**: If prior year budget was never created, display "No data available for [year]"
- **FR-3.2**: Negative balance (credit) should display clearly as a credit, e.g., "($150.00) credit"

### FR-4: Current Year Summary

Display the following for the current fiscal year:

| Field | Calculation |
|-------|-------------|
| Carryover balance | Balance carried forward from prior year |
| Annual dues | Current year's operating budget × unit ownership % |
| **Total due for year** | Carryover + Annual dues |
| Payments made YTD | Sum of payments to unit's Dues category in current year |
| **Remaining balance** | Total due − Payments YTD |

- **FR-4.1**: If current year budget is not yet locked, display notice: "Budget for [year] is pending approval. Amounts shown are preliminary."
- **FR-4.2**: Credits (negative carryover) reduce total due for year
- **FR-4.3**: Remaining balance can be negative (credit balance)

### FR-5: Payment Guidance

| Field | Calculation |
|-------|-------------|
| Standard monthly payment | Annual dues ÷ 12 |
| Months remaining | 12 − current month + 1 (Jan=12, Feb=11, ... Dec=1) |
| Suggested monthly payment | Remaining balance ÷ Months remaining |

- **FR-5.1**: If remaining balance ≤ 0, display "Paid in full" or "Credit balance" instead of suggested payment
- **FR-5.2**: If in December with remaining balance, suggest "Remaining balance: $X due by Dec 31"
- **FR-5.3**: Round suggested monthly to nearest cent

### FR-6: Payment History

- **FR-6.1**: Display recent payments (last 5-10) for the selected unit in current year
- **FR-6.2**: Show: Date, Amount
- **FR-6.3**: Include link/button to view full payment history (all payments for unit)
- **FR-6.4**: Full history should show both current and prior year payments

### FR-7: Automatic Carryover Calculation

- **FR-7.1**: When a budget is locked for a new year, automatically calculate carryover balances for all units
- **FR-7.2**: Carryover = Prior year (Budget + Past Due − Paid YTD)
- **FR-7.3**: Store calculated carryover in `unit_past_dues` table for the new year
- **FR-7.4**: If `unit_past_dues` already has a manually-entered value for a unit/year, do not overwrite (manual override takes precedence)
- **FR-7.5**: Provide admin visibility into auto-calculated vs manually-set past dues

---

## Technical Requirements

### TR-1: Backend API

- **TR-1.1**: New endpoint `GET /api/statement/{unit}?year={year}` returning:
  ```json
  {
    "unit": "201",
    "ownership_pct": 10.4,
    "current_year": {
      "year": 2026,
      "budget_locked": true,
      "carryover_balance": 160.00,
      "annual_dues": 4104.00,
      "total_due": 4264.00,
      "paid_ytd": 700.00,
      "remaining_balance": 3564.00,
      "standard_monthly": 342.00,
      "months_remaining": 10,
      "suggested_monthly": 356.40
    },
    "prior_year": {
      "year": 2025,
      "annual_dues_budgeted": 3960.00,
      "total_paid": 3800.00,
      "balance_carried_forward": 160.00
    },
    "recent_payments": [
      {"date": "2026-02-03", "amount": 350.00},
      {"date": "2026-01-05", "amount": 350.00}
    ]
  }
  ```

- **TR-1.2**: New endpoint `GET /api/statement/{unit}/payments?year={year}` for full payment history

- **TR-1.3**: Modify `POST /api/budgets/lock/{year}` to trigger carryover calculation when locking

### TR-2: Frontend

- **TR-2.1**: Add unit selector component to dashboard header or top of page
- **TR-2.2**: Add "My Account" section component with all display fields
- **TR-2.3**: Store selected unit in localStorage key `selectedUnit`
- **TR-2.4**: Section should update when unit selection changes (no page reload)

### TR-3: Data Model

- **TR-3.1**: Add column `auto_calculated` (boolean) to `unit_past_dues` table to distinguish auto vs manual entries
- **TR-3.2**: Consider adding `carryover_source_year` for audit trail (optional)

---

## UI/UX Requirements

### UX-1: Visual Design

- **UX-1.1**: Match existing dashboard styling (cards, tables, colors)
- **UX-1.2**: Use clear visual hierarchy: section headers, subsection groupings
- **UX-1.3**: Highlight key numbers: Total Due, Remaining Balance, Suggested Monthly
- **UX-1.4**: Use color coding: green for paid/credit, amber for on-track, red for behind

### UX-2: Responsive Behavior

- **UX-2.1**: Section should be readable on mobile devices
- **UX-2.2**: Payment history should scroll if many entries

### UX-3: Empty/Loading States

- **UX-3.1**: Show skeleton loader while fetching statement data
- **UX-3.2**: Clear messaging when no unit selected
- **UX-3.3**: Clear messaging when prior year has no data

---

## Edge Cases & Business Rules

1. **New unit/owner mid-year**: Past due can be manually set to prorate their obligation
2. **Budget unlocked after carryover calculated**: Display warning that amounts may change
3. **Year boundary in January**: "Last year" shows previous calendar year, "This year" shows current
4. **No payments yet**: Payment history shows "No payments recorded for [year]"
5. **Exactly on track**: Suggested monthly equals standard monthly; consider displaying "You're on track!" message

---

## Acceptance Criteria

- [ ] Homeowner can select their unit from a dropdown
- [ ] Selected unit persists across browser sessions
- [ ] My Account section displays last year's summary (budgeted, paid, carryover)
- [ ] My Account section displays current year's summary (total due, paid YTD, remaining)
- [ ] Payment guidance shows standard monthly and suggested catch-up monthly
- [ ] Recent payments display with dates and amounts
- [ ] Full payment history is accessible
- [ ] When admin locks a new year's budget, carryover balances auto-calculate
- [ ] Auto-calculated carryovers do not overwrite manual entries
- [ ] Section displays appropriately for both admin and homeowner roles
- [ ] Pending budget status clearly indicated when budget is not locked

---

## Future Considerations (Out of Scope)

- Email notification when statement is ready (budget locked)
- PDF export of individual unit statement
- Payment reminders / alerts when falling behind
- Individual unit login credentials
