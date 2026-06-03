# Implementation Plan: DWCOA Financial Tracker

**Feature**: 001-financial-tracker
**Date**: 2026-01-02
**Status**: Ready for Implementation

---

## Technical Context

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| Language | Python 3.12 | Constitution requirement |
| Framework | None (raw Lambda) | Simplicity first |
| Data Storage | SQLite in S3 | File-based, portable, queryable |
| API | AWS API Gateway HTTP API | Simple, cheap, Lambda integration |
| Frontend | Vanilla JS + HTML | No build step, print-friendly |
| Hosting | S3 + CloudFront | Static, cheap, HTTPS |
| AI | Claude API (Haiku) | Cost-effective categorization |
| PDF | ReportLab | Lightweight, Lambda-compatible |
| IaC | AWS SAM | Simple deployment |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CloudFront                               │
│                    (HTTPS, caching)                              │
└─────────────────┬────────────────────┬──────────────────────────┘
                  │                    │
                  ▼                    ▼
┌─────────────────────────┐  ┌─────────────────────────────────────┐
│     S3 (Frontend)       │  │         API Gateway                 │
│  - index.html           │  │  - /api/* routes                    │
│  - app.js               │  │  - Lambda authorizer                │
│  - styles.css           │  └───────────────┬─────────────────────┘
└─────────────────────────┘                  │
                                             ▼
                            ┌─────────────────────────────────────┐
                            │         Lambda Function             │
                            │  - API handlers                     │
                            │  - CSV processing                   │
                            │  - Auto-categorization              │
                            │  - PDF generation                   │
                            └───────────────┬─────────────────────┘
                                            │
                        ┌───────────────────┼───────────────────┐
                        ▼                   ▼                   ▼
                ┌──────────────┐   ┌──────────────┐    ┌──────────────┐
                │  S3 (Data)   │   │ Claude API   │    │   Secrets    │
                │ - dwcoa.db   │   │ (Haiku)      │    │  Manager     │
                │ - uploads/   │   │              │    │ - passwords  │
                └──────────────┘   └──────────────┘    │ - api key    │
                                                       └──────────────┘
```

---

## Directory Structure

```
dwcoa-financials/
├── specs/                          # Specifications (existing)
│   ├── CONSTITUTION.md
│   └── 001-financial-tracker/
│       ├── spec.md
│       ├── plan.md                 # This file
│       ├── research.md
│       ├── data-model.md
│       └── contracts/
│           └── api.yaml
├── data/                           # Source data (existing)
│   └── dwcoa-financials-data.csv
├── backend/                        # Lambda function
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Lambda handler
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── transactions.py
│   │   │   ├── categories.py
│   │   │   ├── budgets.py
│   │   │   ├── dues.py
│   │   │   └── reports.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── database.py         # SQLite operations
│   │   │   ├── categorizer.py      # Rules + Claude API
│   │   │   ├── csv_processor.py    # CSV import/export
│   │   │   ├── budget_calc.py      # YTD calculations
│   │   │   └── pdf_generator.py    # ReportLab PDF
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── entities.py         # Dataclasses
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── auth.py             # JWT handling
│   │       └── s3.py               # S3 operations
│   ├── sql/
│   │   ├── schema.sql
│   │   ├── seed.sql
│   │   └── rules.sql
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_categorizer.py
│   │   ├── test_budget_calc.py
│   │   └── test_csv_processor.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/                       # Static web frontend
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── template.yaml                   # SAM template
├── samconfig.toml                  # SAM configuration
├── Makefile                        # Build/deploy commands
├── CLAUDE.md                       # Existing
└── .gitignore                      # Existing
```

---

## Implementation Phases

### Phase 1: Infrastructure Foundation

**Goal**: Deployable skeleton with auth and basic API

1. Create SAM template with:
   - S3 bucket for data
   - S3 bucket for frontend
   - Lambda function
   - API Gateway HTTP API
   - IAM roles

2. Implement core Lambda handler:
   - Request routing
   - Error handling
   - CORS

3. Implement authentication:
   - Password validation
   - JWT token generation
   - Lambda authorizer

4. Deploy and verify:
   - `sam build && sam deploy`
   - Test auth endpoints

**Deliverables**:
- `template.yaml`
- `backend/app/main.py`
- `backend/app/routes/auth.py`
- `backend/app/utils/auth.py`

---

### Phase 2: Data Layer

**Goal**: SQLite database with seed data, S3 persistence

1. Create SQLite schema:
   - All tables from data-model.md
   - Views for dashboard queries
   - Indexes for performance

2. Implement database service:
   - Download SQLite from S3 on cold start
   - In-memory operations
   - Upload back to S3 on write

3. Seed initial data:
   - Categories (22 items)
   - Accounts (3 items)
   - Units (9 items)
   - 2025 budgets
   - Categorization rules

4. Deploy and verify:
   - Database initializes correctly
   - Seed data present

**Deliverables**:
- `backend/sql/schema.sql`
- `backend/sql/seed.sql`
- `backend/sql/rules.sql`
- `backend/app/services/database.py`

---

### Phase 3: CSV Processing & Categorization

**Goal**: Upload CSV, auto-categorize, store transactions

1. Implement CSV processor:
   - Parse bank CSV format
   - Validate columns
   - Map account numbers to names
   - Detect duplicates (warn only)

2. Implement rules engine:
   - Load rules from database
   - Regex pattern matching
   - Return category + confidence

3. Implement Claude API fallback:
   - Batch uncertain transactions
   - Few-shot prompt with examples
   - Parse response for category + confidence

4. Implement transaction storage:
   - Replace all transactions on upload
   - Preserve existing categories
   - Flag needs_review items

5. Implement CSV download:
   - Include all original columns
   - Add app columns (Account, Category, etc.)

**Deliverables**:
- `backend/app/services/csv_processor.py`
- `backend/app/services/categorizer.py`
- `backend/app/routes/transactions.py`

---

### Phase 4: Budget & Dashboard

**Goal**: YTD budget calculations, dashboard API

1. Implement budget calculations:
   - YTD budget by timing pattern
   - YTD actuals from transactions
   - Remaining budget

2. Implement dashboard endpoint:
   - Account balances
   - Income summary
   - Expense summary with remaining
   - Last updated timestamp

3. Implement dues tracking:
   - Expected by unit (ownership × budget)
   - Paid YTD by unit
   - Outstanding by unit

4. Implement category/budget CRUD:
   - List categories
   - Create/update categories
   - List/upsert budgets
   - Copy budgets to new year

**Deliverables**:
- `backend/app/services/budget_calc.py`
- `backend/app/routes/dashboard.py`
- `backend/app/routes/dues.py`
- `backend/app/routes/categories.py`
- `backend/app/routes/budgets.py`

---

### Phase 5: Frontend

**Goal**: Working web interface

1. Create HTML structure:
   - Login form
   - Dashboard layout (print-friendly)
   - Account balances section
   - Income/expense summary
   - Dues tracker
   - Admin controls (if authorized)

2. Create JavaScript app:
   - API client with auth
   - Dashboard data fetch and render
   - File upload handling
   - Download triggers

3. Create CSS styles:
   - Clean, professional design
   - Responsive layout
   - Print styles (`@media print`)

4. Deploy to S3:
   - Configure as static website
   - CloudFront distribution

**Deliverables**:
- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- Updated `template.yaml` for frontend hosting

---

### Phase 6: PDF Generation & Polish

**Goal**: PDF reports, review queue, final touches

1. Implement PDF generation:
   - ReportLab one-page layout
   - Match dashboard design
   - Download endpoint

2. Implement review queue:
   - List needs_review transactions
   - Update category endpoint
   - Clear review flag

3. Polish and test:
   - End-to-end testing
   - Error handling
   - Loading states in UI
   - Mobile responsive check

4. Documentation:
   - Update README
   - Deployment instructions
   - Treasurer user guide

**Deliverables**:
- `backend/app/services/pdf_generator.py`
- `backend/app/routes/reports.py`
- `backend/app/routes/review.py`
- Updated frontend with review UI
- Documentation

---

## Deployment Commands

```bash
# Initial setup
sam build
sam deploy --guided

# Subsequent deploys
sam build && sam deploy

# Frontend deploy
aws s3 sync frontend/ s3://dwcoa-frontend-bucket/

# Initialize database with seed data
aws lambda invoke --function-name dwcoa-api --payload '{"action": "init_db"}' /dev/null
```

---

## Environment Variables

| Variable | Description | Source |
|----------|-------------|--------|
| `DATA_BUCKET` | S3 bucket for SQLite and uploads | SAM template |
| `ADMIN_PASSWORD_HASH` | Bcrypt hash of admin password | Secrets Manager |
| `BOARD_PASSWORD_HASH` | Bcrypt hash of board password | Secrets Manager |
| `ANTHROPIC_API_KEY` | Claude API key | Secrets Manager |
| `JWT_SECRET` | Secret for signing tokens | Secrets Manager |

---

## Testing Strategy

| Area | Approach |
|------|----------|
| Business logic | pytest unit tests |
| Budget calculations | Property-based tests (hypothesis) |
| CSV parsing | Sample file tests |
| API endpoints | Integration tests with moto (S3 mock) |
| Frontend | Manual testing, browser print preview |

---

## Cost Estimate (Monthly)

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Lambda | ~1000 invocations | $0.00 (free tier) |
| API Gateway | ~1000 requests | $0.00 (free tier) |
| S3 | <1 GB storage | $0.02 |
| CloudFront | <10 GB transfer | $0.85 |
| Claude API | ~100 calls/month | $0.10 |
| Secrets Manager | 4 secrets | $1.60 |
| **Total** | | **~$2.57** |

Well under the $5/month target.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SQLite corruption | S3 versioning enabled, easy restore |
| Claude API down | Rules engine continues, queue for later |
| Cold starts slow | Acceptable per Constitution |
| Password compromised | Easy rotation, low-stakes data |

---

## Success Criteria Mapping

| Spec Criteria | How We Achieve It |
|---------------|-------------------|
| SC-001: Import in <10 min | CSV upload + auto-categorize |
| SC-002: 80%+ accuracy | Rules engine + Claude fallback |
| SC-003: <3s load | Static frontend, simple API |
| SC-004: One-page print | CSS `@media print` styles |
| SC-005: Password access | Shared passwords, no accounts |
| SC-006: Correct YTD | Timing-aware budget_calc.py |
| SC-007: <$5/month | Serverless, minimal resources |
| SC-008: Year-end report | Dashboard = report (print/PDF) |

---

## Next Steps

1. Run `/speckit.tasks` to generate detailed task breakdown
2. Begin Phase 1 implementation
3. Deploy MVP after Phase 5
4. Add PDF generation in Phase 6
