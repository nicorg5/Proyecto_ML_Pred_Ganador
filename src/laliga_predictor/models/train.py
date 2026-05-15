"""
Training pipeline for La Liga match prediction models.

Trains classifiers (winner) and over/under classifiers (goals, cards) with
temporal train/val/test splits. Tracks experiments with MLflow.
"""

import logging
import os
from functools import partial
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd

from ..config import get_settings
from ..features.feature_selection import load_selected_features
from ..features.feature_store import load_features
from .base import BasePredictor
from .calibration import CalibratedPredictor
from .classifiers import (
    EnsembleWinner,
    HomeAlwaysWinsBaseline,
    LightGBMWinner,
    RandomForestWinner,
    XGBoostWinner,
)
from .evaluate import evaluate_binary_classifier, evaluate_classifier
from .over_under import LightGBMOverUnder, OverUnderBaseline, XGBoostOverUnder
from .tuning import load_tuned_params

logger = logging.getLogger(__name__)

# Configure MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("laliga-predictor")

# Metadata columns (not features)
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

# Over/Under lines to train
GOALS_LINES = [1.5, 2.5, 3.5]
CARDS_LINES = [3.5, 4.5, 5.5]

MODEL_REGISTRY: dict[str, dict[str, type]] = {
    "winner": {
        "baseline": HomeAlwaysWinsBaseline,
        "rf": RandomForestWinner,
        "xgboost": XGBoostWinner,
        "lightgbm": LightGBMWinner,
        "ensemble": EnsembleWinner,
    },
}

# Dynamically register over/under models for each line
for _line in GOALS_LINES:
    key = f"goals_over_{_line}"
    MODEL_REGISTRY[key] = {
        "baseline": partial(OverUnderBaseline, stat_type="goals", line=_line),
        "xgboost": partial(XGBoostOverUnder, stat_type="goals", line=_line),
        "lightgbm": partial(LightGBMOverUnder, stat_type="goals", line=_line),
    }

for _line in CARDS_LINES:
    key = f"cards_over_{_line}"
    MODEL_REGISTRY[key] = {
        "baseline": partial(OverUnderBaseline, stat_type="cards", line=_line),
        "xgboost": partial(XGBoostOverUnder, stat_type="cards", line=_line),
        "lightgbm": partial(LightGBMOverUnder, stat_type="cards", line=_line),
    }


def _target_name_to_registry_key(target: str) -> str:
    """Map a target name to its MODEL_REGISTRY key."""
    if target == "result":
        return "winner"
    return target


def _get_target_col_and_transform(target: str, df: pd.DataFrame):
    """Get the column and optional binary transform for a target.

    For 'result': uses 'target_result' as-is (multi-class).
    For 'goals_over_2.5': uses 'target_total_goals' > 2.5 → binary 0/1.
    For 'cards_over_4.5': uses 'target_total_cards' > 4.5 → binary 0/1.
    """
    if target == "result":
        return "target_result", None

    # Parse over/under target: "goals_over_2.5" → ("total_goals", 2.5)
    parts = target.split("_over_")
    if len(parts) == 2:
        stat = parts[0]  # "goals" or "cards"
        line = float(parts[1])
        col = f"target_total_{stat}"
        return col, line

    raise ValueError(f"Unknown target format: {target}")


