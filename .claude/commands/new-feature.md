# /new-feature — Añadir Nueva Feature al Pipeline

Guía paso a paso para implementar una nueva feature de ingeniería con todas las garantías de calidad: anti-leakage, tests y documentación.

## Uso

```
/new-feature <nombre_feature> <categoría> <descripción>
```

**Ejemplos:**
```
/new-feature home_recent_clean_sheets venue_form "Porterías a cero del local en los últimos N partidos como local"
/new-feature elo_momentum elo "Cambio de ELO en las últimas 3 jornadas (tendencia)"
/new-feature h2h_goals_avg head_to_head "Media de goles totales en enfrentamientos directos"
```

## Categorías válidas

| Categoría | Prefijo | Descripción |
|-----------|---------|-------------|
| `rolling_form` | `home_/away_` | Estadísticas rolling (ventanas 3, 5, 10) |
| `venue_form` | `home_/away_` | Rendimiento específico local/visitante |
| `espn_advanced` | `home_/away_` | Stats ESPN (posesión, pases, etc.) |
| `head_to_head` | `h2h_` | Histórico enfrentamientos directos |
| `standings` | `home_/away_` | Posición, puntos, diferencia de goles |
| `contextual` | ninguno | Derby, jornada, etc. |
| `elo` | `elo_` | ELO ratings y derivados |
| `streaks` | `home_/away_streak_` | Rachas de victorias/imbatibilidad |
| `ema` | `home_/away_ema_` | Medias exponenciales |
| `differences` | `diff_` | Diferencias directas home-away |
| `total_goals` | `total_` | Medias de goles totales |
| `draw_likelihood` | `draw_` | Indicadores de empate |

## Instrucciones para Claude

### Paso 1: Análisis de viabilidad

Antes de implementar, verifica:

1. ¿La feature puede calcularse SOLO con datos anteriores a `match_date`?
2. ¿Ya existe una feature similar? Revisar `feature_engineering.py`
3. ¿Es correlacionada con features existentes? (evitar redundancia)

```bash
grep -n "$FEATURE_NAME\|$CATEGORIA" src/laliga_predictor/features/feature_engineering.py | head -20
```

### Paso 2: Implementar la feature

Ubicación: `src/laliga_predictor/features/feature_engineering.py`

**Template de función:**

```python
def _compute_<nombre_feature>(
    self,
    team_id: int,
    match_date: datetime,
    venue: str,  # "home" o "away" si aplica
    window: int = 5,
) -> float:
    """
    Calcula <descripción de la feature>.
    
    Args:
        team_id: ID del equipo en la BD
        match_date: Fecha del partido (cutoff temporal)
        venue: "home" o "away" para filtrar por venue
        window: Ventana de partidos a considerar
    
    Returns:
        Valor de la feature. np.nan si no hay suficientes datos.
    
    Note:
        Anti-leakage: Solo usa partidos con date < match_date
    """
    query = """
        SELECT <columnas>
        FROM matches
        WHERE <equipo> = %(team_id)s
          AND match_date < %(match_date)s  -- CRÍTICO: fecha estrictamente anterior
          <filtro_venue_si_aplica>
        ORDER BY match_date DESC
        LIMIT %(window)s
    """
    # ... implementación
```

**Añadir al método principal `build_features()`:**

```python
# En el loop de construcción de features por partido:
features['<nombre_feature>'] = self._compute_<nombre_feature>(
    home_team_id, match_date, venue='home', window=5
)
```

### Paso 3: Escribir el test de anti-leakage

Ubicación: `tests/unit/test_features.py`

**Template de test:**

```python
def test_<nombre_feature>_no_leakage(feature_builder, sample_matches):
    """
    Verifica que <nombre_feature> no usa datos de la fecha del partido
    ni datos futuros.
    """
    match_date = datetime(2023, 3, 15)
    team_id = sample_matches[sample_matches['match_date'] == match_date]['home_team_id'].iloc[0]
    
    # Calcular feature
    result = feature_builder._compute_<nombre_feature>(
        team_id=team_id,
        match_date=match_date,
    )
    
    # Verificar que solo usa partidos anteriores
    used_matches = feature_builder._get_last_matches(team_id, match_date)
    assert all(m['match_date'] < match_date for m in used_matches), \
        "LEAKAGE: la feature usa datos del partido actual o futuros"


def test_<nombre_feature>_insufficient_data(feature_builder):
    """Verifica que retorna np.nan cuando no hay suficientes datos."""
    result = feature_builder._compute_<nombre_feature>(
        team_id=999,  # equipo sin datos
        match_date=datetime(2017, 9, 1),  # inicio del dataset
    )
    assert np.isnan(result), "Debe retornar NaN con datos insuficientes"


def test_<nombre_feature>_value_range(feature_builder, sample_matches):
    """Verifica que los valores están en el rango esperado."""
    # Adaptar según la semántica de la feature
    result = feature_builder._compute_<nombre_feature>(
        team_id=sample_matches.iloc[5]['home_team_id'],
        match_date=sample_matches.iloc[5]['match_date'],
    )
    # Ejemplo para porcentajes:
    assert 0.0 <= result <= 1.0 or np.isnan(result)
```

### Paso 4: Actualizar documentación

1. Actualizar el contador en `README.md`:
```bash
# Buscar la línea del contador de features
grep -n "~144 features\|~[0-9]* features" README.md
```

2. Añadir entrada en la tabla de Feature Engineering del README con la nueva categoría si aplica.

3. Actualizar `CLAUDE.md` si es una nueva categoría.

### Paso 5: Verificar

```bash
# Tests específicos de la nueva feature
uv run pytest tests/unit/test_features.py -k "<nombre_feature>" -v

# Suite completa de anti-leakage
uv run pytest tests/unit/test_features.py -v

# Reconstruir features para verificar que se incluye
make ml-features 2>&1 | tail -20

# Verificar que aparece en el Parquet
python3 -c "
import pandas as pd
df = pd.read_parquet('data/processed/features.parquet')
cols = [c for c in df.columns if '<nombre_feature>' in c]
print(f'Feature encontrada: {cols}')
print(df[cols].describe())
"
```

### Paso 6: Commit

```bash
git add src/laliga_predictor/features/feature_engineering.py
git add tests/unit/test_features.py
git add README.md
git commit -m "feat: Add <nombre_feature> feature (<categoría>)

- Implementa <descripción breve>
- Añade tests de anti-leakage y value range
- Total features: ~XXX"
```

## ⚠️ Checklist antes de hacer PR

- [ ] La feature usa SOLO datos con `date < match_date`
- [ ] Test de anti-leakage escrito y pasando
- [ ] Test de datos insuficientes (retorna NaN) escrito
- [ ] Test de rango de valores escrito
- [ ] Documentación actualizada en README
- [ ] `make test` pasa completo
- [ ] Feature aparece en el Parquet generado
