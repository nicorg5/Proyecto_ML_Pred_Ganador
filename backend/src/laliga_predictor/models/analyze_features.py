"""Analyze feature importance for trained models."""

from pathlib import Path

import pandas as pd

from src.laliga_predictor.models.base import BasePredictor

# Ensure we can import the classes (joblib needs them)
from src.laliga_predictor.models.classifiers import (  # noqa: F401
    EnsembleWinner,
    HomeAlwaysWinsBaseline,
    RandomForestWinner,
    XGBoostWinner,
)
from src.laliga_predictor.models.over_under import (  # noqa: F401
    OverUnderBaseline,
    XGBoostOverUnder,
)


def analyze_model(model_path: Path, top_n: int = 20):
    print(f"\n{'='*60}")
    print(f"ANALYZING MODEL: {model_path.name}")
    print(f"{'='*60}")

    try:
        model = BasePredictor.load(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    try:
        importance = model.get_feature_importance()
        print(f"\nTop {top_n} Features:")
        print("-" * 40)
        pd.options.display.float_format = "{:.4f}".format
        print(importance.head(top_n).to_string(index=False))
    except Exception as e:
        print(f"Error getting feature importance: {e}")


def main():
    base_path = Path("models")

    # Models to analyze
    models_to_analyze = [
        "result_ensemble.joblib",
        "goals_over_2.5_xgboost.joblib",
        "cards_over_4.5_xgboost.joblib",
    ]

    print("Starting Feature Importance Analysis...")
    print(f"Looking for models in: {base_path.absolute()}")

    for model_file in models_to_analyze:
        full_path = base_path / model_file
        if full_path.exists():
            analyze_model(full_path)
        else:
            print(f"\nModel not found: {model_file}")


if __name__ == "__main__":
    main()
