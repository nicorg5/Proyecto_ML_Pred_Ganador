"""
Pytest configuration and shared fixtures.
"""

import os
from collections.abc import Generator
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return path to project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def reset_environment() -> Generator[None, None, None]:
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


# ================================================================
# Synthetic data fixtures for ML pipeline tests
# ================================================================

TEAMS = [
    (1, "Team A"),
    (2, "Team B"),
    (3, "Team C"),
    (4, "Team D"),
]


def _make_matches(n_seasons: int = 2) -> pd.DataFrame:
    """Generate synthetic match data for 4 teams over N seasons.

    Each season: 4 teams = 6 matchups × 2 (home/away) = 12 matches.
    """
    rng = np.random.default_rng(42)
    rows = []
    match_id = 1
    season_codes = ["2223", "2324", "2425"][:n_seasons]

    for season in season_codes:
        year_start = 2000 + int(season[:2])
        base_date = pd.Timestamp(f"{year_start}-08-15")

        matchday = 0
        for round_num in range(2):  # home and away
            for i, (h_id, h_name) in enumerate(TEAMS):
                for j, (a_id, a_name) in enumerate(TEAMS):
                    if i == j:
                        continue
                    if round_num == 1:
                        h_id, a_id = a_id, h_id
                        h_name, a_name = a_name, h_name

                    h_score = int(rng.poisson(1.3))
                    a_score = int(rng.poisson(1.0))
                    if h_score > a_score:
                        result = "H"
                    elif a_score > h_score:
                        result = "A"
                    else:
                        result = "D"

                    match_date = base_date + pd.Timedelta(days=matchday * 7)
                    rows.append(
                        {
                            "match_id": match_id,
                            "season_code": season,
                            "match_date": match_date,
                            "home_team": h_name,
                            "away_team": a_name,
                            "home_team_id": h_id,
                            "away_team_id": a_id,
                            "home_score": h_score,
                            "away_score": a_score,
                            "result": result,
                            "home_shots": int(rng.poisson(12)),
                            "away_shots": int(rng.poisson(10)),
                            "home_shots_on_target": int(rng.poisson(4)),
                            "away_shots_on_target": int(rng.poisson(3)),
                            "home_corners": int(rng.poisson(5)),
                            "away_corners": int(rng.poisson(4)),
                            "home_fouls": int(rng.poisson(12)),
                            "away_fouls": int(rng.poisson(12)),
                            "home_yellow_cards": int(rng.poisson(2)),
                            "away_yellow_cards": int(rng.poisson(2)),
                            "home_red_cards": int(rng.poisson(0.1)),
                            "away_red_cards": int(rng.poisson(0.1)),
                            "venue": f"{h_name} Stadium",
                            "attendance": int(rng.normal(40000, 10000)),
                        }
                    )
                    match_id += 1
                    matchday += 1

    df = pd.DataFrame(rows)
    df["match_date"] = pd.to_datetime(df["match_date"])
    return df


def _make_advanced_stats(matches: pd.DataFrame) -> pd.DataFrame:
    """Generate synthetic ESPN advanced stats for each team in each match."""
    rng = np.random.default_rng(42)
    rows = []

    for _, m in matches.iterrows():
        for is_home in [True, False]:
            team_id = m["home_team_id"] if is_home else m["away_team_id"]
            rows.append(
                {
                    "match_id": m["match_id"],
                    "team_id": team_id,
                    "is_home": is_home,
                    "match_date": m["match_date"],
                    "season_code": m["season_code"],
                    "possession": round(rng.uniform(35, 65), 1),
                    "sh": int(rng.poisson(12)),
                    "sot": int(rng.poisson(4)),
                    "sot_pct": round(rng.uniform(20, 50), 1),
                    "passes_cmp": int(rng.poisson(350)),
                    "passes_att": int(rng.poisson(450)),
                    "passes_cmp_pct": round(rng.uniform(70, 90), 1),
                    "tackles": int(rng.poisson(18)),
                    "tackles_won": int(rng.poisson(10)),
                    "tackles_won_pct": round(rng.uniform(40, 70), 1),
                    "interceptions": int(rng.poisson(8)),
                    "clearances": int(rng.poisson(15)),
                    "clearances_effective": int(rng.poisson(10)),
                    "blocked_shots": int(rng.poisson(3)),
                    "crosses": int(rng.poisson(15)),
                    "crosses_cmp": int(rng.poisson(5)),
                    "crosses_cmp_pct": round(rng.uniform(20, 40), 1),
                    "long_balls_cmp": int(rng.poisson(8)),
                    "long_balls_att": int(rng.poisson(20)),
                    "long_balls_cmp_pct": round(rng.uniform(30, 60), 1),
                    "saves": int(rng.poisson(3)),
                    "corner_kicks": int(rng.poisson(5)),
                    "fouls_committed": int(rng.poisson(12)),
                    "cards_yellow": int(rng.poisson(2)),
                    "cards_red": int(rng.poisson(0.1)),
                    "offsides": int(rng.poisson(2)),
                }
            )

    df = pd.DataFrame(rows)
    df["match_date"] = pd.to_datetime(df["match_date"])
    return df


