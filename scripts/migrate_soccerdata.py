import logging
import psycopg2
from psycopg2 import extras

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SOURCE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'laliga_user',
    'password': 'laliga_password_dev',
    'database': 'laliga_soccerdata'
}

TARGET_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'user': 'laliga_user',
    'password': 'laliga_password_dev',
    'database': 'laliga_soccerdata'
}

TABLES_IN_ORDER = [
    "seasons",
    "teams",
    "team_name_mapping",
    "matches",
    "match_advanced_stats",
    "match_player_stats",
    "shot_events",
    "standings",
    "etl_log"
]

def migrate():
    try:
        src_conn = psycopg2.connect(**SOURCE_CONFIG)
        tgt_conn = psycopg2.connect(**TARGET_CONFIG)
        logger.info("Connected to both source and target databases")

        with src_conn.cursor() as src_cur, tgt_conn.cursor() as tgt_cur:
            # Disable triggers/constraints temporarily if possible, or just follow order
            
            for table in TABLES_IN_ORDER:
                logger.info(f"Migrating table: {table}")
                
                # Get column names
                src_cur.execute(f"SELECT * FROM {table} LIMIT 0")
                columns = [desc[0] for desc in src_cur.description]
                cols_str = ", ".join(columns)
                placeholders = ", ".join(["%s"] * len(columns))
                
                # Clear target table
                tgt_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
                
                # Fetch data from source
                src_cur.execute(f"SELECT {cols_str} FROM {table}")
                rows = src_cur.fetchall()
                
                if not rows:
                    logger.info(f"Table {table} is empty, skipping.")
                    continue
                
                # Insert data into target
                insert_query = f"INSERT INTO {table} ({cols_str}) VALUES %s"
                extras.execute_values(tgt_cur, insert_query, rows)
                
                logger.info(f"Migrated {len(rows)} rows for table {table}")
            
            tgt_conn.commit()
            logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'tgt_conn' in locals():
            tgt_conn.rollback()
    finally:
        if 'src_conn' in locals():
            src_conn.close()
        if 'tgt_conn' in locals():
            tgt_conn.close()

if __name__ == "__main__":
    migrate()
