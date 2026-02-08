"""La Liga prediction models."""

from .base import BasePredictor
from .classifiers import (
    EnsembleWinner,
    HomeAlwaysWinsBaseline,
    RandomForestWinner,
    XGBoostWinner,
)
from .regressors import MeanBaseline, XGBoostCards, XGBoostGoals
from .temporal_cv import SeasonalTimeSeriesSplit

__all__ = [
    "BasePredictor",
    "HomeAlwaysWinsBaseline",
    "RandomForestWinner",
    "XGBoostWinner",
    "EnsembleWinner",
    "MeanBaseline",
    "XGBoostGoals",
    "XGBoostCards",
    "SeasonalTimeSeriesSplit",
]