def prepare_data(
    df: pd.DataFrame,
    target: str,
    train_seasons: list[str],
    val_seasons: list[str],
    test_seasons: list[str],
) -> tuple:
    """Split features into train/val/test by season.

    For over/under targets, creates binary labels from the continuous values.

    Returns:
        (X_train, y_train, X_val, y_val, X_test, y_test)
    """
    target_col, line = _get_target_col_and_transform(target, df)

    # Drop rows with missing target
    df_clean = df.dropna(subset=[target_col])

    feature_cols = [c for c in df_clean.columns if c not in META_COLS]

    # Apply feature selection if available
    selected = load_selected_features(target)
    if selected is not None:
        feature_cols = [c for c in selected if c in feature_cols]
        logger.info(f"Using {len(feature_cols)} selected features for target={target}")

    train_mask = df_clean["season_code"].isin(train_seasons)
    val_mask = df_clean["season_code"].isin(val_seasons)
    test_mask = df_clean["season_code"].isin(test_seasons)

    X_train = df_clean.loc[train_mask, feature_cols].copy()
    y_train = df_clean.loc[train_mask, target_col].copy()
    X_val = df_clean.loc[val_mask, feature_cols].copy()
    y_val = df_clean.loc[val_mask, target_col].copy()
    X_test = df_clean.loc[test_mask, feature_cols].copy()
    y_test = df_clean.loc[test_mask, target_col].copy()

    # Apply binary transform for over/under targets
    if line is not None:
        y_train = (y_train > line).astype(int)
        y_val = (y_val > line).astype(int)
        y_test = (y_test > line).astype(int)
        logger.info(
            f"Binary target (>{line}): "
            f"train over_rate={y_train.mean():.2%}, "
            f"val over_rate={y_val.mean():.2%}, "
            f"test over_rate={y_test.mean():.2%}"
        )

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


def _is_over_under_target(target: str) -> bool:
    """Check if a target is an over/under binary classification target."""
    return "_over_" in target


