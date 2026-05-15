#!/bin/bash

# Start MLflow tracking server
# Usage: ./scripts/start_mlflow.sh
# Access UI at http://localhost:5000

set -e

echo "🚀 Starting MLflow Tracking Server..."
echo ""
echo "Backend: SQLite (mlflow.db)"
echo "Artifacts: ./mlruns/"
echo "UI: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Create mlruns directory if it doesn't exist
mkdir -p mlruns

# Start MLflow server
uv run mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0 \
  --port 5000
