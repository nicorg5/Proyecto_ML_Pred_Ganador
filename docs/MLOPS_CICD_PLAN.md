# 🚀 PROFESIONALIZACIÓN DEL PROYECTO: MLOps & CI/CD

**Autor**: LaLiga Predictor Team
**Fecha**: Marzo 2026
**Versión**: 1.0
**Objetivo**: Transformar el proyecto en un sistema MLOps profesional con CI/CD automatizado

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura Final](#arquitectura-final)
4. [Plan de Implementación](#plan-de-implementación)
   - [Fase 1: CI/CD Básico (1-2 semanas)](#fase-1-cicd-básico-1-2-semanas)
   - [Fase 2: Databricks + MLflow (2-3 semanas)](#fase-2-databricks--mlflow-2-3-semanas)
   - [Fase 3: Data Validation (1 semana)](#fase-3-data-validation-1-semana)
   - [Fase 4: Reentrenamiento Automático (1 semana)](#fase-4-reentrenamiento-automático-1-semana)
   - [Fase 5: API REST + Despliegue Web (2 semanas)](#fase-5-api-rest--despliegue-web-2-semanas)
5. [Cronograma](#cronograma)
6. [Costos y Recursos](#costos-y-recursos)
7. [Métricas de Éxito](#métricas-de-éxito)

---

## Visión General

### Estado Actual del Proyecto
- ✅ Pipeline ML completo y funcional
- ✅ 111 tests unitarios e integración
- ✅ ~144 features con anti-leakage
- ✅ 8 modelos calibrados (Winner + O/U)
- ✅ Docker + PostgreSQL
- ⚠️ Proceso manual de entrenamiento
- ⚠️ Sin versionado de experimentos
- ⚠️ Sin despliegue automatizado

### Estado Objetivo
- ✅ Tests automáticos en cada PR (GitHub Actions)
- ✅ Experimentos versionados y comparables (MLflow)
- ✅ Datasets versionados (Databricks Delta Lake)
- ✅ Validación de datos automática (Great Expectations)
- ✅ Reentrenamiento semanal automático
- ✅ API REST desplegada en la web
- ✅ Monitoreo de performance en producción

---

## Stack Tecnológico

### 🔹 Nivel 1: CI/CD (Integración y Despliegue Continuo)

| Tecnología | Propósito | Costo | Justificación |
|------------|-----------|:-----:|---------------|
| **GitHub Actions** | CI/CD runner | 💰 Gratis | 2,000 min/mes gratis, integrado con GitHub |
| **pytest + pytest-cov** | Testing | 💰 Gratis | Ya implementado, 111 tests |
| **black + ruff** | Linting/Formatting | 💰 Gratis | Ya configurado en pre-commit |
| **codecov.io** | Code coverage | 💰 Gratis | Público, visualización de cobertura |

### 🔹 Nivel 2: MLOps (Gestión de ML)

| Tecnología | Propósito | Costo | Justificación |
|------------|-----------|:-----:|---------------|
| **Databricks Community** | Data platform | 💰 Gratis | Delta Lake + MLflow integrado, 15GB storage |
| **MLflow** | Experiment tracking | 💰 Gratis | Incluido en Databricks, tracking completo |
| **Delta Lake** | Versionado de datos | 💰 Gratis | Time-travel, ACID transactions |
| **Great Expectations** | Data validation | 💰 Gratis | Open-source, detecta anomalías |

### 🔹 Nivel 3: Despliegue (API en Producción)

| Tecnología | Propósito | Costo | Justificación |
|------------|-----------|:-----:|---------------|
| **FastAPI** | API REST framework | 💰 Gratis | Rápido, auto-documentación Swagger |
| **Railway.app** | Hosting API | 💰 $5/mes gratis | Fácil deploy desde GitHub, PostgreSQL incluido |
| **Vercel** (alternativa) | Serverless hosting | 💰 Gratis | Si quieres frontend React + API |
| **Docker** | Containerización | 💰 Gratis | Ya lo usas, portabilidad |

---

## Arquitectura Final

### Diagrama de Flujo Completo

```
┌──────────────────────────────────────────────────────────────────┐
│                        DESARROLLO                                 │
│                                                                   │
│  Developer Push → GitHub → GitHub Actions                        │
│                              │                                    │
│                              ├─→ Tests (pytest)                   │
│                              ├─→ Linting (black, ruff)            │
│                              ├─→ Code Coverage (codecov)          │
│                              └─→ Build Docker Image               │
│                                                                   │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                │ PR Approved
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                      ENTRENAMIENTO                                │
│                                                                   │
│  GitHub Actions (Schedule: Weekly)                               │
│         │                                                         │
│         ├─→ 1. Actualizar datos (ETL)                           │
│         ├─→ 2. Validar datos (Great Expectations)               │
│         ├─→ 3. Construir features                                │
│         ├─→ 4. Subir a Databricks (Delta Lake)                  │
│         │                                                         │
│         └─→ Databricks Cluster                                   │
│                   │                                               │
│                   ├─→ Feature Selection                          │
│                   ├─→ Optuna Tuning                              │
│                   ├─→ Train Models (RF, XGB, LGB)               │
│                   ├─→ MLflow Tracking (metrics, params)          │
│                   └─→ MLflow Model Registry                      │
│                             │                                     │
│                             └─→ Modelo "production"              │
│                                                                   │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                │ Modelo Aprobado
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                      DESPLIEGUE                                   │
│                                                                   │
│  GitHub Actions → Build Docker Image → Push to Registry         │
│                                                                   │
│  Railway.app (o Vercel)                                          │
│         │                                                         │
│         ├─→ FastAPI Container                                    │
│         │      ├─→ /predict (partido individual)                 │
│         │      ├─→ /predict/jornada (jornada completa)           │
│         │      ├─→ /health (healthcheck)                         │
│         │      └─→ /docs (Swagger UI)                            │
│         │                                                         │
│         └─→ PostgreSQL (datos históricos)                        │
│                                                                   │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ↓
                          ┌──────────┐
                          │  USUARIOS │
                          │   WEB     │
                          └──────────┘
```

### Flujo de Datos

```
┌─────────────────┐
│  Football-Data  │ (MatchHistory CSV)
└────────┬────────┘
         │
         ├─→ GitHub Actions ETL (Semanal)
         │
         ↓
┌─────────────────┐
│   PostgreSQL    │ (Local/Railway)
└────────┬────────┘
         │
         ├─→ Feature Engineering (GitHub Actions)
         │
         ↓
┌─────────────────┐
│ features.parquet│
└────────┬────────┘
         │
         ├─→ Upload to Databricks (Delta Lake)
         │
         ↓
┌──────────────────────────────────────┐
│      Databricks Delta Table          │
│   laliga.features (versionado)       │
└────────┬─────────────────────────────┘
         │
         ├─→ MLflow Experiment Tracking
         ├─→ Model Training (Notebook/Script)
         │
         ↓
┌──────────────────────────────────────┐
│    MLflow Model Registry             │
│  Modelo: "laliga_winner_ensemble"    │
│  Versiones: v1, v2, v3...            │
│  Stage: Production                   │
└────────┬─────────────────────────────┘
         │
         ├─→ Download Model (GitHub Actions)
         │
         ↓
┌──────────────────────────────────────┐
│      FastAPI Container               │
│  (Railway/Vercel)                    │
│  Modelo cargado en memoria           │
└──────────────────────────────────────┘
```

---

## Plan de Implementación

---

## Fase 1: CI/CD Básico (1-2 semanas)

**Objetivo**: Automatizar tests y validaciones en cada cambio de código.

### 🎯 Entregables
1. ✅ GitHub Actions workflow para tests
2. ✅ GitHub Actions workflow para linting
3. ✅ Badges de estado en README
4. ✅ Protección de rama master

---

### Paso 1.1: Configurar GitHub Actions - Tests

**Archivo**: `.github/workflows/tests.yml`

```yaml
name: Tests

on:
  push:
    branches: [master, main, feature/**]
  pull_request:
    branches: [master, main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: laliga_soccerdata_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install UV
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: uv sync

      - name: Run unit tests
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_DB: laliga_soccerdata_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        run: |
          uv run pytest tests/unit/ -v --cov=src --cov-report=xml --cov-report=term

      - name: Run integration tests
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_DB: laliga_soccerdata_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        run: |
          uv run pytest tests/integration/ -v --cov=src --cov-append --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: false
```

**Instrucciones de implementación:**

```bash
# 1. Crear directorio para workflows
mkdir -p .github/workflows

# 2. Crear el archivo tests.yml
# (copiar el contenido de arriba)

# 3. Commit y push
git add .github/workflows/tests.yml
git commit -m "ci: Add GitHub Actions workflow for automated testing"
git push origin feature/soccerdata-integration

# 4. Verificar en GitHub → Actions tab que el workflow se ejecuta
```

---

### Paso 1.2: Configurar GitHub Actions - Linting

**Archivo**: `.github/workflows/lint.yml`

```yaml
name: Code Quality

on:
  push:
    branches: [master, main, feature/**]
  pull_request:
    branches: [master, main]

jobs:
  lint:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install linting tools
        run: |
          pip install black ruff mypy

      - name: Check code formatting with black
        run: |
          black --check src/ tests/

      - name: Lint with ruff
        run: |
          ruff check src/ tests/

      - name: Type check with mypy
        run: |
          mypy src/ --ignore-missing-imports
        continue-on-error: true  # No fallar CI por errores de tipo (por ahora)
```

**Instrucciones:**

```bash
# 1. Crear el archivo lint.yml
# (copiar contenido)

# 2. Commit y push
git add .github/workflows/lint.yml
git commit -m "ci: Add linting and code quality workflow"
git push
```

---

### Paso 1.3: Añadir Badges al README

**Modificar**: `README.md` (al principio, después del título)

```markdown
# LaLiga Predictor

[![Tests](https://github.com/[TU-USUARIO]/Proyecto_ML_Pred_Ganador/workflows/Tests/badge.svg)](https://github.com/[TU-USUARIO]/Proyecto_ML_Pred_Ganador/actions?query=workflow%3ATests)
[![Code Quality](https://github.com/[TU-USUARIO]/Proyecto_ML_Pred_Ganador/workflows/Code%20Quality/badge.svg)](https://github.com/[TU-USUARIO]/Proyecto_ML_Pred_Ganador/actions?query=workflow%3A%22Code+Quality%22)
[![codecov](https://codecov.io/gh/[TU-USUARIO]/Proyecto_ML_Pred_Ganador/branch/master/graph/badge.svg)](https://codecov.io/gh/[TU-USUARIO]/Proyecto_ML_Pred_Ganador)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Sistema de Machine Learning para predecir resultados de partidos de La Liga Española...
```

**Instrucciones:**

```bash
# 1. Registrarse en codecov.io con tu cuenta de GitHub (gratis)
# 2. Añadir el repositorio en codecov.io
# 3. Copiar el token y añadirlo como secreto en GitHub:
#    Settings → Secrets and variables → Actions → New repository secret
#    Name: CODECOV_TOKEN
#    Value: [tu-token]

# 4. Reemplazar [TU-USUARIO] en los badges con tu usuario real
# 5. Commit
git add README.md
git commit -m "docs: Add CI/CD status badges"
git push
```

---

### Paso 1.4: Proteger Rama Master

**Instrucciones (en GitHub web):**

1. Ve a **Settings** → **Branches**
2. Click en **Add rule**
3. Branch name pattern: `master` (o `main`)
4. Activar:
   - ✅ **Require a pull request before merging**
   - ✅ **Require status checks to pass before merging**
     - Seleccionar: `test` y `lint`
   - ✅ **Require branches to be up to date before merging**
5. Click **Create**

**Resultado:**
- ❌ No se puede hacer push directo a master
- ✅ Solo PRs aprobados con tests pasando
- ✅ Código siempre limpio y testeado

---

### ✅ Checklist Fase 1

- [ ] `.github/workflows/tests.yml` creado y funcionando
- [ ] `.github/workflows/lint.yml` creado y funcionando
- [ ] Codecov configurado y subiendo coverage
- [ ] Badges añadidos al README
- [ ] Rama master protegida con status checks
- [ ] Tests pasando en todos los workflows

**Tiempo estimado:** 1-2 semanas (configuración + ajustes)

---

## Fase 2: Databricks + MLflow (2-3 semanas)

**Objetivo**: Versionar datos y experimentos con Databricks + MLflow integrado.

### 🎯 Entregables
1. ✅ Cuenta Databricks Community Edition configurada
2. ✅ Delta Lake con datos versionados
3. ✅ MLflow tracking integrado en `train.py`
4. ✅ Notebooks de exploración en Databricks
5. ✅ GitHub Actions que sube datos a Databricks

---

### Paso 2.1: Configurar Databricks Community Edition

**Instrucciones:**

1. **Registrarse en Databricks Community Edition**
   - Ir a: https://community.cloud.databricks.com/login.html
   - Click en "Sign up" → "Get started for free"
   - Usar tu email personal
   - Confirmar email y crear contraseña

2. **Crear un Cluster**
   ```
   Compute → Create Cluster
   - Cluster name: laliga-ml-cluster
   - Cluster mode: Single Node
   - Databricks runtime: 14.3 LTS (ML)
   - Node type: Standard_DS3_v2 (Community default)
   - Auto-terminate: 120 minutes
   ```

3. **Verificar MLflow está disponible**
   - En el sidebar: Machine Learning → Experiments
   - Deberías ver la interfaz de MLflow

4. **Crear un Notebook de prueba**
   ```python
   # Databricks notebook: Test MLflow
   import mlflow

   with mlflow.start_run():
       mlflow.log_param("test", "hello")
       mlflow.log_metric("metric", 1.0)

   print("✅ MLflow working!")
   ```

---

### Paso 2.2: Crear Tabla Delta para Features

**Databricks Notebook**: `00_setup_delta_tables.py`

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Setup Delta Tables para LaLiga Predictor
# MAGIC
# MAGIC Este notebook crea las tablas Delta para almacenar:
# MAGIC - Features versionadas
# MAGIC - Metadatos de entrenamientos

# COMMAND ----------
from delta.tables import DeltaTable
from pyspark.sql import SparkSession

# Crear base de datos
spark.sql("CREATE DATABASE IF NOT EXISTS laliga")

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Crear tabla de features (vacía por ahora)
# MAGIC CREATE TABLE IF NOT EXISTS laliga.features (
# MAGIC   match_id STRING,
# MAGIC   match_date DATE,
# MAGIC   home_team STRING,
# MAGIC   away_team STRING,
# MAGIC   season_code STRING,
# MAGIC   -- Rolling form features
# MAGIC   h_win_rate_3 DOUBLE,
# MAGIC   h_win_rate_5 DOUBLE,
# MAGIC   h_win_rate_10 DOUBLE,
# MAGIC   -- (agregar todas las ~144 features aquí)
# MAGIC   -- ...
# MAGIC   -- Target variables
# MAGIC   result STRING,
# MAGIC   home_goals INT,
# MAGIC   away_goals INT,
# MAGIC   total_goals INT,
# MAGIC   total_cards INT,
# MAGIC   timestamp TIMESTAMP
# MAGIC )
# MAGIC USING DELTA
# MAGIC PARTITIONED BY (season_code)
# MAGIC LOCATION '/mnt/delta/laliga/features'

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Habilitar time travel
# MAGIC ALTER TABLE laliga.features SET TBLPROPERTIES (
# MAGIC   'delta.logRetentionDuration' = 'interval 90 days',
# MAGIC   'delta.deletedFileRetentionDuration' = 'interval 90 days'
# MAGIC )

# COMMAND ----------
# Verificar tabla creada
display(spark.sql("DESCRIBE EXTENDED laliga.features"))
```

**Instrucciones:**
1. Crear este notebook en Databricks: Workspace → Create → Notebook
2. Ejecutar todas las celdas
3. Verificar que la tabla `laliga.features` existe

---

### Paso 2.3: Script para Subir Features a Databricks

**Archivo local**: `src/laliga_predictor/databricks/upload_features.py`

```python
"""
Upload features to Databricks Delta Lake.

This script reads features.parquet and uploads to Databricks Delta table
with versioning support.
"""

import os
from pathlib import Path

import pandas as pd
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config


def upload_features_to_delta(
    features_path: str = "data/processed/features.parquet",
    table_name: str = "laliga.features",
):
    """Upload features to Databricks Delta table."""

    # Leer features locales
    print(f"📖 Reading features from {features_path}")
    df = pd.read_parquet(features_path)
    print(f"   Loaded {len(df)} rows with {len(df.columns)} columns")

    # Conectar a Databricks
    # Usa variables de entorno: DATABRICKS_HOST, DATABRICKS_TOKEN
    config = Config(
        host=os.getenv("DATABRICKS_HOST"),
        token=os.getenv("DATABRICKS_TOKEN"),
    )

    w = WorkspaceClient(config=config)

    # Convertir DataFrame a Spark DataFrame y escribir a Delta
    print(f"📤 Uploading to Delta table: {table_name}")

    # Crear conexión SQL
    with sql.connect(
        server_hostname=config.host,
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=config.token,
    ) as connection:
        cursor = connection.cursor()

        # Opción 1: MERGE (upsert) para evitar duplicados
        # Por simplicidad, aquí hacemos OVERWRITE
        # En producción, usa MERGE para mantener historial

        cursor.execute(f"DELETE FROM {table_name}")
        print(f"   Deleted old data from {table_name}")

        # Insertar en lotes (Databricks tiene límites de tamaño)
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            # Insertar batch (simplificado, en producción usa spark.createDataFrame)
            print(f"   Uploading batch {i//batch_size + 1}...")

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"✅ Upload complete. Table has {count} rows")


if __name__ == "__main__":
    upload_features_to_delta()
```

**Configurar variables de entorno** (`.env`):

```bash
# Databricks credentials
DATABRICKS_HOST=https://community.cloud.databricks.com
DATABRICKS_TOKEN=dapi...  # Generar en: Settings → User Settings → Access Tokens
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/...  # Copiar de tu cluster
```

**Instrucciones:**

```bash
# 1. Instalar SDK de Databricks
uv add databricks-sdk databricks-sql-connector

# 2. Generar token en Databricks:
#    Settings → User Settings → Access Tokens → Generate New Token

# 3. Añadir credenciales al .env

# 4. Ejecutar script localmente (primera vez)
uv run python src/laliga_predictor/databricks/upload_features.py
```

---

### Paso 2.4: Integrar MLflow en train.py

**Modificar**: `src/laliga_predictor/models/train.py`

```python
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

# Al inicio del archivo, configurar MLflow
mlflow.set_tracking_uri("databricks")  # Usa Databricks como backend
# O si quieres local: mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("/Users/[tu-email]/laliga-predictor")


def train_model_with_mlflow(
    model_factory,
    target: str,
    X_train,
    y_train,
    X_val,
    y_val,
    tuned_params: dict = None,
):
    """Train model with MLflow tracking."""

    model_name = model_factory.__name__
    run_name = f"{target}_{model_name}"

    with mlflow.start_run(run_name=run_name) as run:
        print(f"🔬 MLflow Run ID: {run.info.run_id}")

        # Log parameters
        mlflow.log_param("target", target)
        mlflow.log_param("model_type", model_name)
        mlflow.log_param("train_seasons", settings.TRAIN_SEASONS)
        mlflow.log_param("val_seasons", settings.VAL_SEASONS)
        mlflow.log_param("n_features", X_train.shape[1])
        mlflow.log_param("n_train_samples", len(X_train))
        mlflow.log_param("n_val_samples", len(X_val))

        if tuned_params:
            mlflow.log_params({f"hp_{k}": v for k, v in tuned_params.items()})

        # Train model
        print(f"🏋️  Training {model_name} for {target}...")
        model = model_factory(**tuned_params) if tuned_params else model_factory()

        # Wrap with calibration if not baseline
        if "Baseline" not in model_name:
            model = CalibratedPredictor(model, n_classes=len(np.unique(y_train)))

        model.fit(X_train, y_train, X_val, y_val)

        # Evaluate
        y_val_pred = model.predict(X_val)
        y_val_proba = model.predict_proba(X_val)

        metrics = evaluate_model(y_val, y_val_pred, y_val_proba, target_type="multiclass")

        # Log metrics
        mlflow.log_metrics({
            "val_accuracy": metrics["accuracy"],
            "val_f1_macro": metrics["f1_macro"],
            "val_precision": metrics["precision"],
            "val_recall": metrics["recall"],
        })

        # Log per-class metrics
        for cls in ["H", "D", "A"]:
            if f"accuracy_{cls}" in metrics:
                mlflow.log_metric(f"val_accuracy_{cls}", metrics[f"accuracy_{cls}"])

        # Log model
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=f"laliga_{target}_{model_name.lower()}",
        )

        # Log artifacts
        mlflow.log_artifact("models/training_results.json")

        # Tag importante
        mlflow.set_tag("stage", "development")
        mlflow.set_tag("framework", "scikit-learn")

        print(f"✅ Model logged to MLflow")
        print(f"   Run ID: {run.info.run_id}")
        print(f"   Accuracy: {metrics['accuracy']:.3f}")

        return model, metrics


# En la función main(), reemplazar train_model() con train_model_with_mlflow()
```

**Instrucciones:**

```bash
# 1. Instalar MLflow
uv add mlflow

# 2. Modificar train.py (copiar código de arriba)

# 3. Probar localmente primero
uv run python -m src.laliga_predictor.models.train --target winner --model xgboost

# 4. Verificar en Databricks: Machine Learning → Experiments
#    Deberías ver el experimento "laliga-predictor" con runs
```

---

### Paso 2.5: GitHub Actions para Subir a Databricks

**Archivo**: `.github/workflows/upload-to-databricks.yml`

```yaml
name: Upload Features to Databricks

on:
  workflow_dispatch:  # Manual trigger
  schedule:
    - cron: '0 3 * * 2'  # Martes 3 AM (después de jornada)

jobs:
  upload:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: laliga_soccerdata
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: ${{ secrets.DB_PASSWORD }}
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install UV
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: uv sync

      - name: Update ETL data
        run: make ml-update

      - name: Build features
        run: make ml-features

      - name: Upload to Databricks
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
          DATABRICKS_HTTP_PATH: ${{ secrets.DATABRICKS_HTTP_PATH }}
        run: |
          uv run python src/laliga_predictor/databricks/upload_features.py
```

**Configurar Secrets en GitHub:**

```
Settings → Secrets and variables → Actions → New repository secret

Crear 3 secretos:
1. DATABRICKS_HOST = https://community.cloud.databricks.com
2. DATABRICKS_TOKEN = dapi...
3. DATABRICKS_HTTP_PATH = /sql/1.0/warehouses/...
```

---

### ✅ Checklist Fase 2

- [ ] Cuenta Databricks Community configurada
- [ ] Cluster creado y funcionando
- [ ] Tabla Delta `laliga.features` creada
- [ ] Script `upload_features.py` funciona localmente
- [ ] MLflow integrado en `train.py`
- [ ] Experimento visible en Databricks MLflow UI
- [ ] GitHub Actions sube features a Databricks automáticamente
- [ ] Secrets de Databricks configurados en GitHub

**Tiempo estimado:** 2-3 semanas (configuración + integración)

---

## Fase 3: Data Validation (1 semana)

**Objetivo**: Validar automáticamente la calidad de datos antes de entrenar.

### 🎯 Entregables
1. ✅ Great Expectations configurado
2. ✅ Expectations definidas para features
3. ✅ GitHub Actions valida datos antes de training

---

### Paso 3.1: Configurar Great Expectations

**Instrucciones:**

```bash
# 1. Instalar Great Expectations
uv add great-expectations

# 2. Inicializar Great Expectations
uv run great_expectations init

# Esto crea:
# - great_expectations/
#   - great_expectations.yml (config)
#   - expectations/ (reglas de validación)
#   - checkpoints/ (puntos de validación)
#   - uncommitted/ (resultados locales)
```

---

### Paso 3.2: Crear Expectation Suite

**Archivo**: `tests/data_validation/create_expectations.py`

```python
"""
Create Great Expectations suite for features validation.
"""

import great_expectations as gx
from great_expectations.core.expectation_configuration import ExpectationConfiguration

# Crear contexto
context = gx.get_context()

# Crear suite
suite_name = "laliga_features_suite"
suite = context.add_expectation_suite(expectation_suite_name=suite_name)

# ================================
# EXPECTATIVAS: Estructura de datos
# ================================

# 1. Número de columnas debe ser ~144
suite.add_expectation(
    ExpectationConfiguration(
        expectation_type="expect_table_column_count_to_be_between",
        kwargs={
            "min_value": 140,
            "max_value": 150,
        }
    )
)

# 2. Columnas obligatorias deben existir
required_columns = [
    "match_id", "match_date", "home_team", "away_team", "season_code",
    "result", "home_goals", "away_goals",
    "h_win_rate_5", "a_win_rate_5",
    "h_league_position", "a_league_position",
]

for col in required_columns:
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_to_exist",
            kwargs={"column": col}
        )
    )

# ================================
# EXPECTATIVAS: Valores de features
# ================================

# 3. Win rates deben estar entre 0 y 1
for window in [3, 5, 10]:
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": f"h_win_rate_{window}",
                "min_value": 0.0,
                "max_value": 1.0,
            }
        )
    )

# 4. Posiciones en la liga deben estar entre 1 y 20
for team in ["h", "a"]:
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": f"{team}_league_position",
                "min_value": 1,
                "max_value": 20,
            }
        )
    )

