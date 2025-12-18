# 🚀 Setup Completo: API Football para LaLiga Predictor

## ✅ Lo que YA está HECHO

1. ✅ **Dependencias instaladas**: `httpx`, `tenacity` para API calls
2. ✅ **Configuración actualizada**: `.env`, `.env.example`, `config.py`
3. ✅ **Cliente API creado**: `src/laliga_predictor/data/api_football_client.py`
4. ✅ **Proyecto UV funcionando**: 131 paquetes instalados correctamente

---

## 📋 PASOS FINALES (Lo que TÚ necesitas hacer)

### Paso 1: Obtener API Key (5 minutos)

1. **Regístrate en API Football**:
   ```
   https://www.api-football.com/
   ```

2. **Plan gratuito**:
   - 100 requests/día
   - Suficiente para obtener datos de 5 temporadas
   - No requiere tarjeta de crédito

3. **Obtén tu API Key**:
   - Ve a Dashboard → API Key
   - Copia la clave

4. **Añade la clave a tu `.env`**:
   ```bash
   nano .env
   ```

   Cambia esta línea:
   ```
   API_FOOTBALL_KEY=your_api_key_here
   ```

   Por tu clave real:
   ```
   API_FOOTBALL_KEY=tu_clave_aqui_1234567890abcdef
   ```

---

### Paso 2: Probar la Conexión (2 minutos)

```bash
# Instalar nuevas dependencias
uv sync

# Probar el cliente
uv run python -m src.laliga_predictor.data.api_football_client
```

**Salida esperada**:
```
INFO - Initialized API Football client for league 140
INFO - Fetching available seasons...
INFO - Available seasons: [2024, 2023, 2022, 2021, 2020]
INFO - Fetching teams for season 2024...
INFO - Found 20 teams
INFO - First 3 teams:
  - Real Madrid (ID: 541)
  - FC Barcelona (ID: 529)
  - Atlético Madrid (ID: 530)
```

---

### Paso 3: Arreglar Permisos de Database (1 minuto)

```bash
# Cambiar propietario del directorio database
sudo chown -R nico:nico /home/nico/Proyecto_ML_Pred_Ganador/database
```

---

### Paso 4: Configurar Git (2 minutos)

```bash
# Configurar tu identidad
git config --global user.email "tu-email@example.com"
git config --global user.name "Tu Nombre"

# Hacer el commit inicial
git add -A
git commit -m "feat: initial project structure with API Football integration

- Add API Football client for data fetching
- Configure environment for API-Football
- Update dependencies for API calls
- Add comprehensive documentation

🤖 Generated with Claude Code"
```

---

## 🎯 PRÓXIMOS PASOS (Después del setup)

Una vez completados los pasos anteriores, te daré código para:

### 1. Diseñar el Esquema de Base de Datos Minimalista
```sql
-- Tablas mínimas basadas en datos de API Football
CREATE TABLE teams (...)
CREATE TABLE seasons (...)
CREATE TABLE matches (...)  -- Tabla principal con stats básicas
```

### 2. Crear Script de Recolección de Datos
```python
# scripts/fetch_laliga_data.py
# Obtener 5 temporadas de LaLiga (2019-2024)
# ~1,900 partidos en total
# Guardar en PostgreSQL
```

### 3. Feature Engineering
```python
# src/laliga_predictor/features/engineer.py
# Calcular features:
# - Forma reciente (últimos 5 partidos)
# - Rendimiento local/visitante
# - Head-to-head
# - Posición en tabla
```

### 4. Modelo MVP
```python
# src/laliga_predictor/models/train.py
# RandomForest o XGBoost
# Predicción de 3 clases: victoria_local / empate / victoria_visitante
```

---

## 📊 DATOS DISPONIBLES EN API FOOTBALL

### Por cada partido obtienes:

```json
{
  "fixture": {
    "id": 1234567,
    "date": "2024-01-15T20:00:00+00:00",
    "status": {
      "short": "FT"  // Finished
    },
    "venue": {
      "name": "Santiago Bernabéu",
      "city": "Madrid"
    }
  },
  "league": {
    "id": 140,
    "name": "La Liga",
    "season": 2023,
    "round": "Regular Season - 20"
  },
  "teams": {
    "home": {
      "id": 541,
      "name": "Real Madrid",
      "logo": "https://..."
    },
    "away": {
      "id": 529,
      "name": "Barcelona",
      "logo": "https://..."
    }
  },
  "goals": {
    "home": 2,
    "away": 1
  },
  "score": {
    "halftime": {
      "home": 1,
      "away": 0
    },
    "fulltime": {
      "home": 2,
      "away": 1
    }
  }
}
```

