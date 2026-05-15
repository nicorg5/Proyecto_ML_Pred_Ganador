# /project-health — Diagnóstico Completo del Proyecto

Realiza un análisis holístico del estado actual del proyecto LaLiga Predictor y genera un informe de salud con recomendaciones priorizadas.

## Qué hace este comando

1. **Analiza el estado actual** de cada capa del proyecto
2. **Detecta problemas** o deudas técnicas pendientes
3. **Valida coherencia** entre código, tests y documentación
4. **Prioriza próximos pasos** según el roadmap MLOps

## Instrucciones para Claude

Ejecuta los siguientes análisis en orden y presenta los resultados en un informe estructurado:

### 1. Estado del Código

Examina la estructura de `src/laliga_predictor/`:

```bash
find src/ -name "*.py" | head -50
```

Verifica:
- ¿Existen todos los módulos documentados en CLAUDE.md?
- ¿El módulo `api/` ya existe o está pendiente?
- ¿Hay archivos con TODOs o FIXMEs críticos?

```bash
grep -rn "TODO\|FIXME\|HACK\|XXX" src/ --include="*.py" | grep -v "__pycache__"
```

### 2. Estado de Tests

```bash
# Contar tests por módulo
find tests/ -name "test_*.py" -exec grep -c "def test_" {} \; 2>/dev/null

# Verificar cobertura actual (si existe reporte)
cat coverage.xml 2>/dev/null | grep -E 'line-rate|branch-rate' | head -5
```

Verifica:
- ¿Hay módulos sin tests correspondientes?
- ¿Los tests de anti-leakage existen y son comprehensivos?
- ¿Hay tests de la API (Fase 5)?

### 3. Estado del Roadmap MLOps

Verifica qué fases están completadas:

```bash
# Fase 1: CI/CD
ls .github/workflows/ 2>/dev/null && echo "✅ Fase 1: CI/CD configurado" || echo "❌ Fase 1: Sin CI/CD"

# Fase 2: MLflow
grep -r "mlflow" src/ --include="*.py" -l 2>/dev/null && echo "✅ Fase 2: MLflow integrado" || echo "❌ Fase 2: Sin MLflow"

# Fase 3: Validación
grep -r "great_expectations\|ge\." src/ --include="*.py" -l 2>/dev/null && echo "✅ Fase 3: Data validation" || echo "❌ Fase 3: Sin data validation"

# Fase 5: API
ls src/laliga_predictor/api/ 2>/dev/null && echo "✅ Fase 5: API existe" || echo "❌ Fase 5: Sin API"
```

### 4. Calidad de Código

```bash
# Verificar linting (sin ejecutar, solo revisar config)
cat pyproject.toml | grep -A 20 "\[tool.ruff\]\|\[tool.black\]\|\[tool.mypy\]"
```

### 5. Estado de Modelos

```bash
# Ver modelos entrenados
ls -lh models/*.joblib 2>/dev/null | awk '{print $5, $9}'

# Ver última ejecución de entrenamiento
cat models/training_results.json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for target, results in data.items():
    if 'ensemble' in results:
        test = results['ensemble'].get('test', {})
        print(f'{target}: acc={test.get(\"accuracy\", \"N/A\"):.3f}')
    elif 'xgboost' in results:
        test = results['xgboost'].get('test', {})
        print(f'{target}: auc={test.get(\"roc_auc\", \"N/A\")}')
" 2>/dev/null || echo "No hay training_results.json"
```

### 6. Estado de la Base de Datos

```bash
# Verificar docker-compose
cat docker-compose.yml | grep -E "image:|container_name:|ports:"
```

### 7. Dependencias

```bash
# Verificar dependencias desactualizadas o faltantes
cat pyproject.toml | grep -A 50 "\[project\]" | grep "dependencies" -A 30
```

## Formato del Informe

Presenta el informe en este formato:

```
╔══════════════════════════════════════════════════════╗
║         LALIGA PREDICTOR — PROJECT HEALTH REPORT      ║
║                    [FECHA]                            ║
╚══════════════════════════════════════════════════════╝

## 🏆 ESTADO GENERAL: [🟢 SALUDABLE | 🟡 ATENCIÓN | 🔴 CRÍTICO]

## 📊 MÉTRICAS CLAVE
- Tests: X/Y módulos cubiertos | Cobertura: XX%
- Modelos: Winner XX% acc | Goals AUC XX | Cards AUC XX
- Roadmap: Fase X/5 completada

## ✅ LO QUE FUNCIONA BIEN
[Lista de fortalezas del proyecto]

## ⚠️ DEUDA TÉCNICA
[Issues detectados, ordenados por criticidad]

## 🗺️ PRÓXIMOS PASOS PRIORIZADOS

### 🔴 CRÍTICO (hacer esta semana)
1. ...

### 🟡 IMPORTANTE (próximas 2 semanas)
2. ...

### 🟢 MEJORA (cuando sea posible)
3. ...

## 💡 RECOMENDACIÓN PRINCIPAL
[Una sola acción concreta para mayor impacto]
```
