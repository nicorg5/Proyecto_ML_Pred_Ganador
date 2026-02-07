# LaLiga Predictor

Sistema de Machine Learning para predecir resultados de partidos de LaLiga (victoria local / empate / victoria visitante).

## Objetivo del Proyecto

Construir un sistema end-to-end de ML que:
- Obtiene datos historicos de partidos de LaLiga via API Football
- Procesa y genera features a partir de estadisticas de partidos
- Entrena un modelo de clasificacion para predecir resultados
- Despliega predicciones via API REST

## Tech Stack

- **Lenguaje**: Python 3.10+
- **Gestion de dependencias**: UV
- **ML & Data Science**: pandas, numpy, scikit-learn
- **Base de datos**: PostgreSQL 16 (Docker)
- **API de datos**: API Football (api-sports.io)
- **Testing**: pytest, pytest-cov
- **Calidad de codigo**: black, ruff, mypy, pre-commit

---

## Quick Start

### 1. Clonar e Instalar

```bash
# Clonar repositorio
git clone <repo-url>
cd Proyecto_ML_Pred_Ganador

# Instalar dependencias
make install-dev
```

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tu API key de API Football
# Registrate gratis en: https://www.api-football.com/
```

### 3. Levantar Base de Datos

```bash
# Levantar contenedores Docker
docker compose up -d

# Inicializar esquema de base de datos
uv run python -m src.laliga_predictor.data.db_init
```

### 4. Poblar Datos

```bash
# Descargar datos de la temporada 2024 (primeros 30 partidos)
uv run python -m src.laliga_predictor.data.fetch_data --season 2024 --stats-limit 30
```

Ver [docs/DATA_POPULATION_GUIDE.md](docs/DATA_POPULATION_GUIDE.md) para instrucciones completas.

---

## Infraestructura Docker

### Contenedores

| Servicio | Imagen | Puerto | Descripcion |
|----------|--------|--------|-------------|
| PostgreSQL | postgres:16-alpine | 5432 | Base de datos principal |
| pgAdmin | dpage/pgadmin4 | 5050 | Interfaz web para PostgreSQL |

### Comandos Docker

```bash
# Levantar contenedores
docker compose up -d

# Ver estado
docker ps

# Ver logs
docker logs laliga_postgres
docker logs laliga_pgadmin

# Detener contenedores
docker compose down

# Detener y eliminar volumenes (BORRA DATOS)
docker compose down -v
```

---

## Acceso a la Base de Datos

### Opcion 1: psql desde Terminal (Recomendado)

```bash
# Conectar directamente
docker exec -it laliga_postgres psql -U laliga_user -d laliga_predictor
```

Comandos utiles dentro de psql:
```sql
\dt                    -- Ver tablas
\d matches             -- Describir tabla matches
SELECT * FROM teams;   -- Consultar datos
\q                     -- Salir
```

### Opcion 2: pgAdmin (Interfaz Web)

1. **Abrir navegador**: http://localhost:5050

2. **Login**:
   - Email: `admin@example.com`
   - Password: `admin`

3. **Registrar servidor PostgreSQL**:
   - Click derecho en "Servers" -> "Register" -> "Server..."
   - **Tab General**:
     - Name: `LaLiga Predictor`
   - **Tab Connection**:
     - Host: `postgres`
     - Port: `5432`
     - Maintenance database: `laliga_predictor`
     - Username: `laliga_user`
     - Password: `laliga_password_dev`
   - Click "Save"

4. **Ejecutar queries**:
   - Navegar a: Servers -> LaLiga Predictor -> Databases -> laliga_predictor
   - Click derecho -> Query Tool
   - Escribir y ejecutar SQL

### Opcion 3: Cliente PostgreSQL Local

```bash
# Instalar cliente (Ubuntu/Debian)
sudo apt-get install postgresql-client

