"""
Data validation for the soccerdata database.

Checks data completeness, consistency, and quality across all tables
to ensure the data is ready for ML feature engineering.
"""

import logging

import psycopg2
from psycopg2 import sql

from .sd_db_init import get_sd_connection

logger = logging.getLogger(__name__)

EXPECTED_MATCHES_PER_SEASON = 380


class SoccerdataValidator:
    """Validates data quality in the soccerdata database."""

    def __init__(self) -> None:
        self.conn = get_sd_connection()
        self.issues: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> tuple[bool, dict[str, object]]:
        """Run all validation checks.

        Returns:
            Tuple of (is_valid, report_dict)
        """
        self.issues = []
        self.warnings = []

        report: dict[str, object] = {}
        report["counts"] = self._check_counts()
        report["completeness"] = self._check_completeness()
        report["consistency"] = self._check_consistency()
        report["advanced_stats"] = self._check_advanced_stats_coverage()
        report["quality"] = self._check_quality()

        is_valid = len(self.issues) == 0
        report["issues"] = self.issues
        report["warnings"] = self.warnings
        report["is_valid"] = is_valid

        return is_valid, report

    def _check_counts(self) -> dict[str, int]:
        """Check record counts per table."""
        counts: dict[str, int] = {}
        tables = [
            "seasons",
            "teams",
            "team_name_mapping",
            "matches",
            "match_advanced_stats",
            "standings",
            "match_player_stats",
            "shot_events",
            "etl_log",
        ]

        with self.conn.cursor() as cur:
            for table in tables:
                try:
                    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                    counts[table] = cur.fetchone()[0]
                except psycopg2.Error:
                    counts[table] = -1
                    self.conn.rollback()

        if counts.get("seasons", 0) < 1:
            self.issues.append("CRITICAL: No seasons found in database")
        if counts.get("teams", 0) < 10:
            self.issues.append(f"CRITICAL: Only {counts.get('teams', 0)} teams found")
        if counts.get("matches", 0) < 100:
            self.warnings.append(
                f"WARNING: Only {counts.get('matches', 0)} matches "
                f"(expected ~{EXPECTED_MATCHES_PER_SEASON} per season)"
            )

        return counts

    def _check_completeness(self) -> dict[str, object]:
        """Check data completeness per season."""
        completeness: dict[str, object] = {}

        with self.conn.cursor() as cur:
            # Matches per season
            cur.execute(
                """
                SELECT s.season_name, s.season_code, COUNT(m.id) as total,
                       COUNT(m.home_score) as with_scores
                FROM seasons s
                LEFT JOIN matches m ON s.id = m.season_id
                GROUP BY s.id, s.season_name, s.season_code
                ORDER BY s.start_year
            """
            )
            season_counts = cur.fetchall()

            for name, code, total, with_scores in season_counts:
                completeness[code] = {
                    "name": name,
                    "total_matches": total,
                    "with_scores": with_scores,
                    "expected": EXPECTED_MATCHES_PER_SEASON,
                    "pct": round(total / EXPECTED_MATCHES_PER_SEASON * 100, 1),
                }
                if total == 0:
                    self.warnings.append(f"WARNING: Season {name} has no matches")
                elif total < EXPECTED_MATCHES_PER_SEASON * 0.9:
                    self.warnings.append(
                        f"WARNING: Season {name} only has {total}/{EXPECTED_MATCHES_PER_SEASON} matches"
                    )

            # Missing basic stats
            cur.execute(
                """
                SELECT COUNT(*) FROM matches
                WHERE home_score IS NOT NULL
                  AND (home_shots IS NULL OR home_corners IS NULL
                       OR home_fouls IS NULL)
            """
            )
            missing_stats = cur.fetchone()[0]
            completeness["missing_basic_stats"] = missing_stats
            if missing_stats > 0:
                self.warnings.append(
                    f"WARNING: {missing_stats} matches with scores but missing basic stats"
                )

            # Missing xG
            cur.execute(
                """
                SELECT COUNT(*) FROM matches
                WHERE home_score IS NOT NULL AND home_xg IS NULL
            """
            )
            missing_xg = cur.fetchone()[0]
            completeness["missing_xg"] = missing_xg
            if missing_xg > 0:
                self.warnings.append(f"WARNING: {missing_xg} completed matches without xG data")

            # Source coverage
            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE source_match_history) as from_mh,
                    COUNT(*) FILTER (WHERE source_fbref) as from_fbref,
                    COUNT(*) FILTER (WHERE source_espn) as from_espn,
                    COUNT(*) FILTER (WHERE source_match_history AND source_espn) as mh_and_espn
                FROM matches
            """
            )
            sources = cur.fetchone()
            completeness["sources"] = {
                "total": sources[0],
                "match_history": sources[1],
                "fbref": sources[2],
                "espn": sources[3],
                "mh_and_espn": sources[4],
            }

        return completeness

    def _check_consistency(self) -> dict[str, object]:
        """Check data consistency."""
        consistency: dict[str, object] = {}

        with self.conn.cursor() as cur:
            # Result consistency
            cur.execute(
                """
                SELECT COUNT(*) FROM matches
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
                  AND result IS NOT NULL
                  AND (
                    (home_score > away_score AND result != 'H')
                    OR (home_score < away_score AND result != 'A')
                    OR (home_score = away_score AND result != 'D')
                  )
            """
            )
            inconsistent_results = cur.fetchone()[0]
            consistency["inconsistent_results"] = inconsistent_results
            if inconsistent_results > 0:
                self.issues.append(
                    f"CRITICAL: {inconsistent_results} matches with inconsistent results"
                )

            # Duplicate matches
            cur.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT season_id, match_date, home_team_id, away_team_id
                    FROM matches
                    GROUP BY season_id, match_date, home_team_id, away_team_id
                    HAVING COUNT(*) > 1
                ) dupes
            """
            )
            duplicates = cur.fetchone()[0]
            consistency["duplicates"] = duplicates
            if duplicates > 0:
                self.issues.append(f"CRITICAL: {duplicates} duplicate matches found")

            # Standings consistency (points = W*3 + D)
            cur.execute(
                """
                SELECT COUNT(*) FROM standings
                WHERE points != (wins * 3 + draws)
            """
            )
            bad_points = cur.fetchone()[0]
            consistency["bad_standings_points"] = bad_points
            if bad_points > 0:
                self.issues.append(f"CRITICAL: {bad_points} standings rows with incorrect points")

        return consistency

    def _check_advanced_stats_coverage(self) -> dict[str, object]:
        """Check coverage of advanced stats from FBref."""
        coverage: dict[str, object] = {}

        with self.conn.cursor() as cur:
            # How many matches have advanced stats
            cur.execute("SELECT COUNT(DISTINCT match_id) FROM match_advanced_stats")
            matches_with_stats = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM matches WHERE home_score IS NOT NULL")
            total_completed = cur.fetchone()[0]

            coverage["matches_with_advanced_stats"] = matches_with_stats
            coverage["total_completed_matches"] = total_completed
            if total_completed > 0:
                pct = round(matches_with_stats / total_completed * 100, 1)
                coverage["coverage_pct"] = pct
                if pct < 50:
                    self.warnings.append(f"WARNING: Only {pct}% of matches have advanced stats")

            # Check which stat columns are populated
            stat_groups = {
                "shooting": ["sh", "sot", "xg"],
                "passing": ["passes_cmp", "passes_att", "key_passes"],
                "defense": ["tackles", "interceptions", "blocks"],
                "possession": ["touches", "carries", "take_ons_att"],
                "misc": ["cards_yellow", "fouls_committed", "aerials_won"],
            }

            coverage["stat_coverage"] = {}
            for group, columns in stat_groups.items():
                col_name = columns[0]
                try:
                    cur.execute(
                        sql.SQL(
                            "SELECT COUNT(*) FROM match_advanced_stats WHERE {} IS NOT NULL"
                        ).format(sql.Identifier(col_name))
                    )
                    count = cur.fetchone()[0]
                    coverage["stat_coverage"][group] = count
                except psycopg2.Error:
                    coverage["stat_coverage"][group] = 0
                    self.conn.rollback()

        return coverage

    def _check_quality(self) -> dict[str, object]:
        """Check data quality (outliers, unrealistic values)."""
        quality: dict[str, object] = {}

        with self.conn.cursor() as cur:
            # Unrealistic scores
            cur.execute(
                """
                SELECT COUNT(*) FROM matches
                WHERE (home_score > 10 OR away_score > 10)
                  AND home_score IS NOT NULL
            """
            )
            big_scores = cur.fetchone()[0]
            quality["unrealistic_scores"] = big_scores
            if big_scores > 0:
                self.warnings.append(f"WARNING: {big_scores} matches with scores > 10 goals")

            # Negative stats
            cur.execute(
                """
                SELECT COUNT(*) FROM matches
                WHERE home_shots < 0 OR away_shots < 0
                   OR home_corners < 0 OR away_corners < 0
                   OR home_fouls < 0 OR away_fouls < 0
            """
            )
            negative = cur.fetchone()[0]
            quality["negative_stats"] = negative
            if negative > 0:
                self.issues.append(f"CRITICAL: {negative} matches with negative stats")

            # Shots on target > total shots
            cur.execute(
                """
                SELECT COUNT(*) FROM matches
                WHERE (home_shots_on_target > home_shots
                       OR away_shots_on_target > away_shots)
                  AND home_shots IS NOT NULL
                  AND home_shots_on_target IS NOT NULL
            """
            )
            bad_shots = cur.fetchone()[0]
            quality["shots_on_target_exceeds_total"] = bad_shots
            if bad_shots > 0:
                self.warnings.append(
                    f"WARNING: {bad_shots} matches where shots on target > total shots"
                )

            # Basic stats
            cur.execute(
                """
                SELECT
                    ROUND(AVG(home_score + away_score), 2) as avg_goals,
                    MAX(home_score + away_score) as max_goals,
                    ROUND(AVG(home_shots + away_shots), 1) as avg_shots
                FROM matches
                WHERE home_score IS NOT NULL AND home_shots IS NOT NULL
            """
            )
            stats = cur.fetchone()
            if stats and stats[0]:
                quality["avg_goals_per_match"] = float(stats[0])
                quality["max_goals_in_match"] = int(stats[1])
                quality["avg_shots_per_match"] = float(stats[2])

        return quality

    def generate_report(self) -> str:
        """Generate a human-readable validation report."""
        is_valid, report = self.validate_all()

        lines = [
            "=" * 60,
            "SOCCERDATA DATABASE VALIDATION REPORT",
            "=" * 60,
            "",
            "--- Record Counts ---",
        ]

        counts = report.get("counts", {})
        for table, count in counts.items():
            lines.append(f"  {table}: {count}")

        lines.append("")
        lines.append("--- Completeness ---")
        completeness = report.get("completeness", {})
        for _key, val in completeness.items():
            if isinstance(val, dict) and "name" in val:
                lines.append(
                    f"  {val['name']}: {val['total_matches']}/{val['expected']} "
                    f"matches ({val['pct']}%)"
                )

        sources = completeness.get("sources", {})
        if sources:
            lines.append(
                f"  Source coverage: MatchHistory={sources.get('match_history', 0)}, "
                f"ESPN={sources.get('espn', 0)}, FBref={sources.get('fbref', 0)}, "
                f"MH+ESPN={sources.get('mh_and_espn', 0)}"
            )

        lines.append("")
        lines.append("--- Advanced Stats Coverage ---")
        adv = report.get("advanced_stats", {})
        lines.append(
            f"  Matches with advanced stats: "
            f"{adv.get('matches_with_advanced_stats', 0)}"
            f"/{adv.get('total_completed_matches', 0)} "
            f"({adv.get('coverage_pct', 0)}%)"
        )
        for group, count in adv.get("stat_coverage", {}).items():
            lines.append(f"    {group}: {count} rows")

        if self.warnings:
            lines.append("")
            lines.append("--- Warnings ---")
            for w in self.warnings:
                lines.append(f"  {w}")

        if self.issues:
            lines.append("")
            lines.append("--- ISSUES (must fix) ---")
            for i in self.issues:
                lines.append(f"  {i}")

        lines.append("")
        status = "PASS" if is_valid else "FAIL"
        lines.append(f"Overall: {status}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def close(self) -> None:
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()


def main() -> None:
    """CLI entry point."""
    validator = SoccerdataValidator()
    try:
        report = validator.generate_report()
        print(report)
    finally:
        validator.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
