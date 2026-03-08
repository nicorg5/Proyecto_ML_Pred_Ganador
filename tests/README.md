# Testing Strategy

This document explains the testing approach for LaLiga Predictor.

## 📋 Testing Pyramid

We follow a hybrid testing strategy:

```
         ▲
        / \
       /   \  E2E Tests (ETL with real PostgreSQL)
      /     \
     /_______\
    /         \
   /           \  Integration Tests (ML pipeline with synthetic data)
  /             \
 /_______________\
/                 \
/                   \  Unit Tests (isolated logic, no external dependencies)
/_____________________\
```

## 🧪 Test Types

### 1. Unit Tests (`tests/unit/`)

**Purpose**: Test individual functions and classes in isolation

**Characteristics**:
- ✅ Fast (milliseconds)
- ✅ No external dependencies (DB, network, filesystem)
- ✅ Use mocks and fixtures
- ✅ High coverage of edge cases

**Files**:
- `test_config.py` - Configuration management
- `test_features.py` - Feature engineering functions
- `test_models.py` - Model classes and methods
- `test_scraper.py` - Web scraping utilities

**Run**:
```bash
make test-unit
# or
uv run pytest tests/unit/ -v
```

---

### 2. Integration Tests - ML Pipeline (`tests/integration/test_ml_pipeline.py`)

**Purpose**: Test the full ML pipeline end-to-end with synthetic data

**Characteristics**:
- ✅ Fast (seconds)
- ✅ Uses synthetic data generated in `conftest.py`
- ✅ Tests feature engineering → training → prediction flow
- ✅ No database required
- ✅ Deterministic (same random seed = same results)

**What it tests**:
- Feature engineering from DataFrames
- Model training and prediction
- Evaluation metrics computation
- Feature store (save/load parquet)

**Run**:
```bash
make test-integration-ml
# or
uv run pytest tests/integration/test_ml_pipeline.py -v
```

---

### 3. Integration Tests - ETL (`tests/integration/test_etl_database.py`)

**Purpose**: Test ETL operations with real PostgreSQL database

**Characteristics**:
- ⚠️ Slower (seconds to minutes)
- ⚠️ Requires PostgreSQL running
- ✅ Tests real SQL queries and schema
- ✅ Validates database constraints
- ✅ Uses test database (`laliga_soccerdata_test`)

**What it tests**:
- Schema creation and table structure
- Data insertion (seasons, teams, matches, standings)
- Database queries and views
- ETL logging
- Primary keys and constraints

**Requirements**:
- PostgreSQL must be running (via Docker or locally)
- Environment variables must be set

**Run**:
```bash
# First, start PostgreSQL
make docker-up

# Then run ETL tests
make test-integration-db
# or
uv run pytest tests/integration/test_etl_database.py -v
```

---

## 🚀 Running Tests

### All tests
```bash
make test
```

### By category
```bash
make test-unit              # Unit tests only (fast)
make test-integration-ml    # ML pipeline tests (synthetic data)
make test-integration-db    # ETL tests (requires PostgreSQL)
make test-integration       # All integration tests
```

### With coverage
```bash
make test-cov
# Opens htmlcov/index.html
```

---

## 🐳 Local Setup for Database Tests

### Option 1: Docker (Recommended)

```bash
# Start PostgreSQL container
make docker-up

# Verify it's running
docker ps | grep postgres

# Run database tests
make test-integration-db

# Stop when done
make docker-down
```

### Option 2: Local PostgreSQL

If you have PostgreSQL installed locally:

```bash
# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=laliga_soccerdata_test
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres

# Create test database (if it doesn't exist)
createdb laliga_soccerdata_test

# Run tests
make test-integration-db
```

---

## 🤖 GitHub Actions CI/CD

The CI pipeline runs automatically on push/PR and includes:

1. **Lint** - Ruff + Black code quality checks
2. **Test**:
   - ✅ PostgreSQL service container starts automatically
   - ✅ Schema initialized before integration tests
   - ✅ Unit tests run (no DB)
   - ✅ Integration tests run (ML + ETL)
   - ✅ Coverage uploaded to Codecov
3. **Type Check** - Mypy static analysis
4. **Security** - Bandit vulnerability scan
5. **Build** - Package build (master only)

**PostgreSQL in CI**:
- Service: `postgres:16-alpine`
- Database: `laliga_soccerdata_test`
- User: `postgres` / Password: `postgres`
- Port: `5432`

See [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) for details.

---

## 📝 Test Fixtures

### Synthetic Data (for ML tests)

Defined in `conftest.py`:
- `synthetic_matches` - 2 seasons, 4 teams, 24 matches
- `synthetic_advanced_stats` - ESPN-style advanced stats
- `synthetic_standings` - Computed league tables
- `synthetic_3season_*` - 3 seasons for train/val/test splits

### Database (for ETL tests)

- `test_db_connection` - Raw PostgreSQL connection
  - Scope: module
  - Cleanup: Truncates tables after module
  - Skips if PostgreSQL unavailable

- `test_db_with_schema` - Connection with schema initialized
  - Extends `test_db_connection`
  - Runs `sd_db_init` to create tables/views
  - Ready for data insertion

---

## 🎯 Best Practices

### When writing unit tests:
- ✅ Test one thing per test
- ✅ Use descriptive test names (`test_feature_handles_missing_data`)
- ✅ Mock external dependencies
- ✅ Test edge cases and error conditions

### When writing integration tests:
- ✅ Use synthetic data for ML pipeline tests
- ✅ Use real PostgreSQL only for ETL tests
- ✅ Clean up test data in fixtures
- ✅ Make tests idempotent (can run multiple times)

### When writing database tests:
- ✅ Use test database (`laliga_soccerdata_test`)
- ✅ Never connect to production database
- ✅ Use unique test data (e.g., season "9999")
- ✅ Let fixtures handle cleanup

---

## 🔍 Debugging Failed Tests

### Test is skipped with "PostgreSQL not available"
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# If not, start it
make docker-up

# Check logs
make docker-logs
```

### Test fails with "relation does not exist"
```bash
# Schema might not be initialized
# The fixture should handle this, but you can manually run:
uv run python -m src.laliga_predictor.data.sd_db_init
```

### Test fails with connection refused
```bash
# Check environment variables
env | grep POSTGRES

# Set them if missing
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=laliga_soccerdata_test
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
```

### Test passes locally but fails in CI
- Check if test depends on local files not in git
- Verify environment variables are set in `.github/workflows/ci.yml`
- Check if test makes assumptions about system state

---

## 📊 Current Test Coverage

As of latest run:
- **Total tests**: 111+ passing
- **Unit tests**: ~80 tests
- **Integration tests (ML)**: ~20 tests
- **Integration tests (ETL)**: ~15 tests

Run `make test-cov` to see detailed coverage report.

---

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [GitHub Actions PostgreSQL Service](https://docs.github.com/en/actions/using-containerized-services/creating-postgresql-service-containers)