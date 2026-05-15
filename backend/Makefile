.PHONY: help install install-dev sync test test-cov test-unit test-integration test-integration-db test-integration-ml lint format pre-commit scrape train db-init db-migrate db-reset clean docker-up docker-down sd-create-db sd-init sd-init-drop sd-etl sd-etl-mh sd-etl-espn sd-etl-fbref-schedule sd-etl-fbref-stats sd-etl-fbref-stats-type sd-etl-players sd-etl-shots sd-etl-standings sd-etl-season sd-validate sd-status ml-features ml-select-features ml-tune ml-train ml-train-winner ml-train-goals ml-train-cards ml-predict ml-predict-jornada ml-update ml-pipeline mlflow-ui mlflow-clean api-run api-check

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

test-integration: ## Run only integration tests (includes DB tests if PostgreSQL is running)
	@echo "$(BLUE)Running integration tests...$(NC)"
	uv run pytest tests/integration/ -v

test-integration-db: ## Run integration tests that require PostgreSQL (requires Docker running)
	@echo "$(BLUE)Running database integration tests...$(NC)"
	@echo "$(YELLOW)Ensure PostgreSQL is running: make docker-up$(NC)"
	uv run pytest tests/integration/test_etl_database.py -v -m integration

test-integration-ml: ## Run ML pipeline integration tests (no database required)
	@echo "$(BLUE)Running ML pipeline integration tests...$(NC)"
	uv run pytest tests/integration/test_ml_pipeline.py -v

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
# MACHINE LEARNING (soccerdata pipeline)
# ===================================

ml-features: ## Build ML features from database -> data/processed/features.parquet
	@echo "$(BLUE)Building ML features from database...$(NC)"
	uv run python -m src.laliga_predictor.features.feature_engineering

ml-select-features: ## Run feature selection (importance + correlation filtering)
	@echo "$(BLUE)Running feature selection...$(NC)"
	uv run python -m src.laliga_predictor.features.feature_selection --target all

ml-validate-features: ## Validate features.parquet quality
	@echo "$(BLUE)Validating features...$(NC)"
	uv run python -m src.laliga_predictor.data.validate_features

ml-tune: ## Run Optuna hyperparameter tuning (TARGET=all|winner|goals-ou|cards-ou)
	@echo "$(BLUE)Running Optuna hyperparameter tuning...$(NC)"
	uv run python -m src.laliga_predictor.models.tuning --target $(or $(TARGET),all)

ml-train: ## Train ML models (TARGET=all|winner|goals-ou|cards-ou MODEL=all)
	@echo "$(BLUE)Training all ML models...$(NC)"
	uv run python -m src.laliga_predictor.models.train --target all --model all

ml-train-winner: ## Train winner prediction models only (baseline + RF + XGBoost + Ensemble)
	@echo "$(BLUE)Training winner prediction models...$(NC)"
	uv run python -m src.laliga_predictor.models.train --target winner --model all

ml-train-goals: ## Train total goals prediction models only
	@echo "$(BLUE)Training total goals prediction models...$(NC)"
	uv run python -m src.laliga_predictor.models.train --target goals --model all

ml-train-cards: ## Train total cards prediction models only
	@echo "$(BLUE)Training total cards prediction models...$(NC)"
	uv run python -m src.laliga_predictor.models.train --target cards --model all

ml-predict: ## Predict a match (HOME=team AWAY=team DATE=YYYY-MM-DD)
	@echo "$(BLUE)Predicting match: $(HOME) vs $(AWAY) on $(DATE)...$(NC)"
	uv run python -m src.laliga_predictor.models.predict --home "$(HOME)" --away "$(AWAY)" --date "$(DATE)"

ml-predict-jornada: ## Predict a full jornada (JORNADA=N SEASON=2526)
	@echo "$(BLUE)Predicting jornada $(JORNADA) (season $(or $(SEASON),2526))...$(NC)"
	uv run python -m src.laliga_predictor.models.predict_jornada --jornada $(JORNADA) $(if $(SEASON),--season $(SEASON))

ml-update: ## Update DB + features for current season (SEASON=2526)
	@echo "$(BLUE)Updating data for season $(or $(SEASON),2526)...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step match-history --seasons $(or $(SEASON),2526) --force
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step standings --seasons $(or $(SEASON),2526) --force
	uv run python -m src.laliga_predictor.features.feature_engineering
	@echo "$(GREEN)Data updated! Ready to predict.$(NC)"

ml-pipeline: ml-features ml-validate-features ml-select-features ml-train ## Run full ML pipeline (features + validate + select + train)
	@echo "$(GREEN)ML pipeline complete!$(NC)"

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
# SOCCERDATA
# ===================================

