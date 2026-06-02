.PHONY: help setup install migrate test run clean

help: ## Show this help message
	@echo "ACG - Admin & Compliance Guardian"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Complete setup (install + migrate + init)
	@echo "🚀 Setting up ACG..."
	$(MAKE) install
	$(MAKE) migrate
	$(MAKE) init-db
	@echo "✅ Setup complete!"

install: ## Install all dependencies
	@echo "📦 Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Dependencies installed"

migrate: ## Run database migrations
	@echo "🗄️  Running database migrations..."
	cd backend && alembic upgrade head
	@echo "✅ Migrations complete"

init-db: ## Initialize database with sample data
	@echo "🗄️  Initializing database..."
	cd backend && python scripts/init_db.py
	@echo "✅ Database initialized"

verify: ## Verify setup configuration
	@echo "🔍 Verifying setup..."
	cd backend && python scripts/verify_setup.py

generate-keys: ## Generate encryption keys
	@echo "🔑 Generating keys..."
	cd backend && python scripts/generate_keys.py

test: ## Run all tests
	@echo "🧪 Running backend tests..."
	cd backend && pytest tests/ -v
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test
	@echo "✅ All tests passed"

test-backend: ## Run backend tests only
	cd backend && pytest tests/ -v

test-frontend: ## Run frontend tests only
	cd frontend && npm test

test-coverage: ## Run tests with coverage
	cd backend && pytest --cov=app --cov-report=html --cov-report=term
	@echo "📊 Coverage report: backend/htmlcov/index.html"

lint: ## Run linters
	@echo "🔍 Linting backend..."
	cd backend && ruff check app/ tests/
	cd backend && mypy app/
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint
	@echo "✅ Linting complete"

format: ## Format code
	@echo "✨ Formatting backend..."
	cd backend && ruff format app/ tests/
	@echo "✨ Formatting frontend..."
	cd frontend && npm run format
	@echo "✅ Formatting complete"

run: ## Run backend and frontend in development mode
	@echo "🚀 Starting ACG..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "API Docs: http://localhost:8000/docs"
	@$(MAKE) -j2 run-backend run-frontend

run-backend: ## Run backend only
	cd backend && uvicorn app.main:app --reload

run-frontend: ## Run frontend only
	cd frontend && npm run dev

build-frontend: ## Build frontend for production
	@echo "🏗️  Building frontend..."
	cd frontend && npm run build
	@echo "✅ Frontend built: frontend/dist/"

docker-up: ## Start services with Docker Compose
	docker-compose up -d
	@echo "✅ Services started"
	@echo "PostgreSQL: localhost:5432"
	@echo "MinIO: http://localhost:9001"

docker-down: ## Stop Docker services
	docker-compose down
	@echo "✅ Services stopped"

docker-logs: ## Show Docker logs
	docker-compose logs -f

clean: ## Clean generated files
	@echo "🧹 Cleaning..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	cd frontend && rm -rf dist/ node_modules/.vite 2>/dev/null || true
	@echo "✅ Cleaned"

reset-db: ## Reset database (⚠️  deletes all data)
	@echo "⚠️  This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd backend && alembic downgrade base && alembic upgrade head; \
		$(MAKE) init-db; \
		echo "✅ Database reset complete"; \
	fi

logs: ## Show application logs
	tail -f backend/logs/acg.log | jq .

health: ## Check application health
	@echo "🏥 Checking health..."
	@curl -s http://localhost:8000/health | jq .
	@echo ""

.DEFAULT_GOAL := help
