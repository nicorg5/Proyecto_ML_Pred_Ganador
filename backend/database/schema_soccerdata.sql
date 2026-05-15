-- ============================================================
-- LaLiga Soccerdata Database Schema
-- ============================================================
-- Comprehensive schema for ML-ready football data.
-- Sources: FBref, Football-Data.co.uk (MatchHistory), ESPN
-- ============================================================

-- Drop existing objects for clean setup
DROP TABLE IF EXISTS shot_events CASCADE;
DROP TABLE IF EXISTS match_player_stats CASCADE;
DROP TABLE IF EXISTS match_advanced_stats CASCADE;
DROP TABLE IF EXISTS standings CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS team_name_mapping CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS seasons CASCADE;
DROP TABLE IF EXISTS etl_log CASCADE;

-- ============================================================
-- TABLE: seasons
-- ============================================================
CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    season_code VARCHAR(10) UNIQUE NOT NULL,   -- '1718', '2324'
    season_name VARCHAR(20) NOT NULL,          -- '2017-2018'
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: teams
-- ============================================================
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(100) UNIQUE NOT NULL,
    short_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: team_name_mapping
-- Maps variant names from each source to canonical team
-- ============================================================
CREATE TABLE team_name_mapping (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    source VARCHAR(30) NOT NULL,              -- 'fbref', 'match_history', 'espn'
    source_name VARCHAR(150) NOT NULL,
    UNIQUE(source, source_name)
);

-- ============================================================
-- TABLE: matches (CORE TABLE)
-- One row per match, combining data from all sources
-- ============================================================
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,

    -- Identity
    season_id INTEGER NOT NULL REFERENCES seasons(id),
    match_date DATE NOT NULL,
    match_week VARCHAR(20),
    round VARCHAR(50),

    -- Teams
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),

    -- Venue & Officials
    venue VARCHAR(150),
    referee VARCHAR(100),
    attendance INTEGER,

    -- Full-time scores
    home_score INTEGER,
    away_score INTEGER,
    result CHAR(1),                            -- 'H', 'D', 'A'

    -- Half-time scores (from MatchHistory)
    ht_home_score INTEGER,
    ht_away_score INTEGER,
    ht_result CHAR(1),

    -- Basic match stats (from MatchHistory)
    home_shots INTEGER,
    away_shots INTEGER,
    home_shots_on_target INTEGER,
    away_shots_on_target INTEGER,
    home_corners INTEGER,
    away_corners INTEGER,
    home_fouls INTEGER,
    away_fouls INTEGER,
    home_yellow_cards INTEGER,
    away_yellow_cards INTEGER,
    home_red_cards INTEGER,
    away_red_cards INTEGER,

    -- xG (from FBref schedule)
    home_xg DECIMAL(5,2),
    away_xg DECIMAL(5,2),

    -- Source tracking
    fbref_match_id VARCHAR(50),
    espn_game_id VARCHAR(50),
    source_match_history BOOLEAN DEFAULT FALSE,
    source_fbref BOOLEAN DEFAULT FALSE,
    source_espn BOOLEAN DEFAULT FALSE,

    -- Metadata
    status VARCHAR(20) DEFAULT 'FT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicate matches
    UNIQUE(season_id, match_date, home_team_id, away_team_id)
);

