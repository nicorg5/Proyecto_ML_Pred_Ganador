"""
ETL Pipeline for soccerdata-based data loading.

Orchestrates data extraction from MatchHistory, ESPN, and FBref,
transforms it with team name normalization, and loads into PostgreSQL.

Pipeline steps (in order):
  1. load_match_history()     - Fast CSV, no rate limits. Base match data.
  2. load_espn_match_stats()  - Enriches matches with ESPN advanced stats.
  3. load_fbref_schedule()    - (Optional) Enriches with xG, venue, attendance.
  4. load_fbref_team_match_stats() - (Optional) FBref advanced stats.
  5. compute_standings()      - League table per matchweek from results.
  6. load_player_match_stats() - (Optional) Player-level stats.
  7. load_shot_events()       - (Optional) Per-shot xG data.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import psycopg2

from ..config import get_settings
from .sd_db_init import get_sd_connection
from .soccerdata_client import SoccerdataClient
from .team_names import TEAM_NAME_MAP, normalize_team_name

logger = logging.getLogger(__name__)


class SoccerdataETL:
    """ETL pipeline for loading soccerdata into PostgreSQL."""

    def __init__(self, seasons: Optional[list[str]] = None) -> None:
        self.settings = get_settings()
        self.client = SoccerdataClient(seasons=seasons)
        self.conn = get_sd_connection()
        self.conn.autocommit = False
        self._ensure_teams_and_mappings()

    # ================================================================
    # Setup
    # ================================================================

    def _ensure_teams_and_mappings(self) -> None:
        """Insert all known teams and name mappings from TEAM_NAME_MAP."""
        with self.conn.cursor() as cur:
            for canonical, sources in TEAM_NAME_MAP.items():
                cur.execute(
                    """INSERT INTO teams (canonical_name)
                       VALUES (%s)
                       ON CONFLICT (canonical_name) DO NOTHING""",
                    (canonical,),
                )
                cur.execute(
                    "SELECT id FROM teams WHERE canonical_name = %s", (canonical,)
                )
                team_id = cur.fetchone()[0]

                for source, source_name in sources.items():
                    cur.execute(
                        """INSERT INTO team_name_mapping (team_id, source, source_name)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (source, source_name) DO NOTHING""",
                        (team_id, source, source_name),
                    )

            self.conn.commit()
        logger.info(f"Ensured {len(TEAM_NAME_MAP)} teams and name mappings")

    # ================================================================
    # Helper methods
    # ================================================================

    def _get_team_id(self, name: str, source: str) -> int:
        """Resolve a source-specific team name to canonical team_id."""
        canonical = normalize_team_name(name, source)
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM teams WHERE canonical_name = %s", (canonical,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"Team '{canonical}' not found in database")
            return result[0]

    def _get_season_id(self, season_code: str) -> int:
        """Get season_id from season_code."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM seasons WHERE season_code = %s", (season_code,)
            )
            result = cur.fetchone()
            if not result:
                raise ValueError(f"Season '{season_code}' not found in database")
            return result[0]

    def _log_etl(
        self,
        source: str,
        operation: str,
        season_code: str,
        status: str,
        rows: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Log an ETL operation."""
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO etl_log
                   (source, operation, season_code, status, rows_affected,
                    error_message, completed_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    source,
                    operation,
                    season_code,
                    status,
                    rows,
                    error,
                    datetime.now() if status != "started" else None,
                ),
            )
            self.conn.commit()

    def _is_etl_completed(
        self, source: str, operation: str, season_code: str
    ) -> bool:
        """Check if an ETL operation has already completed."""
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM etl_log
                   WHERE source = %s AND operation = %s AND season_code = %s
                     AND status = 'completed'""",
                (source, operation, season_code),
            )
            return cur.fetchone()[0] > 0

    def _find_match_id(
        self, season_id: int, match_date: object, home_team_id: int, away_team_id: int
    ) -> Optional[int]:
        """Find a match by season, date (with +/-1 day tolerance), and teams."""
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT id FROM matches
                   WHERE season_id = %s
                     AND match_date BETWEEN %s AND %s
                     AND home_team_id = %s
                     AND away_team_id = %s
                   LIMIT 1""",
                (
                    season_id,
                    match_date - timedelta(days=1),
                    match_date + timedelta(days=1),
                    home_team_id,
                    away_team_id,
                ),
            )
            result = cur.fetchone()
            return result[0] if result else None

    @staticmethod
    def _safe_int(value: object) -> Optional[int]:
        if pd.isna(value) or value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value: object) -> Optional[float]:
        if pd.isna(value) or value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    # ================================================================
    # STEP 1: MatchHistory (Football-Data.co.uk)
    # ================================================================

    def load_match_history(self, seasons: Optional[list[str]] = None) -> int:
        """Load match data from Football-Data.co.uk.

        Primary base data source: CSV-based, no rate limiting.
        Populates matches with scores, shots, corners, fouls, cards, HT scores.
        """
        total_loaded = 0
        target_seasons = seasons or self.client.seasons

        for season in target_seasons:
            if self._is_etl_completed("match_history", "games", season):
                logger.info(f"MatchHistory games for {season} already loaded, skipping")
                continue

            try:
                self._log_etl("match_history", "games", season, "started")
                df = self.client.fetch_match_history_games(seasons=[season])

                if df.empty:
                    logger.warning(f"No MatchHistory data for season {season}")
                    self._log_etl("match_history", "games", season, "completed", 0)
                    continue

                count = self._store_match_history(df, season)
                total_loaded += count
                self._log_etl("match_history", "games", season, "completed", count)
                logger.info(f"Loaded {count} matches from MatchHistory for {season}")

            except Exception as e:
                logger.error(f"Error loading MatchHistory for {season}: {e}")
                self._log_etl("match_history", "games", season, "failed", error=str(e))
                raise

        return total_loaded

    def _store_match_history(self, df: pd.DataFrame, season_code: str) -> int:
        """Transform and store MatchHistory DataFrame into matches table."""
        season_id = self._get_season_id(season_code)
        rows_inserted = 0

        df_reset = df.reset_index()

        with self.conn.cursor() as cur:
            for _, row in df_reset.iterrows():
                try:
                    home_name = row.get("home_team", "")
                    away_name = row.get("away_team", "")

                    if not home_name or not away_name:
                        logger.warning("Missing team names in row, skipping")
                        continue

                    home_team_id = self._get_team_id(str(home_name), "match_history")
                    away_team_id = self._get_team_id(str(away_name), "match_history")

                    match_date = pd.to_datetime(row.get("date")).date()

                    ftr = row.get("FTR", "")
                    htr = row.get("HTR", "")

                    cur.execute(
                        """INSERT INTO matches (
                            season_id, match_date, home_team_id, away_team_id,
                            home_score, away_score, result,
                            ht_home_score, ht_away_score, ht_result,
                            home_shots, away_shots,
                            home_shots_on_target, away_shots_on_target,
                            home_corners, away_corners,
                            home_fouls, away_fouls,
                            home_yellow_cards, away_yellow_cards,
                            home_red_cards, away_red_cards,
                            source_match_history
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, TRUE
                        )
                        ON CONFLICT (season_id, match_date, home_team_id, away_team_id)
                        DO UPDATE SET
                            home_score = EXCLUDED.home_score,
                            away_score = EXCLUDED.away_score,
                            result = EXCLUDED.result,
                            ht_home_score = EXCLUDED.ht_home_score,
                            ht_away_score = EXCLUDED.ht_away_score,
                            ht_result = EXCLUDED.ht_result,
                            home_shots = EXCLUDED.home_shots,
                            away_shots = EXCLUDED.away_shots,
                            home_shots_on_target = EXCLUDED.home_shots_on_target,
                            away_shots_on_target = EXCLUDED.away_shots_on_target,
                            home_corners = EXCLUDED.home_corners,
                            away_corners = EXCLUDED.away_corners,
                            home_fouls = EXCLUDED.home_fouls,
                            away_fouls = EXCLUDED.away_fouls,
                            home_yellow_cards = EXCLUDED.home_yellow_cards,
                            away_yellow_cards = EXCLUDED.away_yellow_cards,
                            home_red_cards = EXCLUDED.home_red_cards,
                            away_red_cards = EXCLUDED.away_red_cards,
                            source_match_history = TRUE,
                            updated_at = CURRENT_TIMESTAMP""",
                        (
                            season_id,
                            match_date,
                            home_team_id,
                            away_team_id,
                            self._safe_int(row.get("FTHG")),
                            self._safe_int(row.get("FTAG")),
                            str(ftr) if ftr and not pd.isna(ftr) else None,
                            self._safe_int(row.get("HTHG")),
                            self._safe_int(row.get("HTAG")),
                            str(htr) if htr and not pd.isna(htr) else None,
                            self._safe_int(row.get("HS")),
                            self._safe_int(row.get("AS")),
                            self._safe_int(row.get("HST")),
                            self._safe_int(row.get("AST")),
                            self._safe_int(row.get("HC")),
                            self._safe_int(row.get("AC")),
                            self._safe_int(row.get("HF")),
                            self._safe_int(row.get("AF")),
                            self._safe_int(row.get("HY")),
                            self._safe_int(row.get("AY")),
                            self._safe_int(row.get("HR")),
                            self._safe_int(row.get("AR")),
                        ),
                    )
                    rows_inserted += 1

                except KeyError as e:
                    logger.warning(f"Unknown team in MatchHistory row: {e}")
                    continue

            self.conn.commit()

        return rows_inserted

    # ================================================================
    # STEP 2: ESPN Match Stats (advanced stats enrichment)
    # ================================================================

    # ESPN matchsheet column -> DB column mapping
    ESPN_COLUMN_MAP: dict[str, str] = {
        "possession_pct": "possession",
        "total_shots": "sh",
        "shots_on_target": "sot",
        "shot_pct": "sot_pct",
        "penalty_kick_goals": "pk",
        "penalty_kick_shots": "pk_att",
        "accurate_passes": "passes_cmp",
        "total_passes": "passes_att",
        "pass_pct": "passes_cmp_pct",
        "total_crosses": "crosses",
        "accurate_crosses": "crosses_cmp",
        "cross_pct": "crosses_cmp_pct",
        "effective_tackles": "tackles_won",
        "total_tackles": "tackles",
        "tackle_pct": "tackles_won_pct",
        "interceptions": "interceptions",
        "effective_clearance": "clearances_effective",
        "total_clearance": "clearances",
        "blocked_shots": "blocked_shots",
        "accurate_long_balls": "long_balls_cmp",
        "total_long_balls": "long_balls_att",
        "longball_pct": "long_balls_cmp_pct",
        "saves": "saves",
        "won_corners": "corner_kicks",
        "fouls_committed": "fouls_committed",
        "yellow_cards": "cards_yellow",
        "red_cards": "cards_red",
        "offsides": "offsides",
    }

    def load_espn_match_stats(self, seasons: Optional[list[str]] = None) -> int:
        """Load ESPN match stats, enriching existing matches with advanced stats.

        Fetches ESPN schedule to get game_ids, then fetches each matchsheet
        and populates match_advanced_stats.
        """
        total = 0
        target_seasons = seasons or self.client.seasons

        for season in target_seasons:
            if self._is_etl_completed("espn", "match_stats", season):
                logger.info(f"ESPN match stats for {season} already loaded, skipping")
                continue

            try:
                self._log_etl("espn", "match_stats", season, "started")
                count = self._process_espn_season(season)
                total += count
                self._log_etl("espn", "match_stats", season, "completed", count)
                logger.info(f"Loaded ESPN stats for {count} matches in season {season}")
            except Exception as e:
                logger.error(f"Error loading ESPN stats for {season}: {e}")
                self._log_etl("espn", "match_stats", season, "failed", error=str(e))
                raise

        return total

    def _process_espn_season(self, season_code: str) -> int:
        """Process all ESPN matches for a single season."""
        season_id = self._get_season_id(season_code)

        # Fetch ESPN schedule to get game_ids
        schedule = self.client.fetch_espn_schedule(seasons=[season_code])
        if schedule.empty:
            logger.warning(f"No ESPN schedule for season {season_code}")
            return 0

        schedule_reset = schedule.reset_index()
        matches_processed = 0
        matches_skipped = 0

        for _, sched_row in schedule_reset.iterrows():
            game_id_raw = sched_row.get("game_id")
            if game_id_raw is None or pd.isna(game_id_raw):
                continue
            game_id = int(game_id_raw)

            home_name = str(sched_row.get("home_team", ""))
            away_name = str(sched_row.get("away_team", ""))
            match_date_raw = sched_row.get("date")

            if not home_name or not away_name:
                continue

            try:
                home_team_id = self._get_team_id(home_name, "espn")
                away_team_id = self._get_team_id(away_name, "espn")
            except KeyError as e:
                logger.warning(f"Unknown ESPN team: {e}")
                continue

            match_date = pd.to_datetime(match_date_raw).date()

            # Find the match in our DB (inserted by MatchHistory)
            match_id = self._find_match_id(
                season_id, match_date, home_team_id, away_team_id
            )
            if not match_id:
                matches_skipped += 1
                continue

            # Fetch matchsheet for this game
            try:
                matchsheet = self.client.fetch_espn_matchsheet(
                    match_id=game_id, seasons=[season_code]
                )
            except Exception as e:
                logger.debug(f"Error fetching ESPN matchsheet {game_id}: {e}")
                continue

            if matchsheet.empty:
                continue

            # Store ESPN game_id on the match
            self._update_match_espn_id(match_id, game_id)

            # Process each team row from the matchsheet
            ms_reset = matchsheet.reset_index()
            for _, ms_row in ms_reset.iterrows():
                team_name = str(ms_row.get("team", ""))
                if not team_name:
                    continue

                try:
                    team_id = self._get_team_id(team_name, "espn")
                except KeyError:
                    continue

                is_home_val = ms_row.get("is_home")
                is_home = bool(is_home_val) if not pd.isna(is_home_val) else (team_id == home_team_id)

                self._store_espn_team_stats(match_id, team_id, is_home, ms_row)

            # Store venue/attendance from ESPN on the match
            self._update_match_espn_venue(match_id, ms_reset)

            matches_processed += 1
            self.conn.commit()

            if matches_processed % 50 == 0:
                logger.info(
                    f"  ESPN progress: {matches_processed} matches processed"
                )

        if matches_skipped > 0:
            logger.info(
                f"  ESPN: {matches_skipped} matches not found in DB "
                f"(may not be in MatchHistory data)"
            )

        return matches_processed

    def _update_match_espn_id(self, match_id: int, game_id: int) -> None:
        """Store ESPN game_id on the match record."""
        with self.conn.cursor() as cur:
            cur.execute(
                """UPDATE matches SET
                    espn_game_id = %s,
                    source_espn = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s""",
                (str(game_id), match_id),
            )

    def _update_match_espn_venue(
        self, match_id: int, ms_reset: pd.DataFrame
    ) -> None:
        """Update match venue and attendance from ESPN data."""
        first_row = ms_reset.iloc[0] if len(ms_reset) > 0 else None
        if first_row is None:
            return

        venue = first_row.get("venue")
        attendance = self._safe_int(first_row.get("attendance"))

        if (venue and not pd.isna(venue)) or attendance:
            with self.conn.cursor() as cur:
                cur.execute(
                    """UPDATE matches SET
                        venue = COALESCE(%s, venue),
                        attendance = COALESCE(%s, attendance),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s""",
                    (
                        str(venue) if venue and not pd.isna(venue) else None,
                        attendance,
                        match_id,
                    ),
                )

    def _store_espn_team_stats(
        self, match_id: int, team_id: int, is_home: bool, row: pd.Series
    ) -> None:
        """Store ESPN per-team stats into match_advanced_stats."""
        # Build column values from ESPN data
        set_parts = []
        values = []

        for espn_col, db_col in self.ESPN_COLUMN_MAP.items():
            val = row.get(espn_col)
            if val is not None and not pd.isna(val):
                set_parts.append(f"{db_col} = %s")
                values.append(self._safe_float(val))

        if not set_parts:
            return

        with self.conn.cursor() as cur:
            # Ensure row exists
            cur.execute(
                """INSERT INTO match_advanced_stats (match_id, team_id, is_home)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (match_id, team_id) DO NOTHING""",
                (match_id, team_id, is_home),
            )

            # Update with ESPN stats
            set_clause = ", ".join(set_parts)
            update_sql = (
                f"UPDATE match_advanced_stats SET {set_clause} "
                f"WHERE match_id = %s AND team_id = %s"
            )
            values.extend([match_id, team_id])
            cur.execute(update_sql, values)

    # ================================================================
    # STEP 3: FBref Schedule (xG enrichment) - Optional
    # ================================================================

    def load_fbref_schedule(self, seasons: Optional[list[str]] = None) -> int:
        """Load FBref schedule data, enriching existing matches with xG."""
        total_updated = 0
        target_seasons = seasons or self.client.seasons

        for season in target_seasons:
            if self._is_etl_completed("fbref", "schedule", season):
                logger.info(f"FBref schedule for {season} already loaded, skipping")
                continue

            try:
                self._log_etl("fbref", "schedule", season, "started")
                df = self.client.fetch_schedule(seasons=[season])

                if df.empty:
                    logger.warning(f"No FBref schedule data for season {season}")
                    self._log_etl("fbref", "schedule", season, "completed", 0)
                    continue

                count = self._store_fbref_schedule(df, season)
                total_updated += count
                self._log_etl("fbref", "schedule", season, "completed", count)
                logger.info(f"Enriched {count} matches with FBref schedule for {season}")

            except Exception as e:
                logger.error(f"Error loading FBref schedule for {season}: {e}")
                self._log_etl("fbref", "schedule", season, "failed", error=str(e))
                raise

        return total_updated

    def _store_fbref_schedule(self, df: pd.DataFrame, season_code: str) -> int:
        """Enrich existing matches with FBref schedule data (xG, venue, etc)."""
        season_id = self._get_season_id(season_code)
        rows_updated = 0

        df_reset = df.reset_index()

        with self.conn.cursor() as cur:
            for _, row in df_reset.iterrows():
                try:
                    home_name = row.get("home_team", "")
                    away_name = row.get("away_team", "")

                    if not home_name or not away_name:
                        continue

                    home_team_id = self._get_team_id(str(home_name), "fbref")
                    away_team_id = self._get_team_id(str(away_name), "fbref")

                    match_date = pd.to_datetime(row.get("date")).date()

                    match_id = self._find_match_id(
                        season_id, match_date, home_team_id, away_team_id
                    )

                    home_xg = self._safe_float(row.get("home_xg"))
                    away_xg = self._safe_float(row.get("away_xg"))
                    venue = row.get("venue")
                    attendance = self._safe_int(row.get("attendance"))
                    referee = row.get("referee")
                    game_id = row.get("game_id") or row.get("match_report")
                    match_week = row.get("week")

                    if match_id:
                        # Update existing match
                        cur.execute(
                            """UPDATE matches SET
                                home_xg = COALESCE(%s, home_xg),
                                away_xg = COALESCE(%s, away_xg),
                                venue = COALESCE(%s, venue),
                                attendance = COALESCE(%s, attendance),
                                referee = COALESCE(%s, referee),
                                fbref_match_id = COALESCE(%s, fbref_match_id),
                                match_week = COALESCE(%s, match_week),
                                source_fbref = TRUE,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s""",
                            (
                                home_xg,
                                away_xg,
                                venue if venue and not pd.isna(venue) else None,
                                attendance,
                                referee if referee and not pd.isna(referee) else None,
                                str(game_id) if game_id and not pd.isna(game_id) else None,
                                str(match_week) if match_week and not pd.isna(match_week) else None,
                                match_id,
                            ),
                        )
                    else:
                        # Insert new match (FBref has data not in MatchHistory)
                        score = row.get("score")
                        home_score = None
                        away_score = None
                        result = None
                        if score and not pd.isna(score) and "–" in str(score):
                            parts = str(score).split("–")
                            home_score = self._safe_int(parts[0])
                            away_score = self._safe_int(parts[1])
                            if home_score is not None and away_score is not None:
                                if home_score > away_score:
                                    result = "H"
                                elif home_score < away_score:
                                    result = "A"
                                else:
                                    result = "D"

                        cur.execute(
                            """INSERT INTO matches (
                                season_id, match_date, home_team_id, away_team_id,
                                home_score, away_score, result,
                                home_xg, away_xg, venue, attendance, referee,
                                fbref_match_id, match_week, source_fbref
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                            ON CONFLICT (season_id, match_date, home_team_id, away_team_id)
                            DO UPDATE SET
                                home_xg = COALESCE(EXCLUDED.home_xg, matches.home_xg),
                                away_xg = COALESCE(EXCLUDED.away_xg, matches.away_xg),
                                venue = COALESCE(EXCLUDED.venue, matches.venue),
                                attendance = COALESCE(EXCLUDED.attendance, matches.attendance),
                                referee = COALESCE(EXCLUDED.referee, matches.referee),
                                fbref_match_id = COALESCE(EXCLUDED.fbref_match_id, matches.fbref_match_id),
                                match_week = COALESCE(EXCLUDED.match_week, matches.match_week),
                                source_fbref = TRUE,
                                updated_at = CURRENT_TIMESTAMP""",
                            (
                                season_id,
                                match_date,
                                home_team_id,
                                away_team_id,
                                home_score,
                                away_score,
                                result,
                                home_xg,
                                away_xg,
                                venue if venue and not pd.isna(venue) else None,
                                attendance,
                                referee if referee and not pd.isna(referee) else None,
                                str(game_id) if game_id and not pd.isna(game_id) else None,
                                str(match_week) if match_week and not pd.isna(match_week) else None,
                            ),
                        )

                    rows_updated += 1

                except KeyError as e:
                    logger.warning(f"Unknown team in FBref schedule: {e}")
                    continue

            self.conn.commit()

        return rows_updated

    # ================================================================
    # STEP 3: FBref Team Match Stats (Advanced stats)
    # ================================================================

    # Column mapping: FBref DataFrame column -> DB column name
    # Organized by stat_type
    STAT_COLUMN_MAP: dict[str, dict[str, str]] = {
        "schedule": {
            "GF": "goals_for",
            "GA": "goals_against",
            "Poss": "possession",
            "Formation": "formation",
        },
        "shooting": {
            "Sh": "sh",
            "SoT": "sot",
            "SoT%": "sot_pct",
            "G/Sh": "g_per_sh",
            "G/SoT": "g_per_sot",
            "FK": "fk",
            "PK": "pk",
            "PKatt": "pk_att",
            "xG": "xg",
            "npxG": "npxg",
            "npxG/Sh": "npxg_per_sh",
            "G-xG": "g_minus_xg",
        },
        "passing": {
            "Cmp": "passes_cmp",
            "Att": "passes_att",
            "Cmp%": "passes_cmp_pct",
            "TotDist": "passes_tot_dist",
            "PrgDist": "passes_prg_dist",
            "Ast": "assists",
            "xAG": "xag",
            "xA": "xa",
            "KP": "key_passes",
            "1/3": "passes_final_third",
            "PPA": "passes_penalty_area",
            "CrsPA": "crosses_penalty_area",
            "PrgP": "progressive_passes",
        },
        "passing_types": {
            "Live": "passes_live",
            "Dead": "passes_dead",
            "FK": "passes_fk",
            "TB": "through_balls",
            "Sw": "switches",
            "Crs": "crosses",
            "TI": "throw_ins",
            "CK": "corner_kicks",
            "In": "corner_kicks_in",
            "Out": "corner_kicks_out",
            "Str": "corner_kicks_straight",
        },
        "goal_shot_creation": {
            "SCA": "sca",
            "SCA90": "sca_per90",
            "GCA": "gca",
            "GCA90": "gca_per90",
        },
        "defense": {
            "Tkl": "tackles",
            "TklW": "tackles_won",
            "Def 3rd": "tackles_def_3rd",
            "Mid 3rd": "tackles_mid_3rd",
            "Att 3rd": "tackles_att_3rd",
            "Lost": "challenges_lost",
            "Blocks": "blocks",
            "Sh": "blocked_shots",
            "Pass": "blocked_passes",
            "Int": "interceptions",
            "Clr": "clearances",
            "Err": "errors",
        },
        "possession": {
            "Touches": "touches",
            "Def Pen": "touches_def_pen",
            "Def 3rd": "touches_def_3rd",
            "Mid 3rd": "touches_mid_3rd",
            "Att 3rd": "touches_att_3rd",
            "Att Pen": "touches_att_pen",
            "Att": "take_ons_att",
            "Succ": "take_ons_succ",
            "Succ%": "take_ons_succ_pct",
            "Carries": "carries",
            "TotDist": "carries_tot_dist",
            "PrgDist": "carries_prg_dist",
            "PrgC": "progressive_carries",
            "1/3": "carries_final_third",
            "CPA": "carries_penalty_area",
            "Mis": "miscontrols",
            "Dis": "dispossessed",
            "Rec": "passes_received",
            "PrgR": "progressive_passes_rec",
        },
        "misc": {
            "CrdY": "cards_yellow",
            "CrdR": "cards_red",
            "2CrdY": "cards_second_yellow",
            "Fls": "fouls_committed",
            "Fld": "fouls_drawn",
            "Off": "offsides",
            "PKwon": "pens_won",
            "PKcon": "pens_conceded",
            "OG": "own_goals",
            "Recov": "ball_recoveries",
            "Won": "aerials_won",
            "Lost": "aerials_lost",
            "Won%": "aerials_won_pct",
        },
    }

    def load_fbref_team_match_stats(
        self,
        stat_types: Optional[list[str]] = None,
        seasons: Optional[list[str]] = None,
    ) -> int:
        """Load advanced team match stats from FBref into match_advanced_stats.

        Iterates through stat_types and populates the wide table.
        """
        if stat_types is None:
            stat_types = [
                "schedule",
                "shooting",
                "passing",
                "passing_types",
                "goal_shot_creation",
                "defense",
                "possession",
                "misc",
            ]

        total = 0
        target_seasons = seasons or self.client.seasons

        for stat_type in stat_types:
            for season in target_seasons:
                etl_key = f"team_match_stats_{stat_type}"
                if self._is_etl_completed("fbref", etl_key, season):
                    logger.info(f"FBref {stat_type} for {season} already loaded")
                    continue

                try:
                    self._log_etl("fbref", etl_key, season, "started")
                    df = self.client.fetch_team_match_stats(
                        stat_type, seasons=[season]
                    )
                    count = self._store_team_match_stats(df, stat_type, season)
                    total += count
                    self._log_etl("fbref", etl_key, season, "completed", count)
                    logger.info(
                        f"Loaded {count} rows for FBref {stat_type} season {season}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error loading FBref {stat_type} for {season}: {e}"
                    )
                    self._log_etl("fbref", etl_key, season, "failed", error=str(e))
                    continue

        return total

    def _store_team_match_stats(
        self, df: pd.DataFrame, stat_type: str, season_code: str
    ) -> int:
        """Store team match stats, updating appropriate columns by stat_type."""
        season_id = self._get_season_id(season_code)
        column_map = self.STAT_COLUMN_MAP.get(stat_type, {})

        if not column_map:
            logger.warning(f"No column mapping for stat_type={stat_type}")
            return 0

        rows_stored = 0
        df_reset = df.reset_index()

        with self.conn.cursor() as cur:
            for _, row in df_reset.iterrows():
                try:
                    team_name = row.get("team", "")
                    if not team_name:
                        continue

                    team_id = self._get_team_id(str(team_name), "fbref")

                    # Get match date from the row
                    match_date = pd.to_datetime(row.get("date")).date()

                    # Determine if home or away from the venue column
                    venue = row.get("venue", "")
                    is_home = str(venue).lower() == "home" if venue else True

                    # Find opponent to identify the match
                    opponent = row.get("opponent", "")
                    if opponent:
                        opponent_id = self._get_team_id(str(opponent), "fbref")
                        if is_home:
                            match_id = self._find_match_id(
                                season_id, match_date, team_id, opponent_id
                            )
                        else:
                            match_id = self._find_match_id(
                                season_id, match_date, opponent_id, team_id
                            )
                    else:
                        match_id = None

                    if not match_id:
                        logger.debug(
                            f"No match found for {team_name} on {match_date}, skipping"
                        )
                        continue

                    # Build the SET clause dynamically based on available columns
                    set_parts = []
                    values = []
                    for fbref_col, db_col in column_map.items():
                        val = row.get(fbref_col)
                        if val is not None and not pd.isna(val):
                            if db_col == "formation":
                                set_parts.append(f"{db_col} = %s")
                                values.append(str(val))
                            else:
                                set_parts.append(f"{db_col} = %s")
                                values.append(self._safe_float(val))

                    if not set_parts:
                        continue

                    # INSERT or UPDATE
                    set_clause = ", ".join(set_parts)
                    update_clause = ", ".join(
                        f"{p.split(' = ')[0]} = EXCLUDED.{p.split(' = ')[0]}"
                        for p in set_parts
                    )

                    # First ensure a row exists
                    cur.execute(
                        """INSERT INTO match_advanced_stats (match_id, team_id, is_home)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (match_id, team_id) DO NOTHING""",
                        (match_id, team_id, is_home),
                    )

                    # Then update the specific columns
                    if set_parts:
                        update_sql = (
                            f"UPDATE match_advanced_stats SET {set_clause} "
                            f"WHERE match_id = %s AND team_id = %s"
                        )
                        values.extend([match_id, team_id])
                        cur.execute(update_sql, values)

                    rows_stored += 1

                except KeyError as e:
                    logger.warning(f"Unknown team in FBref stats: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing FBref stats row: {e}")
                    continue

            self.conn.commit()

        return rows_stored

    # ================================================================
    # STEP 4: Compute Standings
    # ================================================================

    def compute_standings(self, seasons: Optional[list[str]] = None) -> int:
        """Compute league standings per matchweek from match results."""
        total = 0
        target_seasons = seasons or self.client.seasons

        for season in target_seasons:
            if self._is_etl_completed("computed", "standings", season):
                logger.info(f"Standings for {season} already computed, skipping")
                continue

            try:
                self._log_etl("computed", "standings", season, "started")
                count = self._compute_season_standings(season)
                total += count
                self._log_etl("computed", "standings", season, "completed", count)
                logger.info(f"Computed {count} standing rows for season {season}")
            except Exception as e:
                logger.error(f"Error computing standings for {season}: {e}")
                self._log_etl(
                    "computed", "standings", season, "failed", error=str(e)
                )
                raise

        return total

    def _compute_season_standings(self, season_code: str) -> int:
        """Compute standings for a single season from match results."""
        season_id = self._get_season_id(season_code)
        rows_inserted = 0

        with self.conn.cursor() as cur:
            # Get all finished matches ordered by date
            cur.execute(
                """SELECT id, match_date, home_team_id, away_team_id,
                          home_score, away_score, result
                   FROM matches
                   WHERE season_id = %s AND home_score IS NOT NULL
                   ORDER BY match_date, id""",
                (season_id,),
            )
            matches = cur.fetchall()

            if not matches:
                return 0

            # Track cumulative stats per team
            team_stats: dict[int, dict[str, int]] = {}

            # Assign matchweeks (every ~10 matches = 1 matchweek in La Liga)
            current_week = 1
            matches_in_week = 0

            for match_row in matches:
                _, _, home_id, away_id, home_score, away_score, result = match_row

                # Ensure team entries exist
                for tid in [home_id, away_id]:
                    if tid not in team_stats:
                        team_stats[tid] = {
                            "mp": 0, "w": 0, "d": 0, "l": 0,
                            "gf": 0, "ga": 0,
                        }

                # Update home team
                team_stats[home_id]["mp"] += 1
                team_stats[home_id]["gf"] += home_score
                team_stats[home_id]["ga"] += away_score
                if result == "H":
                    team_stats[home_id]["w"] += 1
                elif result == "D":
                    team_stats[home_id]["d"] += 1
                else:
                    team_stats[home_id]["l"] += 1

                # Update away team
                team_stats[away_id]["mp"] += 1
                team_stats[away_id]["gf"] += away_score
                team_stats[away_id]["ga"] += home_score
                if result == "A":
                    team_stats[away_id]["w"] += 1
                elif result == "D":
                    team_stats[away_id]["d"] += 1
                else:
                    team_stats[away_id]["l"] += 1

                matches_in_week += 1

                # Snapshot standings every 10 matches (1 matchweek)
                if matches_in_week >= 10:
                    rows_inserted += self._insert_standings_snapshot(
                        cur, season_id, current_week, team_stats
                    )
                    current_week += 1
                    matches_in_week = 0

            # Final snapshot if there are remaining matches
            if matches_in_week > 0:
                rows_inserted += self._insert_standings_snapshot(
                    cur, season_id, current_week, team_stats
                )

            self.conn.commit()

        return rows_inserted

    def _insert_standings_snapshot(
        self,
        cur: psycopg2.extensions.cursor,
        season_id: int,
        match_week: int,
        team_stats: dict[int, dict[str, int]],
    ) -> int:
        """Insert a standings snapshot for the given matchweek."""
        # Sort teams by points (then GD, then GF)
        sorted_teams = sorted(
            team_stats.items(),
            key=lambda x: (
                x[1]["w"] * 3 + x[1]["d"],
                x[1]["gf"] - x[1]["ga"],
                x[1]["gf"],
            ),
            reverse=True,
        )

        rows = 0
        for position, (team_id, stats) in enumerate(sorted_teams, 1):
            points = stats["w"] * 3 + stats["d"]
            gd = stats["gf"] - stats["ga"]

            cur.execute(
                """INSERT INTO standings
                   (season_id, match_week, team_id, position,
                    matches_played, wins, draws, losses,
                    goals_for, goals_against, goal_difference, points)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (season_id, match_week, team_id)
                   DO UPDATE SET
                       position = EXCLUDED.position,
                       matches_played = EXCLUDED.matches_played,
                       wins = EXCLUDED.wins,
                       draws = EXCLUDED.draws,
                       losses = EXCLUDED.losses,
                       goals_for = EXCLUDED.goals_for,
                       goals_against = EXCLUDED.goals_against,
                       goal_difference = EXCLUDED.goal_difference,
                       points = EXCLUDED.points""",
                (
                    season_id, match_week, team_id, position,
                    stats["mp"], stats["w"], stats["d"], stats["l"],
                    stats["gf"], stats["ga"], gd, points,
                ),
            )
            rows += 1

        return rows

    # ================================================================
    # STEP 5: Player Match Stats (Optional)
    # ================================================================

    def load_player_match_stats(self, seasons: Optional[list[str]] = None) -> int:
        """Load player-level match stats from FBref."""
        total = 0
        target_seasons = seasons or self.client.seasons

        for season in target_seasons:
            if self._is_etl_completed("fbref", "player_match_stats", season):
                logger.info(f"FBref player stats for {season} already loaded")
                continue

            try:
                self._log_etl("fbref", "player_match_stats", season, "started")
                df = self.client.fetch_player_match_stats(
                    stat_type="summary", seasons=[season]
                )

                if df.empty:
                    self._log_etl("fbref", "player_match_stats", season, "completed", 0)
                    continue

                count = self._store_player_match_stats(df, season)
                total += count
                self._log_etl(
                    "fbref", "player_match_stats", season, "completed", count
                )
                logger.info(f"Loaded {count} player stat rows for {season}")
            except Exception as e:
                logger.error(f"Error loading player stats for {season}: {e}")
                self._log_etl(
                    "fbref", "player_match_stats", season, "failed", error=str(e)
                )
                continue

        return total

    def _store_player_match_stats(
        self, df: pd.DataFrame, season_code: str
    ) -> int:
        """Store player match stats into match_player_stats table."""
        season_id = self._get_season_id(season_code)
        rows_stored = 0
        df_reset = df.reset_index()

        with self.conn.cursor() as cur:
            for _, row in df_reset.iterrows():
                try:
                    team_name = row.get("team", "")
                    if not team_name:
                        continue

                    team_id = self._get_team_id(str(team_name), "fbref")
                    match_date = pd.to_datetime(row.get("date")).date()

                    venue = row.get("venue", "")
                    is_home = str(venue).lower() == "home" if venue else True

                    opponent = row.get("opponent", "")
                    if opponent:
                        opponent_id = self._get_team_id(str(opponent), "fbref")
                        if is_home:
                            match_id = self._find_match_id(
                                season_id, match_date, team_id, opponent_id
                            )
                        else:
                            match_id = self._find_match_id(
                                season_id, match_date, opponent_id, team_id
                            )
                    else:
                        continue

                    if not match_id:
                        continue

                    player_name = row.get("player", "")
                    if not player_name or pd.isna(player_name):
                        continue

                    cur.execute(
                        """INSERT INTO match_player_stats (
                            match_id, team_id, is_home, player_name,
                            player_nation, position, age, minutes,
                            goals, assists, pens_made, pens_att,
                            shots, shots_on_target, xg, npxg, xag,
                            yellow_cards, red_cards,
                            touches, tackles, interceptions, blocks,
                            passes_completed, passes_attempted,
                            pass_completion_pct, progressive_passes,
                            carries, progressive_carries,
                            take_ons_attempted, take_ons_succeeded, saves
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (match_id, team_id, player_name) DO UPDATE SET
                            minutes = EXCLUDED.minutes,
                            goals = EXCLUDED.goals,
                            assists = EXCLUDED.assists,
                            xg = EXCLUDED.xg,
                            npxg = EXCLUDED.npxg,
                            xag = EXCLUDED.xag,
                            yellow_cards = EXCLUDED.yellow_cards,
                            red_cards = EXCLUDED.red_cards""",
                        (
                            match_id, team_id, is_home, str(player_name),
                            row.get("nation"), row.get("pos"), row.get("age"),
                            self._safe_int(row.get("Min")),
                            self._safe_int(row.get("Gls")),
                            self._safe_int(row.get("Ast")),
                            self._safe_int(row.get("PK")),
                            self._safe_int(row.get("PKatt")),
                            self._safe_int(row.get("Sh")),
                            self._safe_int(row.get("SoT")),
                            self._safe_float(row.get("xG")),
                            self._safe_float(row.get("npxG")),
                            self._safe_float(row.get("xAG")),
                            self._safe_int(row.get("CrdY")),
                            self._safe_int(row.get("CrdR")),
                            self._safe_int(row.get("Touches")),
                            self._safe_int(row.get("Tkl")),
                            self._safe_int(row.get("Int")),
                            self._safe_int(row.get("Blocks")),
                            self._safe_int(row.get("Cmp")),
                            self._safe_int(row.get("Att")),
                            self._safe_float(row.get("Cmp%")),
                            self._safe_int(row.get("PrgP")),
                            self._safe_int(row.get("Carries")),
                            self._safe_int(row.get("PrgC")),
                            self._safe_int(row.get("Att_take_ons")),
                            self._safe_int(row.get("Succ")),
                            self._safe_int(row.get("Saves")),
                        ),
                    )
                    rows_stored += 1

                except KeyError as e:
                    logger.debug(f"Unknown team in player stats: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error storing player stats row: {e}")
                    continue

            self.conn.commit()

        return rows_stored

    # ================================================================
    # STEP 6: Shot Events (Optional)
    # ================================================================

    def load_shot_events(self, seasons: Optional[list[str]] = None) -> int:
        """Load per-shot event data from FBref."""
        total = 0
        target_seasons = seasons or self.client.seasons

        for season in target_seasons:
            if self._is_etl_completed("fbref", "shot_events", season):
                logger.info(f"FBref shot events for {season} already loaded")
                continue

            try:
                self._log_etl("fbref", "shot_events", season, "started")
                df = self.client.fetch_shot_events(seasons=[season])

                if df.empty:
                    self._log_etl("fbref", "shot_events", season, "completed", 0)
                    continue

                count = self._store_shot_events(df, season)
                total += count
                self._log_etl("fbref", "shot_events", season, "completed", count)
                logger.info(f"Loaded {count} shot events for {season}")
            except Exception as e:
                logger.error(f"Error loading shot events for {season}: {e}")
                self._log_etl(
                    "fbref", "shot_events", season, "failed", error=str(e)
                )
                continue

        return total

    def _store_shot_events(self, df: pd.DataFrame, season_code: str) -> int:
        """Store shot events into shot_events table."""
        season_id = self._get_season_id(season_code)
        rows_stored = 0
        df_reset = df.reset_index()

        with self.conn.cursor() as cur:
            for _, row in df_reset.iterrows():
                try:
                    team_name = row.get("team", row.get("squad", ""))
                    if not team_name:
                        continue

                    team_id = self._get_team_id(str(team_name), "fbref")

                    # Find match from game_id or date+teams
                    game = row.get("game", "")
                    match_id = None

                    if game and not pd.isna(game):
                        cur.execute(
                            """SELECT id FROM matches
                               WHERE fbref_match_id = %s LIMIT 1""",
                            (str(game),),
                        )
                        result = cur.fetchone()
                        if result:
                            match_id = result[0]

                    if not match_id:
                        continue

                    cur.execute(
                        """INSERT INTO shot_events (
                            match_id, team_id, minute, player_name,
                            xg, psxg, outcome, distance, body_part, notes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            match_id, team_id,
                            self._safe_int(row.get("minute")),
                            row.get("player"),
                            self._safe_float(row.get("xG")),
                            self._safe_float(row.get("PSxG")),
                            row.get("outcome"),
                            self._safe_int(row.get("distance")),
                            row.get("body_part"),
                            row.get("notes"),
                        ),
                    )
                    rows_stored += 1

                except KeyError as e:
                    logger.debug(f"Unknown team in shot events: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error storing shot event: {e}")
                    continue

            self.conn.commit()

        return rows_stored

    # ================================================================
    # Full Pipeline
    # ================================================================

    def run_full_pipeline(self, seasons: Optional[list[str]] = None) -> dict[str, int]:
        """Run the complete ETL pipeline in order.

        Steps: MatchHistory -> ESPN Stats -> Standings.
        (FBref steps skipped by default; use --step to run individually.)
        """
        results: dict[str, int] = {}

        logger.info("=" * 60)
        logger.info("Starting Full Soccerdata ETL Pipeline")
        logger.info("=" * 60)

        logger.info("\n--- Step 1/3: Loading MatchHistory data ---")
        results["match_history"] = self.load_match_history(seasons)

        logger.info("\n--- Step 2/3: Loading ESPN match stats ---")
        results["espn_stats"] = self.load_espn_match_stats(seasons)

        logger.info("\n--- Step 3/3: Computing standings ---")
        results["standings"] = self.compute_standings(seasons)

        logger.info("\n" + "=" * 60)
        logger.info("ETL Pipeline Complete")
        for step, count in results.items():
            logger.info(f"  {step}: {count} rows")
        logger.info("=" * 60)

        return results

    def close(self) -> None:
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
        logger.info("ETL connections closed")


def main() -> None:
    """CLI entry point for ETL pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Soccerdata ETL Pipeline")
    parser.add_argument(
        "--seasons",
        type=str,
        default=None,
        help="Comma-separated seasons (e.g., '2324,2223'). Default: all from config",
    )
    parser.add_argument(
        "--step",
        choices=[
            "all",
            "match-history",
            "espn-stats",
            "fbref-schedule",
            "fbref-stats",
            "player-stats",
            "shot-events",
            "standings",
        ],
        default="all",
        help="Which ETL step to run (default: all)",
    )
    parser.add_argument(
        "--stat-types",
        type=str,
        default=None,
        help="Comma-separated FBref stat types (e.g., 'shooting,passing')",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run even if already completed (clears etl_log for the operation)",
    )

    args = parser.parse_args()

    seasons = [s.strip() for s in args.seasons.split(",")] if args.seasons else None
    stat_types = (
        [s.strip() for s in args.stat_types.split(",")] if args.stat_types else None
    )

    etl = SoccerdataETL(seasons=seasons)

    try:
        if args.force:
            _clear_etl_log(etl.conn, args.step, stat_types, seasons)

        if args.step == "all":
            etl.run_full_pipeline(seasons)
        elif args.step == "match-history":
            count = etl.load_match_history(seasons)
            logger.info(f"MatchHistory: {count} rows loaded")
        elif args.step == "espn-stats":
            count = etl.load_espn_match_stats(seasons)
            logger.info(f"ESPN stats: {count} matches enriched")
        elif args.step == "fbref-schedule":
            count = etl.load_fbref_schedule(seasons)
            logger.info(f"FBref schedule: {count} rows")
        elif args.step == "fbref-stats":
            count = etl.load_fbref_team_match_stats(
                stat_types=stat_types, seasons=seasons
            )
            logger.info(f"FBref stats: {count} rows")
        elif args.step == "player-stats":
            count = etl.load_player_match_stats(seasons)
            logger.info(f"Player stats: {count} rows")
        elif args.step == "shot-events":
            count = etl.load_shot_events(seasons)
            logger.info(f"Shot events: {count} rows")
        elif args.step == "standings":
            count = etl.compute_standings(seasons)
            logger.info(f"Standings: {count} rows")
    finally:
        etl.close()


def _clear_etl_log(
    conn: psycopg2.extensions.connection,
    step: str,
    stat_types: Optional[list[str]],
    seasons: Optional[list[str]],
) -> None:
    """Clear etl_log entries for --force re-runs."""
    source_map = {
        "all": None,
        "match-history": ("match_history", "games"),
        "espn-stats": ("espn", "match_stats"),
        "fbref-schedule": ("fbref", "schedule"),
        "fbref-stats": ("fbref", None),
        "player-stats": ("fbref", "player_match_stats"),
        "shot-events": ("fbref", "shot_events"),
        "standings": ("computed", "standings"),
    }

    with conn.cursor() as cur:
        if step == "all":
            if seasons:
                for s in seasons:
                    cur.execute(
                        "DELETE FROM etl_log WHERE season_code = %s", (s,)
                    )
            else:
                cur.execute("DELETE FROM etl_log")
        else:
            source, operation = source_map.get(step, (None, None))
            if source:
                query = "DELETE FROM etl_log WHERE source = %s"
                params: list[object] = [source]
                if operation:
                    query += " AND operation = %s"
                    params.append(operation)
                if seasons:
                    query += " AND season_code = ANY(%s)"
                    params.append(seasons)
                cur.execute(query, params)

        conn.commit()
        logger.info(f"Cleared etl_log for step={step}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
