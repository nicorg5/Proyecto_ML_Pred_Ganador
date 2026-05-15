# /new-endpoint — Crear Nuevo Endpoint FastAPI

Implementa un nuevo endpoint en la API REST de LaLiga Predictor siguiendo los estándares del proyecto: validación Pydantic, manejo de errores, tests y documentación Swagger.

## Uso

```
/new-endpoint <método> <ruta> <descripción>
```

**Ejemplos:**
```
/new-endpoint GET /teams "Lista de equipos disponibles con sus IDs"
/new-endpoint POST /predict "Predicción de partido individual"
/new-endpoint GET /predict/jornada/{jornada_num} "Predicción de jornada completa"
/new-endpoint GET /model/info "Información del modelo activo (versión, métricas)"
```

## Instrucciones para Claude

### Paso 1: Verificar que la API existe

```bash
ls src/laliga_predictor/api/ 2>/dev/null || echo "⚠️ Módulo API no existe aún"
```

Si no existe, crear la estructura base primero:
```bash
mkdir -p src/laliga_predictor/api
touch src/laliga_predictor/api/__init__.py
```

### Paso 2: Revisar el contrato en CLAUDE.md

Antes de implementar, verificar si el endpoint tiene contrato definido en `CLAUDE.md` (sección "Diseño API"). Si existe, seguirlo exactamente. Si no existe, definir el contrato aquí antes de implementar.

### Paso 3: Implementar el endpoint

**Estructura del módulo API:**

```
src/laliga_predictor/api/
├── __init__.py
├── main.py          ← App FastAPI + routers
├── routers/
│   ├── __init__.py
│   ├── predict.py   ← /predict, /predict/jornada
│   ├── teams.py     ← /teams
│   └── health.py    ← /health, /model/info
├── schemas/
│   ├── __init__.py
│   ├── requests.py  ← Pydantic request models
│   └── responses.py ← Pydantic response models
└── dependencies.py  ← Inyección de dependencias (modelos ML, DB)
```

**Template de endpoint:**

```python
# src/laliga_predictor/api/routers/<router>.py
from fastapi import APIRouter, Depends, HTTPException
from ..schemas.requests import <RequestSchema>
from ..schemas.responses import <ResponseSchema>
from ..dependencies import get_predictor

router = APIRouter(prefix="/<prefix>", tags=["<tag>"])


@router.<method>("/<path>",
    response_model=<ResponseSchema>,
    summary="<descripción corta>",
    description="<descripción larga para Swagger>",
)
async def <nombre_función>(
    request: <RequestSchema>,
    predictor=Depends(get_predictor),
) -> <ResponseSchema>:
    """
    <Descripción del endpoint para docstring>.
    
    Raises:
        HTTPException 422: Si los datos de entrada son inválidos
        HTTPException 404: Si el equipo no existe
        HTTPException 500: Error interno del modelo
    """
    try:
        result = predictor.predict(...)
        return <ResponseSchema>(**result)
    except TeamNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")
```

**Template de schemas Pydantic:**

```python
# src/laliga_predictor/api/schemas/requests.py
from pydantic import BaseModel, Field, validator
from datetime import date


class PredictRequest(BaseModel):
    home_team: str = Field(..., example="Real Madrid", description="Nombre del equipo local")
    away_team: str = Field(..., example="Barcelona", description="Nombre del equipo visitante")
    match_date: date = Field(..., example="2026-03-01", description="Fecha del partido")
    
    @validator('home_team', 'away_team')
    def normalize_team_name(cls, v):
        from ...data.team_names import normalize_team_name
        normalized = normalize_team_name(v)
        if normalized is None:
            raise ValueError(f"Equipo '{v}' no reconocido")
        return normalized
    
    @validator('match_date')
    def validate_date(cls, v):
        from datetime import date
        if v < date(2017, 8, 1):
            raise ValueError("Fecha fuera del rango del modelo (min: 2017-08-01)")
        return v


# src/laliga_predictor/api/schemas/responses.py
class WinnerPrediction(BaseModel):
    predicted_result: str = Field(..., example="H")
    home_win_prob: float = Field(..., ge=0.0, le=1.0)
    draw_prob: float = Field(..., ge=0.0, le=1.0)
    away_win_prob: float = Field(..., ge=0.0, le=1.0)


class PredictResponse(BaseModel):
    match_date: date
    home_team: str
    away_team: str
    winner: WinnerPrediction
    goals: dict  # {"1.5": {"over": 0.85}, ...}
    cards: dict
    model_version: str
    generated_at: datetime
```

### Paso 4: Registrar en main.py

```python
# src/laliga_predictor/api/main.py
from fastapi import FastAPI
from .routers import predict, teams, health

app = FastAPI(
    title="LaLiga Predictor API",
    description="ML predictions for La Liga football matches",
    version="2.0.0",
)

app.include_router(health.router)
app.include_router(teams.router)
app.include_router(predict.router)
```

### Paso 5: Escribir tests del endpoint

Ubicación: `tests/unit/test_api.py`

```python
from fastapi.testclient import TestClient
from src.laliga_predictor.api.main import app

client = TestClient(app)


def test_<endpoint_name>_success():
    """Test del caso happy path."""
    response = client.<method>("<ruta>", json={...})
    assert response.status_code == 200
    data = response.json()
    assert "<campo_esperado>" in data


def test_<endpoint_name>_invalid_team():
    """Test con equipo inválido."""
    response = client.post("/predict", json={
        "home_team": "EquipoInexistente",
        "away_team": "Barcelona",
        "match_date": "2026-03-01"
    })
    assert response.status_code == 422


def test_<endpoint_name>_probabilities_sum_to_one():
    """Las probabilidades H+D+A deben sumar ~1.0."""
    response = client.post("/predict", json={...})
    data = response.json()
    total = data['winner']['home_win_prob'] + data['winner']['draw_prob'] + data['winner']['away_win_prob']
    assert abs(total - 1.0) < 0.01
```

### Paso 6: Verificar

```bash
# Levantar API localmente
uv run uvicorn src.laliga_predictor.api.main:app --reload --port 8000

# Verificar Swagger UI
open http://localhost:8000/docs

# Tests del endpoint
uv run pytest tests/unit/test_api.py -v

# Probar manualmente
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"home_team": "Real Madrid", "away_team": "Barcelona", "match_date": "2026-03-01"}'
```

### Paso 7: Commit

```bash
git add src/laliga_predictor/api/
git add tests/unit/test_api.py
git commit -m "feat(api): Add <método> <ruta> endpoint

- Implementa <descripción>
- Validación Pydantic en request/response
- Tests: happy path + edge cases"
```

## ⚠️ Checklist

- [ ] Schema de request con validación (team normalización, rango de fechas)
- [ ] Schema de response con tipos correctos
- [ ] Manejo de errores: 404, 422, 500
- [ ] Tests: happy path, team inválido, probabilidades suman 1
- [ ] Documentación Swagger completa (summary, description, examples)
- [ ] Endpoint registrado en `main.py`
- [ ] `make test` pasa completo
