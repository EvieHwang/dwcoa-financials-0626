# Feature Specification: DWCOA Financial Tracker

**Feature Branch**: `001-financial-tracker`  
**Created**: 2026-01-03  
**Status**: Ready for Implementation  
**Input**: Collaborative design session documenting treasurer workflow and requirements

## Overview

A web-based financial management tool for the Denny Way Condo Owners Association (9 units). The tool automates transaction categorization, tracks budgets with proper timing patterns, manages dues receivables by unit, and generates clear financial reports for residents.

Key insight: Internal transfers between Savings and Checking accounts are operational plumbing and should be excluded from budget reporting. Only true income (dues, interest) and true expenses (bills paid) matter for financial tracking.

---

## User Scenarios & Testing

### User Story 1 - Upload and Manage Transaction Data (Priority: P1)

The treasurer maintains a master CSV file containing all transactions. When new bank data is available, the treasurer downloads the current file from the app, appends new transactions from the bank export, and re-uploads the complete file. The system replaces the previous data and auto-categorizes any uncategorized transactions.

**Why this priority**: This is the foundation - getting accurate transaction data into the system. Without this, nothing else works.

**Independent Test**: Upload a master CSV with 400+ transactions spanning 2024-2025; system ingests all data, preserves existing categories, auto-categorizes blank ones, and flags low-confidence items for review.

**Acceptance Scenarios**:

1. **Given** a master CSV file with all transactions, **When** uploaded, **Then** the system replaces existing transaction data with the new file
2. **Given** transactions have a Category column already populated, **When** uploaded, **Then** those categories are preserved unchanged
3. **Given** transactions have no category, **When** uploaded, **Then** the system attempts auto-categorization using rules engine first, then Claude API for uncertain items
4. **Given** auto-categorization has low confidence, **When** processed, **Then** the transaction is flagged with Needs_Review = true
5. **Given** the treasurer reviews and corrects a category, **When** saved, **Then** the pattern is learned for future similar transactions
6. **Given** the treasurer downloads the file, **When** opened, **Then** it includes all original columns plus app-added columns (Account, Category, Auto_Category, Confidence, Needs_Review)

---

### User Story 2 - View Financial Dashboard (Priority: P2)

Board members visit the password-protected website and see the current financial status. The dashboard is designed to be print-friendly - it IS the report. The page shows last-updated timestamp, account balances, income summary, expense summary with remaining budget, and dues status by unit.

**Why this priority**: This is what everyone sees and what gets shared at board meetings.

**Independent Test**: Access the website with the board password, see current financial summary with accurate numbers calculated from stored transaction data.

**Acceptance Scenarios**:

1. **Given** a user has the board (view-only) password, **When** they access the site, **Then** they see the financial dashboard
2. **Given** a user has the admin password, **When** they access the site, **Then** they see the dashboard plus admin controls
3. **Given** transactions have been uploaded, **When** viewing the dashboard, **Then** it shows "Last updated: [timestamp of last upload]"
4. **Given** a quarterly expense category (e.g., Cintas Fire Protection) in July, **When** viewing YTD budget, **Then** it shows budget for Q1+Q2 only (not 7/12ths)
5. **Given** actual expenses of $1,200 against YTD budget of $1,500, **When** viewing, **Then** remaining budget shows $300
6. **Given** the "Transfers" category, **When** viewing income/expense summaries, **Then** transfers are excluded (they net to zero)

---

### User Story 3 - Download Reports and Data (Priority: P3)

From the dashboard, users can print the page directly (browser print, fits one page), download as PDF, or download the raw transaction CSV with all data and app-added columns.

**Why this priority**: Output formats for sharing, record-keeping, and the round-trip data workflow.

**Independent Test**: Click print and get a clean one-page printout; click Download CSV and get complete transaction data with categories.

**Acceptance Scenarios**:

1. **Given** the dashboard is displayed, **When** user prints via browser, **Then** the page prints cleanly on one page with all key information
2. **Given** the dashboard is displayed, **When** user clicks "Download PDF", **Then** a PDF matching the dashboard layout is downloaded
3. **Given** a board member wants raw data, **When** they click "Download Transactions", **Then** they receive a CSV with all transaction data including app-added columns
4. **Given** the treasurer downloads the CSV, **When** they append new transactions and re-upload, **Then** the cycle continues seamlessly

