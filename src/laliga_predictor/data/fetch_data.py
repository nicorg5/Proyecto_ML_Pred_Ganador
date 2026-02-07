"""
Data fetching script for LaLiga historical data.

This script fetches historical match data from API Football and stores it
in the PostgreSQL database. It handles rate limiting and can be run
incrementally across multiple days.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import execute_values

from ..config import get_settings
from .api_football_client import APIFootballClient

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches and stores LaLiga data from API Football."""

    def __init__(self):
        """Initialize the data fetcher."""
        self.settings = get_settings()
        self.api_client = APIFootballClient()
        self.db_conn = self._connect_db()
        self.request_count = 0

    def _connect_db(self) -> psycopg2.extensions.connection:
        """Connect to PostgreSQL database."""
        conn = psycopg2.connect(
            host=self.settings.DB_HOST,
            port=self.settings.DB_PORT,
            database=self.settings.DB_NAME,
            user=self.settings.DB_USER,
            password=self.settings.DB_PASSWORD,
        )
        logger.info(f"Connected to database: {self.settings.DB_NAME}")
        return conn

    def fetch_and_store_teams(self, season: int) -> None:
        """
        Fetch teams for a season and store in database.

        Args:
            season: Season year (e.g., 2024)
        """
        logger.info(f"Fetching teams for season {season}...")

        teams_data = self.api_client.get_teams(season)
        self.request_count += 1

        logger.info(f"Found {len(teams_data)} teams")

        # Prepare data for insertion
        teams_to_insert = []
        for team_data in teams_data:
            team = team_data["team"]
            teams_to_insert.append(
                (
                    team["id"],
                    team["name"],
                    team.get("code"),  # short_name
                    team.get("logo"),  # logo_url
                )
            )

        # Insert teams (on conflict do nothing - teams already exist)
        with self.db_conn.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO teams (id, name, short_name, logo_url)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    short_name = EXCLUDED.short_name,
                    logo_url = EXCLUDED.logo_url
                """,
                teams_to_insert,
            )
            self.db_conn.commit()
            logger.info(f"Stored {len(teams_to_insert)} teams")

    def fetch_and_store_fixtures(self, season: int) -> int:
        """
        Fetch all fixtures for a season and store in database.

        Args:
            season: Season year (e.g., 2024)

        Returns:
            Number of fixtures stored
        """
        logger.info(f"Fetching fixtures for season {season}...")

        # Get season_id from database
        with self.db_conn.cursor() as cursor:
            cursor.execute("SELECT id FROM seasons WHERE year = %s", (season,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Season {season} not found in database")
            season_id = result[0]

        # Fetch all fixtures (including not started, in progress, and finished)
        fixtures_data = self.api_client.get_fixtures_by_season(season)
        self.request_count += 1

        logger.info(f"Found {len(fixtures_data)} fixtures for season {season}")

        # Prepare data for insertion
        fixtures_to_insert = []
        for fixture in fixtures_data:
            fixture_info = fixture["fixture"]
            teams = fixture["teams"]
            goals = fixture["goals"]
            score = fixture["score"]

            # Parse date
            match_date = datetime.fromisoformat(
                fixture_info["date"].replace("Z", "+00:00")
            )

            # Determine result
            home_score = goals["home"]
            away_score = goals["away"]
            result = None
            if home_score is not None and away_score is not None:
                if home_score > away_score:
                    result = "H"
                elif home_score < away_score:
                    result = "A"
                else:
                    result = "D"

            fixtures_to_insert.append(
                (
                    fixture_info["id"],
                    season_id,
                    match_date,
                    fixture["league"].get("round", "").replace("Regular Season - ", ""),
                    fixture_info.get("venue", {}).get("name"),
                    fixture_info.get("referee"),
                    teams["home"]["id"],
                    teams["away"]["id"],
                    home_score,
                    away_score,
                    result,
                    fixture_info["status"]["short"],
                )
            )

        # Insert fixtures
        with self.db_conn.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO matches (
                    id, season_id, match_date, match_week, venue, referee,
                    home_team_id, away_team_id, home_score, away_score, result, status
                )
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    match_date = EXCLUDED.match_date,
                    match_week = EXCLUDED.match_week,
                    venue = EXCLUDED.venue,
                    referee = EXCLUDED.referee,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    result = EXCLUDED.result,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                fixtures_to_insert,
            )
            self.db_conn.commit()
            logger.info(f"Stored {len(fixtures_to_insert)} fixtures")

        return len(fixtures_to_insert)

    def fetch_and_store_statistics(self, season: int, limit: Optional[int] = None) -> int:
        """
        Fetch statistics for all finished matches in a season.

        Args:
            season: Season year (e.g., 2024)
            limit: Maximum number of matches to process (for rate limiting)

        Returns:
            Number of matches with statistics stored
        """
        logger.info(f"Fetching match statistics for season {season}...")

        # Get finished matches without statistics
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.id
                FROM matches m
                LEFT JOIN match_stats ms ON m.id = ms.match_id
                WHERE m.season_id = (SELECT id FROM seasons WHERE year = %s)
                  AND m.status = 'FT'
                  AND ms.match_id IS NULL
                ORDER BY m.match_date
                LIMIT %s
                """,
                (season, limit or 10000),
            )
            match_ids = [row[0] for row in cursor.fetchall()]

        logger.info(f"Found {len(match_ids)} matches needing statistics")

        if not match_ids:
            logger.info("No matches to process")
            return 0

        stats_stored = 0

        for idx, match_id in enumerate(match_ids, 1):
            try:
                logger.info(f"Fetching stats for match {match_id} ({idx}/{len(match_ids)})...")

                # Fetch statistics
                stats_data = self.api_client.get_fixture_statistics(match_id)
                self.request_count += 1

                if not stats_data or len(stats_data) < 2:
                    logger.warning(f"No statistics available for match {match_id}")
                    continue

                # Parse statistics for both teams
                self._store_match_statistics(match_id, stats_data)
                stats_stored += 1

                logger.info(
                    f"Stored statistics for match {match_id} "
                    f"({stats_stored}/{len(match_ids)} completed) "
                    f"[Total API requests: {self.request_count}]"
                )

                # Check rate limit
                if self.request_count >= 95:  # Leave some margin
                    logger.warning(
                        f"Approaching rate limit (95/100 requests). "
                        f"Stopping for today. Resume with --season {season}"
                    )
                    break

            except Exception as e:
                logger.error(f"Error fetching statistics for match {match_id}: {e}")
                continue

        return stats_stored

    def _store_match_statistics(self, match_id: int, stats_data: List[Dict[str, Any]]) -> None:
        """
        Store match statistics in database.

        Args:
            match_id: Match ID
            stats_data: Statistics data from API
        """
        # Extract statistics
        match_stats_to_update = []
        match_stats_detailed = []

        for team_stats in stats_data:
            team_id = team_stats["team"]["id"]
            is_home = None  # Will be determined from match data

            # Get match info to determine if team is home
            with self.db_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT home_team_id FROM matches WHERE id = %s",
                    (match_id,),
                )
                result = cursor.fetchone()
                if result:
                    is_home = result[0] == team_id

            statistics = {stat["type"]: stat["value"] for stat in team_stats["statistics"]}

            # Update main matches table with statistics
            prefix = "home" if is_home else "away"

            match_stats_to_update.append(
                {
                    "match_id": match_id,
                    "prefix": prefix,
                    "possession": self._parse_percentage(statistics.get("Ball Possession")),
                    "shots_total": self._parse_int(statistics.get("Total Shots")),
                    "shots_on_goal": self._parse_int(statistics.get("Shots on Goal")),
                    "corners": self._parse_int(statistics.get("Corner Kicks")),
                    "fouls": self._parse_int(statistics.get("Fouls")),
                    "yellow_cards": self._parse_int(statistics.get("Yellow Cards")),
                    "red_cards": self._parse_int(statistics.get("Red Cards")),
                }
            )

            # Detailed statistics for match_stats table
            match_stats_detailed.append(
                (
                    match_id,
                    team_id,
                    is_home,
                    self._parse_float(statistics.get("expected_goals")),  # xG (if available)
                    self._parse_int(statistics.get("Total passes")),
                    self._parse_int(statistics.get("Passes accurate")),
                    self._parse_percentage(statistics.get("Passes %")),
                    self._parse_int(statistics.get("Tackles")),
                    self._parse_int(statistics.get("Interceptions")),
                    self._parse_int(statistics.get("Blocked Shots")),
                    self._parse_int(statistics.get("Goalkeeper Saves")),
                    self._parse_int(statistics.get("Offsides")),
                )
            )

        # Update matches table with basic statistics
        with self.db_conn.cursor() as cursor:
            for stats in match_stats_to_update:
                cursor.execute(
                    f"""
                    UPDATE matches SET
                        {stats['prefix']}_possession = %s,
                        {stats['prefix']}_shots_total = %s,
                        {stats['prefix']}_shots_on_goal = %s,
                        {stats['prefix']}_corners = %s,
                        {stats['prefix']}_fouls = %s,
                        {stats['prefix']}_yellow_cards = %s,
                        {stats['prefix']}_red_cards = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        stats["possession"],
                        stats["shots_total"],
                        stats["shots_on_goal"],
                        stats["corners"],
                        stats["fouls"],
                        stats["yellow_cards"],
                        stats["red_cards"],
                        stats["match_id"],
                    ),
                )

            # Insert detailed statistics
            execute_values(
                cursor,
                """
                INSERT INTO match_stats (
                    match_id, team_id, is_home, expected_goals,
                    passes_total, passes_accurate, passes_accuracy,
                    tackles, interceptions, blocks, saves, offsides
                )
                VALUES %s
                ON CONFLICT (match_id, team_id) DO UPDATE SET
                    expected_goals = EXCLUDED.expected_goals,
                    passes_total = EXCLUDED.passes_total,
                    passes_accurate = EXCLUDED.passes_accurate,
                    passes_accuracy = EXCLUDED.passes_accuracy,
                    tackles = EXCLUDED.tackles,
                    interceptions = EXCLUDED.interceptions,
                    blocks = EXCLUDED.blocks,
                    saves = EXCLUDED.saves,
                    offsides = EXCLUDED.offsides
                """,
                match_stats_detailed,
            )

            self.db_conn.commit()

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        """Parse integer value from API response."""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        """Parse float value from API response."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_percentage(value: Any) -> Optional[float]:
        """Parse percentage value (e.g., '65%' -> 65.0)."""
        if value is None or value == "":
            return None
        try:
            if isinstance(value, str) and "%" in value:
                return float(value.replace("%", ""))
            return float(value)
        except (ValueError, TypeError):
            return None

    def close(self) -> None:
        """Close database connection and API client."""
        self.db_conn.close()
        self.api_client.close()
        logger.info("Closed connections")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch LaLiga historical data")
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year to fetch (2022, 2023, or 2024)",
    )
    parser.add_argument(
        "--stats-limit",
        type=int,
        default=30,
        help="Maximum number of matches to fetch statistics for (default: 30)",
    )
    parser.add_argument(
        "--skip-teams",
        action="store_true",
        help="Skip fetching teams (if already done)",
    )
    parser.add_argument(
        "--skip-fixtures",
        action="store_true",
        help="Skip fetching fixtures (if already done)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only fetch match statistics (skip teams and fixtures)",
    )

    args = parser.parse_args()

    # Validate season
    if args.season not in [2022, 2023, 2024]:
        logger.error("Season must be 2022, 2023, or 2024 (free plan limitation)")
        return

    fetcher = DataFetcher()

    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting data fetch for season {args.season}")
        logger.info(f"{'='*60}\n")

        # Step 1: Fetch teams
        if not args.skip_teams and not args.stats_only:
            fetcher.fetch_and_store_teams(args.season)
            logger.info(f"API requests used: {fetcher.request_count}/100\n")

        # Step 2: Fetch fixtures
        if not args.skip_fixtures and not args.stats_only:
            fetcher.fetch_and_store_fixtures(args.season)
            logger.info(f"API requests used: {fetcher.request_count}/100\n")

        # Step 3: Fetch match statistics
        if not args.stats_only or args.stats_only:
            stats_count = fetcher.fetch_and_store_statistics(
                args.season, limit=args.stats_limit
            )
            logger.info(f"\nStored statistics for {stats_count} matches")
            logger.info(f"Total API requests used: {fetcher.request_count}/100")

        logger.info(f"\n{'='*60}")
        logger.info("Data fetch completed successfully!")
        logger.info(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error during data fetch: {e}")
        raise
    finally:
        fetcher.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()