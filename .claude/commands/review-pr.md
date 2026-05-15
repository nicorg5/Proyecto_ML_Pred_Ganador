# /review-pr — Revisión de Pull Request

Realiza una revisión exhaustiva de los cambios en la rama actual antes de hacer merge, verificando calidad de código, tests, anti-leakage y conformidad con los estándares del proyecto.

## Instrucciones para Claude

### 1. Ver los cambios del PR

```bash
# Cambios respecto a la rama base
git diff main --name-only
git diff main --stat
```

### 2. Análisis por tipo de archivo

**Si hay cambios en `features/`:**
```bash
git diff main -- src/laliga_predictor/features/

# Verificar anti-leakage en código nuevo
grep -n "match_date\s*<=" src/laliga_predictor/features/feature_engineering.py
grep -n "match_date\s*>=" src/laliga_predictor/features/feature_engineering.py

# Verificar que hay tests correspondientes
git diff main -- tests/unit/test_features.py | head -50
```

**Si hay cambios en `models/`:**
```bash
git diff main -- src/laliga_predictor/models/

# Verificar que BasePredictor sigue siendo compatible
grep -n "class.*Predictor\|def fit\|def predict\|def predict_proba\|def save\|def load" \
  src/laliga_predictor/models/classifiers.py | head -20
```

**Si hay cambios en `api/`:**
```bash
git diff main -- src/laliga_predictor/api/

# Verificar que hay tests de API
git diff main -- tests/unit/test_api.py | head -50
```

**Si hay cambios en `.github/workflows/`:**
```bash
cat .github/workflows/*.yml
# Verificar: PostgreSQL service configurado, UV cache, coverage upload
```

### 3. Ejecutar suite de calidad

```bash
# Tests completos
uv run pytest tests/ -v --tb=short 2>&1 | tail -30

# Linting
uv run black --check src/ tests/ 2>&1
uv run ruff check src/ tests/ 2>&1

# Tipos (si mypy está configurado)
uv run mypy src/ 2>&1 | tail -20
```

### 4. Generar el reporte de revisión

Presenta el reporte en este formato:

```
## 📋 CODE REVIEW — [nombre de la rama]
**Archivos cambiados**: X
**Líneas añadidas/eliminadas**: +Y / -Z

---

### 🔒 Seguridad & Anti-Leakage
[✅ Sin issues | ⚠️ Issues encontrados con detalles]

### 🧪 Tests
[✅ Tests añadidos para código nuevo | ❌ Falta cobertura en: X, Y]

### 📐 Calidad de Código  
[✅ Pasa black + ruff | ❌ Issues: ...]

### 🏗️ Arquitectura
[¿Los cambios siguen los patrones del proyecto? ¿Hay deuda técnica nueva?]

### 💬 Comentarios por archivo
[Observaciones específicas por fichero modificado]

---

### ✅ APROBADO / ⚠️ APROBADO CON SUGERENCIAS / ❌ REQUIERE CAMBIOS

**Acción requerida**: [descripción concreta de qué cambiar si aplica]
```
