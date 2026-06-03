.PHONY: build deploy test clean init-db frontend

# Build Lambda package
build:
	sam build

# Deploy to AWS
deploy: build
	sam deploy

# Deploy with guided prompts (first time)
deploy-guided: build
	sam deploy --guided

# Run tests
test:
	cd backend && pytest tests/ -v

# Run tests with coverage
test-cov:
	cd backend && pytest tests/ -v --cov=app --cov-report=html

# Clean build artifacts
clean:
	rm -rf .aws-sam
	rm -rf backend/__pycache__
	rm -rf backend/app/__pycache__
	rm -rf backend/tests/__pycache__
	find . -name "*.pyc" -delete

# Deploy frontend to S3
frontend:
	@if [ -z "$(FRONTEND_BUCKET)" ]; then \
		echo "Error: FRONTEND_BUCKET not set. Run: export FRONTEND_BUCKET=your-bucket-name"; \
		exit 1; \
	fi
	aws s3 sync frontend/ s3://$(FRONTEND_BUCKET)/

# Initialize database with seed data
init-db:
	@echo "Database initializes automatically on first Lambda invocation"

# Local development
local:
	sam local start-api

# View logs
logs:
	sam logs -n DwcoaApiFunction --stack-name dwcoa-financials --tail

# Get stack outputs
outputs:
	aws cloudformation describe-stacks --stack-name dwcoa-financials --query "Stacks[0].Outputs"
