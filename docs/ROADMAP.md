# Roadmap del Proyecto - LaLiga Predictor

## Objetivo Final

Crear un modelo de Machine Learning que prediga el resultado de partidos de LaLiga:
- **Victoria Local (H)**
- **Empate (D)**
- **Victoria Visitante (A)**

---

## Estado Actual

### Completado
- [x] Estructura del proyecto
- [x] Configuracion de Docker (PostgreSQL + pgAdmin)
- [x] Cliente de API Football
- [x] Scripts de inicializacion de base de datos
- [x] Scripts de descarga de datos (fetch_data.py)
- [x] Scripts de validacion de datos
- [x] Descarga parcial de temporada 2024 (380 partidos, 60 con estadisticas)

### En Progreso
- [ ] Poblacion completa de datos (3 temporadas)

---

## FASE 1: Poblacion de Datos (10-12 dias)

### Objetivo
Obtener datos historicos de 3 temporadas de LaLiga (2022-2024) con estadisticas detalladas.

### Tareas
1. **Completar temporada 2024** (~4 dias)
   ```bash
   uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-only --stats-limit 60
   ```

2. **Descargar temporada 2023** (~4 dias)
   ```bash
   uv run python -m src.laliga_predictor.data.fetch_data --season 2023 --stats-limit 30
   uv run python -m src.laliga_predictor.data.fetch_data --season 2023 --stats-only --stats-limit 60
   ```

3. **Descargar temporada 2022** (~4 dias)
   ```bash
   uv run python -m src.laliga_predictor.data.fetch_data --season 2022 --stats-limit 30
   uv run python -m src.laliga_predictor.data.fetch_data --season 2022 --stats-only --stats-limit 60
   ```

4. **Validacion final**
   ```bash
   uv run python -m src.laliga_predictor.data.validate_data
   ```

### Entregables
- ~1,140 partidos en base de datos
- ~95%+ partidos con estadisticas completas
- Validacion sin errores criticos

---

## FASE 2: Feature Engineering (1-2 semanas)

### Objetivo
Transformar los datos crudos en features utiles para el modelo de prediccion.

### Features a Crear

#### A. Features de Forma Reciente (ultimos 5 partidos)

| Feature | Descripcion |
|---------|-------------|
| `home_last5_wins` | Victorias del local en ultimos 5 partidos |
| `home_last5_draws` | Empates del local en ultimos 5 partidos |
| `home_last5_losses` | Derrotas del local en ultimos 5 partidos |
| `home_last5_goals_for` | Goles a favor promedio (local) |
| `home_last5_goals_against` | Goles en contra promedio (local) |
| `away_last5_wins` | Victorias del visitante en ultimos 5 partidos |
| `away_last5_draws` | Empates del visitante en ultimos 5 partidos |
| `away_last5_losses` | Derrotas del visitante en ultimos 5 partidos |
| `away_last5_goals_for` | Goles a favor promedio (visitante) |
| `away_last5_goals_against` | Goles en contra promedio (visitante) |

#### B. Features de Rendimiento Local/Visitante

| Feature | Descripcion |
|---------|-------------|
| `home_home_win_rate` | % victorias jugando en casa |
| `home_home_goals_avg` | Goles promedio en casa |
| `away_away_win_rate` | % victorias jugando fuera |
| `away_away_goals_avg` | Goles promedio fuera |

#### C. Features de Enfrentamiento Directo (H2H)

| Feature | Descripcion |
|---------|-------------|
| `h2h_home_wins` | Victorias del local en ultimos 5 enfrentamientos |
| `h2h_draws` | Empates en ultimos 5 enfrentamientos |
| `h2h_away_wins` | Victorias del visitante en ultimos 5 enfrentamientos |
| `h2h_goals_avg` | Promedio de goles en enfrentamientos |

#### D. Features de Contexto

| Feature | Descripcion |
|---------|-------------|
| `home_position` | Posicion en la tabla del local |
| `away_position` | Posicion en la tabla del visitante |
| `position_diff` | Diferencia de posiciones |
| `home_points` | Puntos del local |
| `away_points` | Puntos del visitante |
| `match_week` | Jornada del campeonato |

#### E. Features Avanzadas (Opcional)

| Feature | Descripcion |
|---------|-------------|
| `home_possession_avg` | Posesion promedio del local |
| `away_possession_avg` | Posesion promedio del visitante |
| `home_shots_avg` | Tiros promedio del local |
| `away_shots_avg` | Tiros promedio del visitante |
| `home_shots_on_target_avg` | Tiros a puerta promedio |
| `days_since_last_match` | Dias de descanso |

