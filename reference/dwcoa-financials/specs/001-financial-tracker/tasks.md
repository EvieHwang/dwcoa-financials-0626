# Task Breakdown: DWCOA Financial Tracker

**Feature**: 001-financial-tracker
**Generated**: 2026-01-02
**Status**: Ready for Implementation

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1 | T001-T006 | Project Setup |
| Phase 2 | T007-T015 | Data Layer & Auth |
| Phase 3 | T016-T026 | US1: Upload & Categorize (P1) |
| Phase 4 | T027-T035 | US2: Dashboard (P2) |
| Phase 5 | T036-T041 | US3: Downloads & Reports (P3) |
| Phase 6 | T042-T048 | US4: Category/Budget Management (P4) |
| Phase 7 | T049-T053 | US5: Dues Tracking (P5) |
| Phase 8 | T054-T058 | Polish & Deploy |

**Total**: 58 tasks

---

## Dependency Graph

```
T001 ─┬─► T002 ─► T003 ─┬─► T004
      │                 │
      └─► T005 ─────────┘
                        │
                        ▼
      ┌─────────────────┴─────────────────┐
      │              T006                  │
      │    (SAM template complete)         │
      └─────────────────┬─────────────────┘
                        │
      ┌─────────────────┼─────────────────┐
      ▼                 ▼                 ▼
    T007              T010              T013
  (schema)          (db svc)          (auth svc)
      │                 │                 │
      ▼                 ▼                 ▼
    T008              T011              T014
   (seed)           (s3 ops)         (authorizer)
      │                 │                 │
      ▼                 ▼                 ▼
    T009              T012              T015
   (rules)          (Lambda)          (deploy)
      │                 │                 │
      └─────────────────┴─────────────────┘
                        │
                        ▼
      ┌─────────────────────────────────────┐
      │      Phase 3: US1 (T016-T026)       │
      │   Upload & Auto-Categorization      │
      └─────────────────────────────────────┘
                        │
                        ▼
      ┌─────────────────────────────────────┐
      │      Phase 4: US2 (T027-T035)       │
      │          Dashboard                   │
      └─────────────────────────────────────┘
                        │
      ┌─────────────────┴─────────────────┐
      ▼                                   ▼
   Phase 5                            Phase 6
  US3: Reports                    US4: Management
  (T036-T041)                      (T042-T048)
      │                                   │
      └─────────────────┬─────────────────┘
                        ▼
      ┌─────────────────────────────────────┐
      │      Phase 7: US5 (T049-T053)       │
      │          Dues Tracking              │
      └─────────────────────────────────────┘
                        │
                        ▼
      ┌─────────────────────────────────────┐
      │      Phase 8: Polish (T054-T058)    │
      └─────────────────────────────────────┘
```

---

## Phase 1: Project Setup

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T001 | [ ] | | Setup | Create project directory structure (`backend/`, `frontend/`, etc.) |
| T002 | [ ] | | Setup | Create `backend/requirements.txt` with dependencies |
| T003 | [ ] | | Setup | Create `backend/requirements-dev.txt` with test dependencies |
| T004 | [ ] | [P] | Setup | Create `Makefile` with build/deploy commands |
| T005 | [ ] | [P] | Setup | Create `samconfig.toml` with deployment defaults |
| T006 | [ ] | | Setup | Create `template.yaml` SAM template (Lambda, API Gateway, S3, IAM) |

### Task Details

**T001**: Create project directory structure
```
mkdir -p backend/app/{routes,services,models,utils}
mkdir -p backend/sql
mkdir -p backend/tests
mkdir -p frontend
```

**T002**: Create `backend/requirements.txt`
```
anthropic>=0.18.0
boto3>=1.34.0
pyjwt>=2.8.0
bcrypt>=4.1.0
reportlab>=4.1.0
```

**T003**: Create `backend/requirements-dev.txt`
```
pytest>=8.0.0
pytest-cov>=4.1.0
moto>=5.0.0
hypothesis>=6.98.0
```

**T006**: SAM template resources
- `DwcoaDataBucket` (S3)
- `DwcoaFrontendBucket` (S3, website hosting)
- `DwcoaApiFunction` (Lambda, Python 3.12)
- `DwcoaApi` (HTTP API)
- `DwcoaAuthorizer` (Lambda authorizer)
- `CloudFrontDistribution` (optional)
- IAM roles with least privilege

---

## Phase 2: Data Layer & Authentication

