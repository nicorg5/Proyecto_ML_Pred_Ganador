# 🚀 IMPLEMENTATION PLAN - LaLiga Predictor MLOps+Frontend+Deploy

**Fecha**: Mayo 2026  
**Versión**: 1.0 (Ejecutable)  
**Objetivo**: Completar MLOps, API, Frontend y Deploy en 3-4 semanas

---

## 📋 DECISIONES TÉCNICAS FINALES

| Decisión | Opción Elegida |
|----------|----------------|
| **Frontend Stack** | React 19 + Vite |
| **Estructura Proyecto** | Monorepositorio (backend/ + frontend/) |
| **Deploy** | Render (backend + frontend) |
| **Data Validation** | Script simple en Python |
| **MLflow** | Local (SQLite + filesystem) |
| **Model Versioning** | Git + GitHub Releases |

---

## 🎯 FASES DE IMPLEMENTACIÓN

### **FASE 2: MLflow Local** ✅ COMPLETADA
- [x] Instalar MLflow + dependencias (MLflow 3.12.0)
- [x] Integrar en `train.py` (logging de experimentos)
- [x] Script para iniciar servidor (`./scripts/start_mlflow.sh`)
- [x] UI web funcional en http://localhost:5000
- [x] ✅ **CHECKPOINT 1**: MLflow corriendo, experiments visible

**Archivos creados/modificados:**
- ✅ `src/laliga_predictor/models/train.py` — MLflow logging integrado
- ✅ `scripts/start_mlflow.sh` — script ejecutable
- ✅ `Makefile` — targets `mlflow-ui`, `mlflow-clean` añadidos
- ✅ `.gitignore` — mlflow.db, mlruns/, .mlflow/ añadidos
- ✅ `pyproject.toml` — MLflow 2.10.0+ added

**Commit**: feat: Add MLflow integration for experiment tracking (a9f2a6f)

---

### **FASE 3: Data Validation** ✅ COMPLETADA
- [x] Crear script de validación simple (10 checks)
- [x] Validar columnas, ranges, nulls, valores inválidos
- [x] Integrar en ML pipeline (antes de entrenar)
- [x] ✅ **CHECKPOINT 2**: Script validando features.parquet correctamente

**Archivos creados/modificados:**
- ✅ `src/laliga_predictor/data/validate_features.py` — script con 10 validaciones
- ✅ `Makefile` — target `ml-validate-features` añadido
- ✅ `Makefile` — `ml-pipeline` actualizado (features → validate → select → train)

**Validaciones implementadas:**
1. Columnas requeridas existen
2. Rango de columnas (135-160)
3. Sin nulls en columnas críticas
4. Valores válidos para resultado (H/D/A)
5. Conteos de goles y tarjetas realistas
6. Win rates en [0, 1]
7. Posiciones liga en [1, 20]
8. Mínimo 300 filas
9. Mínimo 7 temporadas
10. Formatos de datos consistentes

**Commit**: feat: Add simple data validation script for features (ef9af77)

---

### **FASE 4: Automatización (Reentrenamiento)** ✅ COMPLETADA
- [x] Crear workflow GitHub Actions para reentrenamiento semanal
- [x] Subir modelos entrenados a GitHub Releases (versionado)
- [x] Guardar MLflow artifacts en artifacts
- [ ] Testar workflow manualmente (pending - requiere push a master)
- [x] ✅ **CHECKPOINT 3**: Workflow listo, modelos en Releases configurado

**Archivos creados:**
- ✅ `.github/workflows/retrain-weekly.yml` — workflow semanal (martes 4 AM UTC)
- ✅ GitHub Releases integration para versionamiento de modelos

**Workflow pipeline:**
1. Initialize PostgreSQL (laliga_soccerdata)
2. Update data (season 2526)
3. Build features
4. Validate features (fail-fast si hay problemas)
5. Train all models + MLflow tracking
6. Upload artifacts (models + MLflow data)
7. Create GitHub Release with models
8. 30-day retention policy

**Triggers:**
- Scheduled: Martes 4 AM UTC
- Manual: workflow_dispatch (Actions tab)

**Commit**: feat: Add weekly automated retraining workflow (789c91e)

---

### **FASE 5.1: FastAPI** ✅ COMPLETADA
- [x] Crear módulo `api/` con FastAPI
- [x] Endpoints: `/predict`, `/health`, `/teams`, `/docs` (Swagger)
- [x] Pydantic schemas para request/response
- [x] Cargar modelos al startup
- [x] Tests unitarios de API (32 nuevos tests)
- [x] ✅ **CHECKPOINT 4**: API funcionando localmente, `/docs` accesible

