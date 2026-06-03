# DWCOA Financials Constitution

This document establishes the foundational architectural principles, design philosophy, and decision-making framework for the DWCOA Financials project.

## Project Mission

Build a simple, maintainable financial management tool for the Denny Way Condo Owners Association that automates transaction categorization, tracks budgets with proper timing, manages dues receivables by unit, and generates clear financial reports for residents.

## Architectural Principles

### 1. Simplicity First

**Rationale**: This is a personal/small-organization tool. Complexity is the enemy.

**Implementation**:
- File-based data storage (JSON/SQLite) over databases
- Static hosting where possible (S3 + CloudFront)
- Minimal infrastructure to maintain
- No over-engineering for hypothetical scale

**Trade-offs Accepted**:
- Not designed for multi-user concurrent editing
- Manual backup responsibility
- Limited to small data volumes (hundreds of transactions/year)

### 2. Serverless When Dynamic

**Rationale**: Pay only for what you use, zero server maintenance

**Implementation**:
- AWS Lambda for any server-side processing
- API Gateway for API endpoints
- S3 for static frontend hosting
- CloudFront for CDN and HTTPS

**Cost Guardrails**:
- No always-on compute
- No provisioned concurrency
- Cold starts are acceptable
- Target: < $5/month AWS costs

### 3. Claude API for Intelligence

**Rationale**: Leverage AI for transaction categorization without building complex rules

**Implementation**:
- Claude API for auto-categorizing transactions
- Simple rules engine for obvious matches first (reduce API calls)
- Configurable prompt for categorization logic
- Human review queue for low-confidence items

**Cost Guardrails**:
- Use Claude Haiku for categorization (cheapest)
- Cache/remember categorization patterns
- Batch processing where possible

### 4. Password-Protected Web Access

**Rationale**: Share with condo residents without exposing to public internet

**Implementation**:
- Simple password protection (not full auth system)
- Could be CloudFront signed URLs, Lambda@Edge, or simple client-side
- Password shared among board members/residents
- No user accounts or role-based access needed

**Trade-offs Accepted**:
- Single shared password (not per-user)
- Not suitable for highly sensitive data
- Trust-based access model

### 5. PDF Reports as First-Class Output

**Rationale**: Board meetings need printable, shareable documents

**Implementation**:
- One-page financial summary PDF
- Clean, professional formatting
- Generated on-demand or scheduled
- Matches the style of current Excel reports

### 6. Data Portability

**Rationale**: Treasurer role rotates; data must be transferable

**Implementation**:
- All data exportable as CSV/Excel
- No proprietary formats
- Clear documentation of data structure
- Easy to migrate to different system if needed

## Data Principles

### Transaction Categorization
- Categories are stable year-to-year
- Special projects get temporary categories
- Uncategorized items go to review queue
- Historical patterns inform future categorization

### Budget Timing
- Each budget line item has a timing pattern (monthly, quarterly, annual, seasonal)
- YTD budget calculates based on timing, not simple monthly division
- Timing patterns are configurable per category

### Dues Tracking
- Track receivables by unit, not by year
- Outstanding balance is unit-centric regardless of origin year
- Payment history maintained per unit
- Clear aging of receivables

## Development Principles

### Specification-Driven
- Features start with specs in `/specs`
- Specs define requirements before implementation
- Implementation follows specs; deviations require spec updates

### Test Coverage
- Core business logic must have tests
- Financial calculations especially must be tested
- UI can have lighter test coverage

### Incremental Delivery
- Each user story is independently valuable
- MVP first, then iterate
- Do not build features "for later"

## Technology Constraints

### Must Use
- Python 3.12+ for backend
- AWS for hosting (existing account)
- Claude API for AI features

### Prefer
- React or vanilla JS for frontend
- SQLite or JSON for data storage
- AWS SAM for deployment

### Avoid
- Heavy frameworks (Django, etc.)
- Managed databases (RDS, DynamoDB for primary storage)
- Complex build systems
- Dependencies with large footprints

## Success Metrics

### MVP Success
- [ ] Can upload bank transactions and auto-categorize 80%+
- [ ] Can view financial summary on web
- [ ] Can generate one-page PDF report
- [ ] Can track dues by unit with outstanding balances
- [ ] Total monthly AWS cost < $5

### Full Success
- [ ] Treasurer can prepare monthly report in < 15 minutes
- [ ] Board members can access reports via web link
- [ ] Year-end reporting is straightforward
- [ ] New treasurer can take over with minimal training

## Revision History

- **2026-01-03**: Initial constitution established
