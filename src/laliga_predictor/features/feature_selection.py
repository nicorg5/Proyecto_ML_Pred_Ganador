"""
Feature selection for La Liga prediction models.

Reduces features using importance-based and correlation-based filtering
to improve model generalization and reduce overfitting.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from ..config import get_settings

logger = logging.getLogger(__name__)


def select_features(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    target_type: str = "multiclass",
    importance_threshold: float = 0.001,
    correlation_threshold: float = 0.90,
) -> tuple[list[str], dict]:
    """Select features using importance and correlation filtering.

    Steps:
        1. Train a quick XGBoost to get feature importances
        2. Remove features with importance < threshold
        3. Among highly correlated pairs (|r| > threshold), keep the more important one

    Args:
        X_train: Training feature matrix
        y_train: Training labels
        target_type: "multiclass" for winner, "binary" for over/under
        importance_threshold: Minimum feature importance to keep
        correlation_threshold: Maximum pairwise correlation allowed

    Returns:
        (selected_feature_names, metadata_dict)
    """
    settings = get_settings()
    n_original = X_train.shape[1]

    # Step 1: Quick XGBoost for importance
    if target_type == "multiclass":
        model = XGBClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            objective="multi:softprob", num_class=3,
            random_state=settings.RANDOM_STATE, n_jobs=-1, verbosity=0,
        )
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        le.fit(["A", "D", "H"])
        y_enc = le.transform(y_train)
    else:
        model = XGBClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            objective="binary:logistic",
            random_state=settings.RANDOM_STATE, n_jobs=-1, verbosity=0,
        )
        y_enc = y_train

    model.fit(X_train.fillna(0), y_enc)
    importances = pd.Series(model.feature_importances_, index=X_train.columns)

    # Step 2: Remove low-importance features
    important_mask = importances >= importance_threshold
    kept_features = importances[important_mask].sort_values(ascending=False)
    removed_low = list(importances[~important_mask].index)

    logger.info(f"Importance filter: {len(kept_features)}/{n_original} features kept "
                f"(threshold={importance_threshold})")

    # Step 3: Remove highly correlated features (keep the more important one)
    X_kept = X_train[kept_features.index].fillna(0)
    corr_matrix = X_kept.corr().abs()

    # Find pairs above threshold
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    removed_corr = set()

    for col in upper.columns:
        if col in removed_corr:
            continue
        correlated = upper.index[upper[col] > correlation_threshold].tolist()
        for c in correlated:
            if c in removed_corr:
                continue
            # Remove the less important one
            if importances[col] >= importances[c]:
                removed_corr.add(c)
            else:
                removed_corr.add(col)
                break

    selected = [f for f in kept_features.index if f not in removed_corr]
    logger.info(f"Correlation filter: {len(selected)}/{len(kept_features)} features kept "
                f"(threshold={correlation_threshold})")

    metadata = {
        "n_original": n_original,
        "n_after_importance": len(kept_features),
        "n_selected": len(selected),
        "removed_low_importance": removed_low,
        "removed_correlated": list(removed_corr),
        "importance_threshold": importance_threshold,
        "correlation_threshold": correlation_threshold,
    }

    return selected, metadata


def save_selected_features(
    features: list[str], metadata: dict, target: str, output_dir: Optional[Path] = None
) -> Path:
    """Save selected features to JSON."""
    settings = get_settings()
    out_dir = output_dir or settings.FEATURE_CACHE_DIR
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    path = Path(out_dir) / f"selected_features_{target}.json"
    data = {"features": features, "metadata": metadata}
    path.write_text(json.dumps(data, indent=2))
    logger.info(f"Saved {len(features)} selected features to {path}")
    return path


def load_selected_features(target: str, input_dir: Optional[Path] = None) -> Optional[list[str]]:
    """Load selected features from JSON. Returns None if file doesn't exist."""
    settings = get_settings()
    in_dir = input_dir or settings.FEATURE_CACHE_DIR
    path = Path(in_dir) / f"selected_features_{target}.json"

    if not path.exists():
        return None

    data = json.loads(path.read_text())
    features = data["features"]
    logger.info(f"Loaded {len(features)} selected features from {path}")
    return features


# ================================================================
# CLI
# ================================================================


def main() -> None:
    """CLI for running feature selection."""
    import argparse

    from ..models.train import CARDS_LINES, GOALS_LINES, META_COLS, prepare_data

    parser = argparse.ArgumentParser(description="Select features for La Liga models")
    parser.add_argument(
        "--target",
        choices=["winner", "goals-ou", "cards-ou", "all"],
        default="all",
    )
    parser.add_argument("--features", type=str, default=None)

    args = parser.parse_args()
    settings = get_settings()

    from .feature_store import load_features
    features_path = args.features or str(settings.FEATURE_CACHE_DIR / "features.parquet")
    df = load_features(features_path)

    train_s = [s.strip() for s in settings.TRAIN_SEASONS.split(",")]
    val_s = [s.strip() for s in settings.VAL_SEASONS.split(",")]
    test_s = [s.strip() for s in settings.TEST_SEASONS.split(",")]

    # Map targets
    targets_map = {
        "winner": [("result", "multiclass")],
        "goals-ou": [(f"goals_over_{l}", "binary") for l in GOALS_LINES],
        "cards-ou": [(f"cards_over_{l}", "binary") for l in CARDS_LINES],
    }
    if args.target == "all":
        target_list = targets_map["winner"] + targets_map["goals-ou"] + targets_map["cards-ou"]
    else:
        target_list = targets_map[args.target]

    for target, target_type in target_list:
        logger.info(f"\n{'='*40}")
        logger.info(f"Feature selection for: {target}")
        logger.info(f"{'='*40}")

        X_train, y_train, *_ = prepare_data(df, target, train_s, val_s, test_s)
        selected, meta = select_features(X_train, y_train, target_type=target_type)
        save_selected_features(selected, meta, target)
        logger.info(f"  {target}: {meta['n_original']} → {meta['n_selected']} features")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
