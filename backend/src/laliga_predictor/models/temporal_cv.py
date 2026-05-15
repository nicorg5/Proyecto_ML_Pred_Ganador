"""
Temporal cross-validation for time-ordered football data.
"""

import logging
from collections.abc import Iterator

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SeasonalTimeSeriesSplit:
    """Cross-validation splits respecting temporal season ordering.

    Uses an expanding window: each fold adds one more season to training.

    Example with seasons [1718, 1819, 1920, 2021, 2122, 2223, 2324]:
        Fold 1: train=[1718,1819,1920], val=[2021]
        Fold 2: train=[1718..2021],     val=[2122]
        Fold 3: train=[1718..2122],     val=[2223]
        Fold 4: train=[1718..2223],     val=[2324]

    Args:
        min_train_seasons: Minimum number of seasons in training set.
    """

    def __init__(self, min_train_seasons: int = 3) -> None:
        self.min_train_seasons = min_train_seasons

    def split(
        self, X: pd.DataFrame, season_codes: pd.Series
    ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        """Generate train/validation index splits.

        Args:
            X: Feature matrix (used only for indexing).
            season_codes: Season code per row (e.g., "1718", "2324").

        Yields:
            (train_indices, val_indices) as numpy arrays.
        """
        seasons = sorted(season_codes.unique())

        if len(seasons) <= self.min_train_seasons:
            raise ValueError(
                f"Need at least {self.min_train_seasons + 1} seasons, got {len(seasons)}"
            )

        for i in range(self.min_train_seasons, len(seasons)):
            train_seasons = set(seasons[:i])
            val_season = seasons[i]

            train_mask = season_codes.isin(train_seasons)
            val_mask = season_codes == val_season

            train_idx = np.where(train_mask)[0]
            val_idx = np.where(val_mask)[0]

            logger.debug(
                f"Fold: train={sorted(train_seasons)} ({len(train_idx)} samples), "
                f"val={val_season} ({len(val_idx)} samples)"
            )

            yield train_idx, val_idx

    def get_n_splits(self, season_codes: pd.Series) -> int:
        """Return number of splits."""
        return max(0, len(season_codes.unique()) - self.min_train_seasons)
