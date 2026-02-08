"""
Regression models for total goals and total cards prediction.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ..config import get_settings
from .base import BasePredictor

logger = logging.getLogger(__name__)


class MeanBaseline(BasePredictor):
    """Baseline: always predicts the training set mean."""

    def __init__(self, target_name: str = "value") -> None:
        super().__init__(f"MeanBaseline_{target_name}", "regressor")
        self._mean: float = 0.0

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)
        self._mean = float(y_train.mean())
        self.is_fitted = True
        self.metadata["train_mean"] = self._mean
        return self

    def predict(self, X):
        return np.full(len(X), self._mean)

    def get_feature_importance(self):
        return pd.DataFrame({"feature": self.feature_names, "importance": 0.0})


class XGBoostGoals(BasePredictor):
    """XGBoost regressor for total goals prediction."""

    def __init__(self, **kwargs) -> None:
        super().__init__("XGBoost_Goals", "regressor")
        settings = get_settings()
        defaults = {
            "n_estimators": 500,
            "max_depth": 4,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_alpha": 1.0,
            "reg_lambda": 5.0,
            "min_child_weight": 10,
            "objective": "reg:squarederror",
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

        self.model = XGBRegressor(**params)
        self.model.fit(X_train, y_train, **fit_params)
        self.metadata["best_iteration"] = getattr(self.model, "best_iteration", None)
        self.is_fitted = True
        self.metadata["params"] = self.model.get_params()
        return self

    def predict(self, X):
        preds = self.model.predict(X)
        return np.maximum(preds, 0)  # Goals can't be negative

    def get_feature_importance(self):
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.model.feature_importances_,
        }).sort_values("importance", ascending=False)


class XGBoostCards(BasePredictor):
    """XGBoost regressor for total cards prediction."""

    def __init__(self, **kwargs) -> None:
        super().__init__("XGBoost_Cards", "regressor")
        settings = get_settings()
        defaults = {
            "n_estimators": 400,
            "max_depth": 4,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_alpha": 1.0,
            "reg_lambda": 5.0,
            "min_child_weight": 10,
            "objective": "reg:squarederror",
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

        self.model = XGBRegressor(**params)
        self.model.fit(X_train, y_train, **fit_params)
        self.metadata["best_iteration"] = getattr(self.model, "best_iteration", None)
        self.is_fitted = True
        self.metadata["params"] = self.model.get_params()
        return self

    def predict(self, X):
        preds = self.model.predict(X)
        return np.maximum(preds, 0)  # Cards can't be negative

    def get_feature_importance(self):
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.model.feature_importances_,
        }).sort_values("importance", ascending=False)
