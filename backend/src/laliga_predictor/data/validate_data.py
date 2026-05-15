"""
Data validation script.

This script validates the quality and completeness of data in the database,
providing detailed reports on data integrity, missing values, and potential issues.
"""

import logging

import psycopg2
from psycopg2.extras import DictCursor

from ..config import get_settings

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates data quality in the database."""

    def __init__(self):
        """Initialize the data validator."""
        self.settings = get_settings()
        self.db_conn = self._connect_db()
        self.issues: list[str] = []
        self.warnings: list[str] = []

    def _connect_db(self) -> psycopg2.extensions.connection:
        """Connect to PostgreSQL database."""
        conn = psycopg2.connect(
            host=self.settings.DB_HOST,
            port=self.settings.DB_PORT,
            database=self.settings.DB_NAME,
            user=self.settings.DB_USER,
            password=self.settings.DB_PASSWORD,
        )
        return conn

    def validate_all(self) -> tuple[bool, dict[str, any]]:
        """
        Run all validation checks.

        Returns:
            Tuple of (is_valid, report)
        """
        logger.info("=" * 60)
        logger.info("Starting data validation")
        logger.info("=" * 60)

        report = {}

        # 1. Check table counts
        logger.info("\n1. Checking table counts...")
        report["counts"] = self._check_counts()

        # 2. Check data completeness
        logger.info("\n2. Checking data completeness...")
        report["completeness"] = self._check_completeness()

        # 3. Check data consistency
        logger.info("\n3. Checking data consistency...")
        report["consistency"] = self._check_consistency()

        # 4. Check match statistics
        logger.info("\n4. Checking match statistics coverage...")
        report["statistics"] = self._check_statistics()

        # 5. Check data quality
        logger.info("\n5. Checking data quality...")
        report["quality"] = self._check_quality()

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)

        is_valid = len(self.issues) == 0

        if is_valid:
            logger.info("✅ All validation checks passed!")
        else:
            logger.error(f"❌ Found {len(self.issues)} critical issues:")
            for issue in self.issues:
                logger.error(f"  - {issue}")

        if self.warnings:
            logger.warning(f"\n⚠️  Found {len(self.warnings)} warnings:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        return is_valid, report

    def _check_counts(self) -> dict[str, int]:
        """Check record counts in all tables."""
        counts = {}

        tables = ["seasons", "teams", "matches", "match_stats"]

        with self.db_conn.cursor() as cursor:
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                counts[table] = count
                logger.info(f"  {table}: {count} records")

        # Validate expected counts
        if counts["seasons"] < 3:
            self.issues.append(f"Expected at least 3 seasons, found {counts['seasons']}")

        if counts["teams"] < 20:
            self.warnings.append(f"Expected at least 20 teams, found {counts['teams']}")

        if counts["matches"] < 100:
            self.warnings.append(f"Expected at least 100 matches, found {counts['matches']}")

        return counts

    def _check_completeness(self) -> dict[str, any]:
        """Check data completeness (missing values)."""
        completeness = {}

        with self.db_conn.cursor(cursor_factory=DictCursor) as cursor:
            # Check finished matches with missing scores
            cursor.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE status = 'FT'
                  AND (home_score IS NULL OR away_score IS NULL)
            """)
            missing_scores = cursor.fetchone()[0]
            completeness["missing_scores"] = missing_scores

            if missing_scores > 0:
                self.issues.append(f"Found {missing_scores} finished matches with missing scores")
            else:
                logger.info("  ✓ All finished matches have scores")

            # Check matches with missing basic statistics
            cursor.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE status = 'FT'
                  AND (home_possession IS NULL OR away_possession IS NULL)
            """)
            missing_stats = cursor.fetchone()[0]
            completeness["missing_basic_stats"] = missing_stats

            if missing_stats > 0:
                self.warnings.append(
                    f"Found {missing_stats} finished matches with missing basic statistics"
                )
                logger.warning(f"  ⚠ {missing_stats} matches missing basic statistics")
            else:
                logger.info("  ✓ All finished matches have basic statistics")

            # Check coverage by season
            cursor.execute("""
                SELECT s.name, COUNT(m.id) as match_count,
                       COUNT(CASE WHEN m.status = 'FT' THEN 1 END) as finished_count
                FROM seasons s
                LEFT JOIN matches m ON s.id = m.season_id
                GROUP BY s.name
                ORDER BY s.name
            """)
            season_coverage = cursor.fetchall()
            completeness["season_coverage"] = [dict(row) for row in season_coverage]

            logger.info("  Season coverage:")
            for row in season_coverage:
                logger.info(
                    f"    {row['name']}: {row['finished_count']}/{row['match_count']} finished"
                )
                if row["finished_count"] < 300:
                    self.warnings.append(
                        f"Season {row['name']} has only {row['finished_count']} finished matches "
                        f"(expected ~380)"
                    )

        return completeness

    def _check_consistency(self) -> dict[str, any]:
        """Check data consistency."""
        consistency = {}

        with self.db_conn.cursor(cursor_factory=DictCursor) as cursor:
            # Check result consistency (result field should match scores)
            cursor.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE status = 'FT'
                  AND home_score IS NOT NULL
                  AND away_score IS NOT NULL
                  AND (
                      (home_score > away_score AND result != 'H') OR
                      (home_score < away_score AND result != 'A') OR
                      (home_score = away_score AND result != 'D')
                  )
            """)
            inconsistent_results = cursor.fetchone()[0]
            consistency["inconsistent_results"] = inconsistent_results

            if inconsistent_results > 0:
                self.issues.append(
                    f"Found {inconsistent_results} matches with inconsistent results"
                )
            else:
                logger.info("  ✓ All match results are consistent with scores")

            # Check possession totals (should sum to ~100%)
            cursor.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE status = 'FT'
                  AND home_possession IS NOT NULL
                  AND away_possession IS NOT NULL
                  AND ABS((home_possession + away_possession) - 100) > 1
            """)
            invalid_possession = cursor.fetchone()[0]
            consistency["invalid_possession"] = invalid_possession

            if invalid_possession > 0:
                self.warnings.append(
                    f"Found {invalid_possession} matches with possession not summing to 100%"
                )
            else:
                logger.info("  ✓ All possession values are valid")

            # Check for duplicate matches
            cursor.execute("""
                SELECT home_team_id, away_team_id, match_date, COUNT(*) as cnt
                FROM matches
                GROUP BY home_team_id, away_team_id, match_date
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            consistency["duplicate_matches"] = len(duplicates)

            if duplicates:
                self.issues.append(f"Found {len(duplicates)} duplicate matches")
            else:
                logger.info("  ✓ No duplicate matches found")

        return consistency

    def _check_statistics(self) -> dict[str, any]:
        """Check match statistics coverage."""
        statistics = {}

        with self.db_conn.cursor(cursor_factory=DictCursor) as cursor:
            # Check percentage of matches with detailed stats
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT m.id) as total_matches,
                    COUNT(DISTINCT ms.match_id) as matches_with_stats,
                    ROUND(100.0 * COUNT(DISTINCT ms.match_id) / NULLIF(COUNT(DISTINCT m.id), 0), 2) as coverage_pct
                FROM matches m
                LEFT JOIN match_stats ms ON m.id = ms.match_id
                WHERE m.status = 'FT'
            """)
            stats_coverage = cursor.fetchone()
            statistics["coverage"] = dict(stats_coverage)

            logger.info(
                f"  Statistics coverage: {stats_coverage['coverage_pct']}% "
                f"({stats_coverage['matches_with_stats']}/{stats_coverage['total_matches']} matches)"
            )

            if stats_coverage["coverage_pct"] < 50:
                self.warnings.append(
                    f"Only {stats_coverage['coverage_pct']}% of matches have detailed statistics"
                )

            # Check statistics by season
            cursor.execute("""
                SELECT s.name,
                       COUNT(DISTINCT m.id) as total_matches,
                       COUNT(DISTINCT ms.match_id) as matches_with_stats
                FROM seasons s
                JOIN matches m ON s.id = m.season_id
                LEFT JOIN match_stats ms ON m.id = ms.match_id
                WHERE m.status = 'FT'
                GROUP BY s.name
                ORDER BY s.name
            """)
            season_stats = cursor.fetchall()
            statistics["by_season"] = [dict(row) for row in season_stats]

            logger.info("  Statistics by season:")
            for row in season_stats:
                pct = (
                    100.0 * row["matches_with_stats"] / row["total_matches"]
                    if row["total_matches"] > 0
                    else 0
                )
                logger.info(
                    f"    {row['name']}: {row['matches_with_stats']}/{row['total_matches']} "
                    f"({pct:.1f}%)"
                )

        return statistics

    def _check_quality(self) -> dict[str, any]:
        """Check data quality (outliers, anomalies)."""
        quality = {}

        with self.db_conn.cursor(cursor_factory=DictCursor) as cursor:
            # Check for unrealistic scores
            cursor.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE status = 'FT'
                  AND (home_score > 10 OR away_score > 10)
            """)
            unrealistic_scores = cursor.fetchone()[0]
            quality["unrealistic_scores"] = unrealistic_scores

            if unrealistic_scores > 0:
                self.warnings.append(
                    f"Found {unrealistic_scores} matches with scores > 10 (possible data errors)"
                )
            else:
                logger.info("  ✓ All scores are realistic")

            # Check for negative statistics
            cursor.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE home_shots_total < 0 OR away_shots_total < 0
                   OR home_corners < 0 OR away_corners < 0
                   OR home_fouls < 0 OR away_fouls < 0
            """)
            negative_stats = cursor.fetchone()[0]
            quality["negative_stats"] = negative_stats

            if negative_stats > 0:
                self.issues.append(f"Found {negative_stats} matches with negative statistics")
            else:
                logger.info("  ✓ No negative statistics found")

            # Check for shots on goal > total shots
            cursor.execute("""
                SELECT COUNT(*)
                FROM matches
                WHERE (home_shots_on_goal > home_shots_total)
                   OR (away_shots_on_goal > away_shots_total)
            """)
            invalid_shots = cursor.fetchone()[0]
            quality["invalid_shots"] = invalid_shots

            if invalid_shots > 0:
                self.issues.append(
                    f"Found {invalid_shots} matches with shots on goal > total shots"
                )
            else:
                logger.info("  ✓ All shot statistics are valid")

            # Get basic statistics
            cursor.execute("""
                SELECT
                    AVG(home_score + away_score) as avg_goals_per_match,
                    MAX(home_score + away_score) as max_goals_in_match,
                    AVG(home_possession) as avg_home_possession
                FROM matches
                WHERE status = 'FT'
                  AND home_score IS NOT NULL
                  AND away_score IS NOT NULL
            """)
            basic_stats = cursor.fetchone()
            quality["basic_stats"] = dict(basic_stats) if basic_stats else {}

            if basic_stats:
                logger.info(f"  Average goals per match: {basic_stats['avg_goals_per_match']:.2f}")
                logger.info(f"  Maximum goals in a match: {basic_stats['max_goals_in_match']}")
                logger.info(f"  Average home possession: {basic_stats['avg_home_possession']:.1f}%")

        return quality

    def generate_report(self) -> str:
        """Generate a summary report."""
        is_valid, report = self.validate_all()

        report_lines = [
            "\n" + "=" * 60,
            "DATA VALIDATION REPORT",
            "=" * 60,
            "",
            "Status: " + ("✅ VALID" if is_valid else "❌ INVALID"),
            "",
            f"Critical Issues: {len(self.issues)}",
            f"Warnings: {len(self.warnings)}",
            "",
        ]

        if self.issues:
            report_lines.append("CRITICAL ISSUES:")
            for issue in self.issues:
                report_lines.append(f"  ❌ {issue}")
            report_lines.append("")

        if self.warnings:
            report_lines.append("WARNINGS:")
            for warning in self.warnings:
                report_lines.append(f"  ⚠️  {warning}")
            report_lines.append("")

        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def close(self) -> None:
        """Close database connection."""
        self.db_conn.close()


def main() -> None:
    """Main entry point."""
    validator = DataValidator()

    try:
        # Run validation and generate report
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
