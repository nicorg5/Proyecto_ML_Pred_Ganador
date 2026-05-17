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
from fastapi.staticfiles import StaticFiles

from ..config import get_settings
from .predictor import load_features_cache
from .predictor import predict_match as run_prediction
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
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global caches
_models_cache: dict = {}
_features_df = None


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
    """Load models and features cache when API starts."""
    global _features_df
    app.state.models_loaded = _load_models()

    settings = get_settings()
    features_path = Path(settings.FEATURE_CACHE_DIR) / "features.parquet"
    _features_df = load_features_cache(features_path)

    logger.info("API startup complete")


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/api/", tags=["Info"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "LaLiga Predictor API",
        "version": "2.0.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        models_loaded=getattr(app.state, "models_loaded", {}),
        timestamp=datetime.utcnow(),
    )


@app.get("/api/teams", response_model=TeamsResponse, tags=["Info"])
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


@app.post("/api/predict", response_model=PredictionResponse, tags=["Predictions"])
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
        prediction = run_prediction(
            models=_models_cache,
            features_df=_features_df,
            home_team=request.home_team,
            away_team=request.away_team,
        )

        if prediction is None or prediction.get("winner") is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Could not build features for {request.home_team} vs {request.away_team}. "
                    "Insufficient historical data."
                ),
            )

        return PredictionResponse(
            home_team=request.home_team,
            away_team=request.away_team,
            match_date=request.match_date,
            winner=WinnerPrediction(**prediction["winner"]),
            goals=prediction["goals"],
            cards=prediction["cards"],
            model_version="v2.0",
            generated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}") from e


# Montar frontend como StaticFiles
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")


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