sd-create-db: ## Create the soccerdata database in PostgreSQL
	@echo "$(BLUE)Creating soccerdata database...$(NC)"
	@uv run python -c "import psycopg2; from src.laliga_predictor.config import get_settings; s = get_settings(); conn = psycopg2.connect(host=s.SD_DB_HOST, port=s.SD_DB_PORT, database='postgres', user=s.SD_DB_USER, password=s.SD_DB_PASSWORD); conn.autocommit = True; cur = conn.cursor(); cur.execute(\"SELECT 1 FROM pg_database WHERE datname = 'laliga_soccerdata'\"); r = cur.fetchone(); exec('if not r: cur.execute(\"CREATE DATABASE laliga_soccerdata\"); print(\"Database laliga_soccerdata created\")\nelse: print(\"Database laliga_soccerdata already exists\")'); conn.close()"

sd-init: sd-create-db ## Initialize soccerdata database schema
	@echo "$(BLUE)Initializing soccerdata database schema...$(NC)"
	uv run python -m src.laliga_predictor.data.sd_db_init

sd-init-drop: sd-create-db ## Drop and recreate soccerdata schema (WARNING: deletes data)
	@echo "$(RED)WARNING: Dropping all soccerdata tables!$(NC)"
	uv run python -m src.laliga_predictor.data.sd_db_init --drop

sd-etl: ## Run full soccerdata ETL pipeline (all seasons, all steps)
	@echo "$(BLUE)Running full soccerdata ETL pipeline...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step all

sd-etl-mh: ## Load MatchHistory data only (fast, no rate limit)
	@echo "$(BLUE)Loading MatchHistory data...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step match-history

sd-etl-espn: ## Load ESPN advanced match stats (possession, passes, tackles, etc.)
	@echo "$(BLUE)Loading ESPN match stats...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step espn-stats

sd-etl-fbref-schedule: ## Load FBref schedule (xG data)
	@echo "$(BLUE)Loading FBref schedule...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step fbref-schedule

sd-etl-fbref-stats: ## Load FBref advanced team match stats (rate-limited)
	@echo "$(BLUE)Loading FBref advanced team stats...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step fbref-stats

sd-etl-fbref-stats-type: ## Load specific FBref stat type (STAT_TYPE=shooting)
	@echo "$(BLUE)Loading FBref stat type: $(STAT_TYPE)...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step fbref-stats --stat-types $(STAT_TYPE)

sd-etl-players: ## Load player match stats from FBref (optional)
	@echo "$(BLUE)Loading FBref player match stats...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step player-stats

sd-etl-shots: ## Load shot events from FBref (optional)
	@echo "$(BLUE)Loading FBref shot events...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step shot-events

sd-etl-standings: ## Compute standings from match results
	@echo "$(BLUE)Computing standings...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step standings

sd-etl-season: ## Run ETL for specific season (SEASON=2324)
	@echo "$(BLUE)Running ETL for season $(SEASON)...$(NC)"
	uv run python -m src.laliga_predictor.data.etl_soccerdata --step all --seasons $(SEASON)

sd-validate: ## Validate soccerdata database
	@echo "$(BLUE)Validating soccerdata database...$(NC)"
	uv run python -m src.laliga_predictor.data.validate_soccerdata

sd-status: ## Show soccerdata database statistics
	@echo "$(BLUE)Soccerdata database status:$(NC)"
	uv run python -m src.laliga_predictor.data.sd_db_init --verify

# ===================================
# MLFLOW
# ===================================

mlflow-ui: ## Start MLflow Tracking Server (http://localhost:5000)
	@echo "$(BLUE)Starting MLflow Tracking Server...$(NC)"
	./scripts/start_mlflow.sh

mlflow-clean: ## Clean MLflow database and artifacts
	@echo "$(YELLOW)Cleaning MLflow data...$(NC)"
	rm -rf mlflow.db mlruns/
	@echo "$(GREEN)MLflow data cleaned$(NC)"

# ===================================
# API (FastAPI)
# ===================================

api-run: ## Start FastAPI server (http://localhost:8000)
	@echo "$(BLUE)Starting FastAPI server...$(NC)"
	@echo "API docs available at http://localhost:8000/docs"
	uv run uvicorn src.laliga_predictor.api.main:app --reload --host 0.0.0.0 --port 8000

api-check: ## Check API health
	@echo "$(BLUE)Checking API health...$(NC)"
	curl -s http://localhost:8000/health | python -m json.tool || echo "API not running"

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
