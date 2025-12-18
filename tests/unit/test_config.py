"""
Unit tests for configuration module.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.laliga_predictor.config import Settings, get_settings, reload_settings


class TestSettings:
    """Test Settings class."""

    def test_default_settings(self) -> None:
        """Test that default settings are loaded correctly."""
        settings = Settings()

        assert settings.DB_HOST == "localhost"
        assert settings.DB_PORT == 5432
        assert settings.SCRAPING_DELAY == 2
        assert settings.RANDOM_STATE == 42

    def test_database_url_construction(self) -> None:
        """Test database URL is constructed correctly."""
        settings = Settings(
            DB_HOST="localhost",
            DB_PORT=5432,
            DB_NAME="test_db",
            DB_USER="test_user",
            DB_PASSWORD="test_pass",
        )

        expected_url = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert settings.database_url == expected_url

    def test_database_url_async_construction(self) -> None:
        """Test async database URL is constructed correctly."""
        settings = Settings(
            DB_HOST="localhost",
            DB_PORT=5432,
            DB_NAME="test_db",
            DB_USER="test_user",
            DB_PASSWORD="test_pass",
        )

        expected_url = (
            "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
        )
        assert settings.database_url_async == expected_url

    def test_log_level_validation(self) -> None:
        """Test log level validation."""
        # Valid log levels
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            settings = Settings(LOG_LEVEL=level)
            assert settings.LOG_LEVEL == level.upper()

        # Invalid log level
        with pytest.raises(ValidationError):
            Settings(LOG_LEVEL="INVALID")

    def test_environment_validation(self) -> None:
        """Test environment validation."""
        # Valid environments
        valid_envs = ["development", "staging", "production", "test"]
        for env in valid_envs:
            settings = Settings(ENVIRONMENT=env)
            assert settings.ENVIRONMENT == env.lower()

        # Invalid environment
        with pytest.raises(ValidationError):
            Settings(ENVIRONMENT="invalid_env")

    def test_scraping_delay_constraints(self) -> None:
        """Test scraping delay constraints."""
        # Valid delay
        settings = Settings(SCRAPING_DELAY=5)
        assert settings.SCRAPING_DELAY == 5

        # Negative delay should fail
        with pytest.raises(ValidationError):
            Settings(SCRAPING_DELAY=-1)

    def test_test_size_constraints(self) -> None:
        """Test test size constraints."""
        # Valid test size
        settings = Settings(TEST_SIZE=0.3)
        assert settings.TEST_SIZE == 0.3

        # Out of range should fail
        with pytest.raises(ValidationError):
            Settings(TEST_SIZE=0.9)

        with pytest.raises(ValidationError):
            Settings(TEST_SIZE=0.05)

    def test_validate_database_connection(self) -> None:
        """Test database connection validation."""
        # Valid connection
        settings = Settings(DB_USER="user", DB_PASSWORD="password")
        assert settings.validate_database_connection() is True

        # Missing password
        settings_no_pass = Settings(DB_PASSWORD="")
        with pytest.raises(ValueError, match="DB_PASSWORD is required"):
            settings_no_pass.validate_database_connection()

    def test_user_agent_generation(self) -> None:
        """Test user agent string generation."""
        settings = Settings()
        user_agent = settings.get_user_agent()

        assert "Mozilla" in user_agent
        assert "Chrome" in user_agent
        assert len(user_agent) > 0

    def test_path_creation(self) -> None:
        """Test that paths are created automatically."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_models" / "model.pkl"
            log_file = Path(tmpdir) / "test_logs" / "app.log"

            settings = Settings(MODEL_PATH=model_path, LOG_FILE=log_file)

            # Parent directories should be created
            assert settings.MODEL_PATH.parent.exists()
            assert settings.LOG_FILE.parent.exists()


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_singleton(self) -> None:
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reload_settings(self) -> None:
        """Test settings reload functionality."""
        settings1 = get_settings()
        settings2 = reload_settings()

        # Should be different instances after reload
        assert settings1 is not settings2


class TestEnvironmentVariables:
    """Test loading from environment variables."""

    @patch.dict(
        os.environ,
        {
            "DB_HOST": "custom_host",
            "DB_PORT": "5433",
            "SCRAPING_DELAY": "5",
            "RANDOM_STATE": "123",
        },
    )
    def test_load_from_env(self) -> None:
        """Test loading settings from environment variables."""
        settings = Settings()

        assert settings.DB_HOST == "custom_host"
        assert settings.DB_PORT == 5433
        assert settings.SCRAPING_DELAY == 5
        assert settings.RANDOM_STATE == 123
