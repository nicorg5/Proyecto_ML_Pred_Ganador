"""
Prediction pipeline for upcoming La Liga matches.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from ..config import get_settings
from ..features.data_loader import load_all_data
from ..features.feature_engineering import MatchFeatureBuilder
from .base import BasePredictor

logger = logging.getLogger(__name__)


def load_trained_models(
    model_dir: Optional[Path] = None,
) -> dict[str, BasePredictor]:
    """Load best trained models for each target.

    Returns dict with keys: 'winner', 'goals', 'cards'.
    """
    settings = get_settings()
    model_dir = model_dir or settings.MODEL_PATH

    models: dict[str, BasePredictor] = {}

    # Load best model for each target (prefer xgboost > rf > baseline)
    for target, filename_options in {
        "winner": ["result_xgboost.joblib", "result_rf.joblib", "result_baseline.joblib"],
        "goals": ["total_goals_xgboost.joblib", "total_goals_baseline.joblib"],
        "cards": ["total_cards_xgboost.joblib", "total_cards_baseline.joblib"],
    }.items():
        for fname in filename_options:
            path = model_dir / fname
            if path.exists():
                models[target] = BasePredictor.load(path)
                logger.info(f"Loaded {target} model: {fname}")
                break

    return models


def predict_match(
    home_team: str,
    away_team: str,
    match_date: str,
    models: Optional[dict[str, BasePredictor]] = None,
    builder: Optional[MatchFeatureBuilder] = None,
) -> dict:
    """Predict outcome for a single match.

    Args:
        home_team: Canonical home team name
        away_team: Canonical away team name
        match_date: Date string (YYYY-MM-DD)
        models: Pre-loaded models (loads from disk if None)
        builder: Pre-built feature builder (builds from DB if None)

    Returns:
        Prediction dict with probabilities and expected values.
    """
    if models is None:
        models = load_trained_models()

    if builder is None:
        matches, advanced, standings = load_all_data()
        builder = MatchFeatureBuilder(matches, advanced, standings)

    date = pd.Timestamp(match_date)

    # Resolve team IDs from name
    home_row = builder.matches[builder.matches["home_team"] == home_team]
    away_row = builder.matches[builder.matches["away_team"] == away_team]

    if len(home_row) == 0:
        raise ValueError(f"Unknown home team: {home_team}")
    if len(away_row) == 0:
        raise ValueError(f"Unknown away team: {away_team}")

    home_id = int(home_row.iloc[-1]["home_team_id"])
    away_id = int(away_row.iloc[-1]["away_team_id"])

    # Determine season code (approximate)
    year = date.year
    month = date.month
    if month >= 7:
        season_code = f"{str(year)[-2:]}{str(year + 1)[-2:]}"
    else:
        season_code = f"{str(year - 1)[-2:]}{str(year)[-2:]}"

    # Build features
    features = builder.build_features_for_prediction(
        home_team_id=home_id,
        away_team_id=away_id,
        match_date=date,
        season_code=season_code,
        home_team=home_team,
        away_team=away_team,
    )

    if features is None:
        raise ValueError("Could not compute features (insufficient historical data)")

    # Remove metadata from features
    meta_keys = {"match_id", "match_date", "season_code", "home_team", "away_team"}
    feature_dict = {k: v for k, v in features.items() if k not in meta_keys}
    X = pd.DataFrame([feature_dict])

    # Fill NaN with 0 (safe default for prediction)
    X = X.fillna(0)

    result: dict = {
        "match_date": match_date,
        "home_team": home_team,
        "away_team": away_team,
        "predictions": {},
    }

    # Winner prediction
    if "winner" in models:
        model = models["winner"]
        # Ensure feature order matches training
        X_aligned = X.reindex(columns=model.feature_names, fill_value=0)
        proba = model.predict_proba(X_aligned)[0]
        pred = model.predict(X_aligned)[0]
        result["predictions"]["winner"] = {
            "predicted_result": str(pred),
            "home_win_prob": round(float(proba[2]), 3),  # H is index 2
            "draw_prob": round(float(proba[1]), 3),       # D is index 1
            "away_win_prob": round(float(proba[0]), 3),   # A is index 0
        }

    # Goals prediction
    if "goals" in models:
        model = models["goals"]
        X_aligned = X.reindex(columns=model.feature_names, fill_value=0)
        pred = model.predict(X_aligned)[0]
        result["predictions"]["total_goals"] = {
            "predicted": round(float(pred), 1),
            "over_2_5_prob": "N/A",
        }

    # Cards prediction
    if "cards" in models:
        model = models["cards"]
        X_aligned = X.reindex(columns=model.feature_names, fill_value=0)
        pred = model.predict(X_aligned)[0]
        result["predictions"]["total_cards"] = {
            "predicted": round(float(pred), 1),
        }

    return result


# ================================================================
# CLI
# ================================================================


def main() -> None:
    """CLI for match predictions."""
    import argparse

    parser = argparse.ArgumentParser(description="Predict La Liga match outcomes")
    parser.add_argument("--home", type=str, required=True, help="Home team canonical name")
    parser.add_argument("--away", type=str, required=True, help="Away team canonical name")
    parser.add_argument(
        "--date", type=str, required=True,
        help="Match date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output JSON file path (default: print to stdout)",
    )

    args = parser.parse_args()

    result = predict_match(args.home, args.away, args.date)

    output_json = json.dumps(result, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(output_json)
        logger.info(f"Prediction saved to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