### Tareas

1. **Crear modulo de feature engineering**
   ```
   src/laliga_predictor/features/
   ├── __init__.py
   ├── engineer.py        # Funciones de calculo de features
   ├── form.py            # Features de forma reciente
   ├── h2h.py             # Features de head-to-head
   └── context.py         # Features de contexto
   ```

2. **Implementar calculo de features**
   - Usar las vistas `team_last5_home` y `team_last5_away`
   - Crear funciones para cada grupo de features
   - Manejar casos edge (primeros partidos de temporada)

3. **Crear dataset de entrenamiento**
   ```bash
   uv run python -m src.laliga_predictor.features.engineer --output data/processed/training_data.csv
   ```

4. **Analisis exploratorio (EDA)**
   - Crear notebook en `notebooks/01_eda.ipynb`
   - Analizar distribucion de features
   - Identificar correlaciones
   - Detectar valores faltantes o anomalos

### Entregables
- Modulo de feature engineering funcional
- Dataset de entrenamiento (~1,000+ partidos con features)
- Notebook de EDA con visualizaciones

---

## FASE 3: Entrenamiento del Modelo (1 semana)

### Objetivo
Entrenar y evaluar modelos de clasificacion para predecir resultados.

### Modelos a Probar

1. **Baseline: Logistic Regression**
   - Simple, interpretable
   - Sirve como referencia

2. **Random Forest**
   - Buen balance complejidad/rendimiento
   - Maneja bien features no lineales

3. **XGBoost / LightGBM**
   - Estado del arte para datos tabulares
   - Mejor rendimiento esperado

4. **Opcional: Redes Neuronales**
   - Solo si los anteriores no funcionan bien

### Tareas

1. **Crear modulo de modelos**
   ```
   src/laliga_predictor/models/
   ├── __init__.py
   ├── train.py           # Entrenamiento de modelos
   ├── evaluate.py        # Evaluacion y metricas
   ├── predict.py         # Predicciones
   └── utils.py           # Utilidades
   ```

2. **Preparar datos**
   - Split train/validation/test (70/15/15)
   - Usar ultimas 2 jornadas como test (mas realista)
   - Normalizar/escalar features si es necesario

3. **Entrenar modelos**
   ```bash
   uv run python -m src.laliga_predictor.models.train --model random_forest
   ```

4. **Guardar modelos**
   ```
   models/
   ├── random_forest_v1.pkl
   ├── xgboost_v1.pkl
   └── model_metadata.json
   ```

### Entregables
- Modelos entrenados guardados en `models/`
- Script de entrenamiento reproducible
- Logs de entrenamiento

---

## FASE 4: Evaluacion y Ajuste (1 semana)

### Objetivo
Evaluar el rendimiento de los modelos y optimizar hiperparametros.

### Metricas de Evaluacion

| Metrica | Descripcion | Objetivo |
|---------|-------------|----------|
| **Accuracy** | % predicciones correctas | > 50% |
| **F1-Score (macro)** | Balance precision/recall por clase | > 0.45 |
| **F1-Score por clase** | H, D, A individualmente | Equilibrado |
| **Log Loss** | Calidad de probabilidades | Menor mejor |
| **ROI simulado** | Rentabilidad en apuestas simuladas | > 0% |

### Tareas

1. **Evaluar modelos base**
   ```bash
   uv run python -m src.laliga_predictor.models.evaluate --model random_forest_v1
   ```

2. **Optimizacion de hiperparametros**
   - Grid Search o Random Search
   - Cross-validation (5-fold)
   - Usar Optuna si es necesario

3. **Analisis de errores**
   - Confusion matrix
   - Partidos mal predichos
   - Patrones de error

4. **Feature importance**
   - Identificar features mas relevantes
   - Eliminar features irrelevantes
   - Crear nuevas features si es necesario

5. **Crear notebook de evaluacion**
   - `notebooks/02_model_evaluation.ipynb`
   - Visualizaciones de resultados
   - Comparacion de modelos

### Entregables
- Modelo optimizado (`models/best_model.pkl`)
- Reporte de evaluacion
- Notebook con analisis

---

## FASE 5: Despliegue (1-2 semanas)

### Objetivo
Crear una API REST para servir predicciones.