def train_model(
    target: str,
    model_name: str,
    df: pd.DataFrame,
    train_seasons: list[str] | None = None,
    val_seasons: list[str] | None = None,
    test_seasons: list[str] | None = None,
    save_dir: Path | None = None,
    use_mlflow: bool = True,
) -> tuple[BasePredictor, dict]:
    """Train a single model for a target.

    Args:
        target: "result", "goals_over_2.5", "cards_over_4.5", etc.
        model_name: Model key from MODEL_REGISTRY
        df: Feature DataFrame
        train_seasons: Seasons for training
        val_seasons: Seasons for validation
        test_seasons: Seasons for testing
        use_mlflow: Whether to log to MLflow

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

    registry_key = _target_name_to_registry_key(target)
    model_factory = MODEL_REGISTRY.get(registry_key, {}).get(model_name)
    if model_factory is None:
        raise ValueError(f"Unknown model: target={target}, model={model_name}")

    # Instantiate model, applying tuned params if available
    tuned = load_tuned_params(target)
    if tuned and model_name == "xgboost":
        best_params = tuned.get("best_params", {})
        logger.info(f"Applying tuned params for {target}: {best_params}")
        model = model_factory(**best_params)
    else:
        model = model_factory()

    # Wrap non-baseline models with calibration
    is_baseline = model_name == "baseline"
    if not is_baseline and len(X_val) > 0:
        n_classes = 3 if target == "result" else 2
        model = CalibratedPredictor(model, n_classes=n_classes)

    # Start MLflow run if enabled
    run_context = mlflow.start_run(run_name=f"{target}_{model_name}") if use_mlflow else None
    if use_mlflow:
        mlflow.log_param("target", target)
        mlflow.log_param("model_type", model_name)
        mlflow.log_param("train_seasons", ",".join(train_s))
        mlflow.log_param("val_seasons", ",".join(val_s))
        mlflow.log_param("test_seasons", ",".join(test_s))
        mlflow.log_param("n_features", X_train.shape[1])
        mlflow.log_param("n_train_samples", len(X_train))
        mlflow.log_param("n_val_samples", len(X_val))
        mlflow.log_param("n_test_samples", len(X_test))

    logger.info(f"Training {model.name} for target={target}...")
    model.fit(X_train, y_train, X_val, y_val)

    # Evaluate on validation and test sets
    metrics: dict = {"model": model.name, "target": target}

    if target == "result":
        # Multi-class classification (winner)
        if len(y_val) > 0:
            val_metrics = evaluate_classifier(model, X_val, y_val)
            metrics["val"] = val_metrics
            logger.info(
                f"  Val: accuracy={val_metrics['accuracy']:.3f}, "
                f"f1_macro={val_metrics['f1_macro']:.3f}"
            )
            if use_mlflow:
                mlflow.log_metric("val_accuracy", val_metrics["accuracy"])
                mlflow.log_metric("val_f1_macro", val_metrics["f1_macro"])
                mlflow.log_metric("val_precision", val_metrics.get("precision", 0))
                mlflow.log_metric("val_recall", val_metrics.get("recall", 0))
        if len(y_test) > 0:
            test_metrics = evaluate_classifier(model, X_test, y_test)
            metrics["test"] = test_metrics
            logger.info(
                f"  Test: accuracy={test_metrics['accuracy']:.3f}, "
                f"f1_macro={test_metrics['f1_macro']:.3f}"
            )
            if use_mlflow:
                mlflow.log_metric("test_accuracy", test_metrics["accuracy"])
                mlflow.log_metric("test_f1_macro", test_metrics["f1_macro"])
    elif _is_over_under_target(target):
        # Binary classification (over/under)
        if len(y_val) > 0:
            val_metrics = evaluate_binary_classifier(model, X_val, y_val)
            metrics["val"] = val_metrics
            logger.info(
                f"  Val: accuracy={val_metrics['accuracy']:.3f}, "
                f"f1={val_metrics['f1']:.3f}, "
                f"auc_roc={val_metrics['auc_roc']:.3f}"
            )
            if use_mlflow:
                mlflow.log_metric("val_accuracy", val_metrics["accuracy"])
                mlflow.log_metric("val_f1", val_metrics["f1"])
                mlflow.log_metric("val_auc_roc", val_metrics["auc_roc"])
        if len(y_test) > 0:
            test_metrics = evaluate_binary_classifier(model, X_test, y_test)
            metrics["test"] = test_metrics
            logger.info(
                f"  Test: accuracy={test_metrics['accuracy']:.3f}, "
                f"f1={test_metrics['f1']:.3f}, "
                f"auc_roc={test_metrics['auc_roc']:.3f}"
            )
            if use_mlflow:
                mlflow.log_metric("test_accuracy", test_metrics["accuracy"])
                mlflow.log_metric("test_f1", test_metrics["f1"])
                mlflow.log_metric("test_auc_roc", test_metrics["auc_roc"])

    # Save model
    model_path = Path(save_path) / f"{target}_{model_name}.joblib"
    model.save(model_path)

    # Log model to MLflow
    if use_mlflow:
        mlflow.set_tag("framework", "scikit-learn")
        mlflow.set_tag("calibrated", "no" if is_baseline else "yes")
        mlflow.end_run()

    return model, metrics


def train_all(
    df: pd.DataFrame,
    targets: list[str] | None = None,
    model_names: list[str] | None = None,
) -> dict:
    """Train all models for all targets.

    Returns dict of {target: {model_name: metrics}}.
    """
    if targets is None:
        targets = ["result"]
        targets += [f"goals_over_{line}" for line in GOALS_LINES]
        targets += [f"cards_over_{line}" for line in CARDS_LINES]

    all_results: dict = {}

    for target in targets:
        registry_key = _target_name_to_registry_key(target)
        available_models = list(MODEL_REGISTRY.get(registry_key, {}).keys())
        models_to_train = model_names or available_models

        all_results[target] = {}
        for model_name in models_to_train:
            if model_name not in MODEL_REGISTRY.get(registry_key, {}):
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
        choices=["winner", "goals-ou", "cards-ou", "all"],
        default="all",
        help="Which target to train (default: all)",
    )
    parser.add_argument(
        "--model",
        choices=["baseline", "rf", "xgboost", "lightgbm", "ensemble", "all"],
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

    # Map CLI target names to internal target list
    target_map = {
        "winner": ["result"],
        "goals-ou": [f"goals_over_{line}" for line in GOALS_LINES],
        "cards-ou": [f"cards_over_{line}" for line in CARDS_LINES],
        "all": None,  # train_all will use all targets
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
            if "accuracy" in test and "f1_macro" in test:
                # Multi-class (winner)
                logger.info(
                    f"  {target}/{model_name}: "
                    f"accuracy={test['accuracy']:.3f}, f1={test['f1_macro']:.3f}"
                )
            elif "accuracy" in test and "auc_roc" in test:
                # Binary (over/under)
                logger.info(
                    f"  {target}/{model_name}: "
                    f"accuracy={test['accuracy']:.3f}, "
                    f"f1={test['f1']:.3f}, AUC={test['auc_roc']:.3f}"
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
