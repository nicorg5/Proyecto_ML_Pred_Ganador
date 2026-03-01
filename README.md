# LaLiga Predictor

Sistema de Machine Learning para predecir resultados de partidos de La Liga Espanola. Predice tres variables por partido:

- **Ganador**: Victoria local (H) / Empate (D) / Victoria visitante (A)
- **Goles (Over/Under)**: Probabilidad de +1.5, +2.5, +3.5 goles
- **Tarjetas (Over/Under)**: Probabilidad de +3.5, +4.5, +5.5 tarjetas

## Resultados del Modelo (Test: Temporada 2024-2025)

| Target | Modelo | Metrica Principal |
|--------|:---:|:---:|
| Ganador (H/D/A) | Ensemble (RF + XGBoost) | **56.8% accuracy** |
| Goles O/U 2.5 | XGBoost Classifier | **59.1% AUC** |
| Tarjetas O/U 4.5 | XGBoost Classifier | **57.8% AUC** |

> Baseline "siempre gana local": 44.5% accuracy. El Ensemble supera al baseline por +12.3 puntos porcentuales.

## Tech Stack

- **Lenguaje**: Python 3.10+
- **Gestion de dependencias**: UV
- **ML**: scikit-learn, XGBoost, LightGBM, pandas, numpy
- **Optimizacion de hiperparametros**: Optuna
- **Feature Store**: Apache Parquet (pyarrow)
- **Base de datos**: PostgreSQL 16 (Docker)
- **Fuentes de datos**: Football-Data.co.uk (MatchHistory) + ESPN (stats avanzadas)
- **Testing**: pytest (111 tests), pytest-cov
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
                    |  ~144 features, 12 categorias           |
                    |  Anti data-leakage (cutoff temporal)    |
                    +-------------------+--------------------+
                                        |
                                        v
                              data/processed/features.parquet
                                        |
                    +-------------------+--------------------+
                    |    Feature Selection (importance +      |
                    |    correlation filtering) -> ~50-70     |
                    +-------------------+--------------------+
                                        |
                    +-------------------+--------------------+
                    |    Optuna Hyperparameter Tuning         |
                    |    (SeasonalTimeSeriesSplit CV)         |
                    +-------------------+--------------------+
                                        |
                    +-------------------+--------------------+
                    |           Training Pipeline             |
                    |  Temporal split por temporada            |
                    |  Train: 17/18-23/24 | Val: 24/25        |
                    |  Test: 25/26                             |
                    +-------------------+--------------------+
                                        |
                    +----------+--------+---------+-----------+
                    |          |        |         |           |
                    v          v        v         v           v
                Baseline      RF    XGBoost  LightGBM   Ensemble
                                                         (Voting)
                    |          |                  |          |
                    +----------+--------+---------+----------+
                                        |
                                        v
                              models/*.joblib + *.json
                              (Winner + 6 Over/Under models)
                                        |
                    +----------+--------+---------+----------+
                    |                                        |
                    v                                        v
          Prediccion individual                    Prediccion por jornada
          ml-predict HOME=X AWAY=Y                 ml-predict-jornada JORNADA=N
                                                     (Muestra probs O/U)
```

---

## Setup desde cero

Guia completa para quien clona el repositorio por primera vez.

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

# Crear e inicializar la base de datos soccerdata (esquema + temporadas)
make sd-init
```

### 4. Cargar Datos (ETL)

```bash
# Pipeline completo: MatchHistory + ESPN + Standings (8 temporadas, 2017-2025)
make sd-etl

# O por pasos individuales:
make sd-etl-mh          # MatchHistory (rapido, sin rate limit)
make sd-etl-espn        # ESPN advanced stats (lento, ~45 seg/partido)
make sd-etl-standings   # Calcular clasificaciones
```

> **Nota**: El ETL de ESPN es lento (~45 seg por partido, ~4.5 horas para 380 partidos por temporada). MatchHistory + Standings son suficientes para predecir.

### 5. Entrenar Modelos

```bash
# Pipeline completo: construir features + entrenar 8 modelos
make ml-pipeline

# O por pasos:
make ml-features    # Construir features -> data/processed/features.parquet
make ml-train       # Entrenar todos los modelos (Winner + 6 Over/Under classifiers)
```

### 6. Predecir

```bash
# Predecir un partido individual
make ml-predict HOME="Real Madrid" AWAY="Barcelona" DATE="2026-03-01"

# Predecir una jornada completa
make ml-predict-jornada JORNADA=24 SEASON=2526
```

---

## Uso Semanal: Guía Paso a Paso para Predecir una Jornada

Sigue estos pasos para generar predicciones cada semana:

### 1. Preparar el entorno
Asegúrate de que la base de datos está corriendo:

```bash
make docker-up
```

### 2. Actualizar datos (Crítico)
Antes de predecir, necesitas los últimos resultados y estadísticas (partidos jugados ayer, etc.).
Este comando descarga los últimos partidos de MatchHistory, actualiza la clasificación y reconstruye las features:

```bash
make ml-update
```
> *Nota: Por defecto actualiza la temporada actual (25/26). Si necesitas otra, usa `SEASON=2425`.*

### 3. Ejecutar la Predicción
Tienes dos opciones para generar el reporte:

**Opción A: Predecir la próxima jornada automáticamente**
El sistema detectará la última jornada con partidos programados:
```bash
make ml-predict-jornada
```

**Opción B: Predecir una jornada específica (ej. Jornada 24)**
Si quieres ver predicciones para una fecha concreta:
```bash
make ml-predict-jornada JORNADA=24
```

### 4. Interpretar los Resultados
El comando imprimirá una tabla en la terminal.
- **Sección JUGADOS**: Muestra aciertos (OK/X) y compara predicciones vs realidad.
- **Sección POR JUGAR**: Muestra las probabilidades para los partidos futuros.
- **Goles O/U**: Probabilidades para líneas de 1.5, 2.5 y 3.5 goles.
- **Tarjetas O/U**: Probabilidades para líneas de 3.5, 4.5 y 5.5 tarjetas.

### Ejemplo de salida

```
==========================================================================================
  LA LIGA 2425 - JORNADA 22
==========================================================================================

  JUGADOS (9 partidos)
---------------------------------------------------------------------------------------------------------
     |                Local  Res  Visitante            | Pred |    H    D    A |  Goles O/U   |   Tarj O/U
---------------------------------------------------------------------------------------------------------
   X |           Celta Vigo  1-2  Osasuna              |  H   |  53%  30%  17% |  O2.5 53% ✓  |  O4.5 59% ✗
  OK |            Barcelona  3-0  Mallorca             |  H   |  75%  17%   7% |  O2.5 59% ✓  |  U4.5 55% ✓
  OK |        Real Sociedad  3-1  Elche                |  H   |  58%  26%  16% |  U2.5 51% ✗  |  O4.5 54% ✗
  OK |        Athletic Club  4-2  Levante              |  H   |  60%  25%  15% |  O2.5 50% ✓  |  O4.5 62% ✗
 ...
---------------------------------------------------------------------------------------------------------
  Aciertos ganador: 5/9 (56%)
  Aciertos goles O/U 2.5: 5/9 (56%)
  Aciertos tarjetas O/U 4.5: 4/9 (44%)

  POR JUGAR (1 partidos)
---------------------------------------------------------------------------------------------------------
  Fecha        |                Local  vs  Visitante            | Pred |    H    D    A |      Goles       |     Tarjetas
---------------------------------------------------------------------------------------------------------
  2026-03-01   |          Real Madrid  vs  Girona               |  H   |  66%  21%  13% | O1.5 85% O2.5 60% | O3.5 70% O4.5 55%
=========================================================================================================
```

- **OK/X**: Predicción acertada/fallida
- **Pred**: Resultado predicho (H/D/A)
- **H/D/A**: Probabilidades
- **Goles O/U**: Probabilidad de Over 2.5 (jugados) o todas las líneas (por jugar)
- **Tarj O/U**: Probabilidad de Over 4.5 (jugados) o todas las líneas (por jugar)

---

## Cómo Ver las Nuevas Métricas Tras las Mejoras Implementadas

Después de implementar las 7 mejoras al modelo (calibración, nuevas features, feature selection, tuning, scale_pos_weight, LightGBM, y más datos de entrenamiento), puedes ver las nuevas métricas siguiendo estos pasos:

### 1. Reconstruir Features con las Nuevas Variables

El primer paso es regenerar las features con las 25 nuevas variables (ELO, rachas, EMA, diferencias, total_goals, draw-likelihood):

```bash
make ml-features
```

Este comando creará un nuevo archivo `data/processed/features.parquet` con ~144 features (antes eran 119).

### 2. (Opcional) Ejecutar Feature Selection

Para reducir el conjunto de features a las más importantes y eliminar correlaciones:

```bash
make ml-select-features
```

Esto generará archivos JSON en `data/processed/selected_features_*.json` con las features seleccionadas para cada target (winner, goals O/U, cards O/U).

### 3. (Opcional) Ejecutar Optuna Tuning

Si quieres optimizar los hiperparámetros de XGBoost con validación cruzada temporal:

```bash
# Tuning para todos los modelos (~30-60 min con 50 trials por modelo)
make ml-tune

# O solo para un target específico:
make ml-tune TARGET=winner
make ml-tune TARGET=goals-ou
make ml-tune TARGET=cards-ou
```

Los parámetros optimizados se guardarán en `models/tuned_params_*.json` y se aplicarán automáticamente al entrenar.

### 4. Entrenar Todos los Modelos con las Mejoras

Entrena todos los modelos (Baseline, RF, XGBoost, LightGBM, Ensemble) con las nuevas features, calibración, y parámetros tunados:

```bash
make ml-train
```

Este comando:
- Carga las features seleccionadas (si existen)
- Carga los hiperparámetros tunados (si existen)
- Entrena cada modelo
- Aplica **calibración de probabilidades** con regresión isotónica
- Optimiza los **thresholds de clasificación** para maximizar f1_macro
- Calcula automáticamente **scale_pos_weight** para modelos O/U
- Guarda los modelos en `models/*.joblib`

### 5. Ver los Resultados

Los resultados de entrenamiento se guardan en `models/training_results.json`. Puedes verlos con:

```bash
cat models/training_results.json | python -m json.tool
```

O directamente:

```bash
cat models/training_results.json
```

**Formato del archivo:**

```json
{
  "result": {
    "baseline": {
      "val": {"accuracy": 0.439, "f1_macro": 0.295, ...},
      "test": {"accuracy": 0.445, "f1_macro": 0.304, ...}
    },
    "rf": {...},
    "xgboost": {...},
    "lightgbm": {...},
    "ensemble": {...}
  },
  "goals_over_1.5": {
    "baseline": {...},
    "xgboost": {...},
    "lightgbm": {...}
  },
  ...
}
```

### 6. Métricas Clave a Observar

Para **modelos de ganador (H/D/A)**:
- `accuracy`: Porcentaje de aciertos totales
- `f1_macro`: F1-score macro (importante para empates)
- `accuracy_H`, `accuracy_D`, `accuracy_A`: Acierto por clase individual
- `precision_D`, `recall_D`: Precisión y recall para empates (crítico, antes era 0%)

Para **modelos O/U (goles/tarjetas)**:
- `accuracy`: Porcentaje de aciertos Over/Under
- `roc_auc`: Área bajo la curva ROC (debe ser > 0.60 para ser útil)
- `precision`, `recall`: Balance entre falsos positivos y falsos negativos

### 7. Pipeline Completo (Recomendado)

Para ejecutar todo el pipeline de una vez (features + selection + training):

```bash
make ml-pipeline
```

### 8. Comparar Resultados Antes/Después

**Antes de las mejoras** (modelos antiguos):
- Ensemble Winner: 56.8% accuracy, **0% en empates**
- Goals O/U 2.5: AUC = 0.591
- Cards O/U 4.5: AUC = 0.578

**Después de las mejoras** (resultados esperados):
- Ensemble Winner: ~55-60% accuracy, **>10% en empates** (mejora crítica)
- Goals O/U 2.5: AUC > 0.60
- Cards O/U 4.5: AUC > 0.58
- f1_macro significativamente mejorado (mejor balance entre clases)

### 9. Ver Predicciones con Probabilidades Calibradas

Una vez reentrenados los modelos, las predicciones reflejarán las mejoras:

```bash
# Predicción individual con probabilidades calibradas
make ml-predict HOME="Real Madrid" AWAY="Barcelona" DATE="2026-03-01"

# Predicción de jornada completa
make ml-predict-jornada JORNADA=24 SEASON=2526
```

Las probabilidades ahora:
- Están **calibradas** (más realistas, no extremas)
- Usan **thresholds optimizados** para empates
- Incluyen el impacto de las **25 nuevas features**

---

## Prediccion de partido individual

```bash
make ml-predict HOME="Real Madrid" AWAY="Barcelona" DATE="2026-03-01"
```

Salida (JSON):
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
    "total_goals_over_under": {
      "1.5": {"over_prob": 0.85, "under_prob": 0.15},
      "2.5": {"over_prob": 0.60, "under_prob": 0.40},
      "3.5": {"over_prob": 0.35, "under_prob": 0.65}
    },
    "total_cards_over_under": {
      "3.5": {"over_prob": 0.70, "under_prob": 0.30},
      "4.5": {"over_prob": 0.55, "under_prob": 0.45},
      "5.5": {"over_prob": 0.20, "under_prob": 0.80}
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
| `seasons` | Temporadas pre-cargadas | 8+ |
| `teams` | Equipos con normalizacion de nombres | 30 |
| `matches` | Partidos con resultados y estadisticas | 3,040+ |
| `match_advanced_stats` | Stats ESPN por equipo/partido | 6,070 |
| `standings` | Clasificacion por jornada | 6,074+ |
| `etl_log` | Registro de ejecuciones ETL | variable |

### Feature Engineering

~144 features en 12 categorias, todas calculadas con datos **estrictamente anteriores** a la fecha del partido (anti data-leakage):

| Categoria | Features | Descripcion |
|-----------|:---:|-------------|
| Rolling Form | 66 | Win rate, goles, tiros, corners, tarjetas (ventanas 3, 5, 10) |
| Venue Form | 12 | Rendimiento especifico como local/visitante |
| ESPN Advanced | 20 | Posesion, pases, tackles, intercepciones (media 5 partidos) |
| Head-to-Head | 6 | Historico de enfrentamientos directos (ultimos 6) |
| Standings | 8 | Posicion, puntos, diferencia de goles en la clasificacion |
| Contextual | 4 | Derby, jornada temprana/tardia, estimacion de jornada |
| **ELO Rating** | **4** | **Ratings dinamicos ELO, diferencia ELO, victoria esperada** |
| **Rachas** | **8** | **Rachas de victorias, imbatibilidad, goles, porterias a cero** |
| **EMA (Medias Moviles)** | **6** | **Medias exponenciales de goles, puntos, goles encajados** |
| **Diferencias** | **3** | **Diferencias directas: win rate, goles, goles encajados** |
| **Total Goals** | **3** | **Medias de goles totales por partido para prediccion O/U** |
| **Draw Likelihood** | **4** | **Indicadores de probabilidad de empate (similitud defensiva, forma)** |

> **Nota**: Tras el entrenamiento, se aplica **Feature Selection** basada en importancia y correlacion, reduciendo a ~50-70 features para evitar overfitting.

---

## Modelos

### Clasificacion (Ganador)

| Modelo | Val Acc | Test Acc | Descripcion |
|--------|:---:|:---:|-------------|
| HomeAlwaysWins | 43.9% | 44.5% | Baseline: siempre predice victoria local |
| Random Forest | 56.1% | 52.6% | 300 arboles, `class_weight='balanced'` |
| XGBoost | 54.5% | 54.5% | Early stopping, regularizacion L1/L2, hiperparametros tunados con Optuna |
| LightGBM | - | - | Gradient boosting con early stopping y regularizacion |
| **Ensemble** | 54.5% | **56.8%** | **VotingClassifier (soft)**: RF + XGBoost + LightGBM |

> **Mejoras v2**: Todos los modelos (excepto baseline) usan **calibracion de probabilidades** con regresion isotonica + optimizacion de thresholds para mejorar predicciones de empates.

### Clasificacion (Goles y Tarjetas Over/Under)

Modelos XGBoost y LightGBM entrenados para cada línea individualmente.

| Target | Linea | Accuracy (Test) | AUC-ROC |
|--------|:---:|:---:|:---:|
| **Goles** | 1.5 | 72.4% | 0.553 |
| **Goles** | 2.5 | 57.6% | 0.591 |
| **Goles** | 3.5 | 76.1% | 0.606 |
| **Tarjetas** | 3.5 | 66.6% | 0.597 |
| **Tarjetas** | 4.5 | 50.3% | 0.578 |
| **Tarjetas** | 5.5 | 67.4% | 0.567 |

> **Mejoras v2**: Los modelos O/U ahora calculan automáticamente `scale_pos_weight` para manejar desbalance de clases, y están disponibles tanto en XGBoost como LightGBM.

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
│   │   ├── feature_engineering.py  # ~144 features con anti-leakage
│   │   ├── feature_selection.py    # Seleccion por importancia + correlacion
│   │   └── feature_store.py        # Save/load Parquet
│   └── models/
│       ├── base.py                 # BasePredictor ABC
│       ├── classifiers.py          # Baseline, RF, XGBoost, LightGBM, Ensemble (Winner)
│       ├── over_under.py           # Baseline, XGBoost, LightGBM (Goals/Cards O/U)
│       ├── calibration.py          # CalibratedPredictor con regresion isotonica
│       ├── tuning.py               # Optuna hyperparameter tuning
│       ├── temporal_cv.py          # SeasonalTimeSeriesSplit
│       ├── train.py                # Pipeline de entrenamiento
│       ├── evaluate.py             # Metricas de evaluacion
│       ├── predict.py              # CLI de prediccion individual
│       └── predict_jornada.py      # CLI de prediccion por jornada
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

### Prediccion

```bash
make ml-predict HOME="Atletico Madrid" AWAY="Sevilla" DATE="2026-04-15"
make ml-predict-jornada JORNADA=24                # Jornada especifica (temporada 2526)
make ml-predict-jornada JORNADA=22 SEASON=2425    # Otra temporada
make ml-predict-jornada SEASON=2526               # Auto-detecta ultima jornada
```

### ML Pipeline

```bash
make ml-features               # Construir features desde BD -> Parquet
make ml-select-features        # Seleccion de features (importancia + correlacion)
make ml-tune                   # Optuna hyperparameter tuning (XGBoost)
make ml-tune TARGET=winner     # Tuning solo para modelos de ganador
make ml-tune TARGET=goals-ou   # Tuning solo para goles O/U
make ml-train                  # Entrenar todos los modelos
make ml-train-winner           # Solo modelos de ganador
make ml-train TARGET=goals-ou  # Solo modelos de goles O/U
make ml-train TARGET=cards-ou  # Solo modelos de tarjetas O/U
make ml-pipeline               # Pipeline completo: features + select + train
make ml-update                 # Actualizar datos temporada actual + reconstruir features
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
make test               # Ejecutar todos los tests (111 tests)
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