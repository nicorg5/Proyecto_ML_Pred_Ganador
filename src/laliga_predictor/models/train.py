"""
Training pipeline for La Liga match prediction models.

Trains classifiers (winner) and regressors (goals, cards) with
temporal train/val/test splits.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from ..config import get_settings
from ..features.feature_store import load_features
from .base import BasePredictor
from .classifiers import (
    EnsembleWinner,
    HomeAlwaysWinsBaseline,
    RandomForestWinner,
    XGBoostWinner,
)
from .evaluate import evaluate_classifier, evaluate_regressor
from .regressors import MeanBaseline, XGBoostCards, XGBoostGoals

logger = logging.getLogger(__name__)

# Metadata columns (not features)
META_COLS = {
    "match_id", "match_date", "season_code", "home_team", "away_team",
    "target_result", "target_total_goals", "target_total_cards",
}

MODEL_REGISTRY: dict[str, dict[str, type]] = {
    "winner": {
        "baseline": HomeAlwaysWinsBaseline,
        "rf": RandomForestWinner,
        "xgboost": XGBoostWinner,
        "ensemble": EnsembleWinner,
    },
    "goals": {
        "baseline": MeanBaseline,
        "xgboost": XGBoostGoals,
    },
    "cards": {
        "baseline": MeanBaseline,
        "xgboost": XGBoostCards,
    },
}


def prepare_data(
    df: pd.DataFrame,
    target: str,
    train_seasons: list[str],
    val_seasons: list[str],
    test_seasons: list[str],
) -> tuple:
    """Split features into train/val/test by season.

    Returns:
        (X_train, y_train, X_val, y_val, X_test, y_test)
    """
    target_col = f"target_{target}"

    # Drop rows with missing target
    df_clean = df.dropna(subset=[target_col])

    feature_cols = [c for c in df_clean.columns if c not in META_COLS]

    train_mask = df_clean["season_code"].isin(train_seasons)
    val_mask = df_clean["season_code"].isin(val_seasons)
    test_mask = df_clean["season_code"].isin(test_seasons)

    X_train = df_clean.loc[train_mask, feature_cols].copy()
    y_train = df_clean.loc[train_mask, target_col].copy()
    X_val = df_clean.loc[val_mask, feature_cols].copy()
    y_val = df_clean.loc[val_mask, target_col].copy()
    X_test = df_clean.loc[test_mask, feature_cols].copy()
    y_test = df_clean.loc[test_mask, target_col].copy()

    # Fill NaN features with median (from training set only)
    medians = X_train.median()
    X_train = X_train.fillna(medians)
    X_val = X_val.fillna(medians)
    X_test = X_test.fillna(medians)

    logger.info(
        f"Data split for target={target}: "
        f"train={len(X_train)}, val={len(X_val)}, test={len(X_test)}"
    )
    return X_train, y_train, X_val, y_val, X_test, y_test


def train_model(
    target: str,
    model_name: str,
    df: pd.DataFrame,
    train_seasons: Optional[list[str]] = None,
    val_seasons: Optional[list[str]] = None,
    test_seasons: Optional[list[str]] = None,
    save_dir: Optional[Path] = None,
) -> tuple[BasePredictor, dict]:
    """Train a single model for a target.

    Args:
        target: "result", "total_goals", or "total_cards"
        model_name: Model key from MODEL_REGISTRY
        df: Feature DataFrame
        train_seasons: Seasons for training
        val_seasons: Seasons for validation
        test_seasons: Seasons for testing

    Returns:
        (trained_model, metrics_dict)
    """
    settings = get_settings()

    train_s = train_seasons or [s.strip() for s in settings.TRAIN_SEASONS.split(",")]
    val_s = val_seasons or [s.strip() for s in settings.VAL_SEASONS.split(",")]
    test_s = test_seasons or [s.strip() for s in settings.TEST_SEASONS.split(",")]
    save_path = save_dir or settings.MODEL_PATH

    X_train, y_train, X_val, y_val, X_test, y_test = prepare_data(
        df, target, train_s, val_s, test_s
    )

    # Map target name to registry key
    registry_key = {
        "result": "winner",
        "total_goals": "goals",
        "total_cards": "cards",
    }.get(target, target)

    model_cls = MODEL_REGISTRY.get(registry_key, {}).get(model_name)
    if model_cls is None:
        raise ValueError(f"Unknown model: target={target}, model={model_name}")

    if model_name == "baseline" and target in ("goals", "cards"):
        model = model_cls(target_name=target)
    else:
        model = model_cls()

    logger.info(f"Training {model.name} for target={target}...")
    model.fit(X_train, y_train, X_val, y_val)

    # Evaluate on validation and test sets
    metrics: dict = {"model": model.name, "target": target}

    if target == "result":
        if len(y_val) > 0:
            val_metrics = evaluate_classifier(model, X_val, y_val)
            metrics["val"] = val_metrics
            logger.info(
                f"  Val: accuracy={val_metrics['accuracy']:.3f}, "
                f"f1_macro={val_metrics['f1_macro']:.3f}"
            )
        if len(y_test) > 0:
            test_metrics = evaluate_classifier(model, X_test, y_test)
            metrics["test"] = test_metrics
            logger.info(
                f"  Test: accuracy={test_metrics['accuracy']:.3f}, "
                f"f1_macro={test_metrics['f1_macro']:.3f}"
            )
    else:
        if len(y_val) > 0:
            val_metrics = evaluate_regressor(model, X_val, y_val)
            metrics["val"] = val_metrics
            logger.info(
                f"  Val: rmse={val_metrics['rmse']:.3f}, mae={val_metrics['mae']:.3f}"
            )
        if len(y_test) > 0:
            test_metrics = evaluate_regressor(model, X_test, y_test)
            metrics["test"] = test_metrics
            logger.info(
                f"  Test: rmse={test_metrics['rmse']:.3f}, mae={test_metrics['mae']:.3f}"
            )

    # Save model
    model_path = Path(save_path) / f"{target}_{model_name}.joblib"
    model.save(model_path)

    return model, metrics


def train_all(
    df: pd.DataFrame,
    targets: Optional[list[str]] = None,
    model_names: Optional[list[str]] = None,
) -> dict:
    """Train all models for all targets.

    Returns dict of {target: {model_name: metrics}}.
    """
    targets = targets or ["result", "total_goals", "total_cards"]
    all_results: dict = {}

    for target in targets:
        target_key = "winner" if target == "result" else target.replace("total_", "")
        available_models = list(MODEL_REGISTRY.get(target_key, {}).keys())
        models_to_train = model_names or available_models

        all_results[target] = {}
        for model_name in models_to_train:
            if model_name not in MODEL_REGISTRY.get(target_key, {}):
                continue
            _, metrics = train_model(target, model_name, df)
            all_results[target][model_name] = metrics

    return all_results


# ================================================================
# CLI
# ================================================================


def main() -> None:
    """CLI entry point for model training."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Train La Liga prediction models")
    parser.add_argument(
        "--target",
        choices=["winner", "goals", "cards", "all"],
        default="all",
        help="Which target to train (default: all)",
    )
    parser.add_argument(
        "--model",
        choices=["baseline", "rf", "xgboost", "ensemble", "all"],
        default="all",
        help="Which model to train (default: all)",
    )
    parser.add_argument(
        "--features",
        type=str,
        default=None,
        help="Path to features parquet file",
    )

    args = parser.parse_args()
    settings = get_settings()

    features_path = args.features or str(settings.FEATURE_CACHE_DIR / "features.parquet")
    df = load_features(features_path)

    # Map CLI target names to internal names
    target_map = {
        "winner": ["result"],
        "goals": ["total_goals"],
        "cards": ["total_cards"],
        "all": ["result", "total_goals", "total_cards"],
    }
    targets = target_map[args.target]
    model_names = None if args.model == "all" else [args.model]

    logger.info("=" * 60)
    logger.info("La Liga ML Training Pipeline")
    logger.info("=" * 60)

    results = train_all(df, targets=targets, model_names=model_names)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Training Summary")
    logger.info("=" * 60)
    for target, models in results.items():
        for model_name, metrics in models.items():
            test = metrics.get("test", {})
            if "accuracy" in test:
                logger.info(
                    f"  {target}/{model_name}: "
                    f"accuracy={test['accuracy']:.3f}, f1={test['f1_macro']:.3f}"
                )
            elif "rmse" in test:
                logger.info(
                    f"  {target}/{model_name}: "
                    f"rmse={test['rmse']:.3f}, mae={test['mae']:.3f}"
                )

    # Save results summary
    results_path = settings.MODEL_PATH / "training_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(results, indent=2, default=str))
    logger.info(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
