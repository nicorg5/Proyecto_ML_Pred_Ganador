"""
Prediction pipeline for upcoming La Liga matches.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from ..config import get_settings
from ..features.data_loader import load_all_data
from ..features.feature_engineering import MatchFeatureBuilder
from .base import BasePredictor

logger = logging.getLogger(__name__)

# Over/Under lines (must match train.py)
GOALS_LINES = [1.5, 2.5, 3.5]
CARDS_LINES = [3.5, 4.5, 5.5]


def load_trained_models(
    model_dir: Path | None = None,
) -> dict[str, BasePredictor]:
    """Load best trained models for each target.

    Returns dict with keys: 'winner', 'goals_1.5', 'goals_2.5', etc.
    """
    settings = get_settings()
    model_dir = model_dir or settings.MODEL_PATH

    models: dict[str, BasePredictor] = {}

    # Winner model (multi-class)
    for fname in [
        "result_ensemble.joblib",
        "result_xgboost.joblib",
        "result_rf.joblib",
        "result_baseline.joblib",
    ]:
        path = model_dir / fname
        if path.exists():
            models["winner"] = BasePredictor.load(path)
            logger.info(f"Loaded winner model: {fname}")
            break

    # Goals over/under models
    for line in GOALS_LINES:
        key = f"goals_{line}"
        for model_type in ["xgboost", "baseline"]:
            fname = f"goals_over_{line}_{model_type}.joblib"
            path = model_dir / fname
            if path.exists():
                models[key] = BasePredictor.load(path)
                logger.info(f"Loaded {key} model: {fname}")
                break

    # Cards over/under models
    for line in CARDS_LINES:
        key = f"cards_{line}"
        for model_type in ["xgboost", "baseline"]:
            fname = f"cards_over_{line}_{model_type}.joblib"
            path = model_dir / fname
            if path.exists():
                models[key] = BasePredictor.load(path)
                logger.info(f"Loaded {key} model: {fname}")
                break

    return models


def predict_match(
    home_team: str,
    away_team: str,
    match_date: str,
    models: dict[str, BasePredictor] | None = None,
    builder: MatchFeatureBuilder | None = None,
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
        X_aligned = X.reindex(columns=model.feature_names, fill_value=0)
        proba = model.predict_proba(X_aligned)[0]
        pred = model.predict(X_aligned)[0]
        result["predictions"]["winner"] = {
            "predicted_result": str(pred),
            "home_win_prob": round(float(proba[2]), 3),  # H is index 2
            "draw_prob": round(float(proba[1]), 3),  # D is index 1
            "away_win_prob": round(float(proba[0]), 3),  # A is index 0
        }

    # Goals Over/Under predictions
    goals_ou = {}
    for line in GOALS_LINES:
        key = f"goals_{line}"
        if key in models:
            model = models[key]
            X_aligned = X.reindex(columns=model.feature_names, fill_value=0)
            proba = model.predict_proba(X_aligned)[0]
            # proba: [P(under), P(over)]
            goals_ou[str(line)] = {
                "over_prob": round(float(proba[1]), 3),
                "under_prob": round(float(proba[0]), 3),
            }
    if goals_ou:
        result["predictions"]["goals_over_under"] = goals_ou

    # Cards Over/Under predictions
    cards_ou = {}
    for line in CARDS_LINES:
        key = f"cards_{line}"
        if key in models:
            model = models[key]
            X_aligned = X.reindex(columns=model.feature_names, fill_value=0)
            proba = model.predict_proba(X_aligned)[0]
            cards_ou[str(line)] = {
                "over_prob": round(float(proba[1]), 3),
                "under_prob": round(float(proba[0]), 3),
            }
    if cards_ou:
        result["predictions"]["cards_over_under"] = cards_ou

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
        "--date",
        type=str,
        required=True,
        help="Match date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
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
