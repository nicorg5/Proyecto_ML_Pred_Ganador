"""
Probability calibration and classification threshold optimization.

Wraps trained models with per-class isotonic regression to produce
well-calibrated probabilities, and optimizes per-class thresholds
to maximize f1_macro (critical for draw prediction).
"""

import logging

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score

from .base import BasePredictor

logger = logging.getLogger(__name__)

# A=0, D=1, H=2 — matches classifiers.py encoding
RESULT_CLASSES = ["A", "D", "H"]


class CalibratedPredictor(BasePredictor):
    """Wraps a trained classifier with per-class isotonic calibration.

    After the inner model is fit, isotonic regression is fitted per class
    on the validation set to map raw probabilities to calibrated ones.
    For winner prediction, per-class thresholds are optimized to maximize f1_macro.
    """

    def __init__(self, inner_model: BasePredictor, n_classes: int = 3) -> None:
        name = f"Calibrated_{inner_model.name}"
        super().__init__(name, inner_model.model_type)
        self.inner_model = inner_model
        self.n_classes = n_classes
        self._calibrators: list[IsotonicRegression] = []
        self._thresholds: np.ndarray | None = None

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
    ) -> "CalibratedPredictor":
        # Train inner model
        self.inner_model.fit(X_train, y_train, X_val, y_val)
        self.feature_names = self.inner_model.feature_names

        if X_val is not None and y_val is not None and len(X_val) > 0:
            raw_proba = self.inner_model.predict_proba(X_val)

            # Build binary indicators per class
            if self.n_classes == 3:
                y_val_arr = np.array(y_val)
                class_labels = RESULT_CLASSES
            else:
                y_val_arr = np.asarray(y_val, dtype=int)
                class_labels = list(range(self.n_classes))

            # Fit one isotonic regression per class
            self._calibrators = []
            for i, cls in enumerate(class_labels):
                y_binary = (y_val_arr == cls).astype(float)
                ir = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
                ir.fit(raw_proba[:, i], y_binary)
                self._calibrators.append(ir)

            logger.info(f"Calibrated {self.inner_model.name} on {len(X_val)} val samples")

            # Optimize thresholds for multi-class (winner)
            if self.n_classes == 3:
                self._thresholds = optimize_classification_thresholds(self, X_val, y_val)
                self.metadata["classification_thresholds"] = self._thresholds.tolist()
                logger.info(
                    f"Optimized thresholds: A={self._thresholds[0]:.2f}, "
                    f"D={self._thresholds[1]:.2f}, H={self._thresholds[2]:.2f}"
                )
        else:
            logger.warning("No validation data provided — skipping calibration")

        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raw_proba = self.inner_model.predict_proba(X)

        if not self._calibrators:
            return raw_proba

        # Apply isotonic calibration per class
        calibrated = np.column_stack(
            [self._calibrators[i].predict(raw_proba[:, i]) for i in range(self.n_classes)]
        )

        # Renormalize so rows sum to 1
        row_sums = calibrated.sum(axis=1, keepdims=True)
        row_sums = np.maximum(row_sums, 1e-10)  # avoid division by zero
        calibrated = calibrated / row_sums

        return calibrated

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        proba = self.predict_proba(X)

        if self._thresholds is not None and self.n_classes == 3:
            adjusted = proba * self._thresholds
            classes = np.array(RESULT_CLASSES)
            return classes[adjusted.argmax(axis=1)]

        if self.n_classes == 3:
            classes = np.array(RESULT_CLASSES)
            return classes[proba.argmax(axis=1)]

        # Binary
        return (proba[:, 1] >= 0.5).astype(int)

    def get_feature_importance(self) -> pd.DataFrame:
        return self.inner_model.get_feature_importance()


def optimize_classification_thresholds(
    model: BasePredictor,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    draw_multiplier_range: tuple[float, float] = (1.0, 3.0),
    n_steps: int = 21,
) -> np.ndarray:
    """Find per-class threshold multipliers that maximize f1_macro.

    Grid-searches over a multiplier for class D (draw) probability.
    Classes A and H keep multiplier=1.0.

    Returns:
        Array of shape (3,) with multipliers for [A, D, H].
    """
    proba = model.predict_proba(X_val)
    classes = np.array(RESULT_CLASSES)

    best_f1 = -1.0
    best_thresholds = np.array([1.0, 1.0, 1.0])

    for d_mult in np.linspace(draw_multiplier_range[0], draw_multiplier_range[1], n_steps):
        thresholds = np.array([1.0, d_mult, 1.0])
        adjusted = proba * thresholds
        preds = classes[adjusted.argmax(axis=1)]
        f1 = f1_score(y_val, preds, average="macro", zero_division=0)

        if f1 > best_f1:
            best_f1 = f1
            best_thresholds = thresholds.copy()

    logger.info(
        f"Threshold optimization: best f1_macro={best_f1:.4f}, "
        f"D_multiplier={best_thresholds[1]:.2f}"
    )
    return best_thresholds
