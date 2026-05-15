"""
Data loader for ML pipeline.

Loads raw match data, advanced stats, and standings from PostgreSQL
into pandas DataFrames for feature engineering.
"""

import logging

import pandas as pd
import psycopg2

from ..data.sd_db_init import get_sd_connection

logger = logging.getLogger(__name__)


def load_all_matches(conn: psycopg2.extensions.connection) -> pd.DataFrame:
    """Load all completed matches with team names and season info.

    Returns DataFrame with columns:
        match_id, season_code, match_date, home_team, away_team,
        home_team_id, away_team_id, home_score, away_score, result,
        home_shots, away_shots, home_shots_on_target, away_shots_on_target,
        home_corners, away_corners, home_fouls, away_fouls,
        home_yellow_cards, away_yellow_cards, home_red_cards, away_red_cards,
        venue, attendance
    """
    query = """
        SELECT
            m.id AS match_id,
            s.season_code,
            m.match_date,
            ht.canonical_name AS home_team,
            at.canonical_name AS away_team,
            m.home_team_id,
            m.away_team_id,
            m.home_score,
            m.away_score,
            m.result,
            m.home_shots,
            m.away_shots,
            m.home_shots_on_target,
            m.away_shots_on_target,
            m.home_corners,
            m.away_corners,
            m.home_fouls,
            m.away_fouls,
            m.home_yellow_cards,
            m.away_yellow_cards,
            m.home_red_cards,
            m.away_red_cards,
            m.venue,
            m.attendance
        FROM matches m
        JOIN seasons s ON m.season_id = s.id
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.home_score IS NOT NULL
        ORDER BY m.match_date, m.id
    """
    df = pd.read_sql_query(query, conn)
    df["match_date"] = pd.to_datetime(df["match_date"])
    logger.info(f"Loaded {len(df)} completed matches")
    return df


def load_advanced_stats(conn: psycopg2.extensions.connection) -> pd.DataFrame:
    """Load ESPN/FBref advanced stats per team per match.

    Returns DataFrame with columns:
        match_id, team_id, is_home, match_date, season_code,
        possession, sh, sot, sot_pct, passes_cmp, passes_att, passes_cmp_pct,
        tackles, tackles_won, interceptions, clearances, blocked_shots,
        crosses, crosses_cmp, crosses_cmp_pct, long_balls_cmp, long_balls_att,
        long_balls_cmp_pct, saves, corner_kicks, fouls_committed,
        cards_yellow, cards_red, offsides, ...
    """
    query = """
        SELECT
            mas.match_id,
            mas.team_id,
            mas.is_home,
            m.match_date,
            s.season_code,
            mas.possession,
            mas.sh,
            mas.sot,
            mas.sot_pct,
            mas.passes_cmp,
            mas.passes_att,
            mas.passes_cmp_pct,
            mas.tackles,
            mas.tackles_won,
            mas.tackles_won_pct,
            mas.interceptions,
            mas.clearances,
            mas.clearances_effective,
            mas.blocked_shots,
            mas.crosses,
            mas.crosses_cmp,
            mas.crosses_cmp_pct,
            mas.long_balls_cmp,
            mas.long_balls_att,
            mas.long_balls_cmp_pct,
            mas.saves,
            mas.corner_kicks,
            mas.fouls_committed,
            mas.cards_yellow,
            mas.cards_red,
            mas.offsides
        FROM match_advanced_stats mas
        JOIN matches m ON mas.match_id = m.id
        JOIN seasons s ON m.season_id = s.id
        WHERE m.home_score IS NOT NULL
        ORDER BY m.match_date, mas.match_id, mas.is_home DESC
    """
    df = pd.read_sql_query(query, conn)
    df["match_date"] = pd.to_datetime(df["match_date"])
    logger.info(f"Loaded {len(df)} advanced stats rows")
    return df


def load_standings(conn: psycopg2.extensions.connection) -> pd.DataFrame:
    """Load standings per matchweek.

    Returns DataFrame with columns:
        season_code, match_week, team_id, team, position,
        matches_played, wins, draws, losses,
        goals_for, goals_against, goal_difference, points
    """
    query = """
        SELECT
            s.season_code,
            st.match_week,
            st.team_id,
            t.canonical_name AS team,
            st.position,
            st.matches_played,
            st.wins,
            st.draws,
            st.losses,
            st.goals_for,
            st.goals_against,
            st.goal_difference,
            st.points
        FROM standings st
        JOIN seasons s ON st.season_id = s.id
        JOIN teams t ON st.team_id = t.id
        ORDER BY s.season_code, st.match_week, st.position
    """
    df = pd.read_sql_query(query, conn)
    logger.info(f"Loaded {len(df)} standings rows")
    return df


def load_all_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all data needed for feature engineering.

    Returns:
        (matches_df, advanced_stats_df, standings_df)
    """
    conn = get_sd_connection()
    try:
        matches = load_all_matches(conn)
        advanced = load_advanced_stats(conn)
        standings = load_standings(conn)
        return matches, advanced, standings
    finally:
        conn.close()
