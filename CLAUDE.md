# CLAUDE.md — LaLiga Predictor

> Guía maestra para Claude Code. Lee esto antes de cualquier tarea.

## 🎯 Visión del Proyecto

Sistema ML end-to-end para predecir resultados de LaLiga Española, con destino final: **API pública consumida desde una web app**. El objetivo no es solo un modelo que funcione localmente, sino un producto en producción.

**Tres salidas por partido:**
- Ganador: H (local) / D (empate) / A (visitante)  
- Goles Over/Under: líneas 1.5, 2.5, 3.5
- Tarjetas Over/Under: líneas 3.5, 4.5, 5.5

---

## 🗺️ Roadmap (Estado Actual → Producción)

```
FASE 1 [CI/CD]        → GitHub Actions: tests + lint en cada PR
FASE 2 [MLflow]       → Experiment tracking + model registry local
FASE 3 [Validación]   → Great Expectations para datos de entrada
FASE 4 [Automatización] → Reentrenamiento semanal automatizado
FASE 5 [API + Deploy] → FastAPI + Railway/Render (web pública)
```

**Estado actual**: Modelo entrenado localmente (56.8% acc winner, AUC ~0.59 O/U). Tests pasando (111+). PostgreSQL en Docker. Sin CI/CD ni API.

---

## 📁 Estructura del Proyecto

```
Proyecto_ML_Pred_Ganador/
├── CLAUDE.md                        ← ESTÁS AQUÍ
├── .claude/
│   ├── commands/                    ← Slash commands personalizados
│   ├── agents/                      ← Sub-agentes especializados
│   └── skills/                      ← Skills reutilizables
├── src/laliga_predictor/
│   ├── config.py                    ← Pydantic BaseSettings
│   ├── data/                        ← ETL: MatchHistory + ESPN
│   ├── features/                    ← ~144 features anti-leakage
│   ├── models/                      ← ML pipeline (train/predict)
│   └── api/                         ← FastAPI (Fase 5, pendiente)
├── tests/
│   ├── unit/                        ← test_features.py, test_models.py
│   └── integration/                 ← test_ml_pipeline.py
├── .github/workflows/               ← CI/CD (Fase 1, pendiente)
├── models/                          ← Joblib + JSON serializados
├── data/processed/                  ← Features Parquet
├── database/                        ← Schema SQL
├── docker-compose.yml
├── Makefile                         ← Comandos principales
└── pyproject.toml
```

---

## ⚙️ Stack Técnico

| Capa | Tecnología |
|------|-----------|
| **Runtime** | Python 3.10+, UV (gestor de dependencias) |
| **ML** | scikit-learn, XGBoost, LightGBM, Optuna |
| **Base de datos** | PostgreSQL 16 (Docker), SQLAlchemy |
| **Feature Store** | Apache Parquet (pyarrow) |
| **API** | FastAPI (pendiente Fase 5) |
| **MLOps** | MLflow local (pendiente Fase 2) |
| **CI/CD** | GitHub Actions (pendiente Fase 1) |
| **Deploy** | Railway / Render (pendiente Fase 5) |
| **Testing** | pytest, pytest-cov |
| **Calidad** | black, ruff, mypy, pre-commit |
| **Dev env** | WSL2 Ubuntu, VS Code + Claude Code |

---

## 🏗️ Convenciones de Código

### Naming
- **Archivos**: `snake_case.py`
- **Clases**: `PascalCase`
- **Funciones/variables**: `snake_case`
- **Constantes**: `UPPER_SNAKE_CASE`
- **Features**: prefijo de categoría, ej. `home_win_rate_5`, `elo_diff`, `h2h_home_wins`

### Imports
```python
# Orden estricto (ruff lo verifica):
# 1. stdlib
# 2. third-party
# 3. local (src.laliga_predictor.*)
```

### Tipado
- Siempre anotar tipos en funciones públicas
- Usar `Optional[X]` explícito, no `X | None` (compatibilidad Python 3.10)
- Dataclasses o Pydantic para estructuras de datos

### Tests
- Cada módulo nuevo → test unitario correspondiente
- **Anti-leakage es crítico**: cualquier feature nueva debe tener test verificando que no usa datos futuros
- Fixtures en `conftest.py`, datos sintéticos para tests (no BD real)

---

## 🚨 Reglas Críticas (NO violar)

1. **Anti data-leakage**: Las features SOLO pueden usar datos con fecha estrictamente ANTERIOR a `match_date`. Nunca resultados del partido actual.

2. **Temporal split**: Train/val/test siempre por temporadas completas. NUNCA split aleatorio en datos temporales.
   - Train: 2017/18 → 2023/24
   - Val: 2024/25
   - Test: 2025/26

