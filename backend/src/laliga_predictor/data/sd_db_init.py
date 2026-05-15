"""
Database initialization for the soccerdata database.

Creates all tables, indexes, views, and seed data for the soccerdata-based
data pipeline. Connects to a separate PostgreSQL database (laliga_soccerdata).
"""

import logging
from pathlib import Path

import psycopg2
from psycopg2 import sql

from ..config import get_settings

logger = logging.getLogger(__name__)


def get_sd_connection() -> psycopg2.extensions.connection:
    """Get a connection to the soccerdata database."""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.SD_DB_HOST,
        port=settings.SD_DB_PORT,
        database=settings.SD_DB_NAME,
        user=settings.SD_DB_USER,
        password=settings.SD_DB_PASSWORD,
    )


def init_soccerdata_database() -> None:
    """Initialize the soccerdata database schema."""
    settings = get_settings()

    schema_path = Path(__file__).parent.parent.parent.parent / "database" / "schema_soccerdata.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    logger.info(f"Reading schema from: {schema_path}")

    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()

    logger.info(
        f"Connecting to soccerdata database: {settings.SD_DB_NAME} "
        f"at {settings.SD_DB_HOST}:{settings.SD_DB_PORT}"
    )

    try:
        conn = get_sd_connection()

        with conn.cursor() as cursor:
            logger.info("Executing soccerdata schema SQL...")
            cursor.execute(schema_sql)
            conn.commit()
            logger.info("Schema executed successfully")

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """
            )
            tables = cursor.fetchall()

            logger.info(f"Created {len(tables)} tables:")
            for table in tables:
                logger.info(f"  - {table[0]}")

        conn.close()
        logger.info("Soccerdata database initialization completed successfully")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise


def drop_all_tables() -> None:
    """Drop all tables in the soccerdata database. WARNING: deletes all data!"""
    logger.warning("WARNING: Dropping all soccerdata tables!")

    try:
        conn = get_sd_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                DROP TABLE IF EXISTS shot_events CASCADE;
                DROP TABLE IF EXISTS match_player_stats CASCADE;
                DROP TABLE IF EXISTS match_advanced_stats CASCADE;
                DROP TABLE IF EXISTS standings CASCADE;
                DROP TABLE IF EXISTS matches CASCADE;
                DROP TABLE IF EXISTS team_name_mapping CASCADE;
                DROP TABLE IF EXISTS teams CASCADE;
                DROP TABLE IF EXISTS seasons CASCADE;
                DROP TABLE IF EXISTS etl_log CASCADE;
            """
            )
            conn.commit()
            logger.info("All soccerdata tables dropped successfully")

        conn.close()

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise


def verify_soccerdata_database() -> None:
    """Verify soccerdata database structure and show statistics."""
    try:
        conn = get_sd_connection()

        with conn.cursor() as cursor:
            logger.info("\n=== Soccerdata Database Structure ===")

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """
            )
            tables = cursor.fetchall()
            logger.info(f"\nTables ({len(tables)}):")
            for table in tables:
                logger.info(f"  - {table[0]}")

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'VIEW'
                ORDER BY table_name;
            """
            )
            views = cursor.fetchall()
            logger.info(f"\nViews ({len(views)}):")
            for view in views:
                logger.info(f"  - {view[0]}")

            logger.info("\n=== Data Statistics ===")

            table_names = [
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
            for table_name in table_names:
                try:
                    cursor.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name))
                    )
                    count = cursor.fetchone()[0]
                    logger.info(f"  {table_name}: {count} records")
                except psycopg2.Error:
                    logger.info(f"  {table_name}: table not found")
                    conn.rollback()

        conn.close()

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize soccerdata database")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before initializing (WARNING: deletes all data)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify database structure and show statistics",
    )

    args = parser.parse_args()

    try:
        if args.drop:
            drop_all_tables()

        if args.verify:
            verify_soccerdata_database()
        else:
            init_soccerdata_database()
            verify_soccerdata_database()

    except Exception as e:
        logger.error(f"Failed to initialize soccerdata database: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
