# Guia de Poblacion de Datos - LaLiga Predictor

## Objetivo

Poblar la base de datos PostgreSQL con datos historicos de LaLiga desde la API Football para entrenar el modelo de prediccion.

---

## Limitaciones del Plan Gratuito

**API Football Free Plan:**
- 100 requests por dia
- **10 requests por minuto** (rate limit)
- Temporadas disponibles: **2022-2024**
- Total estimado: ~1,140 partidos (380 x 3 temporadas)

**Tiempo estimado para completar:**
- Dia 1: Equipos + Fixtures + 30 partidos con stats = ~32 requests
- Dia 2-4: Continuar con estadisticas (~30-60 partidos por dia)
- **Total: ~10-12 dias para completar las 3 temporadas**

---

## PROCESO PASO A PASO

### **PASO 1: Levantar Contenedores Docker** (30 seg)

```bash
# Levantar PostgreSQL + pgAdmin
docker compose up -d

# O usando Make
make docker-up

# Verificar estado
docker ps
```

**Deberias ver:**
```
CONTAINER ID   IMAGE                   PORTS                    NAMES
xxxxx          postgres:16-alpine      0.0.0.0:5432->5432/tcp   laliga_postgres
xxxxx          dpage/pgadmin4:latest   0.0.0.0:5050->80/tcp     laliga_pgadmin
```

---

### **PASO 2: Inicializar Base de Datos** (1 min)

```bash
# Crear esquema (tablas, indices, vistas)
uv run python -m src.laliga_predictor.data.db_init

# O si quieres recrear desde cero (borra todo)
uv run python -m src.laliga_predictor.data.db_init --drop
```

**Deberias ver:**
```
INFO - Connecting to database: laliga_predictor at localhost:5432
INFO - Executing schema SQL...
INFO - Schema executed successfully
INFO - Created 7 tables:
  - finished_matches
  - match_stats
  - matches
  - seasons
  - team_last5_away
  - team_last5_home
  - teams

=== Database Structure ===

Tables (4):
  - match_stats
  - matches
  - seasons
  - teams

Views (3):
  - finished_matches
  - team_last5_away
  - team_last5_home

=== Data Statistics ===
seasons: 3 records
teams: 0 records
matches: 0 records
match_stats: 0 records
```

---

### **PASO 3: Poblar Datos - Temporada 2024** (DIA 1)

```bash
# Fetch equipos + fixtures + primeros 30 partidos con stats
uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-limit 30
```

**Proceso:**
1. Descarga equipos de LaLiga 2024 (~20 equipos) -> 1 request
2. Descarga todos los fixtures de 2024 (~380 partidos) -> 1 request
3. Descarga estadisticas detalladas de los primeros 30 partidos -> 30 requests
4. **Total: ~32 requests de 100**

**Tiempo estimado:** ~4 minutos (7 segundos entre requests por rate limit)

---

### **PASO 4: Validar Datos** (30 seg)

```bash
# Verificar calidad de datos
uv run python -m src.laliga_predictor.data.validate_data
```

---

### **PASO 5: Continuar con Estadisticas - DIA 2+** (Repetir)

```bash
# Continuar descargando estadisticas (otros 30-60 partidos)
uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-only --stats-limit 60
```

**Proceso:**
- El script detecta automaticamente que partidos ya tienen estadisticas
- Descarga las que faltan
- Usa `--stats-limit` para controlar cuantos partidos procesar

**Repite este comando cada dia hasta completar todos los partidos de 2024**

---

### **PASO 6: Poblar Temporada 2023** (DIA 5-8)

```bash
# Equipos + fixtures + primeros 30 partidos
uv run python -m src.laliga_predictor.data.fetch_data --season 2023 --stats-limit 30

# Dias siguientes: Continuar con estadisticas
uv run python -m src.laliga_predictor.data.fetch_data --season 2023 --stats-only --stats-limit 60
```

---

### **PASO 7: Poblar Temporada 2022** (DIA 9-12)

```bash
# Equipos + fixtures + primeros 30 partidos
uv run python -m src.laliga_predictor.data.fetch_data --season 2022 --stats-limit 30

# Dias siguientes: Continuar con estadisticas
uv run python -m src.laliga_predictor.data.fetch_data --season 2022 --stats-only --stats-limit 60
```

---

### **PASO 8: Validacion Final** (1 min)

```bash
# Verificar que todos los datos estan completos
uv run python -m src.laliga_predictor.data.validate_data
```

---

