"""
Pytest configuration and shared fixtures.
"""

import os
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return path to project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def reset_environment() -> Generator[None, None, None]:
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_match_data() -> dict:
    """Return sample match data for testing."""
    return {
        "season": "2023-2024",
        "date": "2024-01-15",
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "home_score": 2,
        "away_score": 1,
        "result": "victoria_local",
    }


@pytest.fixture
def sample_team_data() -> dict:
    """Return sample team data for testing."""
    return {
        "team_name": "Real Madrid",
        "team_code": "RMA",
        "stadium": "Santiago Bernabéu",
        "city": "Madrid",
    }
