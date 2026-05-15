"""
Unit tests for LaLiga Predictor API.

Tests FastAPI endpoints, request/response schemas, and error handling.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.laliga_predictor.api.main import app
from src.laliga_predictor.api.schemas import (
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
    TeamsResponse,
)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestRootEndpoint:
    """Tests for GET /"""

    def test_root_returns_api_info(self, client):
        """Root endpoint should return API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestHealthEndpoint:
    """Tests for GET /health"""

    def test_health_check_returns_healthy(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "models_loaded" in data
        assert "timestamp" in data

    def test_health_response_schema(self, client):
        """Health response should conform to schema."""
        response = client.get("/health")
        assert response.status_code == 200
        # Should not raise validation error
        HealthResponse(**response.json())


class TestTeamsEndpoint:
    """Tests for GET /teams"""

    def test_teams_returns_list(self, client):
        """Teams endpoint should return list of teams."""
        response = client.get("/teams")
        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert "count" in data
        assert isinstance(data["teams"], list)
        assert len(data["teams"]) > 0
        assert data["count"] == len(data["teams"])

    def test_teams_response_schema(self, client):
        """Teams response should conform to schema."""
        response = client.get("/teams")
        assert response.status_code == 200
        # Should not raise validation error
        TeamsResponse(**response.json())

    def test_teams_are_sorted(self, client):
        """Teams should be returned in alphabetical order."""
        response = client.get("/teams")
        data = response.json()
        teams = data["teams"]
        assert teams == sorted(teams)


class TestPredictionEndpoint:
    """Tests for POST /predict"""

    def test_prediction_valid_request(self, client):
        """Valid prediction request should succeed or return 503 if models not loaded."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        # Either 200 (models loaded) or 503 (models not available)
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert data["home_team"] == "Real Madrid"
            assert data["away_team"] == "Barcelona"
            assert data["match_date"] == "2026-05-20"

    def test_prediction_response_schema(self, client):
        """Prediction response should conform to schema (if models available)."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        if response.status_code == 200:
            # Should not raise validation error
            PredictionResponse(**response.json())

    def test_prediction_includes_winner(self, client):
        """Prediction should include winner probabilities (if models available)."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        if response.status_code == 200:
            data = response.json()
            assert "winner" in data
            assert "predicted" in data["winner"]
            assert "home_prob" in data["winner"]
            assert "draw_prob" in data["winner"]
            assert "away_prob" in data["winner"]

    def test_prediction_includes_goals_ou(self, client):
        """Prediction should include goals over/under (if models available)."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        if response.status_code == 200:
            data = response.json()
            assert "goals" in data
            assert isinstance(data["goals"], dict)
            assert len(data["goals"]) > 0

    def test_prediction_includes_cards_ou(self, client):
        """Prediction should include cards over/under (if models available)."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        if response.status_code == 200:
            data = response.json()
            assert "cards" in data
            assert isinstance(data["cards"], dict)
            assert len(data["cards"]) > 0

    def test_prediction_missing_home_team(self, client):
        """Prediction without home_team should fail."""
        payload = {
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error

    def test_prediction_missing_away_team(self, client):
        """Prediction without away_team should fail."""
        payload = {
            "home_team": "Real Madrid",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 422

    def test_prediction_missing_match_date(self, client):
        """Prediction without match_date should fail."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 422

    def test_prediction_probabilities_sum_to_one(self, client):
        """Winner probabilities should sum to ~1.0 (if models available)."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        if response.status_code == 200:
            data = response.json()
            winner = data["winner"]
            total = winner["home_prob"] + winner["draw_prob"] + winner["away_prob"]
            assert 0.99 <= total <= 1.01  # Allow small floating point error

    def test_prediction_ou_probabilities_sum_to_one(self, client):
        """Over/Under probabilities should sum to ~1.0 (if models available)."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        if response.status_code == 200:
            data = response.json()

            # Check goals
            for line, probs in data["goals"].items():
                total = probs["over"] + probs["under"]
                assert 0.99 <= total <= 1.01

            # Check cards
            for line, probs in data["cards"].items():
                total = probs["over"] + probs["under"]
                assert 0.99 <= total <= 1.01

    def test_prediction_response_has_timestamp(self, client):
        """Prediction response should include generated_at timestamp (if models available)."""
        payload = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "match_date": "2026-05-20",
        }
        response = client.post("/predict", json=payload)
        if response.status_code == 200:
            data = response.json()
            assert "generated_at" in data
            # Should be a valid ISO format datetime
            datetime.fromisoformat(data["generated_at"])


class TestSwaggerDocs:
    """Tests for Swagger UI documentation."""

    def test_swagger_ui_accessible(self, client):
        """Swagger UI should be accessible at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_openapi_schema_accessible(self, client):
        """OpenAPI schema should be accessible at /openapi.json."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
