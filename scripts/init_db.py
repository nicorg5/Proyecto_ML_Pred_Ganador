"""
Database initialization script.

This script creates the database schema and initializes required tables.
Run this after starting the PostgreSQL Docker container.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add src to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.laliga_predictor.config import get_settings

logger = logging.getLogger(__name__)


def create_database_if_not_exists() -> bool:
    """
    Create the database if it doesn't exist.

    Returns:
        True if database exists or was created successfully

    Raises:
        Exception: If database creation fails
    """
    settings = get_settings()

    try:
        # Connect to PostgreSQL server (default postgres database)
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (settings.DB_NAME,)
        )
        exists = cursor.fetchone()

        if not exists:
            logger.info(f"Creating database '{settings.DB_NAME}'...")
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings.DB_NAME))
            )
            logger.info(f"Database '{settings.DB_NAME}' created successfully")
        else:
            logger.info(f"Database '{settings.DB_NAME}' already exists")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Error creating database: {e}")
        raise


def execute_sql_file(cursor: psycopg2.extensions.cursor, file_path: Path) -> None:
    """
    Execute SQL statements from a file.

    Args:
        cursor: Database cursor
        file_path: Path to SQL file

    Raises:
        FileNotFoundError: If SQL file doesn't exist
        psycopg2.Error: If SQL execution fails
    """
    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")

    logger.info(f"Executing SQL file: {file_path.name}")

    with open(file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    try:
        cursor.execute(sql_content)
        logger.info(f"Successfully executed {file_path.name}")
    except psycopg2.Error as e:
        logger.error(f"Error executing {file_path.name}: {e}")
        raise


def initialize_schema() -> bool:
    """
    Initialize database schema by executing SQL files.

    Returns:
        True if schema initialization succeeds

    Raises:
        Exception: If schema initialization fails
    """
    settings = get_settings()

    try:
        # Connect to the application database
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
        )
        cursor = conn.cursor()

        # Get schema files directory
        schema_dir = Path(__file__).parent.parent / "database" / "schemas"

        # Execute schema files in order
        schema_files = sorted(schema_dir.glob("*.sql"))

        if not schema_files:
            logger.warning(f"No SQL files found in {schema_dir}")
            logger.info("Creating basic schema programmatically...")
            # Create basic schema if files don't exist
            create_basic_schema(cursor)
        else:
            for sql_file in schema_files:
                execute_sql_file(cursor, sql_file)

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Database schema initialized successfully")
        return True

    except (psycopg2.Error, FileNotFoundError) as e:
        logger.error(f"Error initializing schema: {e}")
        if conn:
            conn.rollback()
        raise


def create_basic_schema(cursor: psycopg2.extensions.cursor) -> None:
    """
    Create basic schema programmatically if SQL files are not available.

    Args:
        cursor: Database cursor
    """
    logger.info("Creating basic tables...")

    # Enable UUID extension
    cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            team_name VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create seasons table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            season VARCHAR(20) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            season_id UUID REFERENCES seasons(id) ON DELETE CASCADE,
            match_date DATE NOT NULL,
            home_team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
            away_team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
            home_score INTEGER,
            away_score INTEGER,
            result VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT valid_result CHECK (result IN ('victoria_local', 'empate', 'victoria_visitante'))
        )
    """)

    logger.info("Basic schema created")


def verify_connection() -> bool:
    """
    Verify database connection.

    Returns:
        True if connection succeeds

    Raises:
        Exception: If connection fails
    """
    settings = get_settings()

    try:
        logger.info("Verifying database connection...")
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
        )

        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        logger.info(f"Connected to: {version[0]}")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise


def main() -> None:
    """Main function to initialize database."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("LaLiga Predictor - Database Initialization")
    logger.info("=" * 60)

    try:
        # Validate settings
        settings.validate_database_connection()
        logger.info(f"Database: {settings.DB_NAME}")
        logger.info(f"Host: {settings.DB_HOST}:{settings.DB_PORT}")
        logger.info(f"User: {settings.DB_USER}")

        # Step 1: Create database
        logger.info("\n[1/3] Creating database...")
        create_database_if_not_exists()

        # Step 2: Initialize schema
        logger.info("\n[2/3] Initializing schema...")
        initialize_schema()

        # Step 3: Verify connection
        logger.info("\n[3/3] Verifying connection...")
        verify_connection()

        logger.info("\n" + "=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("  1. Run 'make scrape' to collect match data")
        logger.info("  2. Run 'make train' to train the ML model")
        logger.info("  3. Access pgAdmin at http://localhost:5050")

    except Exception as e:
        logger.error(f"\nDatabase initialization failed: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("  1. Ensure Docker containers are running: make docker-up")
        logger.error("  2. Check .env file for correct credentials")
        logger.error("  3. Verify PostgreSQL is accessible on port 5432")
        sys.exit(1)


if __name__ == "__main__":
    main()
