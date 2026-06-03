# Requirements Checklist: Unit Statement Tracking

## User Stories

- [ ] US-1: Select Unit and View Statement
- [ ] US-2: View Last Year Summary
- [ ] US-3: View Current Year Summary
- [ ] US-4: View Payment Guidance
- [ ] US-5: View Recent Payments
- [ ] US-6: Automatic Carryover on Budget Lock

## Functional Requirements

### Unit Selection
- [ ] FR-001: Unit selector dropdown for both roles
- [ ] FR-002: All 9 units displayed
- [ ] FR-003: Selection persists in localStorage
- [ ] FR-004: Prompt when no unit selected

### My Account Section Display
- [ ] FR-005: New dashboard section (not separate page)
- [ ] FR-006: Only visible when unit selected
- [ ] FR-007: Visible to homeowner and admin
- [ ] FR-008: Dynamic update on selection change

### Last Year Summary
- [ ] FR-009: Prior year dues budgeted displayed
- [ ] FR-010: Prior year payments total displayed
- [ ] FR-011: Balance carried forward displayed
- [ ] FR-012: "No data available" for missing prior year
- [ ] FR-013: Credit displayed as "($X.XX) credit"

### Current Year Summary
- [ ] FR-014: Carryover balance displayed
- [ ] FR-015: Current year annual dues displayed
- [ ] FR-016: Total due for year calculated
- [ ] FR-017: Payments made YTD displayed
- [ ] FR-018: Remaining balance calculated
- [ ] FR-019: Preliminary notice if budget not locked
- [ ] FR-020: Credits reduce total due

### Payment Guidance
- [ ] FR-021: Standard monthly payment displayed
- [ ] FR-022: Months remaining calculated correctly
- [ ] FR-023: Suggested monthly payment displayed
- [ ] FR-024: "Paid in full" for zero/negative balance
- [ ] FR-025: December message for remaining balance
- [ ] FR-026: Rounded to nearest cent

### Payment History
- [ ] FR-027: Recent payments displayed (5-10)
- [ ] FR-028: Date and amount shown
- [ ] FR-029: Full history accessible
- [ ] FR-030: "No payments recorded" message

### Automatic Carryover Calculation
- [ ] FR-031: Auto-calculate on budget lock
- [ ] FR-032: Correct carryover formula
- [ ] FR-033: Store in unit_past_dues
- [ ] FR-034: Don't overwrite manual entries
- [ ] FR-035: Track auto vs manual source

## Success Criteria

- [ ] SC-001: Statement loads within 3 seconds
- [ ] SC-002: Carryover matches manual verification
- [ ] SC-003: Selection persists across sessions
- [ ] SC-004: Edge cases handled correctly
- [ ] SC-005: Auto-carryover completes without errors
- [ ] SC-006: Admin can distinguish auto vs manual
