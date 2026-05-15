"""
FastAPI application for LaLiga Predictor.

Provides REST API for match predictions with Swagger documentation.
"""

import logging
from datetime import datetime
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from .schemas import (
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
    TeamsResponse,
    WinnerPrediction,
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LaLiga Predictor API",
    description="ML predictions for La Liga match outcomes",
    version="2.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model cache
_models_cache = {}


def _load_models():
    """Load trained models from disk."""
    global _models_cache
    settings = get_settings()
    model_path = Path(settings.MODEL_PATH)

    logger.info("Loading trained models...")

    models_loaded = {
        "winner": False,
        "goals_ou": 0,
        "cards_ou": 0,
    }

    try:
        # Load winner model
        winner_model_path = model_path / "result_ensemble.joblib"
        if winner_model_path.exists():
            _models_cache["winner"] = joblib.load(winner_model_path)
            models_loaded["winner"] = True
            logger.info("✅ Winner model loaded")
        else:
            logger.warning(f"⚠️ Winner model not found: {winner_model_path}")

        # Load goals O/U models
        for line in ["1.5", "2.5", "3.5"]:
            model_file = model_path / f"goals_over_{line}_xgboost.joblib"
            if model_file.exists():
                _models_cache[f"goals_{line}"] = joblib.load(model_file)
                models_loaded["goals_ou"] += 1
                logger.info(f"✅ Goals O/U {line} loaded")
            else:
                logger.warning(f"⚠️ Goals O/U {line} not found: {model_file}")

        # Load cards O/U models
        for line in ["3.5", "4.5", "5.5"]:
            model_file = model_path / f"cards_over_{line}_xgboost.joblib"
            if model_file.exists():
                _models_cache[f"cards_{line}"] = joblib.load(model_file)
                models_loaded["cards_ou"] += 1
                logger.info(f"✅ Cards O/U {line} loaded")
            else:
                logger.warning(f"⚠️ Cards O/U {line} not found: {model_file}")

    except Exception as e:
        logger.error(f"Error loading models: {e}")

    return models_loaded


# Load models on startup
@app.on_event("startup")
async def startup_event():
    """Load models when API starts."""
    app.state.models_loaded = _load_models()
    logger.info("API startup complete")


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "LaLiga Predictor API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        models_loaded=getattr(app.state, "models_loaded", {}),
        timestamp=datetime.utcnow(),
    )


@app.get("/teams", response_model=TeamsResponse, tags=["Info"])
async def get_teams():
    """Get list of available teams for LaLiga 2025/26 season."""
    teams = [
        "Alavés",
        "Athletic Club",
        "Atlético Madrid",
        "Barcelona",
        "Real Betis",
        "Celta Vigo",
        "Elche CF",
        "Espanyol",
        "Getafe",
        "Girona",
        "Levante UD",
        "Mallorca",
        "Osasuna",
        "Rayo Vallecano",
        "Real Madrid",
        "Real Oviedo",
        "Real Sociedad",
        "Sevilla",
        "Valencia",
        "Villarreal",
    ]
    return TeamsResponse(teams=sorted(teams), count=len(teams))


@app.post("/predict", response_model=PredictionResponse, tags=["Predictions"])
async def predict_match(request: PredictionRequest):
    """
    Predict match outcome (winner, goals, cards).

    Requires home_team, away_team, and match_date in YYYY-MM-DD format.
    """
    logger.info(
        f"Prediction request: {request.home_team} vs {request.away_team} "
        f"on {request.match_date}"
    )

    # Check if models are loaded
    if not _models_cache.get("winner"):
        raise HTTPException(
            status_code=503,
            detail="Winner model not loaded. Models may not be trained yet.",
        )

    try:
        # Placeholder prediction logic
        # In production, this would:
        # 1. Load match features from database
        # 2. Build features for the specific match
        # 3. Run predictions through models
        # 4. Return structured results

        winner_model = _models_cache.get("winner")
        if winner_model is None:
            raise HTTPException(status_code=503, detail="Models not ready")

        # Mock predictions for now (replace with actual prediction logic)
        return PredictionResponse(
            home_team=request.home_team,
            away_team=request.away_team,
            match_date=request.match_date,
            winner=WinnerPrediction(
                predicted="H",
                home_prob=0.45,
                draw_prob=0.30,
                away_prob=0.25,
            ),
            goals={
                "1.5": {"over": 0.80, "under": 0.20},
                "2.5": {"over": 0.60, "under": 0.40},
                "3.5": {"over": 0.35, "under": 0.65},
            },
            cards={
                "3.5": {"over": 0.70, "under": 0.30},
                "4.5": {"over": 0.55, "under": 0.45},
                "5.5": {"over": 0.25, "under": 0.75},
            },
            model_version="v2.0",
            generated_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}") from e


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
