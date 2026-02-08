"""
Feature persistence for ML pipeline.

Saves and loads computed feature DataFrames as Parquet files.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def save_features(df: pd.DataFrame, path: str | Path) -> None:
    """Save features DataFrame to Parquet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="pyarrow")
    logger.info(f"Saved {len(df)} rows to {path}")


def load_features(path: str | Path) -> pd.DataFrame:
    """Load features DataFrame from Parquet."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Feature file not found: {path}")
    df = pd.read_parquet(path, engine="pyarrow")
    logger.info(f"Loaded {len(df)} rows from {path}")
    return df