# Conectar
psql -h localhost -p 5432 -U laliga_user -d laliga_predictor
# Password: laliga_password_dev
```

---

## Estructura del Proyecto

```
Proyecto_ML_Pred_Ganador/
├── src/laliga_predictor/      # Codigo fuente
│   ├── config.py              # Configuracion y settings
│   ├── data/                  # Modulos de datos
│   │   ├── api_football_client.py  # Cliente API Football
│   │   ├── db_init.py         # Inicializacion de BD
│   │   ├── fetch_data.py      # Descarga de datos
│   │   └── validate_data.py   # Validacion de datos
│   ├── features/              # Feature engineering
│   └── models/                # Modelos ML
├── database/                  # Esquemas SQL
│   └── schema.sql             # Esquema de la BD
├── tests/                     # Tests
├── docs/                      # Documentacion
│   ├── DATA_POPULATION_GUIDE.md
│   ├── DATA_STRATEGY.md
│   └── ROADMAP.md
├── docker-compose.yml         # Configuracion Docker
├── Makefile                   # Comandos utiles
└── pyproject.toml             # Configuracion del proyecto
```

---

## Esquema de Base de Datos

### Tablas

| Tabla | Descripcion |
|-------|-------------|
| `seasons` | Temporadas (2022, 2023, 2024) |
| `teams` | Equipos de LaLiga |
| `matches` | Partidos con resultados y estadisticas basicas |
| `match_stats` | Estadisticas detalladas por equipo/partido |

### Vistas

| Vista | Descripcion |
|-------|-------------|
| `finished_matches` | Solo partidos completados |
| `team_last5_home` | Ultimos 5 partidos locales por equipo |
| `team_last5_away` | Ultimos 5 partidos visitantes por equipo |

### Consultas de Ejemplo

```sql
-- Ver partidos recientes
SELECT
    m.match_date::DATE as fecha,
    t1.name as local,
    m.home_score || '-' || m.away_score as resultado,
    t2.name as visitante
FROM matches m
JOIN teams t1 ON m.home_team_id = t1.id
JOIN teams t2 ON m.away_team_id = t2.id
WHERE m.status = 'FT'
ORDER BY m.match_date DESC
LIMIT 10;

-- Estadisticas de cobertura
SELECT
    s.name as temporada,
    COUNT(m.id) as total_partidos,
    COUNT(CASE WHEN m.status = 'FT' THEN 1 END) as finalizados,
    COUNT(ms.match_id) as con_estadisticas
FROM seasons s
LEFT JOIN matches m ON s.id = m.season_id
LEFT JOIN match_stats ms ON m.id = ms.match_id
GROUP BY s.name
ORDER BY s.name DESC;
```

---

## Comandos Make

```bash
make help          # Ver todos los comandos disponibles
make install-dev   # Instalar dependencias de desarrollo
make docker-up     # Levantar contenedores Docker
make docker-down   # Detener contenedores
make test          # Ejecutar tests
make lint          # Verificar calidad de codigo
make format        # Formatear codigo
```

---

## Limitaciones de API Football (Plan Gratuito)

- **100 requests/dia**
- **10 requests/minuto**
- Temporadas disponibles: 2022, 2023, 2024

El script de fetch tiene un delay de 7 segundos entre requests para respetar estos limites.

---

## Proximos Pasos

Ver [docs/ROADMAP.md](docs/ROADMAP.md) para el plan completo del proyecto.

**Resumen**:
1. **Fase 1** (actual): Poblacion de datos
2. **Fase 2**: Feature Engineering
3. **Fase 3**: Entrenamiento del modelo
4. **Fase 4**: Evaluacion y ajuste
5. **Fase 5**: Despliegue (API REST)

---

## Documentacion

- [Guia de Poblacion de Datos](docs/DATA_POPULATION_GUIDE.md)
- [Estrategia de Datos](docs/DATA_STRATEGY.md)
- [Roadmap del Proyecto](docs/ROADMAP.md)

---

## Licencia

MIT License
