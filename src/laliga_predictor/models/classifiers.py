"""
Match winner prediction models (H/D/A classification).
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from ..config import get_settings
from .base import BasePredictor

logger = logging.getLogger(__name__)

# Label encoding: A=0, D=1, H=2
RESULT_CLASSES = ["A", "D", "H"]


class HomeAlwaysWinsBaseline(BasePredictor):
    """Baseline: always predicts Home win."""

    def __init__(self) -> None:
        super().__init__("HomeAlwaysWins", "classifier")

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)
        self.is_fitted = True
        return self

    def predict(self, X):
        return np.full(len(X), "H")

    def predict_proba(self, X):
        # [P(A), P(D), P(H)] = [0, 0, 1]
        proba = np.zeros((len(X), 3))
        proba[:, 2] = 1.0  # H is index 2
        return proba

    def get_feature_importance(self):
        return pd.DataFrame({"feature": self.feature_names, "importance": 0.0})


class RandomForestWinner(BasePredictor):
    """Random Forest classifier for match winner prediction."""

    def __init__(self, **kwargs) -> None:
        super().__init__("RandomForest", "classifier")
        settings = get_settings()
        defaults = {
            "n_estimators": 300,
            "max_depth": 12,
            "min_samples_leaf": 20,
            "class_weight": "balanced",
            "random_state": settings.RANDOM_STATE,
            "n_jobs": -1,
        }
        defaults.update(kwargs)
        self.model = RandomForestClassifier(**defaults)
        self.le = LabelEncoder()
        self.le.fit(RESULT_CLASSES)

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)
        y_encoded = self.le.transform(y_train)
        self.model.fit(X_train, y_encoded)
        self.is_fitted = True
        self.metadata["params"] = self.model.get_params()
        return self

    def predict(self, X):
        y_pred = self.model.predict(X)
        return self.le.inverse_transform(y_pred)

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def get_feature_importance(self):
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.model.feature_importances_,
        }).sort_values("importance", ascending=False)


class XGBoostWinner(BasePredictor):
    """XGBoost classifier for match winner prediction."""

    def __init__(self, **kwargs) -> None:
        super().__init__("XGBoost", "classifier")
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
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "random_state": settings.RANDOM_STATE,
            "n_jobs": -1,
            "verbosity": 0,
        }
        defaults.update(kwargs)
        self._xgb_params = defaults
        self.le = LabelEncoder()
        self.le.fit(RESULT_CLASSES)

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)
        y_encoded = self.le.transform(y_train)

        params = dict(self._xgb_params)
        fit_params: dict = {}
        if X_val is not None and y_val is not None:
            y_val_enc = self.le.transform(y_val)
            fit_params["eval_set"] = [(X_val, y_val_enc)]
            params["early_stopping_rounds"] = 50

        self.model = XGBClassifier(**params)
        self.model.fit(X_train, y_encoded, **fit_params)
        self.is_fitted = True
        self.metadata["params"] = self.model.get_params()
        return self

    def predict(self, X):
        y_pred = self.model.predict(X)
        return self.le.inverse_transform(y_pred)

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def get_feature_importance(self):
        importance = self.model.feature_importances_
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)


class EnsembleWinner(BasePredictor):
    """Stacking ensemble: RF + XGBoost with Logistic Regression meta-learner."""

    def __init__(self) -> None:
        super().__init__("Ensemble", "classifier")
        settings = get_settings()

        self.model = StackingClassifier(
            estimators=[
                ("rf", RandomForestClassifier(
                    n_estimators=200, max_depth=10, min_samples_leaf=20,
                    class_weight="balanced", random_state=settings.RANDOM_STATE, n_jobs=-1,
                )),
                ("xgb", XGBClassifier(
                    n_estimators=300, max_depth=6, learning_rate=0.05,
                    subsample=0.8, colsample_bytree=0.8,
                    objective="multi:softprob", num_class=3,
                    random_state=settings.RANDOM_STATE, n_jobs=-1, verbosity=0,
                )),
            ],
            final_estimator=LogisticRegression(
                max_iter=1000, random_state=settings.RANDOM_STATE,
            ),
            cv=3,
            stack_method="predict_proba",
            n_jobs=-1,
        )
        self.le = LabelEncoder()
        self.le.fit(RESULT_CLASSES)

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        self.feature_names = list(X_train.columns)
        y_encoded = self.le.transform(y_train)
        self.model.fit(X_train, y_encoded)
        self.is_fitted = True
        return self

    def predict(self, X):
        y_pred = self.model.predict(X)
        return self.le.inverse_transform(y_pred)

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def get_feature_importance(self):
        # Use RF feature importance from the ensemble
        rf_model = self.model.estimators_[0]
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": rf_model.feature_importances_,
        }).sort_values("importance", ascending=False)
