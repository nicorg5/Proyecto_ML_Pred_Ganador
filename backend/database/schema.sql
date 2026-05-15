-- LaLiga Predictor Database Schema
-- Minimalista pero completo para Machine Learning

-- Drop tables if exist (for clean setup)
DROP TABLE IF EXISTS match_stats CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS seasons CASCADE;

-- ========================================
-- TABLA: seasons (Temporadas)
-- ========================================
CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    year INTEGER UNIQUE NOT NULL,  -- 2024 (representa temporada 2024-2025)
    name VARCHAR(20) NOT NULL,      -- "2024-2025"
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- TABLA: teams (Equipos)
-- ========================================
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,         -- Usamos ID de API Football
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    logo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- TABLA: matches (Partidos - TABLA PRINCIPAL)
-- ========================================
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,         -- ID de API Football (fixture_id)
    season_id INTEGER NOT NULL REFERENCES seasons(id),

    -- Información del partido
    match_date TIMESTAMP NOT NULL,
    match_week INTEGER,             -- Jornada (1-38)
    venue VARCHAR(100),
    referee VARCHAR(100),

    -- Equipos
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),

    -- Resultado
    home_score INTEGER,
    away_score INTEGER,
    result VARCHAR(10),             -- 'H' (home), 'D' (draw), 'A' (away)

    -- Estadísticas básicas del partido
    home_possession DECIMAL(5,2),
    away_possession DECIMAL(5,2),

    home_shots_total INTEGER,
    away_shots_total INTEGER,

    home_shots_on_goal INTEGER,
    away_shots_on_goal INTEGER,

    home_corners INTEGER,
    away_corners INTEGER,

    home_fouls INTEGER,
    away_fouls INTEGER,

    home_yellow_cards INTEGER,
    away_yellow_cards INTEGER,

    home_red_cards INTEGER,
    away_red_cards INTEGER,

    -- Metadata
    status VARCHAR(20),             -- 'FT' (finished), 'NS' (not started), etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- TABLA: match_stats (Estadísticas Detalladas - OPCIONAL)
-- Para análisis más profundo
-- ========================================
CREATE TABLE match_stats (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    is_home BOOLEAN NOT NULL,

    -- Estadísticas avanzadas
    expected_goals DECIMAL(5,2),    -- xG
    passes_total INTEGER,
    passes_accurate INTEGER,
    passes_accuracy DECIMAL(5,2),

    tackles INTEGER,
    interceptions INTEGER,
    blocks INTEGER,

    saves INTEGER,

    offsides INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(match_id, team_id)
);

-- ========================================
-- ÍNDICES para optimizar queries
-- ========================================
CREATE INDEX idx_matches_season ON matches(season_id);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_result ON matches(result);
CREATE INDEX idx_match_stats_match ON match_stats(match_id);

-- ========================================
-- VISTAS ÚTILES para Feature Engineering
-- ========================================

-- Vista: Partidos completados
CREATE VIEW finished_matches AS
SELECT * FROM matches
WHERE status = 'FT' AND home_score IS NOT NULL;

-- Vista: Últimos 5 partidos de cada equipo (local)
CREATE VIEW team_last5_home AS
SELECT
    home_team_id AS team_id,
    match_date,
    result,
    home_score AS goals_for,
    away_score AS goals_against,
    ROW_NUMBER() OVER (PARTITION BY home_team_id ORDER BY match_date DESC) as rn
FROM finished_matches;

-- Vista: Últimos 5 partidos de cada equipo (visitante)
CREATE VIEW team_last5_away AS
SELECT
    away_team_id AS team_id,
    match_date,
    CASE
        WHEN result = 'H' THEN 'A'
        WHEN result = 'A' THEN 'H'
        ELSE 'D'
    END AS result,
    away_score AS goals_for,
    home_score AS goals_against,
    ROW_NUMBER() OVER (PARTITION BY away_team_id ORDER BY match_date DESC) as rn
FROM finished_matches;

-- ========================================
-- FUNCIONES ÚTILES
-- ========================================

-- Función: Calcular resultado basado en marcador
CREATE OR REPLACE FUNCTION calculate_result(home_score INTEGER, away_score INTEGER)
RETURNS VARCHAR(10) AS $$
BEGIN
    IF home_score IS NULL OR away_score IS NULL THEN
        RETURN NULL;
    END IF;

    IF home_score > away_score THEN
        RETURN 'H';
    ELSIF home_score < away_score THEN
        RETURN 'A';
    ELSE
        RETURN 'D';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-calcular resultado cuando se actualiza marcador
CREATE OR REPLACE FUNCTION update_match_result()
RETURNS TRIGGER AS $$
BEGIN
    NEW.result = calculate_result(NEW.home_score, NEW.away_score);
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_match_result
BEFORE INSERT OR UPDATE OF home_score, away_score ON matches
FOR EACH ROW
EXECUTE FUNCTION update_match_result();

-- ========================================
-- DATOS INICIALES
-- ========================================

-- Insertar temporadas (2022-2024)
INSERT INTO seasons (year, name, is_current) VALUES
    (2022, '2022-2023', FALSE),
    (2023, '2023-2024', FALSE),
    (2024, '2024-2025', TRUE);

-- Commit
COMMIT;