---

### User Story 4 - Manage Categories and Budgets (Priority: P4)

The treasurer (admin) can view and edit categories, set budget amounts per category per year, set timing patterns (monthly, quarterly, annual), and create new year budgets by copying from previous year.

**Why this priority**: Necessary for year-over-year operation, but can be seeded with initial 2025 data.

**Acceptance Scenarios**:

1. **Given** a new year is starting, **When** the treasurer creates a new budget, **Then** they can copy last year's amounts as a starting point and adjust
2. **Given** a category is set to "quarterly" timing with $1,200 annual budget, **When** viewing in August, **Then** YTD budget shows $600 (Q1+Q2 complete)
3. **Given** a category is set to "monthly" timing with $1,200 annual budget, **When** viewing in August, **Then** YTD budget shows $700 (7 months complete)
4. **Given** a category is set to "annual" timing, **When** viewing at any point, **Then** YTD budget shows full annual amount (expense could hit any time)
5. **Given** a category needs to be retired, **When** marked inactive, **Then** it no longer appears for new categorizations but historical data is preserved

---

### User Story 5 - Track Dues by Unit (Priority: P5)

The dashboard shows dues status by unit: expected annual dues (based on ownership percentage and total budget), payments received in current year, and outstanding balance. Outstanding balance is unit-centric regardless of which year the debt originated.

**Why this priority**: Important for collections tracking, builds on transaction data foundation.

**Acceptance Scenarios**:

1. **Given** Unit 201 expects $5,954.75/year and has paid $3,000, **When** viewing dues tracker, **Then** it shows $2,954.75 outstanding
2. **Given** Unit 101 had past-due amounts carried forward, **When** viewing their balance, **Then** outstanding shows total owed (not split by year of origin)
3. **Given** a dues payment is received and categorized as "Dues 201", **When** the dashboard updates, **Then** Unit 201's outstanding balance decreases accordingly
4. **Given** the annual budget changes, **When** dues are recalculated, **Then** each unit's expected dues updates based on their ownership percentage

---

### Edge Cases

- **Duplicate transactions**: System detects potential duplicates (same date + amount + description) and warns but allows upload (bank sometimes shows duplicates legitimately)
- **Uncategorized transactions**: Remain as "Uncategorized", excluded from budget comparisons but included in account totals
- **Category not in list**: If uploaded CSV has a category not in the system, flag for review rather than reject
- **Partial year data**: Dashboard handles partial year gracefully (YTD calculations work regardless of data completeness)
- **Zero budget categories**: Categories with $0 budget still track actuals (useful for unexpected expenses hitting "Other")

---

## Requirements

### Functional Requirements

**Data Management**

- **FR-001**: System MUST accept CSV file upload for transaction data (bank export format, treasurer ensures conformance)
- **FR-002**: System MUST replace all transaction data on each upload (full file replacement, not incremental)
- **FR-003**: System MUST preserve Category values from uploaded file where populated
- **FR-004**: System MUST track upload timestamp and display "Last Updated: [datetime]" on dashboard
- **FR-005**: System MUST store the master CSV and serve it for download with app-added columns

**CSV Format**

- **FR-006**: Input CSV columns (bank export format): Account Number, Post Date, Check, Description, Debit, Credit, Status, Balance
- **FR-007**: System MUST map masked account numbers to friendly names:
  - `****7145` → Savings
  - `****9242` → Checking  
  - `****9226` → Reserve Fund
- **FR-008**: App-added columns on download: Account (friendly name), Category, Auto_Category (AI suggestion), Confidence (0-100), Needs_Review (true/false)
- **FR-009**: Category column may be blank on upload; system attempts to fill it

**Auto-Categorization**

- **FR-010**: System MUST attempt categorization using rules engine first (pattern matching on Description + Account)
- **FR-011**: System MAY use Claude API (Haiku) for uncertain transactions after rules engine
- **FR-012**: System MUST record confidence score (0-100) for each auto-categorization
- **FR-013**: System MUST flag items with confidence < 80 as Needs_Review = true
- **FR-014**: System MUST learn patterns from manually categorized transactions to improve rules engine
- **FR-015**: Auto-categorization prompt is baked into the system (not user-editable via UI)

