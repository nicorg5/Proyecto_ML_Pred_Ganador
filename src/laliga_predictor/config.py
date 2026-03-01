"""
Configuration module for LaLiga Predictor.

This module provides centralized configuration management using Pydantic Settings.
Loads configuration from environment variables and .env files.
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        DB_HOST: PostgreSQL host address
        DB_PORT: PostgreSQL port number
        DB_NAME: Database name
        DB_USER: Database user
        DB_PASSWORD: Database password
        FBREF_BASE_URL: Base URL for FBRef website
        SCRAPING_DELAY: Delay between requests in seconds
        MAX_RETRIES: Maximum number of retries for failed requests
        REQUEST_TIMEOUT: Request timeout in seconds
        MODEL_PATH: Path to save trained models
        RANDOM_STATE: Random seed for reproducibility
        TEST_SIZE: Train/test split ratio
        CV_FOLDS: Number of cross-validation folds
        LOG_LEVEL: Logging level
        LOG_FILE: Path to log file
        ENVIRONMENT: Application environment (development/staging/production)
        DEBUG: Enable debug mode
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database Configuration
    DB_HOST: str = Field(default="localhost", description="PostgreSQL host")
    DB_PORT: int = Field(default=5432, description="PostgreSQL port")
    DB_NAME: str = Field(default="laliga_predictor", description="Database name")
    DB_USER: str = Field(default="laliga_user", description="Database user")
    DB_PASSWORD: str = Field(default="", description="Database password")

    # API Football Configuration
    API_FOOTBALL_KEY: str = Field(default="", description="API-Football API key")
    API_FOOTBALL_BASE_URL: str = Field(
        default="https://v3.football.api-sports.io",
        description="API-Football base URL",
    )
    LALIGA_LEAGUE_ID: int = Field(default=140, description="LaLiga league ID")
    API_REQUEST_TIMEOUT: int = Field(
        default=30, ge=5, le=120, description="API request timeout"
    )
    API_MAX_RETRIES: int = Field(default=3, ge=1, le=10, description="API max retries")
    API_RETRY_DELAY: int = Field(default=2, ge=1, description="API retry delay")

    # Soccerdata Database Configuration
    SD_DB_HOST: str = Field(default="localhost", description="Soccerdata PostgreSQL host")
    SD_DB_PORT: int = Field(default=5432, description="Soccerdata PostgreSQL port")
    SD_DB_NAME: str = Field(default="laliga_soccerdata", description="Soccerdata database name")
    SD_DB_USER: str = Field(default="laliga_user", description="Soccerdata database user")
    SD_DB_PASSWORD: str = Field(default="", description="Soccerdata database password")

    # Soccerdata Scraping Configuration
    SD_SEASONS: str = Field(
        default="1718,1819,1920,2021,2122,2223,2324,2425",
        description="Comma-separated seasons for soccerdata (format: YYYY)",
    )

    # Web Scraping Configuration (Legacy)
    FBREF_BASE_URL: str = Field(
        default="https://fbref.com/en/", description="FBRef base URL"
    )
    SCRAPING_DELAY: int = Field(
        default=2, ge=0, description="Delay between requests in seconds"
    )
    MAX_RETRIES: int = Field(default=3, ge=1, le=10, description="Maximum retries")
    REQUEST_TIMEOUT: int = Field(
        default=30, ge=5, le=120, description="Request timeout in seconds"
    )

    # Machine Learning Configuration
    MODEL_PATH: Path = Field(default=Path("models/"), description="Model save path")
    RANDOM_STATE: int = Field(default=42, description="Random seed")
    TEST_SIZE: float = Field(
        default=0.2, ge=0.1, le=0.5, description="Test set size ratio"
    )
    CV_FOLDS: int = Field(
        default=5, ge=2, le=10, description="Cross-validation folds"
    )

    # ML Pipeline Configuration
    ROLLING_WINDOWS: str = Field(
        default="3,5,10",
        description="Comma-separated rolling window sizes for feature engineering",
    )
    TRAIN_SEASONS: str = Field(
        default="1718,1819,1920,2021,2122,2223,2324",
        description="Seasons for training set",
    )
    VAL_SEASONS: str = Field(
        default="2425",
        description="Seasons for validation set",
    )
    TEST_SEASONS: str = Field(
        default="2526",
        description="Seasons for test set",
    )
    FEATURE_CACHE_DIR: Path = Field(
        default=Path("data/processed"),
        description="Directory for cached feature files",
    )
    N_TUNING_TRIALS: int = Field(
        default=50, ge=10, le=500,
        description="Number of Optuna hyperparameter tuning trials",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: Path = Field(
        default=Path("logs/laliga_predictor.log"), description="Log file path"
    )

    # Application Configuration
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=False, description="Debug mode")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that LOG_LEVEL is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{v}'"
            )
        return v_upper

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate that ENVIRONMENT is a valid environment name."""
        valid_envs = ["development", "staging", "production", "test"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(
                f"ENVIRONMENT must be one of {valid_envs}, got '{v}'"
            )
        return v_lower

    @field_validator("MODEL_PATH", "LOG_FILE")
    @classmethod
    def create_path_if_not_exists(cls, v: Path) -> Path:
        """Create directory path if it doesn't exist."""
        if isinstance(v, str):
            v = Path(v)
        v.parent.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def database_url(self) -> str:
        """
        Construct the database URL for SQLAlchemy.

        Returns:
            PostgreSQL connection string
        """
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_async(self) -> str:
        """
        Construct the async database URL for SQLAlchemy.

        Returns:
            PostgreSQL async connection string
        """
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def soccerdata_database_url(self) -> str:
        """Construct the database URL for the soccerdata database."""
        return (
            f"postgresql://{self.SD_DB_USER}:{self.SD_DB_PASSWORD}"
            f"@{self.SD_DB_HOST}:{self.SD_DB_PORT}/{self.SD_DB_NAME}"
        )

    def setup_logging(self) -> None:
        """
        Configure application logging.

        Sets up both file and console logging handlers with appropriate formatters.
        """
        # Create logs directory if it doesn't exist
        self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler(self.LOG_FILE),
                logging.StreamHandler(),
            ],
        )

        # Set third-party loggers to WARNING to reduce noise
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    def validate_database_connection(self) -> bool:
        """
        Validate database connection parameters.

        Returns:
            True if all required database parameters are set

        Raises:
            ValueError: If required database parameters are missing
        """
        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is required but not set")

        if not self.DB_USER:
            raise ValueError("DB_USER is required but not set")

        return True

    def validate_api_football(self) -> bool:
        """
        Validate API Football configuration.

        Returns:
            True if API key is set

        Raises:
            ValueError: If API key is missing
        """
        if not self.API_FOOTBALL_KEY or self.API_FOOTBALL_KEY == "your_api_key_here":
            raise ValueError(
                "API_FOOTBALL_KEY is required. Get your free key from https://www.api-football.com/"
            )
        return True

    def get_api_headers(self) -> dict[str, str]:
        """
        Get headers for API Football requests.

        Returns:
            Dictionary with API headers
        """
        return {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": self.API_FOOTBALL_KEY,
        }

    def get_user_agent(self) -> str:
        """
        Get user agent string for web scraping.

        Returns:
            User agent string
        """
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.

    Returns:
        Settings instance

    Example:
        >>> settings = get_settings()
        >>> print(settings.database_url)
        postgresql://user:password@localhost:5432/laliga_predictor
    """
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.setup_logging()
    return _settings


# Convenience function to reload settings (useful for testing)
def reload_settings() -> Settings:
    """
    Force reload of settings from environment.

    Returns:
        New Settings instance
    """
    global _settings
    _settings = Settings()
    _settings.setup_logging()
    return _settings
