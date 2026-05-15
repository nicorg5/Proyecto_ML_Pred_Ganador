"""
Base classes for La Liga prediction models.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class BasePredictor(ABC):
    """Abstract base class for all La Liga predictors."""

    def __init__(self, name: str, model_type: str) -> None:
        self.name = name
        self.model_type = model_type  # "classifier" or "regressor"
        self.feature_names: list[str] = []
        self.is_fitted: bool = False
        self.metadata: dict[str, Any] = {}

    @abstractmethod
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
    ) -> "BasePredictor":
        """Train the model."""
        ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions."""
        ...

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities (classifiers only)."""
        raise NotImplementedError(f"{self.name} does not support predict_proba")

    @abstractmethod
    def get_feature_importance(self) -> pd.DataFrame:
        """Return feature importance as DataFrame with columns [feature, importance]."""
        ...

    def save(self, path: str | Path) -> None:
        """Save model and metadata to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

        # Save metadata alongside
        meta_path = path.with_suffix(".json")
        meta = {
            "name": self.name,
            "model_type": self.model_type,
            "feature_count": len(self.feature_names),
            "saved_at": datetime.now().isoformat(),
            **self.metadata,
        }
        meta_path.write_text(json.dumps(meta, indent=2, default=str))
        logger.info(f"Saved model to {path}")

    @classmethod
    def load(cls, path: str | Path) -> "BasePredictor":
        """Load model from disk."""
        path = Path(path)
        model = joblib.load(path)
        logger.info(f"Loaded model from {path}")
        return model
