# Quickstart: Unit Statement Tracking

## Prerequisites

- Python 3.12+
- Node.js (for local testing if needed)
- AWS SAM CLI
- Access to AWS account with deployed DWCOA stack

## Local Development Setup

1. **Clone and checkout feature branch**:
   ```bash
   git checkout feature/002-unit-statement-tracking
   ```

2. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

## Implementation Order

Follow this sequence to build the feature incrementally:

### Phase 1: Seed Data
1. Insert 2025 historical debt into `unit_past_dues` table
2. No schema changes required

### Phase 2: Backend API
1. Create `backend/app/routes/statement.py` with:
   - `handle_get_statement(unit, year)` - main statement endpoint (dynamic carryover calc)
   - `handle_get_payment_history(unit, year)` - full history endpoint
2. Add helper functions to `database.py`:
   - `get_total_operating_budget_annual(year)`
   - `get_unit_payments_total(unit, year)`
   - `get_unit_recent_payments(unit, year, limit)`
3. Wire up routes in `main.py`

### Phase 3: Frontend
1. Add unit selector dropdown to `index.html`
2. Add My Account section HTML structure
3. Add JavaScript in `app.js`:
   - `loadStatement(unit)` - fetch and render
   - `renderMyAccount(data)` - display logic
   - localStorage handling for unit persistence
4. Add CSS styles for new section

### Phase 4: Testing & Deployment
1. Manual testing with real data
2. Verify carryover calculations match manual verification
3. Deploy with `sam build && sam deploy`

## Key Files to Modify

| File | Changes |
|------|---------|
| `backend/app/routes/statement.py` | **NEW** - statement endpoints with dynamic carryover |
| `backend/app/services/database.py` | Add statement query functions |
| `backend/app/main.py` | Add statement routes |
| `frontend/index.html` | Add unit selector, My Account section |
| `frontend/app.js` | Add statement fetching/rendering |
| `frontend/styles.css` | Add My Account styles |

**NOT modified**: `schema.sql`, `budgets.py` - no schema changes, budget lock unchanged

## Testing Checklist

- [ ] Select unit from dropdown, see statement populated
- [ ] Refresh page, selected unit persists
- [ ] Prior year shows correct budgeted vs paid
- [ ] Current year shows correct total due and remaining
- [ ] Payment guidance shows reasonable monthly amount
- [ ] Recent payments list appears with dates/amounts
- [ ] 2025 historical debt (seed data) reflected in calculations
- [ ] Credit balances display correctly (negative amounts)

## API Testing

```bash
# Get statement for unit 201
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-api.com/api/statement/201"

# Get full payment history
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-api.com/api/statement/201/payments?year=2026"
```

## Troubleshooting

**Statement shows $0 annual dues**:
- Check if current year budget exists
- Verify budget is not empty (run `/api/budgets?year=2026`)

**Carryover not showing 2025 historical debt**:
- Check `unit_past_dues` table has 2025 seed data
- Query: `SELECT * FROM unit_past_dues WHERE year = 2025`

**Unit selector not persisting**:
- Check browser localStorage is enabled
- Look for `selectedUnit` key in browser dev tools

**Payment history empty but payments exist**:
- Verify transactions are categorized as "Dues {unit}" (e.g., "Dues 201")
- Check category name matches exactly
