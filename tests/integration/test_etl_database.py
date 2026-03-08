"""
Integration tests for ETL pipeline with real PostgreSQL database.

These tests verify that:
- Database schema is created correctly
- Data can be inserted and queried
- ETL operations work with real PostgreSQL

Requirements:
- PostgreSQL must be running (via Docker or locally)
- Environment variables must be set (POSTGRES_HOST, POSTGRES_DB, etc.)
- Tests will be skipped if PostgreSQL is not available
"""

import pytest


class TestDatabaseSchema:
    """Test database schema creation and structure."""

    def test_schema_initialization(self, test_db_with_schema):
        """Verify that all required tables are created."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # Check that all expected tables exist
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        )
        tables = [row[0] for row in cur.fetchall()]

        # Expected tables from schema_soccerdata.sql
        expected_tables = {
            "etl_log",
            "matches",
            "match_advanced_stats",
            "seasons",
            "standings",
            "team_name_mapping",
            "teams",
        }

        # All expected tables should exist
        for table in expected_tables:
            assert table in tables, f"Required table '{table}' not found in database"

        cur.close()

    def test_primary_keys_exist(self, test_db_with_schema):
        """Verify that primary keys are defined on critical tables."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # Check primary key on matches table
        cur.execute(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'matches'
            AND constraint_type = 'PRIMARY KEY'
        """
        )
        pk = cur.fetchone()
        assert pk is not None, "Primary key not found on 'matches' table"

        # Check primary key on teams table
        cur.execute(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'teams'
            AND constraint_type = 'PRIMARY KEY'
        """
        )
        pk = cur.fetchone()
        assert pk is not None, "Primary key not found on 'teams' table"

        cur.close()


class TestDatabaseOperations:
    """Test basic database insert/query operations."""

    def test_insert_team(self, test_db_with_schema):
        """Test inserting a team into the teams table."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # Insert a test team (using correct column name: canonical_name)
        cur.execute(
            """
            INSERT INTO teams (canonical_name, short_name)
            VALUES (%s, %s)
            ON CONFLICT (canonical_name) DO NOTHING
            RETURNING id, canonical_name
        """,
            ("Test Team FC", "Test FC"),
        )

        result = cur.fetchone()
        if result:  # Only check if it was actually inserted (not a conflict)
            team_id, canonical_name = result
            assert team_id > 0
            assert canonical_name == "Test Team FC"

        # Verify team exists
        cur.execute("SELECT canonical_name FROM teams WHERE canonical_name = %s", ("Test Team FC",))
        result = cur.fetchone()
        assert result is not None
        assert result[0] == "Test Team FC"

        cur.close()

    def test_query_seasons(self, test_db_with_schema):
        """Test querying the pre-seeded seasons."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # Query seasons (should have 8 pre-seeded seasons)
        cur.execute("SELECT COUNT(*) FROM seasons")
        count = cur.fetchone()[0]

        assert count == 8, f"Expected 8 pre-seeded seasons, found {count}"

        # Verify season structure
        cur.execute("SELECT season_code, season_name, start_year, end_year FROM seasons LIMIT 1")
        result = cur.fetchone()

        assert result is not None
        season_code, season_name, start_year, end_year = result
        assert len(season_code) == 4  # Format: '1718'
        assert "-" in season_name  # Format: '2017-2018'
        assert start_year < end_year
        assert end_year - start_year == 1

        cur.close()


class TestStandingsTable:
    """Test standings table operations."""

    def test_standings_structure(self, test_db_with_schema):
        """Verify standings table has correct columns."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # Check that standings table has expected columns
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'standings'
            ORDER BY ordinal_position
        """
        )
        columns = [row[0] for row in cur.fetchall()]

        expected_columns = {
            "id",
            "season_id",
            "match_week",
            "team_id",
            "position",
            "matches_played",
            "wins",
            "draws",
            "losses",
            "goals_for",
            "goals_against",
            "goal_difference",
            "points",
        }

        for col in expected_columns:
            assert col in columns, f"Expected column '{col}' not found in standings table"

        cur.close()


class TestETLLog:
    """Test ETL logging functionality."""

    def test_etl_log_structure(self, test_db_with_schema):
        """Test that ETL log table exists and has correct structure."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # Check ETL log table exists
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'etl_log'
            ORDER BY ordinal_position
        """
        )
        columns = [row[0] for row in cur.fetchall()]

        # Just verify critical columns exist (schema may vary)
        critical_columns = {"id", "source", "operation", "status"}

        for col in critical_columns:
            assert col in columns, f"Expected column '{col}' not found in etl_log table"

        # Verify we have at least 5 columns
        assert (
            len(columns) >= 5
        ), f"ETL log table should have at least 5 columns, found {len(columns)}"

        cur.close()


class TestDatabaseQueries:
    """Test realistic database queries."""

    def test_query_team_matches_join(self, test_db_with_schema):
        """Test joining matches and teams tables."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # This query should work even if no data exists
        cur.execute(
            """
            SELECT COUNT(*)
            FROM matches m
            JOIN teams t ON t.id = m.home_team_id
            WHERE t.canonical_name = %s
        """,
            ("Nonexistent Team",),
        )
        count = cur.fetchone()[0]

        assert count == 0  # No matches for nonexistent team

        cur.close()

    def test_query_season_standings(self, test_db_with_schema):
        """Test querying standings with season join."""
        conn = test_db_with_schema
        cur = conn.cursor()

        # This query should work even if no data exists
        cur.execute(
            """
            SELECT COUNT(*)
            FROM standings s
            JOIN seasons se ON se.id = s.season_id
            WHERE se.season_code = %s
        """,
            ("9999",),
        )
        count = cur.fetchone()[0]

        assert count == 0  # No standings for nonexistent season

        cur.close()


# Mark all tests in this module to require database
pytestmark = pytest.mark.integration
