# 👨‍💻 DEVELOPMENT GUIDE - LaLiga Predictor

Guía práctica para desarrollar localmente durante la implementación de MLOps + Frontend + Deploy.

---

## 🛠️ SETUP INICIAL

```bash
# 1. Clonar repo
git clone https://github.com/TU_USER/Proyecto_ML_Pred_Ganador.git
cd Proyecto_ML_Pred_Ganador

# 2. Instalar dependencias (backend)
make install-dev

# 3. Levantar PostgreSQL
make docker-up

# 4. Inicializar base de datos
make sd-init

# 5. Verificar que todo funciona
make test
```

---

## 📦 DURANTE IMPLEMENTACIÓN

### Fase 2: MLflow

```bash
# Terminal 1: Iniciar servidor MLflow
make mlflow-ui
# Abre http://localhost:5000

# Terminal 2: Entrenar modelos (automáticamente loguea en MLflow)
make ml-pipeline

# Terminal 3: Ver logs
docker compose logs postgres
```

**Checklist:**
- ✅ Servidor MLflow corriendo en puerto 5000
- ✅ Experimentos visibles en UI
- ✅ Métricas loguadas correctamente
- ✅ Modelos registrados en Model Registry

---

### Fase 3: Data Validation

```bash
# Validar features antes de entrenar
make ml-validate-features

# Debe mostrar: ✅ Validation PASSED
# Si falla: ve a src/laliga_predictor/data/validate_features.py
```

---

### Fase 4: Automatización

```bash
# Ver workflow en GitHub Actions
# https://github.com/TU_USER/Proyecto_ML_Pred_Ganador/actions

# Trigger manual (si necesitas testar):
# Ve a Actions → Weekly Retraining → Run workflow

# Para ver artefactos subidos:
# https://github.com/TU_USER/Proyecto_ML_Pred_Ganador/releases
```

---

### Fase 5.1: FastAPI

```bash
# Terminal 1: Servidor API
make api-run
# O manualmente:
uv run uvicorn src.laliga_predictor.api.main:app --reload --port 8000

# Terminal 2: Testar endpoints
curl http://localhost:8000/health
curl http://localhost:8000/teams
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"home_team": "Real Madrid", "away_team": "Barcelona", "match_date": "2026-05-20"}'

# Swagger UI (auto-documentación):
# http://localhost:8000/docs
```

---

### Fase 5.2: Docker

```bash
# Build imagen
docker build -t laliga-api:latest .

# Run contenedor
docker run -p 8000:8000 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PORT=5432 \
  laliga-api:latest

# Testar (desde otra terminal)
curl http://localhost:8000/health

# Logs
docker logs <CONTAINER_ID>
```

---

### Fase 5.3: Restructuración

```bash
# Después de restructurar (backend/ + frontend/):

# Backend: mismo que antes
cd backend && make test

# Frontend: nuevo
cd frontend && npm install && npm run dev
```

---

### Fase 5.4: React Frontend

```bash
# Scaffolding (en frontend/)
npm create vite@latest . -- --template react

# Instalar dependencias
npm install

# Desarrollo
npm run dev
# http://localhost:5173

# Build para producción
npm run build
# Genera dist/ para deploy

# Tests (opcional)
npm install --save-dev vitest
npm run test
```

---

### Fase 5.5: Deploy en Render

```bash
# 1. Pushear a master
git add .
git commit -m "feat: Complete MLOps + Frontend + Deploy"
git push origin master

# 2. Ir a https://render.com
# 3. New → Web Service → Connect GitHub
# 4. Render detecta Dockerfile automáticamente
# 5. Deploy!

# Monitorear:
# https://dashboard.render.com → tu app → Logs
```

---

## 🧪 TESTING DURANTE DESARROLLO

```bash
# Tests unitarios (rápido, sin DB)
make test-unit

# Tests de integración (incluye DB)
make test-integration-db

# Cobertura
make test-cov
# Abre htmlcov/index.html

# Linting
make lint
make format
```

---

## 📋 CHECKLIST PARA CADA FASE

### ✅ Fase 2 - MLflow
- [ ] `pip install mlflow`
- [ ] `make mlflow-ui` funciona
- [ ] Experimentos visibles en http://localhost:5000
- [ ] Modelos registrados en Model Registry
- [ ] CI/CD pasa (GitHub Actions)

