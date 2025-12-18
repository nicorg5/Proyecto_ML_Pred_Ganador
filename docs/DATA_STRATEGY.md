# 📊 Estrategia de Datos para Predicción de Resultados de LaLiga

## 🎯 Objetivo
Predecir el resultado de un partido de LaLiga (victoria local / empate / victoria visitante) usando datos históricos.

---

## 1. DATOS DISPONIBLES EN FBREF

### Estructura de FBRef para LaLiga

#### Nivel 1: Histórico de Temporadas
**URL**: `https://fbref.com/en/comps/12/history/La-Liga-Seasons`

**Datos disponibles por temporada**:
- Temporada (ej: 2023-2024)
- Campeón
- Estadísticas agregadas de la temporada
- Enlaces a páginas detalladas de cada temporada

#### Nivel 2: Temporada Específica
**URL**: `https://fbref.com/en/comps/12/2023-2024/2023-2024-La-Liga-Stats`

**Tablas disponibles**:
1. **Tabla de clasificación** (League Table)
   - Posición, equipo, partidos jugados, victorias, empates, derrotas
   - Goles a favor, goles en contra, diferencia de goles
   - Puntos

2. **Calendario y resultados** (Scores & Fixtures)
   - Fecha, jornada
   - Equipo local, equipo visitante
   - Resultado (goles local - goles visitante)
   - Asistencia (espectadores)
   - Árbitro
   - **Enlace a estadísticas detalladas del partido**

3. **Estadísticas de equipos** (Squad Stats)
   - Estadísticas ofensivas: goles, tiros, tiros a puerta, xG
   - Estadísticas defensivas: goles en contra, tiros en contra
   - Posesión promedio
   - Pases completados
   - Faltas, tarjetas

#### Nivel 3: Partido Específico
**URL**: `https://fbref.com/en/matches/[match-id]/[teams]-[competition]`

**Datos detallados**:
- **Estadísticas generales**: posesión, tiros, tiros a puerta, corners, faltas
- **xG (Expected Goals)**: xG local, xG visitante
- **Pases**: completados, intentados, precisión
- **Defensas**: tackles, intercepciones, bloqueos
- **Portería**: paradas, goles en contra
- **Disciplina**: tarjetas amarillas, rojas
- **Alineaciones y jugadores**

---

## 2. ESTRATEGIA DE SCRAPING RECOMENDADA

### ⚠️ Problemas con FBRef
1. **Bloqueo 403**: FBRef bloquea scrapers automáticos agresivos
2. **Rate limiting**: Necesitas delays largos entre requests (3-5 segundos mínimo)
3. **Estructura HTML compleja**: Muchas tablas comentadas en HTML
4. **JavaScript rendering**: Algunas partes requieren renderizado JS

### ✅ Soluciones Recomendadas

#### Opción A: Scraping Manual Inicial (RECOMENDADO para empezar)
1. **Descargar HTMLs manualmente** de 5 temporadas recientes
2. Guardarlos en `data/raw/seasons/`
3. Parsear los HTMLs localmente sin hacer requests
4. **Ventaja**: No hay bloqueos, puedes desarrollar tranquilo

**Temporadas recomendadas**:
- 2023-2024 (actual)
- 2022-2023
- 2021-2022
- 2020-2021
- 2019-2020

#### Opción B: API de FBRef (si existe)
- FBRef no tiene API pública oficial
- Statsbomb (propietarios) tienen API de pago

#### Opción C: Fuentes Alternativas de Datos
1. **API Football**: https://www.api-football.com/
   - 100 requests/día gratis
   - Datos en tiempo real
   - Estadísticas históricas

2. **Football-Data.org**: https://www.football-data.org/
   - API gratuita con límites
   - Datos de LaLiga

3. **Kaggle Datasets**:
   - Buscar "LaLiga historical data"
   - Datasets ya preparados

#### Opción D: Scraping Inteligente con Rotación
1. Usar **Selenium** o **Playwright** para renderizar JS
2. Rotar **User-Agents**
3. Usar **proxies**
4. Delays largos (5-10 segundos)
5. Scraping nocturno/off-peak

---

## 3. FEATURES RECOMENDADAS PARA EL MODELO

### 🎯 Features Críticas (Básicas - MVP)

#### A. Features del Equipo Local (últimos 5 partidos)
1. **Forma reciente**:
   - Victorias en últimos 5 partidos
   - Empates en últimos 5 partidos
   - Derrotas en últimos 5 partidos
   - Puntos promedio por partido

2. **Goles**:
   - Goles marcados promedio (últimos 5)
   - Goles recibidos promedio (últimos 5)
   - Diferencia de goles promedio

3. **Rendimiento en casa**:
   - % de victorias en casa (última temporada)
   - Goles marcados en casa promedio
   - Goles recibidos en casa promedio

#### B. Features del Equipo Visitante (últimos 5 partidos)
1. **Forma reciente**:
   - Mismo que equipo local

2. **Rendimiento fuera**:
   - % de victorias fuera
   - Goles marcados fuera promedio
   - Goles recibidos fuera promedio

#### C. Features del Enfrentamiento
1. **Head-to-head**:
   - Últimos 5 enfrentamientos: victorias local
   - Últimos 5 enfrentamientos: empates
   - Últimos 5 enfrentamientos: victorias visitante
   - Goles promedio en enfrentamientos

#### D. Features de Contexto
1. **Posición en tabla**:
   - Posición actual equipo local
   - Posición actual equipo visitante
   - Diferencia de posiciones

2. **Puntos**:
   - Puntos equipo local
   - Puntos equipo visitante
   - Diferencia de puntos

### 🚀 Features Avanzadas (Fase 2)

