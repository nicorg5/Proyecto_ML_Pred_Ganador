# Skill: FastAPI Production Patterns

## Propósito

Implementar endpoints FastAPI para el LaLiga Predictor siguiendo patrones de producción: carga lazy de modelos, validación robusta, manejo de errores, y rendimiento.

## Cuándo usar esta skill

- Al implementar la Fase 5 del roadmap (API + Deploy)
- Al añadir nuevos endpoints con `/new-endpoint`
- Al revisar el rendimiento de la API

## Estructura Canónica del Módulo API

```
src/laliga_predictor/api/
├── __init__.py
├── main.py              ← FastAPI app + lifespan + routers
├── dependencies.py      ← DI: predictor, db connection
├── routers/
│   ├── __init__.py
│   ├── health.py        ← GET /health, GET /model/info
│   ├── teams.py         ← GET /teams
│   └── predict.py       ← POST /predict, GET /predict/jornada/{n}
└── schemas/
    ├── __init__.py
    ├── requests.py      ← Pydantic request models
    └── responses.py     ← Pydantic response models
```

## Patterns Clave

### Pattern 1: Lifespan para carga de modelos

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import joblib
from pathlib import Path


def load_predictor() -> dict:
    """Carga todos los modelos al iniciar. Solo se ejecuta una vez."""
    models_dir = Path("models")
    return {
        "winner": joblib.load(models_dir / "winner_ensemble.joblib"),
        "goals_1.5": joblib.load(models_dir / "goals_ou_1.5_xgboost.joblib"),
        "goals_2.5": joblib.load(models_dir / "goals_ou_2.5_xgboost.joblib"),
        "goals_3.5": joblib.load(models_dir / "goals_ou_3.5_xgboost.joblib"),
        "cards_3.5": joblib.load(models_dir / "cards_ou_3.5_xgboost.joblib"),
        "cards_4.5": joblib.load(models_dir / "cards_ou_4.5_xgboost.joblib"),
        "cards_5.5": joblib.load(models_dir / "cards_ou_5.5_xgboost.joblib"),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.models = load_predictor()
    app.state.feature_builder = FeatureBuilder()  # conecta a BD
    yield
    # Shutdown (cleanup si necesario)
    pass


app = FastAPI(
    title="LaLiga Predictor API",
    version="2.0.0",
    lifespan=lifespan,
)
```

### Pattern 2: Dependency Injection

```python
# dependencies.py
from fastapi import Request


def get_models(request: Request) -> dict:
    """Inyecta modelos cargados en startup."""
    return request.app.state.models


def get_feature_builder(request: Request):
    """Inyecta el feature builder."""
    return request.app.state.feature_builder
```

### Pattern 3: Schemas con validación de equipos

```python
# schemas/requests.py
from pydantic import BaseModel, field_validator
from datetime import date
from ...data.team_names import VALID_TEAMS, normalize_team_name


class PredictRequest(BaseModel):
    home_team: str
    away_team: str
    match_date: date
    
    @field_validator("home_team", "away_team")
    @classmethod
    def validate_and_normalize_team(cls, v: str) -> str:
        normalized = normalize_team_name(v)
        if normalized is None:
            valid_list = ", ".join(sorted(VALID_TEAMS)[:10])
            raise ValueError(
                f"Equipo '{v}' no reconocido. "
                f"Ejemplos válidos: {valid_list}..."
            )
        return normalized
    
    @field_validator("match_date")
    @classmethod
    def validate_match_date(cls, v: date) -> date:
        min_date = date(2017, 8, 1)
        if v < min_date:
            raise ValueError(f"Fecha mínima: {min_date}")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "match_date": "2026-03-01"
            }
        }
    }
```

### Pattern 4: Respuestas tipadas

```python
# schemas/responses.py
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Literal


class WinnerPrediction(BaseModel):
    predicted_result: Literal["H", "D", "A"]
    home_win_prob: float = Field(ge=0.0, le=1.0)
    draw_prob: float = Field(ge=0.0, le=1.0)
    away_win_prob: float = Field(ge=0.0, le=1.0)


class OULine(BaseModel):
    over_prob: float = Field(ge=0.0, le=1.0)
    under_prob: float = Field(ge=0.0, le=1.0)


class PredictResponse(BaseModel):
    match_date: date
    home_team: str
    away_team: str
    winner: WinnerPrediction
    goals: dict[str, OULine]   # {"1.5": OULine, "2.5": OULine, "3.5": OULine}
    cards: dict[str, OULine]
    model_version: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "match_date": "2026-03-01",
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "winner": {
                    "predicted_result": "H",
                    "home_win_prob": 0.40,
                    "draw_prob": 0.32,
                    "away_win_prob": 0.28
                },
                "goals": {
                    "1.5": {"over_prob": 0.85, "under_prob": 0.15},
                    "2.5": {"over_prob": 0.60, "under_prob": 0.40},
                    "3.5": {"over_prob": 0.35, "under_prob": 0.65}
                },
                "cards": {
                    "3.5": {"over_prob": 0.70, "under_prob": 0.30},
                    "4.5": {"over_prob": 0.55, "under_prob": 0.45},
                    "5.5": {"over_prob": 0.20, "under_prob": 0.80}
                },
                "model_version": "v2.1",
                "generated_at": "2026-03-01T10:00:00Z"
            }
        }
    }
