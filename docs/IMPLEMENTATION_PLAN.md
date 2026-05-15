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

### **FASE 5.1: FastAPI** ⏱️ 2-3 días
- [ ] Crear módulo `api/` con FastAPI
- [ ] Endpoints: `/predict`, `/health`, `/teams`, `/docs` (Swagger)
- [ ] Pydantic schemas para request/response
- [ ] Cargar modelos al startup
- [ ] Tests unitarios de API
- [ ] ✅ **CHECKPOINT 4**: API funcionando localmente, `/docs` accesible

**Archivos a crear/modificar:**
- `src/laliga_predictor/api/main.py` — FastAPI app
- `src/laliga_predictor/api/schemas.py` — Pydantic models
- `tests/unit/test_api.py` — tests de endpoints
- `Makefile` — target `api-run` (uvicorn)

---

### **FASE 5.2: Dockerfile** ⏱️ 1-2 días
- [ ] Crear Dockerfile para backend
- [ ] Testar build local
- [ ] Testar run con `docker run`
- [ ] Actualizar docker-compose.yml (agregar backend service)
- [ ] ✅ **CHECKPOINT 5**: Backend dockerizado, funciona en contenedor

**Archivos a crear/modificar:**
- `Dockerfile` — en raíz
- `docker-compose.yml` — actualizado con backend service
- `.dockerignore` — excluir archivos innecesarios

---

### **FASE 5.3: Restructuración Monorepositorio** ⏱️ 1 día
- [ ] Crear carpetas `backend/` y `frontend/`
- [ ] Mover `src/` → `backend/src/`
- [ ] Mover `tests/` → `backend/tests/`
- [ ] Mover `models/` → `backend/models/`
- [ ] Mover `Dockerfile` → `backend/Dockerfile`
- [ ] Actualizar imports y rutas en código
- [ ] Verificar que CI/CD sigue funcionando
- [ ] ✅ **CHECKPOINT 6**: Monorepositorio estructurado, tests pasando

**Archivos a mover/actualizar:**
- Estructura de directorios
- `Makefile` (o duplicar para cada parte)
- `.github/workflows/ci.yml` — actualizar paths

---

### **FASE 5.4: React Frontend** ⏱️ 3-4 días
- [ ] Scaffolding React 19 + Vite en `frontend/`
- [ ] Componentes principales: Predictor, Histórico, Stats
- [ ] Conectar a API backend
- [ ] Responsive design (mobile-friendly)
- [ ] Dockerfile para frontend (Nginx)
- [ ] ✅ **CHECKPOINT 7**: Frontend funcionando, conectado a API local

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
  Jueves 15 mayo:  Fase 5.1 (FastAPI) → INICIANDO AHORA
  Viernes:         Fase 5.1 + Fase 5.2 (Dockerfile)
  
SEMANA 2/3:
  Lunes-Martes:    Fase 5.2 (Dockerfile)
  Miércoles:       Fase 5.3 (Restructuración)
  Jueves-Viernes:  Fase 5.4 (React Frontend)
  
SEMANA 3/4:
  Lunes-Martes:    Fase 5.5 (Deploy Render)
  Miércoles+:      Documentación final + bugfixes
```

**PROGRESO ACTUAL**: 3/5 fases completadas (60% de MLOps core)

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