## Opciones del Script de Fetch

```bash
# Ver ayuda
uv run python -m src.laliga_predictor.data.fetch_data --help

# Solo estadisticas (sin equipos ni fixtures)
uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-only --stats-limit 50

# Limitar numero de partidos con estadisticas
uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-limit 20
```

---

## Verificar Datos

### Opcion 1: psql desde Terminal (Recomendado)

```bash
# Conectar a PostgreSQL
docker exec -it laliga_postgres psql -U laliga_user -d laliga_predictor
```

Dentro de psql:
```sql
-- Ver tablas
\dt

-- Ver temporadas
SELECT * FROM seasons;

-- Ver equipos
SELECT * FROM teams ORDER BY name;

-- Ver partidos recientes
SELECT
    m.match_date::DATE as fecha,
    t1.name as local,
    m.home_score,
    m.away_score,
    t2.name as visitante,
    m.result
FROM matches m
JOIN teams t1 ON m.home_team_id = t1.id
JOIN teams t2 ON m.away_team_id = t2.id
WHERE m.status = 'FT'
ORDER BY m.match_date DESC
LIMIT 10;

-- Salir
\q
```

### Opcion 2: pgAdmin (Interfaz Web)

1. Abrir navegador: http://localhost:5050
2. Login:
   - Email: `admin@example.com`
   - Password: `admin`
3. Conectar a servidor PostgreSQL:
   - Click derecho en "Servers" -> "Register" -> "Server..."
   - **General tab**: Name: `LaLiga Predictor`
   - **Connection tab**:
     - Host: `postgres`
     - Port: `5432`
     - Database: `laliga_predictor`
     - Username: `laliga_user`
     - Password: `laliga_password_dev`
4. Click "Save"

---

## Estrategia Recomendada (10-12 dias)

### **Dia 1: Setup + Temporada 2024 (parcial)**
```bash
docker compose up -d
uv run python -m src.laliga_predictor.data.db_init
uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-limit 30
```

### **Dias 2-4: Completar 2024**
```bash
uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-only --stats-limit 60
```

### **Dias 5-8: Temporada 2023**
```bash
# Dia 5: Equipos + fixtures + 30 partidos
uv run python -m src.laliga_predictor.data.fetch_data --season 2023 --stats-limit 30

# Dias 6-8: Continuar estadisticas
uv run python -m src.laliga_predictor.data.fetch_data --season 2023 --stats-only --stats-limit 60
```

### **Dias 9-12: Temporada 2022**
```bash
# Dia 9: Equipos + fixtures + 30 partidos
uv run python -m src.laliga_predictor.data.fetch_data --season 2022 --stats-limit 30

# Dias 10-12: Completar estadisticas + Validacion Final
uv run python -m src.laliga_predictor.data.fetch_data --season 2022 --stats-only --stats-limit 60
uv run python -m src.laliga_predictor.data.validate_data
```

---

## Troubleshooting

### Error: "API rate limit exceeded" o "Too many requests"
**Causa:** Limite de 10 requests/minuto o 100 requests/dia
**Solucion:** El script tiene un delay de 7 segundos entre requests. Si ves este error, espera 1 minuto y vuelve a ejecutar.

### Error: "Database connection refused"
**Solucion:**
```bash
# Verificar que Docker esta corriendo
docker ps

# Si no esta corriendo
docker compose up -d
```

### Error: "relation does not exist"
**Solucion:**
```bash
# Reinicializar base de datos
uv run python -m src.laliga_predictor.data.db_init
```

### pgAdmin no puede conectar
**Solucion:** Asegurate de usar:
- Host: `postgres` (no `localhost`)
- Database: `laliga_predictor`

---

## Checklist Final

Antes de continuar con Feature Engineering, verifica:

- [ ] Base de datos inicializada correctamente
- [ ] ~1,140 partidos en total (380 x 3 temporadas)
- [ ] ~20 equipos registrados
- [ ] ~95%+ de partidos con estadisticas
- [ ] Validacion sin errores criticos

---

## Notas Tecnicas

### Rate Limiting

El script implementa:
- **7 segundos de delay** entre requests (para respetar limite de 10 req/min)
- Contador de requests usado
- Modo incremental (detecta que ya existe)

### Idempotencia

Los scripts son **idempotentes**:
- Puedes ejecutarlos multiples veces sin duplicar datos
- Usan `ON CONFLICT` para actualizar en lugar de insertar duplicados
- Detectan automaticamente que datos faltan
