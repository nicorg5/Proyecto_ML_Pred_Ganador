"""La Liga prediction models."""

from .base import BasePredictor
from .calibration import CalibratedPredictor
from .classifiers import (
    EnsembleWinner,
    HomeAlwaysWinsBaseline,
    LightGBMWinner,
    RandomForestWinner,
    XGBoostWinner,
)
from .over_under import LightGBMOverUnder, OverUnderBaseline, XGBoostOverUnder
from .temporal_cv import SeasonalTimeSeriesSplit

__all__ = [
    "BasePredictor",
    "CalibratedPredictor",
    "HomeAlwaysWinsBaseline",
    "RandomForestWinner",
    "XGBoostWinner",
    "LightGBMWinner",
    "EnsembleWinner",
    "OverUnderBaseline",
    "XGBoostOverUnder",
    "LightGBMOverUnder",
    "SeasonalTimeSeriesSplit",
]
