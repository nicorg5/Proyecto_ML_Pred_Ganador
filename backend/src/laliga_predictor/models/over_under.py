"""
Over/Under binary classification models for goals and cards prediction.

Each model predicts P(over) for a specific line (e.g., over/under 2.5 goals).
"""

import logging

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier

from ..config import get_settings
from .base import BasePredictor

logger = logging.getLogger(__name__)


class OverUnderBaseline(BasePredictor):
    """Baseline: always predicts the majority class from training data."""

    def __init__(self, stat_type: str = "goals", line: float = 2.5) -> None:
        super().__init__(f"Baseline_O/U_{stat_type}_{line}", "classifier")
        self.stat_type = stat_type
        self.line = line
        self._over_rate: float = 0.5

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)
        self._over_rate = float(y_train.mean())
        self.is_fitted = True
        self.metadata["line"] = self.line
        self.metadata["stat_type"] = self.stat_type
        self.metadata["train_over_rate"] = self._over_rate
        return self

    def predict(self, X):
        # Predict majority class
        if self._over_rate >= 0.5:
            return np.ones(len(X), dtype=int)
        return np.zeros(len(X), dtype=int)

    def predict_proba(self, X):
        # [P(under), P(over)]
        proba = np.zeros((len(X), 2))
        proba[:, 0] = 1 - self._over_rate
        proba[:, 1] = self._over_rate
        return proba

    def get_feature_importance(self):
        return pd.DataFrame({"feature": self.feature_names, "importance": 0.0})


class XGBoostOverUnder(BasePredictor):
    """XGBoost binary classifier for over/under prediction.

    Args:
        stat_type: "goals" or "cards"
        line: The over/under line (e.g., 2.5, 3.5)
    """

    def __init__(self, stat_type: str = "goals", line: float = 2.5, **kwargs) -> None:
        super().__init__(f"XGBoost_O/U_{stat_type}_{line}", "classifier")
        self.stat_type = stat_type
        self.line = line
        settings = get_settings()
        defaults = {
            "n_estimators": 500,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.5,
            "reg_lambda": 3.0,
            "min_child_weight": 5,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "random_state": settings.RANDOM_STATE,
            "n_jobs": -1,
            "verbosity": 0,
        }
        defaults.update(kwargs)
        self._xgb_params = defaults

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)

        params = dict(self._xgb_params)
        fit_params: dict = {}
        if X_val is not None and y_val is not None:
            fit_params["eval_set"] = [(X_val, y_val)]
            params["early_stopping_rounds"] = 50

        # Auto-compute scale_pos_weight for class imbalance
        if "scale_pos_weight" not in params or params.get("scale_pos_weight") is None:
            n_neg = int((y_train == 0).sum())
            n_pos = int((y_train == 1).sum())
            if n_pos > 0:
                params["scale_pos_weight"] = n_neg / n_pos
                logger.info(
                    f"{self.name}: auto scale_pos_weight={params['scale_pos_weight']:.3f} "
                    f"(neg={n_neg}, pos={n_pos})"
                )

        self.model = XGBClassifier(**params)
        self.model.fit(X_train, y_train, **fit_params)
        self.is_fitted = True
        self.metadata["line"] = self.line
        self.metadata["stat_type"] = self.stat_type
        self.metadata["params"] = self.model.get_params()
        self.metadata["best_iteration"] = getattr(self.model, "best_iteration", None)
        return self

    def predict(self, X):
        return self.model.predict(X)

    def predict_proba(self, X):
        # Returns [P(under), P(over)]
        return self.model.predict_proba(X)

    def get_feature_importance(self):
        return pd.DataFrame(
            {
                "feature": self.feature_names,
                "importance": self.model.feature_importances_,
            }
        ).sort_values("importance", ascending=False)


class LightGBMOverUnder(BasePredictor):
    """LightGBM binary classifier for over/under prediction."""

    def __init__(self, stat_type: str = "goals", line: float = 2.5, **kwargs) -> None:
        super().__init__(f"LightGBM_O/U_{stat_type}_{line}", "classifier")
        self.stat_type = stat_type
        self.line = line
        settings = get_settings()
        defaults = {
            "n_estimators": 500,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.5,
            "reg_lambda": 3.0,
            "min_child_samples": 20,
            "num_leaves": 31,
            "objective": "binary",
            "metric": "binary_logloss",
            "random_state": settings.RANDOM_STATE,
            "n_jobs": -1,
            "verbosity": -1,
        }
        defaults.update(kwargs)
        self._lgb_params = defaults

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)

        params = dict(self._lgb_params)
        fit_params: dict = {}
        if X_val is not None and y_val is not None:
            fit_params["eval_set"] = [(X_val, y_val)]

        # Auto-compute scale_pos_weight for class imbalance
        if "scale_pos_weight" not in params or params.get("scale_pos_weight") is None:
            n_neg = int((y_train == 0).sum())
            n_pos = int((y_train == 1).sum())
            if n_pos > 0:
                params["scale_pos_weight"] = n_neg / n_pos

        self.model = LGBMClassifier(**params)
        self.model.fit(X_train, y_train, **fit_params)
        self.is_fitted = True
        self.metadata["line"] = self.line
        self.metadata["stat_type"] = self.stat_type
        self.metadata["params"] = self.model.get_params()
        return self

    def predict(self, X):
        return self.model.predict(X)

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def get_feature_importance(self):
        return pd.DataFrame(
            {
                "feature": self.feature_names,
                "importance": self.model.feature_importances_,
            }
        ).sort_values("importance", ascending=False)
