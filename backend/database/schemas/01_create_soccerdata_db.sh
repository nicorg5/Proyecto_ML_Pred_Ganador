#!/bin/bash
set -e

# Create the soccerdata database on first container initialization
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE laliga_soccerdata OWNER $POSTGRES_USER;
EOSQL

echo "Database laliga_soccerdata created successfully"
