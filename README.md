# LaLiga Predictor

Sistema de Machine Learning para predecir resultados de partidos de La Liga Espa&ntilde;ola. Predice tres variables por partido:

- **Ganador**: Victoria local (H) / Empate (D) / Victoria visitante (A)
- **Total de goles**: Goles esperados en el partido
- **Total de tarjetas**: Tarjetas esperadas en el partido

## Resultados del Modelo (Test: Temporada 2024-2025)

| Target | Mejor Modelo | Metrica Principal |
|--------|:---:|:---:|
| Ganador (H/D/A) | Ensemble (RF + XGBoost) | **56.8% accuracy** |
| Total Goles | XGBoost Regressor | **1.594 RMSE** |
| Total Tarjetas | XGBoost Regressor | **2.540 RMSE** |

> Baseline "siempre gana local": 44.5% accuracy. El Ensemble supera al baseline por +12.3 puntos porcentuales.

## Tech Stack

- **Lenguaje**: Python 3.10+
- **Gestion de dependencias**: UV
- **ML**: scikit-learn, XGBoost, pandas, numpy
- **Feature Store**: Apache Parquet (pyarrow)
- **Base de datos**: PostgreSQL 16 (Docker)
- **Fuentes de datos**: Football-Data.co.uk (MatchHistory) + ESPN (stats avanzadas)
- **Testing**: pytest (62 tests), pytest-cov
- **Calidad de codigo**: black, ruff, mypy, pre-commit

---

## Arquitectura

```
                    +-----------------+     +------------------+
                    | Football-Data   |     |    ESPN API      |
                    | (MatchHistory)  |     | (Advanced Stats) |
                    +-------+---------+     +--------+---------+
                            |                        |
                            v                        v
                    +----------------------------------------+
                    |        PostgreSQL (laliga_soccerdata)   |
                    |  matches | advanced_stats | standings   |
                    +-------------------+--------------------+
                                        |
                                        v
                    +----------------------------------------+
                    |         Feature Engineering             |
                    |  119 features, 6 categorias             |
                    |  Anti data-leakage (cutoff temporal)    |
                    +-------------------+--------------------+
                                        |
                                        v
                              data/processed/features.parquet
                                        |
                    +-------------------+--------------------+
                    |           Training Pipeline             |
                    |  Temporal split por temporada            |
                    |  Train: 17/18-22/23 | Val: 23/24        |
                    |  Test: 24/25                             |
                    +-------------------+--------------------+
                                        |
                    +----------+--------+---------+----------+
                    |          |                  |          |
                    v          v                  v          v
                Baseline   Random Forest    XGBoost    Ensemble
                    |          |                  |          |
                    +----------+--------+---------+----------+
                                        |
                                        v
                              models/*.joblib + *.json
                                        |
                                        v
                    +----------------------------------------+
                    |         Prediction CLI                  |
                    |  make ml-predict HOME=X AWAY=Y DATE=Z  |
                    +----------------------------------------+
```

---

## Quick Start

### 1. Clonar e Instalar

```bash
git clone <repo-url>
cd Proyecto_ML_Pred_Ganador

# Instalar dependencias (incluye XGBoost, scikit-learn, etc.)
make install-dev
```

### 2. Configurar Variables de Entorno

```bash
cp .env.example .env
# Editar .env con los datos de conexion a PostgreSQL
```

### 3. Levantar Base de Datos

```bash
# Levantar PostgreSQL + pgAdmin
make docker-up

# Crear e inicializar la base de datos soccerdata
make sd-init
```

### 4. Cargar Datos (ETL)

```bash
# Pipeline completo: MatchHistory + ESPN + Standings (8 temporadas)
make sd-etl

# O por pasos individuales:
make sd-etl-mh          # MatchHistory (rapido, sin rate limit)
make sd-etl-espn        # ESPN advanced stats
make sd-etl-standings   # Calcular clasificaciones
```

### 5. Entrenar Modelos

```bash
# Pipeline completo: features + entrenamiento
make ml-pipeline

# O por pasos:
make ml-features    # Construir features -> data/processed/features.parquet
make ml-train       # Entrenar todos los modelos (8 modelos x 3 targets)
```

### 6. Predecir Partidos

```bash
make ml-predict HOME="Real Madrid" AWAY="Barcelona" DATE="2026-03-01"
```

Ejemplo de salida:
```json
{
  "match_date": "2026-03-01",
  "home_team": "Real Madrid",
  "away_team": "Barcelona",
  "predictions": {
    "winner": {
      "predicted_result": "H",
      "home_win_prob": 0.399,
      "draw_prob": 0.317,
      "away_win_prob": 0.284
    },
    "total_goals": {
      "predicted": 3.0
    },
    "total_cards": {
      "predicted": 4.8
    }
  }
}
```

---

## Datos

### Fuentes

| Fuente | Datos | Temporadas | Metodo |
|--------|-------|:---:|--------|
| **Football-Data.co.uk** (MatchHistory) | Resultados, goles, tiros, corners, faltas, tarjetas | 2017-2025 (8) | CSV descarga directa |
| **ESPN** | Posesion, pases, tackles, intercepciones, despejes, centros, balones largos, paradas | 2017-2025 (8) | API HTTP |

### Base de Datos (PostgreSQL)

| Tabla | Descripcion | Filas aprox. |
|-------|-------------|:---:|
| `seasons` | Temporadas pre-cargadas | 8 |
| `teams` | Equipos con normalizacion de nombres | 30 |
| `matches` | Partidos con resultados y estadisticas | 3,040 |
| `match_advanced_stats` | Stats ESPN por equipo/partido | 6,070 |
| `standings` | Clasificacion por jornada | 6,074 |
| `etl_log` | Registro de ejecuciones ETL | variable |