def _make_standings(matches: pd.DataFrame) -> pd.DataFrame:
    """Generate synthetic standings from match results."""
    rows = []

    for season in matches["season_code"].unique():
        season_matches = matches[matches["season_code"] == season].sort_values("match_date")
        team_stats: dict[int, dict] = {}

        for _, team in enumerate(TEAMS):
            team_stats[team[0]] = {
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
                "matches_played": 0,
            }

        match_week = 0
        for idx, m in season_matches.iterrows():
            # Update home team
            h_id = m["home_team_id"]
            a_id = m["away_team_id"]
            team_stats[h_id]["matches_played"] += 1
            team_stats[a_id]["matches_played"] += 1
            team_stats[h_id]["goals_for"] += m["home_score"]
            team_stats[h_id]["goals_against"] += m["away_score"]
            team_stats[a_id]["goals_for"] += m["away_score"]
            team_stats[a_id]["goals_against"] += m["home_score"]

            if m["result"] == "H":
                team_stats[h_id]["wins"] += 1
                team_stats[h_id]["points"] += 3
                team_stats[a_id]["losses"] += 1
            elif m["result"] == "A":
                team_stats[a_id]["wins"] += 1
                team_stats[a_id]["points"] += 3
                team_stats[h_id]["losses"] += 1
            else:
                team_stats[h_id]["draws"] += 1
                team_stats[h_id]["points"] += 1
                team_stats[a_id]["draws"] += 1
                team_stats[a_id]["points"] += 1

            # Emit standings every 2 matches (simulating matchweeks)
            if (idx + 1) % 2 == 0:
                match_week += 1
                sorted_teams = sorted(
                    team_stats.items(),
                    key=lambda x: (-x[1]["points"], -(x[1]["goals_for"] - x[1]["goals_against"])),
                )
                for pos, (tid, stats) in enumerate(sorted_teams, 1):
                    team_name = next(t[1] for t in TEAMS if t[0] == tid)
                    rows.append(
                        {
                            "season_code": season,
                            "match_week": match_week,
                            "team_id": tid,
                            "team": team_name,
                            "position": pos,
                            "matches_played": stats["matches_played"],
                            "wins": stats["wins"],
                            "draws": stats["draws"],
                            "losses": stats["losses"],
                            "goals_for": stats["goals_for"],
                            "goals_against": stats["goals_against"],
                            "goal_difference": stats["goals_for"] - stats["goals_against"],
                            "points": stats["points"],
                        }
                    )

    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def synthetic_matches() -> pd.DataFrame:
    """Synthetic matches: 4 teams, 2 seasons, 12 matches/season = 24 total."""
    return _make_matches(n_seasons=2)


@pytest.fixture(scope="session")
def synthetic_advanced_stats(synthetic_matches: pd.DataFrame) -> pd.DataFrame:
    """Synthetic ESPN advanced stats: 2 rows per match (home + away)."""
    return _make_advanced_stats(synthetic_matches)


@pytest.fixture(scope="session")
def synthetic_standings(synthetic_matches: pd.DataFrame) -> pd.DataFrame:
    """Synthetic standings from match results."""
    return _make_standings(synthetic_matches)


@pytest.fixture(scope="session")
def synthetic_3season_matches() -> pd.DataFrame:
    """Synthetic matches with 3 seasons (for train/val/test splits)."""
    return _make_matches(n_seasons=3)


@pytest.fixture(scope="session")
def synthetic_3season_advanced(synthetic_3season_matches: pd.DataFrame) -> pd.DataFrame:
    return _make_advanced_stats(synthetic_3season_matches)


@pytest.fixture(scope="session")
def synthetic_3season_standings(synthetic_3season_matches: pd.DataFrame) -> pd.DataFrame:
    return _make_standings(synthetic_3season_matches)


# ================================================================
# PostgreSQL database fixtures for ETL integration tests
# ================================================================


@pytest.fixture(scope="module")
def test_db_connection() -> Generator:
    """
    Provide a PostgreSQL connection for ETL integration tests.

    This fixture:
    - Connects to the test database using environment variables
    - Initializes the schema if needed
    - Cleans up test data after each module
    - Skips tests if PostgreSQL is not available

    Environment variables required:
    - POSTGRES_HOST (default: localhost)
    - POSTGRES_PORT (default: 5432)
    - POSTGRES_DB (default: laliga_soccerdata_test)
    - POSTGRES_USER (default: postgres)
    - POSTGRES_PASSWORD (default: postgres)
    """
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # Get connection parameters from environment
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "laliga_soccerdata_test"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }

    # Try to connect to PostgreSQL
    try:
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    except psycopg2.OperationalError as e:
        pytest.skip(f"PostgreSQL not available: {e}")
        return

    # Yield connection to tests
    yield conn

    # Cleanup: truncate all tables after module tests complete
    try:
        cur = conn.cursor()
        # Get all tables in public schema
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename NOT LIKE 'pg_%'
        """)
        tables = cur.fetchall()

        # Truncate each table
        for (table_name,) in tables:
            if table_name != "etl_log":  # Keep ETL log for debugging
                cur.execute(f'TRUNCATE TABLE "{table_name}" CASCADE')

        cur.close()
    except Exception as e:
        print(f"Warning: Could not clean up test data: {e}")
    finally:
        conn.close()


@pytest.fixture(scope="module")
def test_db_with_schema(test_db_connection) -> Generator:
    """
    Provide a PostgreSQL connection with schema initialized.

    This fixture extends test_db_connection by ensuring the
    soccerdata schema (tables, views, etc.) is created.
    """
    from src.laliga_predictor.data.sd_db_init import init_soccerdata_database

    conn = test_db_connection

    # Initialize schema (idempotent - safe to call multiple times)
    try:
        init_soccerdata_database()
    except Exception as e:
        pytest.skip(f"Could not initialize test schema: {e}")
        return

    yield conn