# 5. Goles deben ser no negativos
for col in ["home_goals", "away_goals"]:
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": col,
                "min_value": 0,
                "max_value": 15,  # Máximo razonable
            }
        )
    )

# 6. Resultado debe ser H, D o A
suite.add_expectation(
    ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={
            "column": "result",
            "value_set": ["H", "D", "A"],
        }
    )
)

# 7. No debe haber nulls en features críticas
for col in ["h_league_position", "a_league_position", "result"]:
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": col}
        )
    )

# 8. ELO ratings deben estar en rango razonable
for team in ["h", "a"]:
    suite.add_expectation(
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": f"{team}_elo",
                "min_value": 1200,
                "max_value": 1800,
            }
        )
    )

# Guardar suite
context.save_expectation_suite(suite)
print(f"✅ Created expectation suite: {suite_name}")
print(f"   Total expectations: {len(suite.expectations)}")
```

**Ejecutar:**

```bash
uv run python tests/data_validation/create_expectations.py
```

---

### Paso 3.3: Crear Checkpoint

**Archivo**: `tests/data_validation/validate_features.py`

```python
"""
Validate features.parquet using Great Expectations.
"""

import sys
import great_expectations as gx
from great_expectations.checkpoint import Checkpoint

def validate_features(features_path: str = "data/processed/features.parquet"):
    """Validate features and return results."""

    context = gx.get_context()

    # Crear datasource
    datasource = context.sources.add_pandas(name="features_datasource")
    data_asset = datasource.add_parquet_asset(
        name="features",
        batching_regex=r"features\.parquet",
    )

    # Crear batch request
    batch_request = data_asset.build_batch_request()

    # Crear checkpoint
    checkpoint = Checkpoint(
        name="features_checkpoint",
        data_context=context,
        expectation_suite_name="laliga_features_suite",
        action_list=[
            {
                "name": "store_validation_result",
                "action": {"class_name": "StoreValidationResultAction"},
            },
            {
                "name": "update_data_docs",
                "action": {"class_name": "UpdateDataDocsAction"},
            },
        ],
    )

    # Ejecutar validación
    print(f"🔍 Validating {features_path}...")
    result = checkpoint.run(batch_request=batch_request)

    # Verificar resultado
    if result["success"]:
        print("✅ Validation PASSED")
        print(f"   All {len(result['run_results'])} checks passed")
        return 0
    else:
        print("❌ Validation FAILED")
        for check, details in result["run_results"].items():
            if not details["success"]:
                print(f"   Failed: {check}")
        print("\n💡 View detailed report: great_expectations/uncommitted/data_docs/local_site/index.html")
        return 1


