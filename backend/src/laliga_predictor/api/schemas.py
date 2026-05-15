"""
Pydantic schemas for LaLiga Predictor API.

Defines request/response models for type validation and documentation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Request model for match prediction."""

    home_team: str = Field(..., min_length=1, example="Real Madrid")
    away_team: str = Field(..., min_length=1, example="Barcelona")
    match_date: str = Field(..., example="2026-05-20", description="Date in YYYY-MM-DD format")

    class Config:
        json_schema_extra = {
            "example": {
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "match_date": "2026-05-20",
            }
        }


class WinnerPrediction(BaseModel):
    """Winner prediction (H/D/A)."""

    predicted: str = Field(..., example="H", description="H (home), D (draw), A (away)")
    home_prob: float = Field(..., ge=0, le=1, example=0.45)
    draw_prob: float = Field(..., ge=0, le=1, example=0.30)
    away_prob: float = Field(..., ge=0, le=1, example=0.25)


class OverUnderPrediction(BaseModel):
    """Over/Under prediction for a line."""

    over: float = Field(..., ge=0, le=1, example=0.65, description="Probability of OVER")
    under: float = Field(..., ge=0, le=1, example=0.35, description="Probability of UNDER")


class PredictionResponse(BaseModel):
    """Response model for match prediction."""

    home_team: str = Field(..., example="Real Madrid")
    away_team: str = Field(..., example="Barcelona")
    match_date: str = Field(..., example="2026-05-20")
    winner: WinnerPrediction
    goals: dict[str, OverUnderPrediction] = Field(
        ..., example={"1.5": {"over": 0.80, "under": 0.20}}
    )
    cards: dict[str, OverUnderPrediction] = Field(
        ..., example={"4.5": {"over": 0.55, "under": 0.45}}
    )
    model_version: str = Field(..., example="v2.1")
    generated_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., example="healthy")
    models_loaded: dict[str, int | bool] = Field(
        ...,
        example={
            "winner": True,
            "goals_ou": 3,
            "cards_ou": 3,
        },
    )
    timestamp: datetime


class TeamsResponse(BaseModel):
    """List of available teams."""

    teams: list[str] = Field(..., example=["Real Madrid", "Barcelona", "Atlético Madrid"])
    count: int = Field(..., example=20)
