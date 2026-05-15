# Skill: Anti-Leakage Auditor

## Propósito

Auditar código de feature engineering para detectar y prevenir data leakage temporal — el error más crítico en modelos de predicción deportiva con series temporales.

## Cuándo usar esta skill

- Al revisar cualquier código en `src/laliga_predictor/features/`
- Antes de hacer merge de una PR que añade nuevas features
- Al depurar por qué el modelo rinde peor en producción que en validación
- Como parte de code review automatizado

## Definición de Leakage en este Proyecto

**Leakage** ocurre cuando una feature para predecir el partido `P` (fecha `D`) utiliza información que no estaría disponible antes de `D`.

### Tipos de leakage

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| **Directo** | Usa el resultado del propio partido | `match_result` como feature |
| **Futuro** | Usa partidos posteriores a `D` | Rolling avg que incluye partidos de la semana siguiente |
| **Boundary** | Incluye el partido del día `D` (≤ en vez de <) | `WHERE match_date <= %(match_date)s` |
| **Indirecto** | Feature derivada de target | ELO actualizado con el resultado de `P` antes de predecir `P` |
| **Standings** | Clasificación calculada con el partido actual | `WHERE matchday <= %(matchday)s` en vez de `< %(matchday)s` |

## Proceso de Auditoría

### 1. Inspección estática del código

Buscar patrones de riesgo:

```python
# ❌ PELIGROSO: <= incluye el partido actual
WHERE match_date <= %(match_date)s

# ✅ CORRECTO: < excluye el partido actual  
WHERE match_date < %(match_date)s

# ❌ PELIGROSO: >= incluye la jornada actual
WHERE matchday >= %(matchday)s

# ❌ PELIGROSO: usar resultado/goles del partido a predecir
features['match_result'] = row['result']  # directo
features['goals_in_match'] = row['home_goals'] + row['away_goals']  # directo

# ❌ PELIGROSO: ELO calculado post-partido
elo_after_match = update_elo(elo_before, result)
features['elo_rating'] = elo_after_match  # debe ser elo_before

# ✅ CORRECTO: ELO pre-partido
features['home_elo'] = get_elo_before_match(team_id, match_date)
```

### 2. Test de inyección

El test más fiable: inyectar un partido artificial con valores extremos en el "futuro" del partido a predecir y verificar que las features no cambian.

```python
def audit_feature_for_leakage(feature_fn, team_id, match_date, data):
    """
    Audita una función de feature inyectando datos futuros extremos.
    
    Returns:
        (bool, str): (has_leakage, explanation)
    """
    from datetime import timedelta
    
    # Calcular feature con datos normales
    normal_value = feature_fn(team_id, match_date, data)
    
    # Crear dataset contaminado con partido futuro extremo
    future_date = match_date + timedelta(days=1)
    poison_row = {
        "team_id": team_id,
        "match_date": future_date,
        "goals": 999,  # valor imposible
        "result": "X_FUTURE",
    }
    contaminated_data = pd.concat([data, pd.DataFrame([poison_row])], ignore_index=True)
    
    # Calcular con datos contaminados
    contaminated_value = feature_fn(team_id, match_date, contaminated_data)
    
    has_leakage = not np.isclose(normal_value, contaminated_value, equal_nan=True)
    explanation = (
        f"LEAKAGE: {normal_value} → {contaminated_value} al añadir dato futuro"
        if has_leakage
        else "OK: feature no afectada por datos futuros"
    )
    
    return has_leakage, explanation
```

### 3. Inspección de SQL

Para cada query SQL en `feature_engineering.py`:

```python
import re

def audit_sql_for_leakage(sql: str) -> list[str]:
    """Detecta patrones peligrosos en SQL de features."""
    issues = []
    
    # Buscar <= con match_date
    if re.search(r'match_date\s*<=', sql, re.IGNORECASE):
        issues.append("⚠️  match_date <= incluye el partido actual. Usar <")
    
    # Buscar >= con matchday
    if re.search(r'matchday\s*>=', sql, re.IGNORECASE):
        issues.append("⚠️  matchday >= puede incluir jornada actual")
    
    # Verificar que existe filtro temporal
    if 'match_date' not in sql.lower() and 'matchday' not in sql.lower():
        issues.append("🚨 Query sin filtro temporal — posible leakage total")
    
    return issues
```

## Comandos de Auditoría

```bash
# Buscar todos los posibles <= con match_date en el código
grep -n "match_date\s*<=" src/laliga_predictor/features/feature_engineering.py

# Buscar uso de columnas de resultado (target leakage)
grep -n "result\|home_goals\|away_goals" src/laliga_predictor/features/feature_engineering.py | \
  grep -v "def \|#\|rolling\|avg\|mean\|sum\|target"

# Verificar que todos los queries tienen filtro temporal
grep -n "SELECT\|FROM\|WHERE" src/laliga_predictor/features/feature_engineering.py | \
  awk 'NR%3==0 {if (!found_where) print NR": posible query sin WHERE temporal"; found_where=0} /WHERE/ {found_where=1}'

# Ejecutar todos los tests de anti-leakage
uv run pytest tests/unit/test_features.py -k "leakage" -v --tb=short
```

## Señales de Leakage en Métricas

Si detectas estos síntomas, sospechar de leakage:

| Síntoma | Probabilidad de leakage |
|---------|------------------------|
| Accuracy en val/test >>> que en producción real | Alta |
| Accuracy en train ≈ 100% | Muy alta |
| Feature importance concentrada en 1-2 features inesperadas | Media |
| El modelo predice bien partidos pasados pero falla los futuros | Alta |
| Accuracy mejora mucho al añadir una feature nueva sin lógica clara | Media-Alta |

## Template de Reporte de Auditoría

```
## 🔍 Auditoría Anti-Leakage — [módulo auditado]
**Fecha**: YYYY-MM-DD
**Auditor**: Claude Code (test-expert agent)

### Resultado: ✅ LIMPIO / 🚨 LEAKAGE DETECTADO

### Issues encontrados:
1. [descripción del issue, línea, tipo de leakage]

### Código problemático:
```python
# Línea X: PELIGRO
WHERE match_date <= %(match_date)s
```

### Corrección recomendada:
```python
# Corrección
WHERE match_date < %(match_date)s
```

### Tests añadidos/actualizados:
- `test_<feature>_no_future_data` en `tests/unit/test_features.py`
```

## Integración con CI/CD

Añadir al workflow de tests:

```yaml
- name: Anti-leakage audit
  run: |
    uv run pytest tests/unit/test_features.py -k "leakage" -v \
      --tb=short \
      -x  # Falla en el primer leakage detectado
```