-- ============================================================
-- TABLE: match_advanced_stats
-- Detailed per-team-per-match stats from FBref
-- Wide table: one row per team per match, ~80 stat columns
-- ============================================================
CREATE TABLE match_advanced_stats (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    is_home BOOLEAN NOT NULL,

    -- stat_type='schedule'
    goals_for INTEGER,
    goals_against INTEGER,
    possession DECIMAL(5,2),
    formation VARCHAR(20),

    -- stat_type='shooting'
    sh INTEGER,                                -- Total shots
    sot INTEGER,                               -- Shots on target
    sot_pct DECIMAL(5,2),                      -- Shots on target %
    g_per_sh DECIMAL(5,3),                     -- Goals per shot
    g_per_sot DECIMAL(5,3),                    -- Goals per shot on target
    fk INTEGER,                                -- Free kick shots
    pk INTEGER,                                -- Penalty kicks scored
    pk_att INTEGER,                            -- Penalty kicks attempted
    xg DECIMAL(5,2),
    npxg DECIMAL(5,2),                         -- Non-penalty xG
    npxg_per_sh DECIMAL(5,3),                  -- Non-penalty xG per shot
    g_minus_xg DECIMAL(5,2),                   -- Goals minus xG

    -- stat_type='passing'
    passes_cmp INTEGER,                        -- Passes completed
    passes_att INTEGER,                        -- Passes attempted
    passes_cmp_pct DECIMAL(5,2),               -- Pass completion %
    passes_tot_dist INTEGER,                   -- Total passing distance
    passes_prg_dist INTEGER,                   -- Progressive passing distance
    passes_short_cmp INTEGER,
    passes_short_att INTEGER,
    passes_short_cmp_pct DECIMAL(5,2),
    passes_medium_cmp INTEGER,
    passes_medium_att INTEGER,
    passes_medium_cmp_pct DECIMAL(5,2),
    passes_long_cmp INTEGER,
    passes_long_att INTEGER,
    passes_long_cmp_pct DECIMAL(5,2),
    assists INTEGER,
    xag DECIMAL(5,2),                          -- Expected assists
    xa DECIMAL(5,2),                           -- Expected assists (alternate)
    key_passes INTEGER,
    passes_final_third INTEGER,
    passes_penalty_area INTEGER,
    crosses_penalty_area INTEGER,
    progressive_passes INTEGER,

    -- stat_type='passing_types'
    passes_live INTEGER,
    passes_dead INTEGER,
    passes_fk INTEGER,                         -- Passes from free kicks
    through_balls INTEGER,
    switches INTEGER,
    crosses INTEGER,
    throw_ins INTEGER,
    corner_kicks INTEGER,
    corner_kicks_in INTEGER,
    corner_kicks_out INTEGER,
    corner_kicks_straight INTEGER,

    -- stat_type='goal_shot_creation'
    sca INTEGER,                               -- Shot-Creating Actions
    sca_per90 DECIMAL(5,2),
    sca_passes_live INTEGER,
    sca_passes_dead INTEGER,
    sca_take_ons INTEGER,
    sca_shots INTEGER,
    sca_fouls_drawn INTEGER,
    sca_defense INTEGER,
    gca INTEGER,                               -- Goal-Creating Actions
    gca_per90 DECIMAL(5,2),

    -- stat_type='defense'
    tackles INTEGER,
    tackles_won INTEGER,
    tackles_def_3rd INTEGER,
    tackles_mid_3rd INTEGER,
    tackles_att_3rd INTEGER,
    challenges_lost INTEGER,
    blocks INTEGER,
    blocked_shots INTEGER,
    blocked_passes INTEGER,
    interceptions INTEGER,
    clearances INTEGER,
    errors INTEGER,

    -- stat_type='possession'
    touches INTEGER,
    touches_def_pen INTEGER,
    touches_def_3rd INTEGER,
    touches_mid_3rd INTEGER,
    touches_att_3rd INTEGER,
    touches_att_pen INTEGER,
    take_ons_att INTEGER,
    take_ons_succ INTEGER,
    take_ons_succ_pct DECIMAL(5,2),
    carries INTEGER,
    carries_tot_dist INTEGER,
    carries_prg_dist INTEGER,
    progressive_carries INTEGER,
    carries_final_third INTEGER,
    carries_penalty_area INTEGER,
    miscontrols INTEGER,
    dispossessed INTEGER,
    passes_received INTEGER,
    progressive_passes_rec INTEGER,

    -- stat_type='misc'
    cards_yellow INTEGER,
    cards_red INTEGER,
    cards_second_yellow INTEGER,
    fouls_committed INTEGER,
    fouls_drawn INTEGER,
    offsides INTEGER,
    pens_won INTEGER,
    pens_conceded INTEGER,
    own_goals INTEGER,
    ball_recoveries INTEGER,
    aerials_won INTEGER,
    aerials_lost INTEGER,
    aerials_won_pct DECIMAL(5,2),

    -- ESPN-specific stats
    saves INTEGER,
    crosses_cmp INTEGER,                       -- Accurate crosses
    crosses_cmp_pct DECIMAL(5,2),              -- Cross completion %
    tackles_won_pct DECIMAL(5,2),              -- Tackle success %
    clearances_effective INTEGER,              -- Effective clearances
    long_balls_cmp INTEGER,                    -- Accurate long balls
    long_balls_att INTEGER,                    -- Total long balls
    long_balls_cmp_pct DECIMAL(5,2),           -- Long ball accuracy %

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(match_id, team_id)
);

-- ============================================================
-- TABLE: standings
-- League table per matchweek (computed from results)
-- ============================================================
CREATE TABLE standings (
    id SERIAL PRIMARY KEY,
    season_id INTEGER NOT NULL REFERENCES seasons(id),
    match_week INTEGER NOT NULL,
    team_id INTEGER NOT NULL REFERENCES teams(id),

    position INTEGER NOT NULL,
    matches_played INTEGER NOT NULL,
    wins INTEGER NOT NULL,
    draws INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    goals_for INTEGER NOT NULL,
    goals_against INTEGER NOT NULL,
    goal_difference INTEGER NOT NULL,
    points INTEGER NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(season_id, match_week, team_id)
);