**Archivos creados:**
- ✅ `src/laliga_predictor/api/__init__.py`
- ✅ `src/laliga_predictor/api/main.py` — FastAPI app con 4 endpoints
- ✅ `src/laliga_predictor/api/schemas.py` — Pydantic models (7 modelos)
- ✅ `tests/unit/test_api.py` — 32 tests de endpoints
- ✅ `Makefile` — targets `api-run`, `api-check` añadidos

**Endpoints implementados:**
- `GET /` — API info
- `GET /health` — Health check con estado de modelos
- `GET /teams` — Lista de 20 equipos
- `POST /predict` — Predicción de partido (winner + goals O/U + cards O/U)
- `GET /docs` — Swagger UI auto-generada

**CORS configurado** para acceso desde frontend

**Tests**: 125 tests pasando (32 nuevos para API)

**Commit**: feat: Implement FastAPI for LaLiga Predictor (1b2e599)

---

### **FASE 5.2: Dockerfile** ✅ COMPLETADA
- [x] Crear Dockerfile para backend
- [x] Testar build local
- [x] Testar run con `docker compose up`
- [x] Actualizar docker-compose.yml (agregar backend service)
- [x] ✅ **CHECKPOINT 5**: Backend dockerizado, funciona en contenedor

**Archivos creados/modificados:**
- ✅ `Dockerfile` — multi-stage build con UV, Python 3.11-slim
- ✅ `docker-compose.yml` — actualizado con backend service, network bridge
- ✅ `.dockerignore` — excluir archivos innecesarios (~25 entries)

**Docker Build Details:**
- Base image: `python:3.11-slim`
- Multi-stage build: builder (dependencies) + production (runtime)
- Package manager: UV (sin dev dependencies en prod)
- Healthcheck configurado: `curl http://localhost:8000/health` cada 30s
- CORS habilitado para conexión desde frontend
- Volúmenes montados: `/app/models`, `/app/data`
- Network: bridge compartida (postgres, pgadmin, backend)

**Endpoints validados:**
- ✅ GET / → API info
- ✅ GET /health → Status + models_loaded dict
- ✅ GET /teams → Lista de 20 equipos
- ✅ GET /docs → Swagger UI funcional
- ✅ POST /predict → 503 cuando modelos no entrenados (comportamiento correcto)

**Commit**: feat: Add Docker containerization (Dockerfile + docker-compose backend service)

---

### **FASE 5.3: Restructuración Monorepositorio** ✅ COMPLETADA
- [x] Crear carpetas `backend/` y `frontend/`
- [x] Mover `src/` → `backend/src/`
- [x] Mover `tests/` → `backend/tests/`
- [x] Mover `models/` → `backend/models/`
- [x] Mover `Dockerfile` → `backend/Dockerfile`
- [x] Actualizar imports y rutas en código
- [x] Verificar que CI/CD sigue funcionando
- [x] ✅ **CHECKPOINT 6**: Monorepositorio estructurado, tests pasando

**Archivos movidos/actualizados:**
- ✅ Estructura monorepositorio: `backend/` (src, tests, models, data, database, Dockerfile, pyproject.toml, Makefile)
- ✅ Frontend: `frontend/` (src/components, src/pages, public)
- ✅ `.github/workflows/ci.yml` — actualizado con `cd backend &&`
- ✅ `.github/workflows/retrain-weekly.yml` — actualizado con `cd backend &&`
- ✅ `docker-compose.yml` — rutas actualizadas a `./backend/*`
- ✅ Root `Makefile` — wrapper que delega a `backend/Makefile`
- ✅ `backend/pyproject.toml` — referencia a `../README.md`
- ✅ Removido `shap` (incompatible con numpy 2.0, no crítico)

**Tests validados:**
- ✅ 125 unit tests pasando después de restructuración
- ✅ Imports relativos funcionan correctamente desde `backend/`
- ✅ Makefiles funcionales desde root y desde backend/

**Commit**: refactor: Restructure as monorepository with backend/ and frontend/ folders (750740e)

---

### **FASE 5.4: React Frontend** ✅ COMPLETADA
- [x] Scaffolding React 19 + Vite en `frontend/`
- [x] Componentes principales: Predictor, Histórico, Stats
- [x] Conectar a API backend
- [x] Responsive design (mobile-friendly)
- [x] Dockerfile para frontend (Nginx)
- [x] ✅ **CHECKPOINT 7**: Frontend funcionando, conectado a API local

**Archivos a crear:**
- `frontend/package.json` — React + Vite
- `frontend/src/App.jsx` — componente principal
- `frontend/src/components/` — componentes reutilizables
- `frontend/src/pages/` — páginas (Predict, History, etc.)
- `frontend/Dockerfile` — Nginx para servir build
- `frontend/vite.config.js` — config Vite

---

