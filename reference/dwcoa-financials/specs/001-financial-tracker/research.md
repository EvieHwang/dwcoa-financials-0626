# Technical Research: DWCOA Financial Tracker

**Feature**: 001-financial-tracker
**Date**: 2026-01-02
**Status**: Complete

## Executive Summary

This document captures technical decisions for the DWCOA Financial Tracker. Following the Constitution's principles of "Simplicity First" and "Serverless When Dynamic", we've selected a minimal-infrastructure approach using AWS Lambda, S3, and SQLite.

---

## Decision 1: Data Storage

### Question
How should we persist transaction data, budgets, and configuration?

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **SQLite file in S3** | Simple, portable, SQL queries, no DB infra | Lambda cold start with S3 fetch |
| JSON files in S3 | Very simple, human-readable | No query capability, file size limits |
| DynamoDB | Managed, scalable, fast | Cost, complexity, against Constitution |
| PostgreSQL (RDS) | Full SQL, robust | Cost, complexity, overkill |

### Decision: **SQLite file in S3**

**Rationale**:
- Matches Constitution's "file-based data storage" preference
- SQL queries simplify budget/timing calculations
- Easy to backup and migrate (just copy the file)
- Lambda downloads SQLite on cold start, works entirely in memory
- File size will be tiny (<5MB even with years of data)

**Trade-offs Accepted**:
- Cold start penalty (~1s to download from S3)
- Write operations require upload back to S3
- No concurrent write support (acceptable per Constitution)

---

## Decision 2: Auto-Categorization Architecture

### Question
How should we implement auto-categorization with rules engine + Claude API fallback?

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Rules engine first, Claude API fallback** | Cost-effective, fast for known patterns | Two systems to maintain |
| Claude API only | Simple, consistent | Higher cost, slower |
| ML model (trained) | Fast once trained | Complex, overkill for <500 txns/year |

### Decision: **Rules Engine First, Claude API Fallback**

**Implementation**:
1. **Rules Engine** (Python, in Lambda):
   - Pattern matching on Description field
   - Regex patterns learned from historical data
   - Store patterns in SQLite: `pattern -> category + confidence`
   - Example: `r"WASHINGTON.*ALARM" -> "Fire Alarm", 95`

2. **Claude API Fallback** (Haiku model):
   - Only called when rules engine confidence < 80%
   - Batch processing (multiple transactions per API call)
   - Few-shot prompt with category list and examples
   - Response includes category + confidence score

**Cost Analysis**:
- ~50 new transactions/month typical
- Rules engine handles ~80% with high confidence
- ~10 transactions/month to Claude API
- At $0.25/1M input tokens, $1.25/1M output tokens (Haiku)
- Estimated: <$0.10/month for categorization

---

## Decision 3: Frontend Architecture

### Question
How should we build the web frontend?

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Vanilla JS + HTML** | Simple, no build step, fast | More code for interactivity |
| React SPA | Component reuse, ecosystem | Build complexity, overkill |
| Server-rendered (Jinja) | Simple, SEO | Lambda cold starts on every page |
| HTMX | Progressive enhancement | Another dependency |

### Decision: **Vanilla JS + HTML**

**Rationale**:
- Matches Constitution's "avoid complex build systems"
- Dashboard is mostly static display with minimal interactivity
- No build step = deploy directly to S3
- Print-friendly by default (no framework overhead)

**Implementation**:
- Single `index.html` with inline CSS
- `app.js` for API calls and DOM updates
- CSS Grid/Flexbox for responsive layout
- `@media print` styles for one-page printing

---

## Decision 4: Authentication

### Question
How should we implement password-protected access?

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **API Gateway + Lambda authorizer** | Simple, stateless, works with S3 hosting | Token management |
| CloudFront signed URLs | S3 native | Complexity, URL expiry issues |
| Lambda@Edge | Flexible | Cost, latency, complexity |
| Client-side only | Very simple | Not secure |
| Cognito | Full auth system | Overkill per Constitution |

### Decision: **API Gateway Lambda Authorizer + Session Token**

**Implementation**:
1. Frontend shows password prompt (no session stored)
2. Password sent to `/api/auth` endpoint
3. Lambda verifies against stored hash (admin or board password)
4. Returns JWT-like session token (valid 24 hours)
5. Token stored in localStorage, sent with all API requests
6. Lambda authorizer validates token on protected endpoints

