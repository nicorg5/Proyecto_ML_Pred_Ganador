"""
Optuna hyperparameter tuning with temporal cross-validation.

Tunes XGBoost parameters using SeasonalTimeSeriesSplit to respect
the temporal nature of football data.
"""

import json
import logging
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import f1_score, log_loss
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from ..config import get_settings
from .temporal_cv import SeasonalTimeSeriesSplit

logger = logging.getLogger(__name__)

# Suppress Optuna's verbose logging
optuna.logging.set_verbosity(optuna.logging.WARNING)


def _xgb_search_space(trial: optuna.Trial) -> dict:
    """Define XGBoost hyperparameter search space."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 800),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.01, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0.0, 2.0),
    }


def tune_xgboost(
    X: pd.DataFrame,
    y: pd.Series,
    season_codes: pd.Series,
    target_type: str = "multiclass",
    n_trials: int | None = None,
    scale_pos_weight: float | None = None,
) -> dict:
    """Tune XGBoost hyperparameters using Optuna with temporal CV.

    Args:
        X: Feature matrix (all seasons for CV)
        y: Target variable
        season_codes: Season code per row
        target_type: "multiclass" for winner, "binary" for O/U
        n_trials: Number of Optuna trials (default from config)
        scale_pos_weight: For imbalanced binary targets

    Returns:
        Dict with best_params, best_score, study summary
    """
    settings = get_settings()
    n_trials = n_trials or settings.N_TUNING_TRIALS
    cv = SeasonalTimeSeriesSplit(min_train_seasons=3)

    if target_type == "multiclass":
        le = LabelEncoder()
        le.fit(["A", "D", "H"])
        y_encoded = pd.Series(le.transform(y), index=y.index)
    else:
        y_encoded = y

    def objective(trial: optuna.Trial) -> float:
        params = _xgb_search_space(trial)

        if target_type == "multiclass":
            params["objective"] = "multi:softprob"
            params["num_class"] = 3
            params["eval_metric"] = "mlogloss"
        else:
            params["objective"] = "binary:logistic"
            params["eval_metric"] = "logloss"
            if scale_pos_weight is not None:
                params["scale_pos_weight"] = scale_pos_weight

        params["random_state"] = settings.RANDOM_STATE
        params["n_jobs"] = -1
        params["verbosity"] = 0

        scores = []
        for train_idx, val_idx in cv.split(X, season_codes):
            X_train_fold = X.iloc[train_idx].fillna(0)
            y_train_fold = y_encoded.iloc[train_idx]
            X_val_fold = X.iloc[val_idx].fillna(0)
            y_val_fold = y_encoded.iloc[val_idx]

            model = XGBClassifier(**params)
            model.fit(
                X_train_fold,
                y_train_fold,
                eval_set=[(X_val_fold, y_val_fold)],
                verbose=False,
            )

            proba = model.predict_proba(X_val_fold)

            if target_type == "multiclass":
                # Optimize f1_macro (critical for draw prediction)
                preds = le.inverse_transform(proba.argmax(axis=1))
                y_val_original = le.inverse_transform(y_val_fold)
                score = f1_score(y_val_original, preds, average="macro", zero_division=0)
            else:
                # Optimize negative log_loss (lower is better)
                score = -log_loss(y_val_fold, proba[:, 1])

            scores.append(score)

        return float(np.mean(scores))

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    best = study.best_trial
    logger.info(f"Optuna tuning: best score={best.value:.4f} after {n_trials} trials")
    logger.info(f"Best params: {best.params}")

    return {
        "best_params": best.params,
        "best_score": best.value,
        "n_trials": n_trials,
    }


def save_tuned_params(params: dict, target: str, output_dir: Path | None = None) -> Path:
    """Save tuned parameters to JSON."""
    settings = get_settings()
    out_dir = output_dir or settings.MODEL_PATH
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    path = Path(out_dir) / f"tuned_params_{target}.json"
    path.write_text(json.dumps(params, indent=2))
    logger.info(f"Saved tuned params to {path}")
    return path


def load_tuned_params(target: str, input_dir: Path | None = None) -> dict | None:
    """Load tuned parameters from JSON. Returns None if not found."""
    settings = get_settings()
    in_dir = input_dir or settings.MODEL_PATH
    path = Path(in_dir) / f"tuned_params_{target}.json"

    if not path.exists():
        return None

    data = json.loads(path.read_text())
    logger.info(f"Loaded tuned params from {path}: {data.get('best_params', {})}")
    return data


# ================================================================
# CLI
# ================================================================


def main() -> None:
    """CLI for Optuna hyperparameter tuning."""
    import argparse

    from ..features.feature_selection import load_selected_features
    from ..features.feature_store import load_features
    from .train import CARDS_LINES, GOALS_LINES, META_COLS

    parser = argparse.ArgumentParser(description="Optuna hyperparameter tuning")
    parser.add_argument(
        "--target",
        choices=["winner", "goals-ou", "cards-ou", "all"],
        default="all",
    )
    parser.add_argument("--trials", type=int, default=None)
    parser.add_argument("--features", type=str, default=None)

    args = parser.parse_args()
    settings = get_settings()

    features_path = args.features or str(settings.FEATURE_CACHE_DIR / "features.parquet")
    df = load_features(features_path)

    train_s = [s.strip() for s in settings.TRAIN_SEASONS.split(",")]
    val_s = [s.strip() for s in settings.VAL_SEASONS.split(",")]

    # For tuning, combine train + val seasons for CV
    all_tune_seasons = train_s + val_s

    # Map targets
    targets_map = {
        "winner": [("result", "multiclass")],
        "goals-ou": [(f"goals_over_{line}", "binary") for line in GOALS_LINES],
        "cards-ou": [(f"cards_over_{line}", "binary") for line in CARDS_LINES],
    }
    if args.target == "all":
        target_list = targets_map["winner"] + targets_map["goals-ou"] + targets_map["cards-ou"]
    else:
        target_list = targets_map[args.target]

    from .train import _get_target_col_and_transform

    for target, target_type in target_list:
        logger.info(f"\n{'='*40}")
        logger.info(f"Tuning XGBoost for: {target}")
        logger.info(f"{'='*40}")

        target_col, line = _get_target_col_and_transform(target, df)
        df_clean = df.dropna(subset=[target_col])

        # Get feature columns
        feature_cols = [c for c in df_clean.columns if c not in META_COLS]
        selected = load_selected_features(target)
        if selected is not None:
            feature_cols = [c for c in selected if c in feature_cols]

        mask = df_clean["season_code"].isin(all_tune_seasons)
        X_tune = df_clean.loc[mask, feature_cols].copy()
        y_tune = df_clean.loc[mask, target_col].copy()
        seasons_tune = df_clean.loc[mask, "season_code"].copy()

        if line is not None:
            y_tune = (y_tune > line).astype(int)

        # Calculate scale_pos_weight for imbalanced binary
        spw = None
        if target_type == "binary":
            n_neg = (y_tune == 0).sum()
            n_pos = (y_tune == 1).sum()
            if n_pos > 0:
                spw = n_neg / n_pos

        result = tune_xgboost(
            X_tune,
            y_tune,
            seasons_tune,
            target_type=target_type,
            n_trials=args.trials,
            scale_pos_weight=spw,
        )
        save_tuned_params(result, target)
        logger.info(f"  {target}: best_score={result['best_score']:.4f}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
