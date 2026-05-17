"""
Real prediction logic backed by the cached features.parquet.

Avoids a database dependency by using the pre-computed features for the most
recent match between the requested teams (or the latest individual matches as
a fallback).
"""

from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Metadata columns that are not features
META_COLS = {
    "match_id",
    "match_date",
    "season_code",
    "home_team",
    "away_team",
    "target_result",
    "target_total_goals",
    "target_total_cards",
}

# Maps UI team names (with accents / full names) to the parquet's team labels.
# Parquet uses ASCII names without accents.
TEAM_NAME_MAP = {
    "Alavés": "Deportivo Alaves",
    "Athletic Club": "Athletic Club",
    "Atlético Madrid": "Atletico Madrid",
    "Barcelona": "Barcelona",
    "Real Betis": "Real Betis",
    "Celta Vigo": "Celta Vigo",
    "Elche CF": "Elche",
    "Espanyol": "Espanyol",
    "Getafe": "Getafe",
    "Girona": "Girona",
    "Levante UD": "Levante",
    "Mallorca": "Mallorca",
    "Osasuna": "Osasuna",
    "Rayo Vallecano": "Rayo Vallecano",
    "Real Madrid": "Real Madrid",
    "Real Oviedo": "Real Oviedo",  # may not exist in historical parquet
    "Real Sociedad": "Real Sociedad",
    "Sevilla": "Sevilla",
    "Valencia": "Valencia",
    "Villarreal": "Villarreal",
}


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize_team(name: str) -> str:
    """Translate a UI team name into the parquet's canonical form."""
    if name in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[name]
    # Fallback: strip accents and use as-is
    return _strip_accents(name)


def load_features_cache(parquet_path: Path) -> pd.DataFrame | None:
    """Load features.parquet into memory. Returns None if missing."""
    if not parquet_path.exists():
        logger.warning(f"⚠️ features.parquet not found at {parquet_path}")
        return None
    df = pd.read_parquet(parquet_path)
    df["match_date"] = pd.to_datetime(df["match_date"])
    logger.info(f"✅ Loaded features cache: {len(df)} rows, {len(df.columns)} columns")
    return df


def _row_to_features(row: pd.Series) -> pd.DataFrame:
    """Convert a parquet row into a single-row feature DataFrame (no metadata)."""
    feature_cols = [c for c in row.index if c not in META_COLS]
    return pd.DataFrame([row[feature_cols].to_dict()])


def _latest_h2h(df: pd.DataFrame, home: str, away: str) -> pd.Series | None:
    """Find the most recent match where `home` was local and `away` visitor."""
    mask = (df["home_team"] == home) & (df["away_team"] == away)
    matches = df[mask].sort_values("match_date")
    if len(matches) == 0:
        return None
    return matches.iloc[-1]


def _latest_role(df: pd.DataFrame, team: str, is_home: bool) -> pd.Series | None:
    """Find the most recent match where `team` played in the given role."""
    col = "home_team" if is_home else "away_team"
    matches = df[df[col] == team].sort_values("match_date")
    if len(matches) == 0:
        return None
    return matches.iloc[-1]


def build_match_features(df: pd.DataFrame, home_team: str, away_team: str) -> pd.DataFrame | None:
    """Build a feature vector for an upcoming match.

    Strategy:
      1. If both teams played a recent H2H with this orientation, use those features.
      2. Otherwise combine the latest home-role row of `home_team` with the
         latest away-role row of `away_team` (copying away columns from the latter).
      3. If either team has no history, return None.
    """
    h_norm = normalize_team(home_team)
    a_norm = normalize_team(away_team)

    h2h = _latest_h2h(df, h_norm, a_norm)
    if h2h is not None:
        return _row_to_features(h2h)

    home_row = _latest_role(df, h_norm, is_home=True)
    away_row = _latest_role(df, a_norm, is_home=False)
    if home_row is None or away_row is None:
        return None

    # Start from the home row, overwrite all away-team columns from the away row.
    merged = home_row.copy()
    for col in away_row.index:
        if col.startswith("a_") or col.startswith("away_"):
            merged[col] = away_row[col]
    return _row_to_features(merged)


def predict_match(
    models: dict[str, Any],
    features_df: pd.DataFrame | None,
    home_team: str,
    away_team: str,
) -> dict[str, Any] | None:
    """Run all loaded models on the built features and return structured probabilities.

    Returns None if features could not be built (unknown team / insufficient data).
    """
    if features_df is None:
        return None

    X_match = build_match_features(features_df, home_team, away_team)
    if X_match is None:
        return None

    # Fill NaN with 0 (safe default; training also imputes)
    X_match = X_match.fillna(0)

    result: dict[str, Any] = {"winner": None, "goals": {}, "cards": {}}

    # Winner: multi-class
    winner = models.get("winner")
    if winner is not None and hasattr(winner, "feature_names"):
        X = X_match.reindex(columns=winner.feature_names, fill_value=0)
        proba = winner.predict_proba(X)[0]
        pred = winner.predict(X)[0]
        # Class order in training: A=0, D=1, H=2
        result["winner"] = {
            "predicted": str(pred),
            "home_prob": round(float(proba[2]), 3),
            "draw_prob": round(float(proba[1]), 3),
            "away_prob": round(float(proba[0]), 3),
        }

    # Over/Under: binary classifiers; class order [under=0, over=1]
    for line in ["1.5", "2.5", "3.5"]:
        model = models.get(f"goals_{line}")
        if model is not None and hasattr(model, "feature_names"):
            X = X_match.reindex(columns=model.feature_names, fill_value=0)
            proba = model.predict_proba(X)[0]
            result["goals"][line] = {
                "over": round(float(proba[1]), 3),
                "under": round(float(proba[0]), 3),
            }

    for line in ["3.5", "4.5", "5.5"]:
        model = models.get(f"cards_{line}")
        if model is not None and hasattr(model, "feature_names"):
            X = X_match.reindex(columns=model.feature_names, fill_value=0)
            proba = model.predict_proba(X)[0]
            result["cards"][line] = {
                "over": round(float(proba[1]), 3),
                "under": round(float(proba[0]), 3),
            }

    return result