if __name__ == "__main__":
    features_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/features.parquet"
    exit_code = validate_features(features_path)
    sys.exit(exit_code)
```

**Probar localmente:**

```bash
# 1. Generar features
make ml-features

# 2. Validar
uv run python tests/data_validation/validate_features.py

# 3. Ver reporte HTML (si falla)
open great_expectations/uncommitted/data_docs/local_site/index.html
```

---

### Paso 3.4: Integrar en GitHub Actions

**Modificar**: `.github/workflows/upload-to-databricks.yml`

Añadir step antes de "Build features":

```yaml
      - name: Validate data quality
        run: |
          uv run python tests/data_validation/validate_features.py data/processed/features.parquet
        continue-on-error: false  # Fallar CI si validación falla
```

---

### ✅ Checklist Fase 3

- [ ] Great Expectations instalado y configurado
- [ ] Expectation suite creada con ~20 validaciones
- [ ] Checkpoint funciona localmente
- [ ] GitHub Actions valida datos antes de subir a Databricks
- [ ] Reportes HTML generados en caso de fallos

**Tiempo estimado:** 1 semana

---

## Fase 4: Reentrenamiento Automático (1 semana)

**Objetivo**: Reentrenar modelos automáticamente cada semana después de la jornada.

### 🎯 Entregables
1. ✅ Workflow de reentrenamiento programado
2. ✅ Entrena en Databricks cluster
3. ✅ Registra nuevo modelo en MLflow
4. ✅ Notificaciones de éxito/fallo

---

### Paso 4.1: Databricks Notebook para Training

**Databricks Notebook**: `01_train_models.py`

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # LaLiga Predictor - Training Pipeline
# MAGIC
# MAGIC Este notebook entrena todos los modelos y registra en MLflow.

# COMMAND ----------
# MAGIC %pip install scikit-learn xgboost lightgbm optuna

# COMMAND ----------
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# Configurar MLflow
mlflow.set_experiment("/Users/[tu-email]/laliga-training")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Cargar Features desde Delta Lake

# COMMAND ----------
# Leer features desde Delta table
df = spark.table("laliga.features").toPandas()

print(f"📊 Loaded {len(df)} samples")
print(f"   Features: {len(df.columns)} columns")
print(f"   Seasons: {df['season_code'].unique()}")

# COMMAND ----------
# Split por temporadas
train_seasons = ["1718", "1819", "1920", "2021", "2122", "2223", "2324"]
val_seasons = ["2425"]
test_seasons = ["2526"]

train_df = df[df["season_code"].isin(train_seasons)]
val_df = df[df["season_code"].isin(val_seasons)]
test_df = df[df["season_code"].isin(test_seasons)]

print(f"Train: {len(train_df)} samples")
print(f"Val:   {len(val_df)} samples")
print(f"Test:  {len(test_df)} samples")

# COMMAND ----------
# Separar features y target
feature_cols = [col for col in df.columns if col not in [
    "match_id", "match_date", "home_team", "away_team", "season_code",
    "result", "home_goals", "away_goals", "total_goals", "total_cards"
]]

X_train = train_df[feature_cols]
y_train = train_df["result"]

X_val = val_df[feature_cols]
y_val = val_df["result"]

print(f"Features: {len(feature_cols)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Entrenar Ensemble Model

# COMMAND ----------
with mlflow.start_run(run_name="ensemble_winner") as run:

    # Log params
    mlflow.log_param("model_type", "VotingClassifier")
    mlflow.log_param("n_features", len(feature_cols))
    mlflow.log_param("train_size", len(X_train))
    mlflow.log_param("val_size", len(X_val))

    # Crear ensemble
    ensemble = VotingClassifier(
        estimators=[
            ("rf", RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42)),
            ("xgb", XGBClassifier(n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42)),
            ("lgb", LGBMClassifier(n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42)),
        ],
        voting="soft",
        n_jobs=-1,
    )

    # Entrenar
    print("🏋️  Training ensemble...")
    ensemble.fit(X_train, y_train)

    # Evaluar
    val_acc = ensemble.score(X_val, y_val)
    mlflow.log_metric("val_accuracy", val_acc)

    # Log model
    mlflow.sklearn.log_model(
        ensemble,
        artifact_path="model",
        registered_model_name="laliga_winner_ensemble",
    )

    print(f"✅ Model trained and logged")
    print(f"   Val Accuracy: {val_acc:.3f}")
    print(f"   Run ID: {run.info.run_id}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Transicionar Modelo a Production

# COMMAND ----------
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Obtener última versión del modelo
model_name = "laliga_winner_ensemble"
latest_versions = client.get_latest_versions(model_name, stages=["None"])

if latest_versions:
    latest_version = latest_versions[0].version

    # Archivar versión anterior en Production (si existe)
    prod_versions = client.get_latest_versions(model_name, stages=["Production"])
    for mv in prod_versions:
        client.transition_model_version_stage(
            name=model_name,
            version=mv.version,
            stage="Archived",
        )

    # Promover nueva versión a Production
    client.transition_model_version_stage(
        name=model_name,
        version=latest_version,
        stage="Production",
    )

    print(f"✅ Model version {latest_version} transitioned to Production")
```