**Passwords**:
- Stored as environment variables (hashed)
- Two passwords: admin (full access) and board (view-only)
- No user accounts, just shared passwords per Constitution

---

## Decision 5: PDF Generation

### Question
How should we generate PDF reports?

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **ReportLab (Python)** | Full control, lightweight | Manual layout |
| WeasyPrint | HTML to PDF | Heavy dependency |
| Browser print to PDF | Zero backend | User must print |
| Puppeteer/Playwright | Pixel-perfect | Heavy, cold start issues |

### Decision: **ReportLab for Lambda, Browser Print as Fallback**

**Implementation**:
1. Primary: Browser print (`@media print` CSS) - already implemented in frontend
2. Secondary: `/api/report/pdf` endpoint using ReportLab
3. ReportLab generates one-page PDF matching dashboard layout

**Rationale**:
- Browser print is zero-cost and works immediately
- ReportLab adds ~4MB to Lambda package (acceptable)
- Covers users who want a downloadable PDF file

---

## Decision 6: Deployment Strategy

### Question
How should we deploy and manage infrastructure?

### Decision: **AWS SAM**

**Implementation**:
- `template.yaml` defines all resources
- Single `sam build && sam deploy` command
- Resources:
  - S3 bucket for frontend static files
  - S3 bucket for data (SQLite, uploads)
  - Lambda function for API
  - API Gateway HTTP API
  - CloudFront distribution (optional, for HTTPS)

**Justification**:
- Per Constitution: "AWS SAM for deployment"
- Infrastructure as code, version controlled
- Easy to replicate or tear down

---

## Decision 7: Budget Timing Calculations

### Question
How should we calculate YTD budget based on timing patterns?

### Decision: **Server-side calculation in Python**

**Implementation**:
```python
def calculate_ytd_budget(annual_amount: float, timing: str, as_of_date: date) -> float:
    month = as_of_date.month

    if timing == "monthly":
        return (annual_amount / 12) * month

    elif timing == "quarterly":
        quarters_complete = (month - 1) // 3
        return (annual_amount / 4) * quarters_complete

    elif timing == "annual":
        return annual_amount  # Full amount available all year

    return annual_amount  # Default to annual
```

**Examples** (as of August = month 8):
- Monthly $1,200: YTD = $800 (8 months × $100)
- Quarterly $1,200: YTD = $600 (Q1+Q2 complete = 2 quarters × $300)
- Annual $1,200: YTD = $1,200 (expense could hit any time)

---

## Decision 8: CSV Processing

### Question
How should we handle CSV upload and processing?

### Decision: **Python csv module + pandas for validation**

**Implementation**:
1. Upload CSV to S3 (temporary location)
2. Lambda triggered, downloads and parses CSV
3. Validate columns match expected format
4. Map account numbers to friendly names
5. Process each row:
   - If Category populated: preserve it
   - If Category blank: run through categorization
6. Store in SQLite (replace all transactions)
7. Save SQLite back to S3

**Error Handling**:
- Reject if required columns missing
- Warn on duplicate detection (same date + amount + description)
- Flag unknown categories for review

---

## Technical Stack Summary

| Component | Technology | Justification |
|-----------|------------|---------------|
| Runtime | Python 3.12 | Constitution requirement |
| Data Storage | SQLite in S3 | Simple, portable, queryable |
| Backend | AWS Lambda | Serverless, pay-per-use |
| API | API Gateway HTTP API | Simple, cheap |
| Frontend | Vanilla JS + HTML | No build step |
| Hosting | S3 + CloudFront | Static, cheap, HTTPS |
| Auth | Lambda Authorizer | Simple token-based |
| AI | Claude API (Haiku) | Cost-effective categorization |
| PDF | ReportLab | Lightweight, Lambda-compatible |
| Deployment | AWS SAM | IaC, simple deploys |

---

## Risk Analysis

| Risk | Mitigation |
|------|------------|
| SQLite corruption | Daily S3 versioning, easy restore |
| Claude API unavailable | Rules engine continues working, queue for later |
| Lambda cold starts | Acceptable per Constitution, ~2-3s max |
| Password leak | Easy to rotate, low-stakes data |
| S3 costs spike | CloudFront caching, minimal data |

---

## Next Steps

1. Create data model (data-model.md)
2. Define API contracts (contracts/api.yaml)
3. Build task breakdown (tasks.md)
4. Begin implementation