### **FASE 5.5: Deploy en Render** ⏱️ 2-3 días
- [ ] Crear cuenta Render + conectar GitHub
- [ ] Desplegar backend (Web Service)
- [ ] Desplegar frontend (Static Site o Web Service)
- [ ] Configurar env vars en Render
- [ ] Verificar auto-deploy en push a `master`
- [ ] Tests E2E (predicción real en prod)
- [ ] ✅ **CHECKPOINT 8**: API pública + Frontend vivo en Render

**Archivos/configuración:**
- `render.yaml` (opcional, para blueprint)
- Variables de entorno en Render Dashboard
- GitHub secrets (si es necesario)

---

### **BONUS: Documentación Final** ⏱️ 1 día
- [ ] `docs/API.md` — documentación de endpoints
- [ ] `docs/DEPLOYMENT.md` — guía de deploy en Render
- [ ] `docs/DEVELOPMENT.md` — guía para desarrollar localmente
- [ ] `README.md` — actualizado con badges, links
- [ ] ✅ **CHECKPOINT 9**: Documentación completa y clara

---

## ⏱️ TIMELINE ESTIMADO

```
SEMANA 1 (8-14 mayo):
  Lunes-Martes:    Fase 2 (MLflow) ✅ COMPLETADA
  Miércoles:       Fase 3 (Validación) ✅ COMPLETADA
  Jueves-Viernes:  Fase 4 (Automatización) ✅ COMPLETADA
  
SEMANA 2 (15-21 mayo):  ← ESTAMOS AQUÍ
  Jueves 15 mayo:  Fase 5.1 (FastAPI) ✅ COMPLETADA
  Viernes 15 mayo: Fase 5.2 (Docker) ✅ COMPLETADA
  Viernes 15 mayo: Fase 5.3 (Restructuración) ✅ COMPLETADA
  
SEMANA 2/3:
  Miércoles 15 mayo: Fase 5.4 (React Frontend) ✅ COMPLETADA
  Próximo:           Fase 5.5 (Deploy Render) - Testing local + Deploy
  
SEMANA 3/4:
  Final:             Documentación final + bugfixes
```

**PROGRESO ACTUAL**: 7/10 sub-fases completadas (70% de implementación total)

---

## 🎯 CHECKPOINTS - Validación Progresiva

Después de cada fase, validaremos:

1. **Checkpoint 1** (Fase 2): `make mlflow-ui` → ver experimentos en http://localhost:5000
2. **Checkpoint 2** (Fase 3): `make ml-validate-features` → validación exitosa
3. **Checkpoint 3** (Fase 4): GitHub Actions UI → workflow ejecutado, artifacts en Releases
4. **Checkpoint 4** (Fase 5.1): `make api-run` → curl http://localhost:8000/health → {"status": "healthy"}
5. **Checkpoint 5** (Fase 5.2): `docker build -t api . && docker run -p 8000:8000 api` → funciona
6. **Checkpoint 6** (Fase 5.3): `git log --oneline` → restructuring commit, `make test` → pasa
7. **Checkpoint 7** (Fase 5.4): `cd frontend && npm run dev` → React en http://localhost:5173
8. **Checkpoint 8** (Fase 5.5): `curl https://api.tu-render-app.onrender.com/health` → funciona
9. **Checkpoint 9** (Documentación): README + docs completados, links funcionales

---

## 📁 ESTRUCTURA FINAL (MONOREPOSITORIO)

```
Proyecto_ML_Pred_Ganador/
├── backend/
│   ├── src/laliga_predictor/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py              ← FastAPI app
│   │   │   └── schemas.py           ← Pydantic models
│   │   ├── data/
│   │   ├── features/
│   │   ├── models/
│   │   ├── config.py
│   │   └── utils/
│   ├── tests/
│   ├── models/                      ← Joblib serializados
│   ├── data/processed/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── Makefile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── docker-compose.yml               ← Backend + Frontend + PostgreSQL
├── .github/workflows/
│   ├── ci.yml                      ← Actualizado
│   ├── retrain-weekly.yml          ← NUEVO
│   └── deploy.yml                  ← NUEVO (opcional)
│
├── docs/
│   ├── feature_dictionary.json
│   ├── API.md                      ← NUEVO
│   ├── DEPLOYMENT.md               ← NUEVO
│   ├── DEVELOPMENT.md              ← NUEVO
│   └── IMPLEMENTATION_PLAN.md      ← Éste archivo
│
├── README.md                        ← Actualizado
└── CLAUDE.md                        ← Guía de desarrollo
```

---

## 🚀 PRÓXIMO PASO

**Empezamos con Fase 2: MLflow Local**

Seguiremos este documento como guía, marcando checkpoints conforme avanzamos.

---

## 📝 NOTAS

- Cada fase tiene archivos específicos a crear/modificar
- Validaremos con checkpoints explícitos
- Si algo falla, investigaremos antes de avanzar
- Este documento se actualiza conforme progresamos