### Feature Engineering

119 features en 6 categorias, todas calculadas con datos **estrictamente anteriores** a la fecha del partido (anti data-leakage):

| Categoria | Features | Descripcion |
|-----------|:---:|-------------|
| Rolling Form | 66 | Win rate, goles, tiros, corners, tarjetas (ventanas 3, 5, 10) |
| Venue Form | 12 | Rendimiento especifico como local/visitante |
| ESPN Advanced | 20 | Posesion, pases, tackles, intercepciones (media 5 partidos) |
| Head-to-Head | 6 | Historico de enfrentamientos directos (ultimos 6) |
| Standings | 8 | Posicion, puntos, diferencia de goles en la clasificacion |
| Contextual | 7 | Dias de descanso, derby, jornada temprana/tardia |

---

## Modelos

### Clasificacion (Ganador)

| Modelo | Val Acc | Test Acc | Descripcion |
|--------|:---:|:---:|-------------|
| HomeAlwaysWins | 43.9% | 44.5% | Baseline: siempre predice victoria local |
| Random Forest | 56.1% | 52.6% | 300 arboles, `class_weight='balanced'` |
| XGBoost | 54.5% | 54.5% | Early stopping, regularizacion L1/L2 |
| **Ensemble** | 54.5% | **56.8%** | Stacking: RF + XGB con meta-learner LR |

### Regresion (Goles / Tarjetas)

| Modelo | Target | Val RMSE | Test RMSE |
|--------|--------|:---:|:---:|
| MeanBaseline | Goles | 1.773 | 1.625 |
| **XGBoost** | **Goles** | **1.744** | **1.594** |
| MeanBaseline | Tarjetas | 2.479 | 2.610 |
| **XGBoost** | **Tarjetas** | **2.442** | **2.540** |

---

## Estructura del Proyecto

```
Proyecto_ML_Pred_Ganador/
├── src/laliga_predictor/
│   ├── config.py                   # Pydantic BaseSettings (.env)
│   ├── data/
│   │   ├── soccerdata_client.py    # Cliente MatchHistory + ESPN
│   │   ├── etl_soccerdata.py       # Pipeline ETL completo
│   │   ├── sd_db_init.py           # Inicializacion BD soccerdata
│   │   ├── team_names.py           # Normalizacion de nombres (30 equipos)
│   │   └── validate_soccerdata.py  # Validacion de datos
│   ├── features/
│   │   ├── data_loader.py          # SQL -> DataFrames
│   │   ├── feature_engineering.py  # 119 features con anti-leakage
│   │   └── feature_store.py        # Save/load Parquet
│   └── models/
│       ├── base.py                 # BasePredictor ABC
│       ├── classifiers.py          # Baseline, RF, XGBoost, Ensemble
│       ├── regressors.py           # MeanBaseline, XGBoostGoals/Cards
│       ├── temporal_cv.py          # SeasonalTimeSeriesSplit
│       ├── train.py                # Pipeline de entrenamiento
│       ├── evaluate.py             # Metricas de evaluacion
│       └── predict.py              # CLI de prediccion
├── tests/
│   ├── unit/
│   │   ├── test_features.py        # Anti-leakage, rolling averages
│   │   └── test_models.py          # Interfaces, save/load, temporal CV
│   └── integration/
│       └── test_ml_pipeline.py     # End-to-end pipeline
├── models/                         # Modelos serializados (.joblib + .json)
├── data/processed/                 # Feature cache (Parquet)
├── database/
│   ├── schema_soccerdata.sql       # Esquema BD soccerdata
│   └── schemas/
├── docker-compose.yml
├── Makefile                        # Comandos make (sd-*, ml-*)
└── pyproject.toml
```

---

## Comandos Make

### ML Pipeline

```bash
make ml-features        # Construir features desde BD -> Parquet
make ml-train           # Entrenar todos los modelos
make ml-train-winner    # Solo modelos de ganador
make ml-train-goals     # Solo modelos de goles
make ml-train-cards     # Solo modelos de tarjetas
make ml-predict HOME="Atletico Madrid" AWAY="Sevilla" DATE="2026-04-15"
make ml-pipeline        # Pipeline completo: features + train
```

### ETL / Datos

```bash
make sd-init            # Crear e inicializar BD soccerdata
make sd-etl             # ETL completo (MatchHistory + ESPN + Standings)
make sd-etl-mh          # Solo MatchHistory
make sd-etl-espn        # Solo ESPN advanced stats
make sd-etl-standings   # Solo calcular clasificaciones
make sd-etl-season SEASON=2324  # ETL para una temporada especifica
make sd-validate        # Validar integridad de datos
make sd-status          # Ver estadisticas de la BD
```

### Testing y Calidad

```bash
make test               # Ejecutar todos los tests (62 tests)
make test-unit          # Solo tests unitarios
make test-integration   # Solo tests de integracion
make test-cov           # Tests con reporte de cobertura
make lint               # Verificar calidad de codigo
make format             # Formatear codigo
```

### Docker

```bash
make docker-up          # Levantar PostgreSQL + pgAdmin
make docker-down        # Detener contenedores
make docker-logs        # Ver logs
```

---

## Testing

62 tests cubriendo:

- **Anti data-leakage**: Verifica que ninguna feature usa datos futuros
- **Interfaces de modelos**: Todos implementan BasePredictor correctamente
- **Serializacion**: Save/load produce predicciones identicas
- **Temporal CV**: Train siempre antes que validation
- **Pipeline E2E**: Datos sinteticos -> features -> train -> evaluate -> predict

```bash
make test
# ===== 62 passed in 25s =====
```

---

## Licencia

MIT License
