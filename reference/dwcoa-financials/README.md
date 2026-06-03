# DWCOA Financial Dashboard

A serverless financial management application for the Denny Way Condo Owners Association (9 units). Automates transaction categorization, tracks budgets with timing patterns, manages dues by unit, and generates financial reports.

## Features

- **Transaction Management**: Upload bank CSV exports, auto-categorize using rules engine + Claude AI
- **Transaction Viewer**: Sortable, filterable data table with pagination and CSV export
- **Visual Charts**: YTD Budget vs Actual bar chart and Monthly Cash Flow line chart
- **Budget Tracking**: Annual budgets with timing patterns (monthly, quarterly, annual) for accurate YTD calculations
- **Dues Tracking**: Track payments by unit based on ownership percentages
- **Reserve Fund Monitoring**: Track contributions and expenses with YTD net change
- **Financial Reports**: Dashboard view, PDF download, CSV export
- **Date Snapshots**: View financial state as of any historical date
- **Role-Based Access**: Admin (full access) and Homeowner (view-only) roles
- **Mobile Responsive**: Works on desktop and mobile devices

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vanilla HTML/CSS/JavaScript, Chart.js, Tabulator.js |
| Backend | Python 3.12, AWS Lambda |
| Database | SQLite (stored in S3) |
| API | AWS API Gateway (HTTP API) |
| CDN | AWS CloudFront |
| Hosting | AWS S3 (static files) |
| AI | Claude API (Anthropic) for auto-categorization |
| PDF | ReportLab |
| IaC | AWS SAM |

## Usage Guide

### Logging In

1. Navigate to the dashboard URL
2. Enter the password:
   - **Admin password**: Full access (upload, edit budgets, review transactions)
   - **Homeowner password**: View-only access (dashboard, downloads)
3. Your role badge appears in the header (Admin/Homeowner)

### Viewing the Dashboard

The dashboard shows financial data for the current year by default. Use the date picker to view historical snapshots.

- **"View as of" date picker**: Select any date to see balances and YTD figures as of that date
- **"Reset to Today"**: Return to current date view
- **Last updated**: Shows when transaction data was last uploaded

### Uploading Transaction Data (Admin Only)

1. Download the latest transactions from your bank as CSV
2. Click **Choose File** and select the CSV
3. Click **Upload** - the system will:
   - Parse and store all transactions
   - Auto-categorize using rules and AI
   - Flag low-confidence items for review
4. Review flagged transactions by clicking **Review Transactions**

### Downloading Reports

- **CSV button**: Download all transactions with categories
- **PDF button**: Download a formatted report matching the dashboard layout

### Managing Budgets (Admin Only)

1. Click **Manage Budgets** to open the budget editor
2. Select a year from the dropdown (auto-loads on change)
3. For each category, set:
   - **Timing**: Monthly, Quarterly, or Annual
   - **Annual Amount**: Budget for the full year
4. Click **Save** to update each row
5. Use **Copy Budgets** to duplicate a year's budgets to another year
6. Click **+ Add Category** to create new budget categories

## Dashboard Sections

### Financial Overview (Charts)
Two charts providing visual summaries:
- **YTD Budget vs Actual**: Bar chart comparing budgeted vs actual amounts for Income & Dues and Operating Expenses
- **Monthly Cash Flow**: Line chart showing income and expenses by month for the selected year

### Account Balances
Three account cards showing current balances:
- **Checking**: Operating account balance
- **Savings**: Savings account balance
- **Reserve Fund**: Reserve balance + YTD change (contributions minus expenses)
- **Total Cash**: Sum of all accounts

### Income & Dues
- **Summary box**: Budget (YTD), Actual, Remaining totals
- **Dues table**: Per-unit breakdown showing:
  - Unit number
  - Ownership share percentage
  - Expected dues (YTD, prorated by timing)
  - Actual payments received
  - Remaining balance (positive = still owed)

### Operating Expenses
- **Summary box**: Budget (YTD), Actual, Remaining totals
- **Expense table**: Per-category breakdown showing:
  - Category name
  - YTD Budget (prorated based on timing pattern)
  - Actual spending
  - Remaining budget (positive = under budget)

### Admin Controls (Admin Only)
- **Choose File / Upload**: Upload bank CSV exports
- **Review Transactions (n)**: Review and categorize flagged transactions
- **Manage Budgets**: Open budget editor modal

### Transaction History
Interactive data table showing all uploaded transactions:
- **Columns**: Post Date, Account, Category, Description, Debit, Credit
- **Sorting**: Click any column header to sort ascending/descending
- **Filtering**: Type in header filter boxes to search within columns
- **Pagination**: Choose 25, 50, or 100 rows per page
- **Export CSV**: Download filtered/sorted transactions

## Setup & Deployment

### Prerequisites

- Python 3.12+
- AWS CLI configured
- AWS SAM CLI

### Local Development

```bash
cd backend
pip install -r requirements.txt
pytest
sam build
sam local start-api
```

### Deploy to AWS

```bash
# Build and deploy backend
sam build
sam deploy --guided  # First time
sam deploy           # Subsequent

# Deploy frontend
aws s3 sync frontend/ s3://dwcoa-frontend-{ACCOUNT_ID}
aws cloudfront create-invalidation --distribution-id {DIST_ID} --paths "/*"
```

### Configuration

Set these parameters during `sam deploy --guided`:

| Parameter | Description |
|-----------|-------------|
| `AdminPasswordHash` | Bcrypt hash for admin login |
| `BoardPasswordHash` | Bcrypt hash for homeowner login |
| `AnthropicApiKey` | API key for Claude auto-categorization |
| `JwtSecret` | Secret for signing JWT tokens |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # Lambda handler
│   │   ├── routes/              # API endpoints
│   │   └── services/            # Business logic
│   ├── sql/                     # Database schema
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── specs/                       # Feature specifications
└── template.yaml                # SAM template
```

## License

Private - All rights reserved.