**Budget Management**

- **FR-016**: System MUST store budgets separately: Year + Category + Annual Amount + Timing Pattern
- **FR-017**: System MUST support three timing patterns: monthly, quarterly, annual
- **FR-018**: YTD Budget calculation by timing:
  - Monthly: (Annual / 12) × months elapsed
  - Quarterly: (Annual / 4) × quarters completed
  - Annual: Full annual amount (expense could occur any time)
- **FR-019**: System MUST calculate and display Remaining Budget = YTD Budget - YTD Actual

**Account Handling**

- **FR-020**: System MUST recognize three accounts: Savings, Checking, Reserve Fund
- **FR-021**: Income = Credits to Savings account (excluding transfers)
- **FR-022**: Expenses = Debits from Checking account (excluding transfers)
- **FR-023**: Transfers category MUST be excluded from income/expense budget reporting
- **FR-024**: Total Cash = Current balance of Savings + Checking + Reserve Fund

**Dues Tracking**

- **FR-025**: System MUST store unit ownership percentages (static: 101=11.7%, 102=10.4%, 103=11.2%, 201=11.7%, 202=10.4%, 203=11.2%, 301=11.7%, 302=10.4%, 303=11.2%)
- **FR-026**: Expected dues per unit = Total Expense Budget × Unit Percentage
- **FR-027**: System MUST track payments received per unit (sum of transactions in "Dues [unit]" category)
- **FR-028**: Outstanding balance per unit = Expected - Paid (unit-centric, not year-centric)

**Access Control**

- **FR-029**: System MUST have two passwords: Admin and Board (view-only)
- **FR-030**: Admin access: upload data, manage categories, manage budgets, review queue, plus all view functions
- **FR-031**: Board access: view dashboard, print, download PDF, download transaction CSV

**Reporting**

- **FR-032**: Dashboard MUST show: Last Updated, Account Balances, Income Summary, Expense Summary with Remaining, Dues by Unit
- **FR-033**: Dashboard MUST be print-friendly (fits one page via browser print)
- **FR-034**: System MUST provide PDF download matching dashboard layout
- **FR-035**: System MUST provide CSV download of all transaction data

---

### Key Entities

**Transaction**
- Account Number (string, masked - from bank export)
- Account (string, friendly name - app-derived: Savings, Checking, Reserve Fund)
- Post Date (date)
- Check (string, optional)
- Description (string)
- Debit (decimal, optional)
- Credit (decimal, optional)
- Status (string)
- Balance (decimal)
- Category (string, optional - from category list)
- Auto_Category (string, app-generated)
- Confidence (integer 0-100, app-generated)
- Needs_Review (boolean, app-generated)

**Category**
- Name (string, unique)
- Type (enum: Income, Expense, Transfer, Internal)
- Default Account (enum: Savings, Checking, Reserve Fund, Any)
- Timing (enum: Monthly, Quarterly, Annual)
- Active (boolean)

**Budget**
- Year (integer)
- Category (reference to Category)
- Annual Amount (decimal)
- Timing (enum: Monthly, Quarterly, Annual) - can override category default

**Unit**
- Number (string: 101, 102, 103, 201, 202, 203, 301, 302, 303)
- Ownership Percentage (decimal)

---

## Initial Data

### Account Mapping (seed data)

| Masked Account Number | Friendly Name |
|-----------------------|---------------|
| ****7145 | Savings |
| ****9242 | Checking |
| ****9226 | Reserve Fund |

### Categories (seed data)