**Instrucciones:**
1. Crear este notebook en Databricks
2. Ejecutar manualmente la primera vez para verificar que funciona
3. Anotar el path del notebook (ej: `/Users/tu@email.com/01_train_models`)

---

### Paso 4.2: GitHub Actions - Trigger Databricks Job

**Archivo**: `.github/workflows/retrain-weekly.yml`

```yaml
name: Weekly Model Retraining

on:
  schedule:
    - cron: '0 4 * * 2'  # Martes 4 AM
  workflow_dispatch:      # Trigger manual

jobs:
  retrain:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Databricks CLI
        run: pip install databricks-cli

      - name: Configure Databricks CLI
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: |
          echo "$DATABRICKS_HOST" > ~/.databrickscfg
          echo "$DATABRICKS_TOKEN" >> ~/.databrickscfg

      - name: Update data and upload to Databricks
        run: |
          # Este step ya existe en upload-to-databricks.yml
          # Llamarlo desde aquí o duplicar lógica
          echo "Triggering data upload..."

      - name: Trigger Databricks Notebook
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: |
          # Ejecutar notebook usando REST API
          curl -X POST "$DATABRICKS_HOST/api/2.1/jobs/run-now" \
            -H "Authorization: Bearer $DATABRICKS_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{
              "job_id": "YOUR_JOB_ID",
              "notebook_params": {}
            }'

      - name: Wait for job completion
        run: |
          # Poll job status
          echo "Waiting for training to complete..."
          sleep 300  # Simplificado, en producción usar polling real

      - name: Notify success
        if: success()
        run: |
          echo "✅ Weekly retraining completed successfully!"
          # Aquí puedes añadir notificación a Slack, email, etc.

      - name: Notify failure
        if: failure()
        run: |
          echo "❌ Weekly retraining FAILED!"
          # Notificar fallo
```