**Depends on**: Phase 1 complete

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T007 | [ ] | [P] | Data | Create `backend/sql/schema.sql` with all tables |
| T008 | [ ] | [P] | Data | Create `backend/sql/seed.sql` with initial data |
| T009 | [ ] | [P] | Data | Create `backend/sql/rules.sql` with categorization rules |
| T010 | [ ] | | Data | Implement `backend/app/services/database.py` (SQLite ops) |
| T011 | [ ] | | Data | Implement `backend/app/utils/s3.py` (S3 download/upload) |
| T012 | [ ] | | Data | Implement `backend/app/main.py` (Lambda handler, routing) |
| T013 | [ ] | [P] | Auth | Implement `backend/app/utils/auth.py` (JWT, password verify) |
| T014 | [ ] | | Auth | Implement `backend/app/routes/auth.py` (login, verify) |
| T015 | [ ] | | Deploy | First deployment: `sam build && sam deploy --guided` |

### Task Details

**T007**: Tables from `data-model.md`
- transactions, categories, budgets, units, accounts, categorize_rules, app_config
- Views: v_transaction_summary, v_budget_status, v_dues_status

**T010**: Database service functions
- `init_db()`: Create tables if not exist, run seed
- `get_connection()`: Download from S3, return connection
- `save_db()`: Upload SQLite file to S3
- Context manager for transactions

**T013**: Auth utilities
- `hash_password(password)`: bcrypt hash
- `verify_password(password, hash)`: bcrypt verify
- `create_token(role, secret)`: JWT with 24h expiry
- `verify_token(token, secret)`: Decode and validate

---

## Phase 3: US1 - Upload and Manage Transaction Data (P1)

**User Story**: The treasurer uploads a master CSV, system auto-categorizes transactions.

**Depends on**: T010-T015 complete

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T016 | [ ] | | US1 | Implement `backend/app/models/entities.py` (dataclasses) |
| T017 | [ ] | | US1 | Implement `backend/app/services/csv_processor.py` (parse CSV) |
| T018 | [ ] | | US1 | Add account number to name mapping in csv_processor |
| T019 | [ ] | | US1 | Add duplicate detection (warn only) in csv_processor |
| T020 | [ ] | | US1 | Implement rules engine in `backend/app/services/categorizer.py` |
| T021 | [ ] | | US1 | Implement Claude API fallback in categorizer.py |
| T022 | [ ] | | US1 | Add confidence scoring and needs_review flagging |
| T023 | [ ] | | US1 | Implement `backend/app/routes/transactions.py` (upload endpoint) |
| T024 | [ ] | | US1 | Add CSV download endpoint to transactions.py |
| T025 | [ ] | | US1 | Write tests: `backend/tests/test_csv_processor.py` |
| T026 | [ ] | | US1 | Write tests: `backend/tests/test_categorizer.py` |

### Task Details

**T017**: CSV processor functions
- `parse_csv(file_content)`: Parse bank CSV, return list of dicts
- `validate_columns(headers)`: Check required columns present
- `map_account(masked_number)`: Return friendly name
- `detect_duplicates(transactions)`: Return list of potential dupes

**T020**: Rules engine
- `load_rules(db)`: Get active rules sorted by priority
- `match_rule(description, rules)`: Return (category_id, confidence) or None
- Regex matching with case-insensitive option

**T021**: Claude API fallback
- `categorize_with_claude(transactions, categories)`: Batch call
- Few-shot prompt with category list and examples
- Parse JSON response for category + confidence

**T023**: Upload endpoint (`POST /transactions/upload`)
- Require admin role
- Accept multipart/form-data
- Process through csv_processor and categorizer
- Replace all transactions in database
- Return stats: total, categorized, needs_review

---

## Phase 4: US2 - View Financial Dashboard (P2)

**User Story**: Board members view password-protected dashboard with financial summary.

**Depends on**: T023-T024 complete (transactions loaded)

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T027 | [ ] | | US2 | Implement `backend/app/services/budget_calc.py` (YTD logic) |
| T028 | [ ] | | US2 | Add timing-aware YTD budget calculation |
| T029 | [ ] | | US2 | Add YTD actual calculation from transactions |
| T030 | [ ] | | US2 | Implement `backend/app/routes/dashboard.py` |
| T031 | [ ] | | US2 | Create `frontend/index.html` (login + dashboard layout) |
| T032 | [ ] | | US2 | Create `frontend/styles.css` (dashboard styling, print CSS) |
| T033 | [ ] | | US2 | Create `frontend/app.js` (API client, render logic) |
| T034 | [ ] | | US2 | Deploy frontend to S3 and configure CloudFront |
| T035 | [ ] | | US2 | Write tests: `backend/tests/test_budget_calc.py` |

### Task Details

**T027-T029**: Budget calculations
```python
def calculate_ytd_budget(annual: Decimal, timing: str, month: int) -> Decimal:
    if timing == "monthly":
        return (annual / 12) * month
    elif timing == "quarterly":
        quarters = (month - 1) // 3
        return (annual / 4) * quarters
    elif timing == "annual":
        return annual
```

