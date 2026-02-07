.PHONY: help install install-dev sync test test-cov lint format pre-commit scrape train db-init db-migrate db-reset clean docker-up docker-down

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)LaLiga Predictor - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ===================================
# INSTALLATION & SETUP
# ===================================

install: ## Install production dependencies with UV
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	uv sync --no-dev

install-dev: ## Install all dependencies including dev tools
	@echo "$(BLUE)Installing all dependencies (including dev)...$(NC)"
	uv sync --all-extras

sync: ## Sync dependencies with lock file
	@echo "$(BLUE)Syncing dependencies...$(NC)"
	uv sync

# ===================================
# TESTING
# ===================================

test: ## Run tests with pytest
	@echo "$(BLUE)Running tests...$(NC)"
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	uv run pytest tests/ -v --cov=src/laliga_predictor --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

test-unit: ## Run only unit tests
	@echo "$(BLUE)Running unit tests...$(NC)"
	uv run pytest tests/unit/ -v

test-integration: ## Run only integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	uv run pytest tests/integration/ -v

# ===================================
# CODE QUALITY
# ===================================

lint: ## Run linting with ruff
	@echo "$(BLUE)Running ruff linter...$(NC)"
	uv run ruff check src/ tests/

lint-fix: ## Run linting with auto-fix
	@echo "$(BLUE)Running ruff linter with auto-fix...$(NC)"
	uv run ruff check src/ tests/ --fix

format: ## Format code with black and ruff
	@echo "$(BLUE)Formatting code with black...$(NC)"
	uv run black src/ tests/
	@echo "$(BLUE)Formatting imports with ruff...$(NC)"
	uv run ruff check src/ tests/ --select I --fix

format-check: ## Check code formatting without making changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	uv run black src/ tests/ --check
	uv run ruff check src/ tests/

type-check: ## Run mypy type checking
	@echo "$(BLUE)Running mypy type checker...$(NC)"
	uv run mypy src/

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	uv run pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	uv run pre-commit install

# ===================================
# DATA & SCRAPING
# ===================================

scrape: ## Run the web scraper to collect match data
	@echo "$(BLUE)Starting web scraper...$(NC)"
	uv run python -m src.laliga_predictor.data.scraper

scrape-season: ## Scrape specific season (usage: make scrape-season SEASON=2023-2024)
	@echo "$(BLUE)Scraping season $(SEASON)...$(NC)"
	uv run python -m src.laliga_predictor.data.scraper --season $(SEASON)

# ===================================
# MACHINE LEARNING
# ===================================

train: ## Train the ML model
	@echo "$(BLUE)Training ML model...$(NC)"
	uv run python -m src.laliga_predictor.models.train

predict: ## Make predictions (requires trained model)
	@echo "$(BLUE)Making predictions...$(NC)"
	uv run python -m src.laliga_predictor.models.predict

evaluate: ## Evaluate model performance
	@echo "$(BLUE)Evaluating model...$(NC)"
	uv run python -m src.laliga_predictor.models.evaluate

# ===================================
# DATABASE
# ===================================

db-init: ## Initialize database schema
	@echo "$(BLUE)Initializing database...$(NC)"
	uv run python database/init_db.py

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	uv run alembic upgrade head

db-migrate-create: ## Create new migration (usage: make db-migrate-create MSG="description")
	@echo "$(BLUE)Creating new migration...$(NC)"
	uv run alembic revision --autogenerate -m "$(MSG)"

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Resetting database...$(NC)"; \
		docker compose down -v; \
		docker compose up -d postgres; \
		sleep 5; \
		uv run python database/init_db.py; \
	fi

# ===================================
# DOCKER
# ===================================

docker-up: ## Start Docker containers (PostgreSQL + pgAdmin)
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	docker compose up -d
	@echo "$(GREEN)PostgreSQL running on localhost:5432$(NC)"
	@echo "$(GREEN)pgAdmin running on http://localhost:5050$(NC)"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker compose down

docker-logs: ## Show Docker container logs
	@echo "$(BLUE)Showing Docker logs...$(NC)"
	docker compose logs -f

docker-restart: ## Restart Docker containers
	@echo "$(BLUE)Restarting Docker containers...$(NC)"
	docker compose restart

# ===================================
# JUPYTER NOTEBOOK
# ===================================

notebook: ## Start Jupyter Lab
	@echo "$(BLUE)Starting Jupyter Lab...$(NC)"
	uv run jupyter lab --notebook-dir=notebooks

# ===================================
# CLEANUP
# ===================================

clean: ## Clean temporary files and cache
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ .eggs/
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: clean ## Clean everything including data and models
	@echo "$(YELLOW)Cleaning data and models...$(NC)"
	rm -rf data/processed/*
	rm -rf models/*.pkl models/*.joblib
	@echo "$(GREEN)Complete cleanup done!$(NC)"

# ===================================
# PROJECT INFO
# ===================================

info: ## Show project information
	@echo "$(BLUE)Project Information$(NC)"
	@echo "  Name:    laliga-predictor"
	@echo "  Version: 0.1.0"
	@echo "  Python:  >= 3.10"
	@echo ""
	@echo "$(BLUE)Environment$(NC)"
	@which python || echo "  Python: not found"
	@uv --version || echo "  UV: not found"
	@echo ""
	@echo "$(BLUE)Docker Status$(NC)"
	@docker compose ps 2>/dev/null || echo "  Docker Compose: not running"