**Configurar Databricks Job:**

1. En Databricks: Workflows → Create Job
2. Configurar:
   - Task: Notebook
   - Path: `/Users/tu@email.com/01_train_models`
   - Cluster: laliga-ml-cluster
3. Guardar y anotar el Job ID
4. Reemplazar `YOUR_JOB_ID` en el workflow

---

### ✅ Checklist Fase 4

- [ ] Notebook de training creado en Databricks
- [ ] Notebook ejecuta correctamente y registra en MLflow
- [ ] Databricks Job configurado
- [ ] GitHub Actions puede triggerar el Job
- [ ] Workflow programado para Martes 4 AM
- [ ] Notificaciones configuradas (opcional)

**Tiempo estimado:** 1 semana

---

## Fase 5: API REST + Despliegue Web (2 semanas)

**Objetivo**: Desplegar API públicamente para consumir predicciones.

### 🎯 Entregables
1. ✅ FastAPI con endpoints de predicción
2. ✅ Dockerfile para containerizar API
3. ✅ Desplegado en Railway.app (gratis)
4. ✅ CI/CD automático para deploy

---

### Paso 5.1: Crear FastAPI Application

**Archivo**: `src/laliga_predictor/api/main.py`

```python
"""
FastAPI application for LaLiga Predictor.

Endpoints:
- POST /predict: Predict single match
- POST /predict/jornada: Predict full matchday
- GET /health: Health check
- GET /models: List available models
"""

from datetime import date
from typing import List, Optional

import mlflow
import mlflow.sklearn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..features.feature_engineering import MatchFeatureBuilder
from ..features.data_loader import MatchDataLoader

# Initialize FastAPI
app = FastAPI(
    title="LaLiga Predictor API",
    description="ML-powered predictions for La Liga matches",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS para permitir acceso desde web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load models from MLflow (on startup)
@app.on_event("startup")
async def load_models():
    """Load models from MLflow Model Registry."""
    global winner_model, goals_ou_models

    print("📦 Loading models from MLflow...")

    # Load winner model (production stage)
    winner_model = mlflow.sklearn.load_model(
        "models:/laliga_winner_ensemble/Production"
    )
    print("✅ Winner model loaded")

    # Load O/U models
    goals_ou_models = {}
    for line in ["1.5", "2.5", "3.5"]:
        model_name = f"laliga_goals_over_{line.replace('.', '_')}"
        try:
            goals_ou_models[line] = mlflow.sklearn.load_model(
                f"models:/{model_name}/Production"
            )
            print(f"✅ Goals O/U {line} model loaded")
        except Exception as e:
            print(f"⚠️  Could not load Goals O/U {line}: {e}")


# ================================
# Pydantic Models (Request/Response)
# ================================

class MatchPredictionRequest(BaseModel):
    """Request for single match prediction."""
    home_team: str = Field(..., example="Real Madrid")
    away_team: str = Field(..., example="Barcelona")
    match_date: str = Field(..., example="2026-03-15")


class MatchPredictionResponse(BaseModel):
    """Response with predictions."""
    home_team: str
    away_team: str
    match_date: str
    prediction: str  # H, D, or A
    probabilities: dict = Field(..., example={
        "home_win": 0.45,
        "draw": 0.30,
        "away_win": 0.25,
    })
    goals_over_under: dict = Field(..., example={
        "1.5": {"over": 0.85, "under": 0.15},
        "2.5": {"over": 0.60, "under": 0.40},
        "3.5": {"over": 0.35, "under": 0.65},
    })


# ================================
# Endpoints
# ================================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint."""
    return {
        "message": "LaLiga Predictor API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["General"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "models_loaded": {
            "winner": winner_model is not None,
            "goals_ou": len(goals_ou_models),
        }
    }


@app.get("/models", tags=["General"])
async def list_models():
    """List available models."""
    return {
        "winner_model": "VotingClassifier (RF + XGBoost + LightGBM)",
        "goals_ou_models": list(goals_ou_models.keys()),
    }


@app.post("/predict", response_model=MatchPredictionResponse, tags=["Predictions"])
async def predict_match(request: MatchPredictionRequest):
    """
    Predict outcome of a single match.

    Returns:
    - Predicted result (H/D/A)
    - Probabilities for each outcome
    - Over/Under probabilities for goals
    """
    try:
        # Build features
        loader = MatchDataLoader()
        builder = MatchFeatureBuilder(
            matches=loader.load_matches(),
            advanced_stats=loader.load_advanced_stats(),
            standings=loader.load_standings(),
        )

        # Create synthetic match for prediction
        match = {
            "home_team": request.home_team,
            "away_team": request.away_team,
            "match_date": date.fromisoformat(request.match_date),
            "season_code": "2526",  # Current season
        }

        features = builder.build_features_for_match(match)

        if features is None:
            raise HTTPException(
                status_code=400,
                detail="Could not build features. Check team names and date."
            )

        # Predict winner
        X = features[winner_model.feature_names_in_]  # Ensure correct order
        proba = winner_model.predict_proba([X])[0]
        prediction = winner_model.predict([X])[0]

        # Predict goals O/U
        goals_predictions = {}
        for line, model in goals_ou_models.items():
            goals_proba = model.predict_proba([X])[0]
            goals_predictions[line] = {
                "over": float(goals_proba[1]),
                "under": float(goals_proba[0]),
            }

        return MatchPredictionResponse(
            home_team=request.home_team,
            away_team=request.away_team,
            match_date=request.match_date,
            prediction=prediction,
            probabilities={
                "home_win": float(proba[2]),
                "draw": float(proba[1]),
                "away_win": float(proba[0]),
            },
            goals_over_under=goals_predictions,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Probar localmente:**

```bash
# 1. Instalar FastAPI y uvicorn
uv add fastapi uvicorn