**T030**: Dashboard endpoint (`GET /dashboard`)
- Query parameters: `year` (default: current)
- Return: last_updated, accounts, total_cash, income_summary, expense_summary, dues_status, review_count

**T031**: Frontend HTML structure
- Login modal (password input)
- Header with title and last_updated
- Account balances grid
- Income summary table
- Expense summary table with remaining budget
- Dues status by unit table
- Admin controls section (if authorized)

**T032**: CSS requirements
- Max-width container for readability
- Grid layout for account cards
- Responsive table styling
- `@media print` styles:
  - Hide login modal, admin controls
  - Single page layout
  - Black text on white background

---

## Phase 5: US3 - Download Reports and Data (P3)

**User Story**: Users can print, download PDF, and download CSV.

**Depends on**: T030-T034 complete (dashboard working)

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T036 | [ ] | | US3 | Verify browser print works (one page via CSS) |
| T037 | [ ] | | US3 | Implement `backend/app/services/pdf_generator.py` (ReportLab) |
| T038 | [ ] | | US3 | Create PDF layout matching dashboard design |
| T039 | [ ] | | US3 | Implement `backend/app/routes/reports.py` (PDF endpoint) |
| T040 | [ ] | | US3 | Add download buttons to frontend (PDF, CSV) |
| T041 | [ ] | | US3 | Test PDF generation with sample data |

### Task Details

**T037-T038**: PDF generation
- Use ReportLab SimpleDocTemplate
- Letter size, portrait orientation
- Match dashboard sections: accounts, income, expense, dues
- Header with title and date
- One-page constraint (adjust font sizes if needed)

**T039**: PDF endpoint (`GET /reports/pdf`)
- Query parameter: `year` (default: current)
- Return: `application/pdf` with Content-Disposition attachment
- Filename: `DWCOA_Financial_Report_{year}.pdf`

---

## Phase 6: US4 - Manage Categories and Budgets (P4)

**User Story**: Admin can manage categories, set budgets, configure timing.

**Depends on**: T030 complete (dashboard API exists)

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T042 | [ ] | | US4 | Implement `backend/app/routes/categories.py` (CRUD) |
| T043 | [ ] | | US4 | Implement `backend/app/routes/budgets.py` (CRUD) |
| T044 | [ ] | | US4 | Add copy budgets from previous year endpoint |
| T045 | [ ] | | US4 | Add retire category endpoint (set active=false) |
| T046 | [ ] | | US4 | Add admin UI for category management to frontend |
| T047 | [ ] | | US4 | Add admin UI for budget management to frontend |
| T048 | [ ] | | US4 | Test budget copy and timing override |

### Task Details

**T042**: Categories endpoints
- `GET /categories`: List all (filter by active, type)
- `POST /categories`: Create new category (admin only)
- `PATCH /categories/{id}`: Update category (admin only)

**T043-T044**: Budgets endpoints
- `GET /budgets?year=2025`: List budgets for year
- `POST /budgets`: Upsert budget (admin only)
- `POST /budgets/copy`: Copy from year X to year Y (admin only)

---

## Phase 7: US5 - Track Dues by Unit (P5)

**User Story**: Dashboard shows dues status by unit with outstanding balances.

**Depends on**: T030 complete, T023 complete (transactions with dues categories)

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T049 | [ ] | | US5 | Implement `backend/app/routes/dues.py` (dues status) |
| T050 | [ ] | | US5 | Calculate expected dues = total expense budget × ownership % |
| T051 | [ ] | | US5 | Calculate paid YTD = sum of "Dues {unit}" transactions |
| T052 | [ ] | | US5 | Calculate outstanding = expected - paid |
| T053 | [ ] | | US5 | Add dues table to dashboard frontend |

### Task Details

**T049-T052**: Dues endpoint (`GET /dues`)
- Query parameter: `year` (default: current)
- For each unit:
  - Get ownership percentage from units table
  - Calculate expected: `SUM(expense budgets) × ownership_pct`
  - Calculate paid: `SUM(credits WHERE category = 'Dues {unit}')`
  - Calculate outstanding: `expected - paid`
- Return array sorted by unit number

---

## Phase 8: Polish & Deploy

**Depends on**: All previous phases complete

| Task | Status | Parallel | Story | Description |
|------|--------|----------|-------|-------------|
| T054 | [ ] | | Polish | Implement review queue in frontend (list needs_review transactions) |
| T055 | [ ] | | Polish | Add loading states and error handling to frontend |
| T056 | [ ] | | Polish | Run full end-to-end test with production data |
| T057 | [ ] | | Polish | Verify all acceptance scenarios from spec.md |
| T058 | [ ] | | Polish | Final deployment and smoke test |

