# Quickstart: DWCOA Financial Tracker

This guide covers setting up the development environment and deploying the DWCOA Financial Tracker.

---

## Prerequisites

### Required Tools

```bash
# Python 3.12+
python3 --version  # Should be 3.12.x

# AWS CLI v2
aws --version

# AWS SAM CLI
sam --version

# Node.js (for frontend tooling, optional)
node --version
```

### AWS Configuration

```bash
# Configure AWS credentials
aws configure

# Verify access
aws sts get-caller-identity
```

### Anthropic API Key

1. Get an API key from [console.anthropic.com](https://console.anthropic.com)
2. Save it for the deployment step

---

## Project Setup

### Clone and Navigate

```bash
cd /path/to/dwcoa-financials
```

### Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (once backend is created)
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

---

## Local Development

### Database Setup

The SQLite database is created automatically on first run. To reset:

```bash
# Initialize with seed data
python -c "from backend.app.services.database import init_db; init_db()"
```

### Running Locally

```bash
# Start local API (SAM local)
sam local start-api

# Or run tests
pytest backend/tests/
```

### Environment Variables (Local)

Create `.env` file in project root:

```bash
DATA_BUCKET=local
ADMIN_PASSWORD_HASH=<bcrypt hash>
BOARD_PASSWORD_HASH=<bcrypt hash>
ANTHROPIC_API_KEY=sk-ant-xxxxx
JWT_SECRET=local-dev-secret
```

Generate password hashes:

```python
import bcrypt
password = b"your-password-here"
print(bcrypt.hashpw(password, bcrypt.gensalt()).decode())
```

---

## Deployment

### First-Time Setup

```bash
# Build the Lambda package
sam build

# Deploy with guided prompts
sam deploy --guided
```

You'll be prompted for:
- Stack name: `dwcoa-financials`
- AWS Region: `us-west-2` (or your preference)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`

### Store Secrets

After first deploy, store secrets in AWS Secrets Manager:

```bash
# Admin password
aws secretsmanager create-secret \
  --name dwcoa/admin-password \
  --secret-string "$(python -c "import bcrypt; print(bcrypt.hashpw(b'admin-password', bcrypt.gensalt()).decode())")"

# Board password
aws secretsmanager create-secret \
  --name dwcoa/board-password \
  --secret-string "$(python -c "import bcrypt; print(bcrypt.hashpw(b'board-password', bcrypt.gensalt()).decode())")"

# Claude API key
aws secretsmanager create-secret \
  --name dwcoa/anthropic-api-key \
  --secret-string "sk-ant-xxxxx"

# JWT secret
aws secretsmanager create-secret \
  --name dwcoa/jwt-secret \
  --secret-string "$(python -c "import secrets; print(secrets.token_hex(32))")"
```

### Deploy Frontend

```bash
# Get the frontend bucket name from stack outputs
FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name dwcoa-financials \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucket'].OutputValue" \
  --output text)

# Sync frontend files
aws s3 sync frontend/ s3://$FRONTEND_BUCKET/
```

### Subsequent Deploys

```bash
# Backend changes
sam build && sam deploy

# Frontend changes only
aws s3 sync frontend/ s3://$FRONTEND_BUCKET/

# Invalidate CloudFront cache (if needed)
aws cloudfront create-invalidation \
  --distribution-id <DIST_ID> \
  --paths "/*"
```

---

## Initialize Database

After first deploy, initialize the database with seed data:

```bash
# Get the API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name dwcoa-financials \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)

# Initialize database (one-time)
curl -X POST "$API_URL/admin/init-db" \
  -H "Authorization: Bearer <admin-token>"
```

---

## Verify Deployment

### Check API Health

```bash
# Get API URL
echo $API_URL

# Test auth
curl -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"password": "admin-password"}'
```

### Check Frontend

Open the CloudFront URL in a browser:

```bash
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name dwcoa-financials \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" \
  --output text)

echo "Frontend: https://$CLOUDFRONT_URL"
```

---

## Upload Transaction Data

1. Log in with admin password
2. Click "Upload Transactions"
3. Select `data/dwcoa-financials-data.csv`
4. Review auto-categorization results
5. Fix any items marked "Needs Review"
6. Dashboard updates automatically

---

## Common Tasks

### Reset Database

```bash
# Delete and reinitialize
aws s3 rm s3://$DATA_BUCKET/dwcoa.db
# Then trigger init endpoint or let Lambda recreate on next request
```

### View Logs

```bash
# Lambda logs
sam logs -n DwcoaApiFunction --stack-name dwcoa-financials --tail
```

### Update Passwords

```bash
# Update secret
aws secretsmanager update-secret \
  --secret-id dwcoa/admin-password \
  --secret-string "$(python -c "import bcrypt; print(bcrypt.hashpw(b'new-password', bcrypt.gensalt()).decode())")"
```

---

## Troubleshooting

### Lambda Cold Start Slow

Expected behavior per Constitution. First request after idle period may take 2-3 seconds.

### CSV Upload Fails

- Check CSV format matches expected columns
- Ensure file encoding is UTF-8
- Verify file size < 10MB

### Categories Not Matching

- Check categorization rules in database
- Review Claude API responses in logs
- Manual categorization always overrides auto

### PDF Not Generating

- Check ReportLab is in Lambda package
- Verify PDF endpoint permissions
- Check Lambda memory (may need 256MB+)

---

## Development Workflow

1. Make changes to backend code
2. Run local tests: `pytest backend/tests/`
3. Build and deploy: `sam build && sam deploy`
4. Test in browser
5. Commit with descriptive message

---

## Project Links

- **Spec**: `specs/001-financial-tracker/spec.md`
- **Plan**: `specs/001-financial-tracker/plan.md`
- **API Contract**: `specs/001-financial-tracker/contracts/api.yaml`
- **Data Model**: `specs/001-financial-tracker/data-model.md`