### ✅ Fase 3 - Validación
- [ ] Script `validate_features.py` creado
- [ ] `make ml-validate-features` pasa
- [ ] Integrado en `ml-pipeline`
- [ ] Tests pasan

### ✅ Fase 4 - Automatización
- [ ] Workflow `.github/workflows/retrain-weekly.yml` creado
- [ ] Workflow se ejecuta sin errores (manual trigger)
- [ ] Artifacts subidos a GitHub Releases
- [ ] Modelos pueden descargarse desde Releases

### ✅ Fase 5.1 - FastAPI
- [ ] `src/laliga_predictor/api/main.py` creado
- [ ] `/health` endpoint funciona
- [ ] `/predict` endpoint funciona
- [ ] `/docs` muestra Swagger UI
- [ ] Tests en `tests/unit/test_api.py` pasan

### ✅ Fase 5.2 - Docker
- [ ] `Dockerfile` creado
- [ ] `docker build` sin errores
- [ ] `docker run` funciona localmente
- [ ] API responde desde contenedor
- [ ] Docker Compose tiene backend service

### ✅ Fase 5.3 - Restructuración
- [ ] Directorios `backend/` y `frontend/` creados
- [ ] Código movido correctamente
- [ ] Imports actualizados
- [ ] `make test` pasa en `backend/`
- [ ] CI/CD actualizado y pasa

### ✅ Fase 5.4 - React
- [ ] React app scaffolded
- [ ] Componentes principales creados
- [ ] API conectada (environment variables)
- [ ] Funciona en `npm run dev`
- [ ] Build genera `dist/` correctamente

### ✅ Fase 5.5 - Deploy
- [ ] Backend en Render (Web Service)
- [ ] Frontend en Render (Static Site o Web Service)
- [ ] Auto-deploy en push a master
- [ ] URLs públicas funcionan
- [ ] Predicción E2E funciona

---

## 🔧 TROUBLESHOOTING

### MLflow no corre
```bash
# Verificar
pip list | grep mlflow

# Reinstalar
pip uninstall mlflow && pip install mlflow

# Limpiar
rm -rf mlflow.db mlruns/
```

### API da error de modelos
```bash
# Verificar que existen
ls -la models/

# Reentrenar si es necesario
make ml-train

# Checar paths en src/laliga_predictor/api/main.py
```

### Tests fallan
```bash
# Verificar DB está levantada
docker compose ps

# Reinstalar dependencias
make install-dev

# Limpiar caché
make clean
```

### Docker build falla
```bash
# Ver logs completos
docker build -t api:test . --progress=plain

# Limpiar caché de Docker
docker system prune -a
```

### Frontend no conecta a API
```bash
# Verificar CORS en backend (src/laliga_predictor/api/main.py)
# Verificar URL en frontend (.env, vite.config.js)
# Logs del navegador: F12 → Console
```

---

## 📊 COMANDOS ÚTILES

```bash
# Estado general
make info

# Ver logs en tiempo real
docker compose logs -f postgres

# Limpiar todo
make clean-all

# Format automático
make format

# Type checking
make type-check

# Pre-commit hooks
make pre-commit

# Predecir un partido
make ml-predict HOME="Real Madrid" AWAY="Barcelona" DATE="2026-05-20"

# Predecir una jornada completa
make ml-predict-jornada JORNADA=24
```

---

## 💡 TIPS

1. **Siempre en ramas feature**: No trabajar directamente en `master`
   ```bash
   git checkout -b feature/mlflow
   git checkout -b feature/fastapi
   git checkout -b feature/react
   ```

2. **Commits descriptivos**: Sigue convención
   ```bash
   git commit -m "feat: Add MLflow integration to train.py"
   git commit -m "fix: Correct data validation schema"
   git commit -m "test: Add API endpoint tests"
   ```

3. **PRs antes de merge a master**: Así GitHub Actions corre tests

4. **Env variables locales**: Crear `.env.local` para desarrollo
   ```bash
   # .env.local (no commitar)
   MLFLOW_TRACKING_URI=sqlite:///mlflow.db
   POSTGRES_HOST=localhost
   ```

5. **Hot reload en desarrollo**:
   - Backend: `uvicorn --reload`
   - Frontend: `npm run dev` (Vite ya reloada)

---

## 🎯 SIGUIENTE PASO

Dirígete a `docs/IMPLEMENTATION_PLAN.md` para seguir el plan detallado.

¡Empezamos con **Fase 2: MLflow Local**! 🚀