```

### Pattern 5: Router con manejo de errores

```python
# routers/predict.py
from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import get_models, get_feature_builder
from ..schemas.requests import PredictRequest
from ..schemas.responses import PredictResponse

router = APIRouter(prefix="/predict", tags=["predictions"])


@router.post(
    "",
    response_model=PredictResponse,
    summary="Predict match outcome",
    description="Predicts winner, goals O/U and cards O/U for a match."
)
async def predict_match(
    request: PredictRequest,
    models: dict = Depends(get_models),
    feature_builder = Depends(get_feature_builder),
) -> PredictResponse:
    try:
        # Construir features
        features = feature_builder.build_for_match(
            request.home_team,
            request.away_team,
            request.match_date,
        )
        
        # Predecir ganador
        winner_probs = models["winner"].predict_proba(features)[0]
        predicted_result = ["H", "D", "A"][winner_probs.argmax()]
        
        # Predecir O/U
        def get_ou(key: str) -> dict:
            over_prob = float(models[key].predict_proba(features)[0][1])
            return {"over_prob": over_prob, "under_prob": 1 - over_prob}
        
        return PredictResponse(
            match_date=request.match_date,
            home_team=request.home_team,
            away_team=request.away_team,
            winner={
                "predicted_result": predicted_result,
                "home_win_prob": float(winner_probs[0]),
                "draw_prob": float(winner_probs[1]),
                "away_win_prob": float(winner_probs[2]),
            },
            goals={
                "1.5": get_ou("goals_1.5"),
                "2.5": get_ou("goals_2.5"),
                "3.5": get_ou("goals_3.5"),
            },
            cards={
                "3.5": get_ou("cards_3.5"),
                "4.5": get_ou("cards_4.5"),
                "5.5": get_ou("cards_5.5"),
            },
            model_version="v2.1",
        )
    
    except FeatureNotAvailableError as e:
        raise HTTPException(
            status_code=422,
            detail=f"No hay suficientes datos históricos para predecir: {e}"
        )
    except Exception as e:
        # Log internamente pero no exponer stack trace
        logger.exception(f"Error predicting {request.home_team} vs {request.away_team}")
        raise HTTPException(status_code=500, detail="Error interno del modelo")
```

### Pattern 6: Health check robusto

```python
# routers/health.py
from fastapi import APIRouter, Depends
from ..dependencies import get_models, get_feature_builder
import time

router = APIRouter(tags=["system"])


@router.get("/health", summary="Health check")
async def health(models: dict = Depends(get_models)):
    return {
        "status": "healthy",
        "models_loaded": list(models.keys()),
        "model_count": len(models),
        "timestamp": time.time(),
    }


@router.get("/model/info", summary="Model information")
async def model_info(models: dict = Depends(get_models)):
    return {
        "version": "v2.1",
        "targets": {
            "winner": "H/D/A classification",
            "goals": ["1.5", "2.5", "3.5"],
            "cards": ["3.5", "4.5", "5.5"],
        },
        "train_seasons": "2017/18 - 2023/24",
        "test_season": "2025/26",
        "metrics": {
            "winner_accuracy": 0.568,
            "goals_2.5_auc": 0.591,
            "cards_4.5_auc": 0.578,
        }
    }
```

## Configuración para Producción

```python
# main.py (producción)
import logging
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LaLiga Predictor API",
    version="2.0.0",
    lifespan=lifespan,
    # En producción, deshabilitar docs si es privado:
    # docs_url=None, redoc_url=None
)

# CORS para la web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tu-webapp.com", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Variables de Entorno Requeridas

```bash
# .env (nunca commitear)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=laliga_soccerdata
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
MODELS_DIR=./models          # Ruta a los modelos .joblib
API_VERSION=v2.1
LOG_LEVEL=INFO
```

## Comandos de Desarrollo

```bash
# Levantar en modo desarrollo (hot reload)
uv run uvicorn src.laliga_predictor.api.main:app --reload --port 8000

# Levantar con Docker
docker build -t laliga-api . && docker run -p 8000:8000 --env-file .env laliga-api

# Probar endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"home_team":"Real Madrid","away_team":"Barcelona","match_date":"2026-03-01"}'

# Ver documentación interactiva
open http://localhost:8000/docs
```