### Con endpoint `/fixtures/statistics` obtienes:

```json
{
  "statistics": [
    {
      "team": {
        "id": 541,
        "name": "Real Madrid"
      },
      "statistics": [
        {"type": "Shots on Goal", "value": 8},
        {"type": "Shots off Goal", "value": 5},
        {"type": "Total Shots", "value": 13},
        {"type": "Ball Possession", "value": "58%"},
        {"type": "Passes %", "value": "87%"},
        {"type": "expected_goals", "value": "1.8"},
        {"type": "Corners", "value": 6},
        {"type": "Fouls", "value": 12},
        {"type": "Yellow Cards", "value": 2},
        {"type": "Red Cards", "value": 0}
      ]
    }
  ]
}
```

---

## 📈 ESTRATEGIA DE OBTENCIÓN DE DATOS

### Plan de 5 días (100 requests/día):

**Día 1** - Temporada 2023-2024:
```bash
# ~40 requests
- Get teams (1 request)
- Get standings (1 request)
- Get fixtures (~1 request para 380 partidos en lotes)
- Get statistics for 38 partidos (38 requests)
```

**Día 2** - Temporada 2022-2023:
```bash
# ~40 requests
# Mismo proceso
```

**Día 3** - Temporada 2021-2022:
```bash
# ~40 requests
```

**Día 4** - Temporada 2020-2021:
```bash
# ~40 requests
```

**Día 5** - Temporada 2019-2020:
```bash
# ~40 requests
```

### Optimización:
- **No pedir estadísticas detalladas para TODOS los partidos**
- Solo pedir stats detalladas para partidos de entrenamiento
- Usar datos básicos (goles, equipos) para el resto
- **Total**: ~200-300 requests para 1,900 partidos
- **Tiempo**: 2-3 días en lugar de 5

---

## 🎓 FEATURES RECOMENDADAS (Basadas en API Football)

### Features Básicas (Sin stats detalladas):
```python
# De fixtures básicos (sin gastar requests extra):
- home_team_id
- away_team_id
- home_goals_last_5
- away_goals_last_5
- home_wins_last_5
- away_wins_last_5
- home_position_in_table
- away_position_in_table
- h2h_last_5_home_wins
- h2h_last_5_draws
- h2h_last_5_away_wins
```

### Features Avanzadas (Con stats detalladas):
```python
# Solo para subset de datos:
- home_possession_avg
- away_possession_avg
- home_shots_avg
- away_shots_avg
- home_xg_avg
- away_xg_avg
```

---

## ⚠️ IMPORTANTE: Rate Limiting

El cliente ya implementa:
- ✅ Rate limiting automático (1 segundo entre requests)
- ✅ Retry logic con backoff exponencial
- ✅ Logging de requests remaining
- ✅ Manejo de errores

**Nunca excederás el límite de 100 requests/día** si sigues el plan.

---

## 🔥 COMANDO RÁPIDO DE INICIO

Una vez tengas tu API key:

```bash
# 1. Actualizar .env con tu API key
nano .env

# 2. Sync dependencies
uv sync

# 3. Probar conexión
uv run python -m src.laliga_predictor.data.api_football_client

# 4. Si funciona, estás listo para el siguiente paso
```

---

## ❓ ¿Problemas?

### Error: "API_FOOTBALL_KEY is required"
```bash
# Verifica que pusiste la clave en .env:
cat .env | grep API_FOOTBALL_KEY

# Debe mostrar:
API_FOOTBALL_KEY=tu_clave_real_aqui
```

### Error: "403 Forbidden" o "401 Unauthorized"
```
# Tu API key es incorrecta o expiró
# Ve a https://www.api-football.com/ y genera una nueva
```

### Error: "429 Too Many Requests"
```
# Excediste el límite de 100 requests/día
# Espera hasta mañana o upgrade tu plan
```

---

## 📞 ¿Listo para continuar?

Cuando hayas completado los 4 pasos de setup, avísame y te daré:

1. 📊 **Esquema de base de datos** optimizado para API Football
2. 🔄 **Script de recolección** de datos (5 temporadas)
3. 🧮 **Feature engineering** completo
4. 🤖 **Modelo ML MVP** entrenado y evaluado

¡Vamos a construir el predictor! 🚀⚽