1. **Expected Goals (xG)**:
   - xG promedio últimos 5 partidos (local y visitante)
   - xG concedido promedio

2. **Estadísticas avanzadas**:
   - Posesión promedio
   - Tiros a puerta promedio
   - Corners promedio
   - Precisión de pases

3. **Features temporales**:
   - Días de descanso
   - Jornada del campeonato
   - Mes del partido

4. **Features de momentum**:
   - Racha de victorias/derrotas
   - Tendencia de goles (últimos 3 vs últimos 10)

---

## 4. DISEÑO DE BASE DE DATOS MINIMALISTA

### Tablas Mínimas Necesarias

#### 1. `teams` (Equipos)
```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    short_name VARCHAR(20)
);
```

#### 2. `seasons` (Temporadas)
```sql
CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) UNIQUE NOT NULL,  -- "2023-2024"
    start_year INTEGER,
    end_year INTEGER
);
```

#### 3. `matches` (Partidos - TABLA PRINCIPAL)
```sql
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    season_id INTEGER REFERENCES seasons(id),
    match_date DATE NOT NULL,
    match_week INTEGER,

    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),

    home_score INTEGER,
    away_score INTEGER,
    result VARCHAR(20),  -- 'home_win', 'draw', 'away_win'

    -- Estadísticas básicas del partido
    home_possession DECIMAL(5,2),
    away_possession DECIMAL(5,2),

    home_shots INTEGER,
    away_shots INTEGER,

    home_shots_on_target INTEGER,
    away_shots_on_target INTEGER,

    home_corners INTEGER,
    away_corners INTEGER,

    -- Metadata
    attendance INTEGER,
    referee VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. `match_stats` (Estadísticas detalladas - OPCIONAL)
```sql
CREATE TABLE match_stats (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    team_id INTEGER REFERENCES teams(id),
    is_home BOOLEAN,

    -- xG
    xg DECIMAL(5,2),

    -- Pases
    passes_completed INTEGER,
    passes_attempted INTEGER,
    pass_accuracy DECIMAL(5,2),

    -- Defensa
    tackles INTEGER,
    interceptions INTEGER,

    -- Disciplina
    yellow_cards INTEGER,
    red_cards INTEGER
);
```

---

## 5. PIPELINE DE DATOS RECOMENDADO

### Fase 1: Recolección (Semana 1)
```
1. Descargar manualmente HTMLs de 5 temporadas
2. Guardar en data/raw/seasons/2023-2024.html
3. Parsear con BeautifulSoup
4. Extraer datos básicos: fecha, equipos, resultado
5. Guardar en CSV: data/processed/matches_raw.csv
```

### Fase 2: Feature Engineering (Semana 2)
```
1. Calcular features de forma reciente (últimos 5 partidos)
2. Calcular features de rendimiento local/visitante
3. Calcular features de head-to-head
4. Crear dataset final: data/processed/matches_with_features.csv
```

### Fase 3: Modelo MVP (Semana 3)
```
1. Entrenar modelo simple: RandomForest o XGBoost
2. Métricas: accuracy, F1-score por clase
3. Validación: últimas 2 jornadas como test
4. Guardar modelo: models/model_v1.pkl
```

---

## 6. RECOMENDACIÓN FINAL

### Para Empezar AHORA (Próximos Pasos)

1. **No scrapers por ahora** - Evita bloqueos

2. **Opción A - Datos Manuales** (RECOMENDADO):
   ```bash
   # Crear carpeta para HTMLs
   mkdir -p data/raw/seasons

   # Descargar manualmente:
   # - Ve a https://fbref.com/en/comps/12/schedule/La-Liga-Scores-and-Fixtures
   # - Guarda la página (Ctrl+S) como "2023-2024.html"
   # - Repite para 4 temporadas más
   ```

3. **Opción B - API Football** (ALTERNATIVA):
   ```bash
   # Registrarte en https://www.api-football.com/
   # 100 requests/día gratis
   # Suficiente para obtener 5 temporadas en 5 días
   ```

4. **Crear parser para datos locales**:
   ```python
   # scripts/parse_local_html.py
   # Leer HTMLs guardados
   # Extraer matches básicos
   # Guardar en data/processed/matches.csv
   ```

5. **Feature engineering simple**:
   ```python
   # src/laliga_predictor/features/engineer.py
   # Calcular últimos 5 partidos
   # Crear dataset entrenamiento
   ```

---

## 7. DATASET MÍNIMO VIABLE

### Estructura CSV Recomendada

**matches_with_features.csv**:
```csv
match_id,date,home_team,away_team,result,
home_last5_wins,home_last5_draws,home_last5_losses,
home_last5_goals_for,home_last5_goals_against,
away_last5_wins,away_last5_draws,away_last5_losses,
away_last5_goals_for,away_last5_goals_against,
home_position,away_position,
h2h_last5_home_wins,h2h_last5_draws,h2h_last5_away_wins
```

**Tamaño estimado**:
- 5 temporadas × 380 partidos = **1,900 partidos**
- Suficiente para entrenar un modelo básico
- Train (80%): ~1,500 partidos
- Test (20%): ~400 partidos

---

## 📌 ¿Qué prefieres hacer?

**A)** Usar datos manuales (descargar HTMLs) y parsearlos localmente
**B)** Usar API Football (100 requests/día gratuitos)
**C)** Buscar dataset de Kaggle ya preparado
**D)** Desarrollar scraper avanzado con Selenium/Playwright (más complejo)

**Mi recomendación**: Empieza con **A o B** para tener datos rápidamente y validar el modelo. Luego, si funciona, inviertes tiempo en un scraper robusto.