3. **Calibración**: Los modelos de clasificación deben calibrar probabilidades (isotonic regression). No servir probabilidades crudas del modelo.

4. **Normalización de nombres**: Usar siempre `team_names.py` para normalizar equipos. La BD tiene 30 equipos con aliases definidos.

5. **Migrations**: Cualquier cambio de esquema → nuevo archivo SQL en `database/schemas/`. NUNCA modificar el schema original.

6. **Secrets**: DB credentials solo en `.env` (en `.gitignore`). Usar `config.py` (Pydantic Settings) para acceder.

---

## 🔧 Comandos Frecuentes

```bash
# Entorno
make docker-up          # Levantar PostgreSQL + pgAdmin
make install-dev        # Instalar dependencias con UV

# Datos
make sd-etl             # ETL completo (MatchHistory + ESPN)
make ml-update          # Actualizar datos temporada actual

# ML Pipeline
make ml-pipeline        # features + selection + train (completo)
make ml-features        # Solo construir features → Parquet
make ml-train           # Solo entrenar modelos
make ml-tune            # Optuna hyperparameter tuning

# Predicción
make ml-predict HOME="Real Madrid" AWAY="Barcelona" DATE="2026-03-01"
make ml-predict-jornada JORNADA=24

# Calidad
make test               # 111+ tests
make test-cov           # Con cobertura
make lint               # black + ruff
make format             # Auto-formatear
```

---

## 📊 Métricas Objetivo

| Modelo | Métrica | Actual | Objetivo |
|--------|---------|--------|----------|
| Winner Ensemble | Accuracy | 56.8% | >58% |
| Winner Ensemble | F1-macro | ~0.35 | >0.40 |
| Winner - Empates | Recall_D | ~10% | >20% |
| Goals O/U 2.5 | AUC-ROC | 0.591 | >0.62 |
| Cards O/U 4.5 | AUC-ROC | 0.578 | >0.60 |

**Baseline**: HomeAlwaysWins = 44.5% accuracy.

---

## 🌐 Diseño API (Fase 5 - Target)

```
GET  /health                    → Status del servicio
GET  /teams                     → Lista de equipos disponibles
POST /predict                   → Predicción partido individual
GET  /predict/jornada/{n}       → Predicción jornada completa
GET  /docs                      → Swagger UI (auto-generado)
```

**Contrato `/predict`:**
```json
// Request
{"home_team": "Real Madrid", "away_team": "Barcelona", "match_date": "2026-03-01"}

// Response
{
  "winner": {"predicted": "H", "home_prob": 0.40, "draw_prob": 0.32, "away_prob": 0.28},
  "goals": {"1.5": {"over": 0.85}, "2.5": {"over": 0.60}, "3.5": {"over": 0.35}},
  "cards": {"3.5": {"over": 0.70}, "4.5": {"over": 0.55}, "5.5": {"over": 0.20}},
  "model_version": "v2.1",
  "generated_at": "2026-03-01T10:00:00Z"
}
```

---

## 🧪 Estrategia de Testing

```
tests/
├── unit/
│   ├── test_features.py      ← Anti-leakage, rolling avgs, ELO
│   ├── test_models.py        ← Interfaces BasePredictor, save/load
│   ├── test_calibration.py   ← Probabilidades calibradas
│   └── test_api.py           ← Endpoints FastAPI (Fase 5)
└── integration/
    ├── test_ml_pipeline.py   ← E2E: datos sintéticos → predict
    └── test_etl_pipeline.py  ← ETL → BD → features
```

**Cobertura mínima**: 80% en `src/`. Los módulos críticos (`features/`, `models/`) deben tener >90%.

---

## 📝 Guía para Claude Code

### Antes de implementar cualquier cosa:
1. Verificar en qué Fase del roadmap encaja la tarea
2. Revisar si hay tests existentes que puedan romperse
3. Respetar las Reglas Críticas (especialmente anti-leakage)
4. Comprobar normalización de nombres de equipos

### Al crear nuevas features:
- Documentar la categoría y ventana temporal
- Añadir test de anti-leakage en `test_features.py`
- Actualizar el contador en README (actualmente ~144)

### Al modificar modelos:
- Mantener compatibilidad con la interfaz `BasePredictor`
- Los modelos deben serializar/deserializar con joblib
- Registrar en MLflow (cuando esté en Fase 2)

### Al crear endpoints API:
- Seguir el contrato definido en este documento
- Incluir validación Pydantic en request/response
- Añadir test en `tests/unit/test_api.py`