| Category | Type | Default Account | Timing |
|----------|------|-----------------|--------|
| Dues 101 | Income | Savings | Monthly |
| Dues 102 | Income | Savings | Monthly |
| Dues 103 | Income | Savings | Monthly |
| Dues 201 | Income | Savings | Monthly |
| Dues 202 | Income | Savings | Monthly |
| Dues 203 | Income | Savings | Monthly |
| Dues 301 | Income | Savings | Monthly |
| Dues 302 | Income | Savings | Monthly |
| Dues 303 | Income | Savings | Monthly |
| Interest income | Income | Any | Monthly |
| Bulger Safe & Lock | Expense | Checking | Annual |
| Cintas Fire Protection | Expense | Checking | Annual |
| Common Area Cleaning | Expense | Checking | Monthly |
| Fire Alarm | Expense | Checking | Monthly |
| Grounds/Landscaping | Expense | Checking | Monthly |
| Homeowners Club Dues | Expense | Checking | Annual |
| Insurance Premiums | Expense | Checking | Monthly |
| Seattle City Light | Expense | Checking | Monthly |
| Other | Expense | Checking | Annual |
| Reserve Contribution | Transfer | Savings | Monthly |
| Reserve Expenses | Expense | Reserve Fund | Annual |
| Transfers | Internal | Any | N/A |

### 2025 Budget (seed data)

**Income:**
| Category | Annual Budget |
|----------|---------------|
| Dues 101 | $5,954.75 |
| Dues 102 | $5,293.11 |
| Dues 103 | $5,700.27 |
| Dues 201 | $5,954.75 |
| Dues 202 | $5,293.11 |
| Dues 203 | $5,700.27 |
| Dues 301 | $5,954.75 |
| Dues 302 | $5,293.11 |
| Dues 303 | $5,700.27 |
| Interest income | $26.00 |

**Expenses:**
| Category | Annual Budget |
|----------|---------------|
| Reserve Contribution | $18,000.00 |
| Bulger Safe & Lock | $400.00 |
| Cintas Fire Protection | $1,500.00 |
| Common Area Cleaning | $2,700.00 |
| Fire Alarm | $3,300.00 |
| Grounds/Landscaping | $12,000.00 |
| Other | $7,500.00 |
| Insurance Premiums | $4,500.00 |
| Seattle City Light | $6,000.00 |

### Unit Ownership (seed data)

| Unit | Percentage |
|------|------------|
| 101 | 0.117 |
| 102 | 0.104 |
| 103 | 0.112 |
| 201 | 0.117 |
| 202 | 0.104 |
| 203 | 0.112 |
| 301 | 0.117 |
| 302 | 0.104 |
| 303 | 0.112 |

---

## Training Data for Auto-Categorization

The file `DWCOA_Financials_24_v3.xlsx` in the project contains ~400 already-categorized transactions. Use this to:
1. Build pattern-matching rules for the rules engine
2. Create few-shot examples for the Claude API prompt
3. Test auto-categorization accuracy (target: 80%+)

See `specs/001-financial-tracker/training-data.md` for details.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Treasurer can import and review a month's transactions in under 10 minutes
- **SC-002**: Auto-categorization achieves 80%+ accuracy on recurring transaction types
- **SC-003**: Dashboard loads in under 3 seconds
- **SC-004**: Dashboard prints cleanly on one page via browser print
- **SC-005**: Board members can access dashboard with just a password (no account creation needed)
- **SC-006**: YTD budget calculations correctly reflect timing patterns (verified against manual calculation)
- **SC-007**: Monthly AWS costs remain under $5
- **SC-008**: Treasurer can prepare year-end financial statement by printing dashboard as of 12/31

---

## Assumptions

- Treasurer ensures CSV format conformance (system does not need to handle arbitrary formats)
- Bank export format is consistent (8 columns as documented)
- Single-user write access (treasurer only uploads; no concurrent editing concerns)
- Trust-based access model (shared passwords acceptable for this use case)
- Cold starts acceptable for Lambda functions
- Data volumes are small (hundreds of transactions per year, not thousands)

---

## Out of Scope (Future Considerations)

- Individual user accounts with authentication
- Multi-year trend analysis or charts
- Automated bank import (API integration with bank)
- Email notifications or reminders
- Mobile-specific UI (responsive web is sufficient)
- Audit trail of changes (beyond what's in the CSV)
- Integration with accounting software

---

## Dependencies

- AWS account (existing)
- Claude API key (for auto-categorization)
- Domain/hosting (to be determined - could be S3+CloudFront or similar)