-- ============================================================
-- TABLE: match_player_stats
-- Per-player-per-match stats from FBref
-- ============================================================
CREATE TABLE match_player_stats (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    is_home BOOLEAN NOT NULL,

    player_name VARCHAR(150) NOT NULL,
    player_nation VARCHAR(10),
    position VARCHAR(10),
    age VARCHAR(10),
    minutes INTEGER,

    goals INTEGER,
    assists INTEGER,
    pens_made INTEGER,
    pens_att INTEGER,
    shots INTEGER,
    shots_on_target INTEGER,
    xg DECIMAL(5,2),
    npxg DECIMAL(5,2),
    xag DECIMAL(5,2),

    yellow_cards INTEGER,
    red_cards INTEGER,

    touches INTEGER,
    tackles INTEGER,
    interceptions INTEGER,
    blocks INTEGER,
    passes_completed INTEGER,
    passes_attempted INTEGER,
    pass_completion_pct DECIMAL(5,2),
    progressive_passes INTEGER,
    carries INTEGER,
    progressive_carries INTEGER,
    take_ons_attempted INTEGER,
    take_ons_succeeded INTEGER,

    saves INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(match_id, team_id, player_name)
);

-- ============================================================
-- TABLE: shot_events
-- Per-shot data from FBref read_shot_events
-- ============================================================
CREATE TABLE shot_events (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id),

    minute INTEGER,
    player_name VARCHAR(150),
    xg DECIMAL(5,3),
    psxg DECIMAL(5,3),
    outcome VARCHAR(30),
    distance INTEGER,
    body_part VARCHAR(30),
    notes VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: etl_log
-- Track ETL pipeline runs for idempotency
-- ============================================================
CREATE TABLE etl_log (
    id SERIAL PRIMARY KEY,
    source VARCHAR(30) NOT NULL,               -- 'fbref', 'match_history', 'espn'
    operation VARCHAR(50) NOT NULL,            -- 'schedule', 'team_match_stats_shooting', 'espn_stats', etc.
    season_code VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,               -- 'started', 'completed', 'failed'
    rows_affected INTEGER,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_matches_season ON matches(season_id);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_result ON matches(result);
CREATE INDEX idx_matches_fbref_id ON matches(fbref_match_id);
CREATE INDEX idx_matches_espn_id ON matches(espn_game_id);
CREATE INDEX idx_advanced_match ON match_advanced_stats(match_id);
CREATE INDEX idx_advanced_team ON match_advanced_stats(team_id);
CREATE INDEX idx_standings_season_week ON standings(season_id, match_week);
CREATE INDEX idx_player_stats_match ON match_player_stats(match_id);
CREATE INDEX idx_shots_match ON shot_events(match_id);
CREATE INDEX idx_team_mapping_source ON team_name_mapping(source, source_name);
CREATE INDEX idx_etl_log_lookup ON etl_log(source, operation, season_code);

-- ============================================================
-- VIEWS
-- ============================================================

-- Completed matches with team names
CREATE VIEW v_completed_matches AS
SELECT
    m.id,
    s.season_name,
    s.season_code,
    m.match_date,
    m.match_week,
    ht.canonical_name AS home_team,
    at.canonical_name AS away_team,
    m.home_score, m.away_score, m.result,
    m.ht_home_score, m.ht_away_score,
    m.home_shots, m.away_shots,
    m.home_shots_on_target, m.away_shots_on_target,
    m.home_corners, m.away_corners,
    m.home_fouls, m.away_fouls,
    m.home_yellow_cards, m.away_yellow_cards,
    m.home_red_cards, m.away_red_cards,
    m.home_xg, m.away_xg,
    m.venue, m.referee, m.attendance
FROM matches m
JOIN seasons s ON m.season_id = s.id
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
WHERE m.home_score IS NOT NULL;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update updated_at on matches
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_matches_updated
BEFORE UPDATE ON matches
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- ============================================================
-- SEED DATA: Seasons (2017-2025)
-- ============================================================
INSERT INTO seasons (season_code, season_name, start_year, end_year, is_current) VALUES
    ('1718', '2017-2018', 2017, 2018, FALSE),
    ('1819', '2018-2019', 2018, 2019, FALSE),
    ('1920', '2019-2020', 2019, 2020, FALSE),
    ('2021', '2020-2021', 2020, 2021, FALSE),
    ('2122', '2021-2022', 2021, 2022, FALSE),
    ('2223', '2022-2023', 2022, 2023, FALSE),
    ('2324', '2023-2024', 2023, 2024, FALSE),
    ('2425', '2024-2025', 2024, 2025, TRUE);