### Task Details

**T054**: Review queue
- Show transactions where needs_review = true
- Allow selecting category from dropdown
- Save updates category, clears needs_review flag

**T056**: End-to-end test
1. Upload `data/dwcoa-financials-data.csv`
2. Verify auto-categorization results
3. Check dashboard totals match expectations
4. Print page and verify one-page layout
5. Download PDF and CSV
6. Test admin functions (add category, update budget)

**T057**: Acceptance scenarios checklist
- [ ] US1-1: Upload replaces all transactions
- [ ] US1-2: Existing categories preserved
- [ ] US1-3: Auto-categorization runs
- [ ] US1-4: Low confidence flagged
- [ ] US1-5: Manual corrections saved
- [ ] US1-6: Download includes app columns
- [ ] US2-1: Board password shows dashboard
- [ ] US2-2: Admin password shows admin controls
- [ ] US2-3: Last updated timestamp displayed
- [ ] US2-4: Quarterly timing calculates correctly
- [ ] US2-5: Remaining budget shows correctly
- [ ] US2-6: Transfers excluded from budget
- [ ] US3-1: Print fits one page
- [ ] US3-2: PDF download works
- [ ] US3-3: CSV download works
- [ ] US3-4: Round-trip upload/download works
- [ ] US4-1: Copy budgets from previous year
- [ ] US4-2: Quarterly timing calculates correctly (August = Q1+Q2)
- [ ] US4-3: Monthly timing calculates correctly (August = 7 months)
- [ ] US4-4: Annual timing shows full amount
- [ ] US4-5: Retired categories hidden from new entries
- [ ] US5-1: Unit dues shows expected/paid/outstanding
- [ ] US5-2: Outstanding reflects all-time balance
- [ ] US5-3: Payment reduces outstanding
- [ ] US5-4: Budget changes update expected dues

---

## Execution Notes

### Parallelizable Tasks

Tasks marked `[P]` can be worked on simultaneously with other tasks in the same phase:
- T004, T005 (after T003)
- T007, T008, T009 (after T006)
- T013 (parallel with T010-T012)

### Critical Path

The critical path determines minimum implementation time:

```
T001 → T002 → T006 → T010 → T012 → T015 → T017 → T023 → T030 → T034
```

Completing this path gives a working MVP (upload + dashboard).

### Testing Strategy

- Unit tests: T025, T026, T035
- Integration: T056
- Acceptance: T057
- Each phase should have tests passing before moving to next

### Rollback Points

Safe points to stop and have a working system:
- After T015: Auth + empty database
- After T026: Upload + categorization working
- After T035: Full dashboard working
- After T041: Reports working
- After T058: Complete system

---

## File Checklist

### Backend Files to Create

- [ ] `backend/__init__.py`
- [ ] `backend/requirements.txt`
- [ ] `backend/requirements-dev.txt`
- [ ] `backend/app/__init__.py`
- [ ] `backend/app/main.py`
- [ ] `backend/app/routes/__init__.py`
- [ ] `backend/app/routes/auth.py`
- [ ] `backend/app/routes/dashboard.py`
- [ ] `backend/app/routes/transactions.py`
- [ ] `backend/app/routes/categories.py`
- [ ] `backend/app/routes/budgets.py`
- [ ] `backend/app/routes/dues.py`
- [ ] `backend/app/routes/reports.py`
- [ ] `backend/app/services/__init__.py`
- [ ] `backend/app/services/database.py`
- [ ] `backend/app/services/categorizer.py`
- [ ] `backend/app/services/csv_processor.py`
- [ ] `backend/app/services/budget_calc.py`
- [ ] `backend/app/services/pdf_generator.py`
- [ ] `backend/app/models/__init__.py`
- [ ] `backend/app/models/entities.py`
- [ ] `backend/app/utils/__init__.py`
- [ ] `backend/app/utils/auth.py`
- [ ] `backend/app/utils/s3.py`
- [ ] `backend/sql/schema.sql`
- [ ] `backend/sql/seed.sql`
- [ ] `backend/sql/rules.sql`
- [ ] `backend/tests/__init__.py`
- [ ] `backend/tests/test_csv_processor.py`
- [ ] `backend/tests/test_categorizer.py`
- [ ] `backend/tests/test_budget_calc.py`

### Frontend Files to Create

- [ ] `frontend/index.html`
- [ ] `frontend/app.js`
- [ ] `frontend/styles.css`

### Infrastructure Files to Create

- [ ] `template.yaml`
- [ ] `samconfig.toml`
- [ ] `Makefile`
