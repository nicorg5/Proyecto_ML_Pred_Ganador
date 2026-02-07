"""
Database initialization script.

This script creates all necessary tables, indexes, views, and functions
for the LaLiga Predictor database.
"""

import logging
from pathlib import Path

import psycopg2
from psycopg2 import sql

from ..config import get_settings

logger = logging.getLogger(__name__)


def init_database() -> None:
    """
    Initialize the database schema.

    Reads and executes the schema.sql file to create all tables,
    indexes, views, and functions.
    """
    settings = get_settings()

    # Path to schema file
    schema_path = Path(__file__).parent.parent.parent.parent / "database" / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    logger.info(f"Reading schema from: {schema_path}")

    # Read schema SQL
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Connect to database
    logger.info(f"Connecting to database: {settings.DB_NAME} at {settings.DB_HOST}:{settings.DB_PORT}")

    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )

        with conn.cursor() as cursor:
            logger.info("Executing schema SQL...")
            cursor.execute(schema_sql)
            conn.commit()
            logger.info("Schema executed successfully")

            # Verify tables were created
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()

            logger.info(f"Created {len(tables)} tables:")
            for table in tables:
                logger.info(f"  - {table[0]}")

        conn.close()
        logger.info("Database initialization completed successfully")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise


def drop_all_tables() -> None:
    """
    Drop all tables in the database.

    WARNING: This will delete ALL data!
    Use only for development/testing.
    """
    settings = get_settings()

    logger.warning("WARNING: Dropping all tables!")

    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )

        with conn.cursor() as cursor:
            # Drop all tables
            cursor.execute("""
                DROP TABLE IF EXISTS match_stats CASCADE;
                DROP TABLE IF EXISTS matches CASCADE;
                DROP TABLE IF EXISTS teams CASCADE;
                DROP TABLE IF EXISTS seasons CASCADE;
            """)
            conn.commit()
            logger.info("All tables dropped successfully")

        conn.close()

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise


def verify_database() -> None:
    """
    Verify database structure and show statistics.
    """
    settings = get_settings()

    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )

        with conn.cursor() as cursor:
            logger.info("\n=== Database Structure ===")

            # Tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            logger.info(f"\nTables ({len(tables)}):")
            for table in tables:
                logger.info(f"  - {table[0]}")

            # Views
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'VIEW'
                ORDER BY table_name;
            """)
            views = cursor.fetchall()
            logger.info(f"\nViews ({len(views)}):")
            for view in views:
                logger.info(f"  - {view[0]}")

            # Count records
            logger.info("\n=== Data Statistics ===")

            for table_name in ["seasons", "teams", "matches", "match_stats"]:
                try:
                    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
                    count = cursor.fetchone()[0]
                    logger.info(f"{table_name}: {count} records")
                except psycopg2.Error:
                    logger.info(f"{table_name}: table not found")

        conn.close()

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize LaLiga Predictor database")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before initializing (WARNING: deletes all data)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify database structure and show statistics",
    )

    args = parser.parse_args()

    try:
        if args.drop:
            drop_all_tables()

        if args.verify:
            verify_database()
        else:
            init_database()
            verify_database()

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