### Arquitectura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Cliente   │────▶│  FastAPI    │────▶│  PostgreSQL │
│   (Web/App) │     │  (API REST) │     │  (Docker)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Modelo    │
                    │   (pickle)  │
                    └─────────────┘
```

### Endpoints API

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/health` | Estado del servicio |
| GET | `/teams` | Lista de equipos |
| POST | `/predict` | Predecir resultado de partido |
| GET | `/predictions/upcoming` | Predicciones proxima jornada |

### Tareas

1. **Crear API con FastAPI**
   ```
   src/laliga_predictor/api/
   ├── __init__.py
   ├── main.py            # App FastAPI
   ├── routes/
   │   ├── health.py
   │   ├── teams.py
   │   └── predictions.py
   └── schemas.py         # Pydantic models
   ```

2. **Implementar endpoint de prediccion**
   ```python
   # POST /predict
   {
     "home_team": "Real Madrid",
     "away_team": "Barcelona"
   }

   # Response
   {
     "prediction": "H",
     "probabilities": {
       "H": 0.45,
       "D": 0.30,
       "A": 0.25
     }
   }
   ```

3. **Dockerizar API**
   ```dockerfile
   # Dockerfile.api
   FROM python:3.10-slim
   ...
   ```

4. **Actualizar docker-compose**
   ```yaml
   services:
     api:
       build: .
       ports:
         - "8000:8000"
   ```

5. **Documentacion API**
   - Swagger UI automatico en `/docs`
   - Ejemplos de uso

### Entregables
- API REST funcional
- Documentacion Swagger
- Docker Compose actualizado
- README con instrucciones de uso

---

## FASE 6: Mejoras Futuras (Opcional)

### Ideas para Mejorar el Modelo

1. **Mas datos**
   - Temporadas anteriores (2019-2021)
   - Otras ligas para transfer learning

2. **Mas features**
   - Datos de jugadores (lesiones, suspensiones)
   - Clima en el momento del partido
   - Importancia del partido (relegation, champions, etc.)

3. **Modelo ensemble**
   - Combinar multiples modelos
   - Stacking o blending

4. **Actualizacion automatica**
   - Cron job para actualizar datos
   - Re-entrenar modelo periodicamente

5. **Interfaz web**
   - Frontend con React/Vue
   - Visualizaciones interactivas

---

## Timeline Estimado

| Fase | Duracion | Acumulado |
|------|----------|-----------|
| Fase 1: Datos | 10-12 dias | 12 dias |
| Fase 2: Features | 1-2 semanas | 4 semanas |
| Fase 3: Modelo | 1 semana | 5 semanas |
| Fase 4: Evaluacion | 1 semana | 6 semanas |
| Fase 5: Despliegue | 1-2 semanas | 8 semanas |

**Total estimado: 6-8 semanas**

---

## Recursos Utiles

### Documentacion
- [scikit-learn](https://scikit-learn.org/)
- [XGBoost](https://xgboost.readthedocs.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [pandas](https://pandas.pydata.org/)

### Papers/Articulos
- "Predicting Football Match Results with Machine Learning"
- "Feature Engineering for Sports Analytics"

### Datasets Similares
- [Football-Data.co.uk](https://www.football-data.co.uk/)
- [Kaggle Football Datasets](https://www.kaggle.com/datasets?search=football)

---

## Checklist General

### Fase 1: Datos
- [ ] Completar temporada 2024
- [ ] Descargar temporada 2023
- [ ] Descargar temporada 2022
- [ ] Validacion final

### Fase 2: Features
- [ ] Implementar features de forma
- [ ] Implementar features H2H
- [ ] Implementar features de contexto
- [ ] Crear dataset de entrenamiento
- [ ] Notebook EDA

### Fase 3: Modelo
- [ ] Entrenar Logistic Regression
- [ ] Entrenar Random Forest
- [ ] Entrenar XGBoost
- [ ] Guardar modelos

### Fase 4: Evaluacion
- [ ] Evaluar modelos
- [ ] Optimizar hiperparametros
- [ ] Analisis de errores
- [ ] Seleccionar mejor modelo

### Fase 5: Despliegue
- [ ] Crear API FastAPI
- [ ] Implementar endpoints
- [ ] Dockerizar
- [ ] Documentar

---

## Notas

- Los tiempos son estimados y pueden variar
- Priorizar calidad sobre velocidad
- Documentar decisiones importantes
- Hacer commits frecuentes con mensajes descriptivos