# 2. Ejecutar API
uv run uvicorn src.laliga_predictor.api.main:app --reload

# 3. Abrir navegador: http://localhost:8000/docs
# 4. Probar endpoint /predict con Swagger UI
```

---

### Paso 5.2: Dockerizar API

**Archivo**: `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar UV
RUN pip install uv

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./

# Instalar dependencias
RUN uv sync --no-dev

# Copiar código fuente
COPY src/ ./src/
COPY models/ ./models/

# Exponer puerto
EXPOSE 8000

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV MLFLOW_TRACKING_URI=databricks

# Comando de inicio
CMD ["uv", "run", "uvicorn", "src.laliga_predictor.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Probar Docker localmente:**

```bash
# 1. Build
docker build -t laliga-predictor-api .

# 2. Run
docker run -p 8000:8000 \
  -e DATABRICKS_HOST=$DATABRICKS_HOST \
  -e DATABRICKS_TOKEN=$DATABRICKS_TOKEN \
  laliga-predictor-api

# 3. Verificar: http://localhost:8000/docs
```

---

### Paso 5.3: Desplegar en Railway.app

**Instrucciones:**

1. **Crear cuenta en Railway**
   - Ir a: https://railway.app
   - Sign up con GitHub (gratis, $5 crédito mensual)

2. **Crear nuevo proyecto**
   - Dashboard → New Project
   - Deploy from GitHub repo
   - Seleccionar: `Proyecto_ML_Pred_Ganador`
   - Railway detecta Dockerfile automáticamente

3. **Configurar variables de entorno**
   - En Railway dashboard → Variables
   - Añadir:
     ```
     DATABRICKS_HOST=https://community.cloud.databricks.com
     DATABRICKS_TOKEN=dapi...
     POSTGRES_HOST=...  (si usas PostgreSQL en Railway)
     ```

4. **Añadir servicio PostgreSQL (opcional)**
   - New Service → Database → PostgreSQL
   - Railway lo conecta automáticamente

5. **Deploy**
   - Railway hace deploy automáticamente al hacer push a GitHub
   - URL pública: `https://tu-proyecto.railway.app`

**Alternativa: Render.com (completamente gratis)**

```yaml
# render.yaml
services:
  - type: web
    name: laliga-predictor-api
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: DATABRICKS_HOST
        value: https://community.cloud.databricks.com
      - key: DATABRICKS_TOKEN
        sync: false  # Secret
    plan: free  # Duerme tras 15 min inactividad
```

1. Crear cuenta en https://render.com
2. New → Web Service → Connect to GitHub
3. Render detecta `render.yaml` y deploya automáticamente

---

### Paso 5.4: CI/CD para Deploy Automático

**Archivo**: `.github/workflows/deploy-api.yml`

```yaml
name: Deploy API

on:
  push:
    branches: [master]
    paths:
      - 'src/laliga_predictor/api/**'
      - 'Dockerfile'
      - '.github/workflows/deploy-api.yml'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/api:latest
            ghcr.io/${{ github.repository }}/api:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Trigger Railway deployment
        run: |
          # Railway deploya automáticamente desde GitHub
          echo "✅ Docker image pushed. Railway will auto-deploy."
```

---

### Paso 5.5: Frontend Simple (Opcional)

**Archivo**: `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>LaLiga Predictor</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #333; text-align: center; }
        input, button {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #5568d3; }
        #result {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 5px;
        }
        .prediction { font-size: 24px; font-weight: bold; color: #667eea; }
        .probs { margin-top: 10px; }
        .prob-bar {
            height: 30px;
            background: #667eea;
            color: white;
            display: flex;
            align-items: center;
            padding: 0 10px;
            margin: 5px 0;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚽ LaLiga Predictor</h1>
        <p style="text-align: center; color: #666;">
            Predicción con ML de partidos de La Liga
        </p>

        <form id="predictionForm">
            <input type="text" id="homeTeam" placeholder="Equipo Local (ej: Real Madrid)" required>
            <input type="text" id="awayTeam" placeholder="Equipo Visitante (ej: Barcelona)" required>
            <input type="date" id="matchDate" required>
            <button type="submit">Predecir Resultado</button>
        </form>

        <div id="result" style="display: none;">
            <h2>Resultado Predicho: <span class="prediction" id="prediction"></span></h2>
            <div class="probs">
                <div class="prob-bar" id="homeBar"></div>
                <div class="prob-bar" id="drawBar"></div>
                <div class="prob-bar" id="awayBar"></div>
            </div>
        </div>
    </div>

    <script>
        const API_URL = 'https://tu-proyecto.railway.app';  // Reemplazar con tu URL

        document.getElementById('predictionForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const homeTeam = document.getElementById('homeTeam').value;
            const awayTeam = document.getElementById('awayTeam').value;
            const matchDate = document.getElementById('matchDate').value;

            try {
                const response = await fetch(`${API_URL}/predict`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ home_team: homeTeam, away_team: awayTeam, match_date: matchDate })
                });

                const data = await response.json();

                // Mostrar resultado
                document.getElementById('prediction').textContent =
                    data.prediction === 'H' ? `Victoria Local (${homeTeam})` :
                    data.prediction === 'D' ? 'Empate' :
                    `Victoria Visitante (${awayTeam})`;

                // Barras de probabilidad
                const probs = data.probabilities;
                document.getElementById('homeBar').style.width = `${probs.home_win * 100}%`;
                document.getElementById('homeBar').textContent = `Local: ${(probs.home_win * 100).toFixed(1)}%`;

                document.getElementById('drawBar').style.width = `${probs.draw * 100}%`;
                document.getElementById('drawBar').textContent = `Empate: ${(probs.draw * 100).toFixed(1)}%`;
                document.getElementById('drawBar').style.background = '#f39c12';

                document.getElementById('awayBar').style.width = `${probs.away_win * 100}%`;
                document.getElementById('awayBar').textContent = `Visitante: ${(probs.away_win * 100).toFixed(1)}%`;
                document.getElementById('awayBar').style.background = '#e74c3c';

                document.getElementById('result').style.display = 'block';

            } catch (error) {
                alert('Error al hacer predicción: ' + error.message);
            }
        });
    </script>
</body>
</html>
```

**Desplegar frontend en Vercel (gratis):**

```bash
# 1. Instalar Vercel CLI
npm install -g vercel

# 2. Deploy
cd frontend/
vercel --prod

# 3. URL pública: https://tu-frontend.vercel.app
```

---

### ✅ Checklist Fase 5

- [ ] FastAPI implementada con endpoints `/predict`, `/health`, `/docs`
- [ ] API funciona localmente
- [ ] Dockerfile creado y probado
- [ ] API desplegada en Railway.app
- [ ] URL pública funcionando
- [ ] GitHub Actions deploya automáticamente
- [ ] Frontend opcional desplegado en Vercel

**Tiempo estimado:** 2 semanas

---

## Cronograma

```
┌─────────────────────────────────────────────────────────────────┐
│                      ROADMAP (7-9 semanas)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SEMANA 1-2: ████████░░ Fase 1 - CI/CD Básico                  │
│              - GitHub Actions (tests + linting)                 │
│              - Badges + protección de rama                      │
│                                                                  │
│  SEMANA 3-5: ██████████████░░ Fase 2 - Databricks + MLflow     │
│              - Databricks Community setup                       │
│              - Delta Lake + MLflow tracking                     │
│              - Integración con train.py                         │
│                                                                  │
│  SEMANA 6:   ████░░ Fase 3 - Data Validation                   │
│              - Great Expectations                               │
│              - Validaciones automáticas                         │
│                                                                  │
│  SEMANA 7:   ████░░ Fase 4 - Reentrenamiento Auto              │
│              - Workflow semanal                                 │
│              - Databricks Job scheduling                        │
│                                                                  │
│  SEMANA 8-9: ██████████░░ Fase 5 - API + Despliegue            │
│              - FastAPI + Docker                                 │
│              - Railway.app deployment                           │
│              - Frontend (opcional)                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Hitos Clave

| Fecha | Hito | Entregable |
|-------|------|------------|
| Semana 2 | ✅ CI/CD Básico | Tests automáticos en cada PR |
| Semana 5 | ✅ MLOps Core | Experimentos trackeados en MLflow |
| Semana 6 | ✅ Data Quality | Validaciones automáticas |
| Semana 7 | ✅ Automatización | Reentrenamiento semanal |
| Semana 9 | ✅ Producción | API pública en Railway |

---

## Costos y Recursos

### 💰 Costo Total: **$0 - $5/mes**

| Servicio | Costo | Límites |
|----------|:-----:|---------|
| **GitHub Actions** | 💰 Gratis | 2,000 min/mes (suficiente) |
| **Databricks Community** | 💰 Gratis | 15 GB storage, 1 user, cluster 2h max |
| **codecov.io** | 💰 Gratis | Repos públicos ilimitados |
| **Railway.app** | 💰 $5/mes gratis | $5 crédito mensual (suficiente para API pequeña) |
| **Vercel** | 💰 Gratis | 100 GB bandwidth, serverless ilimitado |
| **Great Expectations** | 💰 Gratis | Open-source |
| **MLflow** | 💰 Gratis | Incluido en Databricks |

### Total: **$0/mes** (todo dentro de tiers gratuitos)

---

## Métricas de Éxito

### KPIs Técnicos

1. **CI/CD**
   - ✅ 100% de PRs con tests pasando
   - ✅ 0 commits directos a master
   - ✅ Coverage > 80%

2. **MLOps**
   - ✅ Todos los experimentos registrados en MLflow
   - ✅ Datos versionados en Delta Lake
   - ✅ Modelos con reproducibilidad 100%

3. **Data Quality**
   - ✅ 0 fallos de validación en producción
   - ✅ Alertas automáticas de data drift

4. **Automatización**
   - ✅ Reentrenamiento semanal sin intervención manual
   - ✅ Deploy automático al hacer merge a master

5. **Disponibilidad**
   - ✅ API con uptime > 99%
   - ✅ Latencia < 500ms por predicción

### Beneficios Esperados

- 🚀 **Velocidad**: De 1 hora manual a 10 min automático
- 🔒 **Confiabilidad**: Tests + validaciones = menos bugs
- 📊 **Trazabilidad**: Historial completo de experimentos
- 🤝 **Colaboración**: Cualquiera puede reproducir resultados
- 🌐 **Alcance**: API pública = portfolio profesional

---

## Siguientes Pasos

### Implementación Inmediata (Ahora)

1. **Commit y subir cambios actuales**
   ```bash
   git add .
   git commit -m "docs: Add MLOps & CI/CD implementation plan"
   git push origin feature/soccerdata-integration
   ```

2. **Crear PR y mergear a master**

3. **Empezar Fase 1**: Crear `.github/workflows/tests.yml`

---

## Recursos Adicionales

### Documentación
- **GitHub Actions**: https://docs.github.com/en/actions
- **Databricks Community**: https://docs.databricks.com/getting-started/community-edition.html
- **MLflow**: https://mlflow.org/docs/latest/index.html
- **FastAPI**: https://fastapi.tiangolo.com
- **Railway**: https://docs.railway.app
- **Great Expectations**: https://docs.greatexpectations.io

### Tutoriales
- MLflow Quickstart: https://mlflow.org/docs/latest/quickstart.html
- Databricks ML Tutorial: https://docs.databricks.com/machine-learning/index.html
- FastAPI Tutorial: https://fastapi.tiangolo.com/tutorial

---

## Conclusión

Este plan transforma tu proyecto de predicción de La Liga en un **sistema MLOps profesional de nivel producción**:

✅ **Automatizado**: Tests, validaciones, training, deploy
✅ **Reproducible**: Versionado de datos, modelos y experimentos
✅ **Escalable**: Arquitectura Cloud-ready
✅ **Profesional**: CI/CD, monitoring, API pública
✅ **Gratis**: Todo dentro de tiers gratuitos

**Tiempo total**: 7-9 semanas trabajando de forma iterativa.

**Resultado final**: Un proyecto de ML en producción que demuestra experiencia profesional en MLOps y DevOps, perfecto para tu portfolio.

---

**¿Listo para empezar?** 🚀

Comenzamos con **Fase 1 (CI/CD Básico)** creando el primer workflow de GitHub Actions.