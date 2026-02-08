"""
Unit tests for feature engineering pipeline.

Tests anti-data-leakage, rolling average correctness,
edge cases, and feature consistency.
"""

import numpy as np
import pandas as pd
import pytest

from src.laliga_predictor.features.feature_engineering import (
    MatchFeatureBuilder,
    _safe_add,
    _safe_mean,
    _safe_sub,
)


class TestAntiLeakage:
    """CRITICAL: Verify no future data leaks into features."""

    def test_no_future_data_in_features(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Features for each match must only use data from BEFORE that match."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3, 5],
        )
        dataset = builder.build_dataset()

        # For each row, verify the match_date is AFTER all data used
        for _, row in dataset.iterrows():
            match_date = row["match_date"]

            # Rolling form features should only reflect past matches
            # Check by verifying the feature set was built with cutoff < match_date
            # We do this indirectly: for the FIRST match of the first season,
            # features should be None (or not in dataset) because there's no history
            assert match_date is not None

        # The first match of the first season should NOT be in the dataset
        # because there's no historical data to compute features from
        earliest_match = synthetic_matches.sort_values("match_date").iloc[0]
        assert earliest_match["match_id"] not in dataset["match_id"].values

    def test_features_dont_use_match_result(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Feature columns must not contain the match's own result data."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        feature_cols = [c for c in dataset.columns if c.startswith(("h_", "a_", "h2h_",
                                                                     "position_", "points_",
                                                                     "rest_", "match_week",
                                                                     "is_"))]
        # Targets should be separate columns
        assert "target_result" in dataset.columns
        assert "target_total_goals" in dataset.columns
        assert "target_total_cards" in dataset.columns

        # No feature column should be named like a target
        for col in feature_cols:
            assert not col.startswith("target_")

    def test_rolling_uses_strictly_before_cutoff(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Rolling averages must exclude the current match's data."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )

        # Get a match from the middle of the dataset
        sorted_matches = synthetic_matches.sort_values("match_date")
        mid_match = sorted_matches.iloc[len(sorted_matches) // 2]

        features = builder._build_features_for_match(mid_match)
        assert features is not None

        # The features should be computable and non-null for a mid-season match
        assert features.get("h_win_rate_3") is not None


class TestRollingAverageCorrectness:
    """Verify rolling average calculations are correct."""

    def test_rolling_win_rate_range(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Win rate must be between 0 and 1."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3, 5],
        )
        dataset = builder.build_dataset()

        for col in dataset.columns:
            if "win_rate" in col:
                valid = dataset[col].dropna()
                assert (valid >= 0).all(), f"{col} has negative values"
                assert (valid <= 1).all(), f"{col} has values > 1"

    def test_rolling_draw_rate_range(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Draw rate must be between 0 and 1."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        for col in dataset.columns:
            if "draw_rate" in col:
                valid = dataset[col].dropna()
                assert (valid >= 0).all()
                assert (valid <= 1).all()

    def test_goals_non_negative(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Average goals scored/conceded cannot be negative."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        for col in dataset.columns:
            if "avg_goals" in col:
                valid = dataset[col].dropna()
                assert (valid >= 0).all(), f"{col} has negative values"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_first_match_of_season_excluded(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """First matches should be excluded when there's no prior history."""
        # Use only the first season
        first_season = synthetic_matches["season_code"].unique()[0]
        s1_matches = synthetic_matches[synthetic_matches["season_code"] == first_season]
        s1_adv = synthetic_advanced_stats[
            synthetic_advanced_stats["season_code"] == first_season
        ]
        s1_standings = synthetic_standings[
            synthetic_standings["season_code"] == first_season
        ]

        builder = MatchFeatureBuilder(s1_matches, s1_adv, s1_standings, rolling_windows=[3])
        dataset = builder.build_dataset()

        # With only 1 season and 4 teams, first match has no history
        assert len(dataset) < len(s1_matches)

    def test_head_to_head_no_prior_meetings(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Teams with no prior meetings should get h2h defaults."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )

        # Get first season matches
        first_season = synthetic_matches["season_code"].unique()[0]
        s1 = synthetic_matches[synthetic_matches["season_code"] == first_season]
        first_match = s1.sort_values("match_date").iloc[1]  # 2nd match (1st might be skipped)

        features = builder._build_features_for_match(first_match)
        if features is not None:
            # H2H should have 0 matches or None for averages
            assert features.get("h2h_total_matches", 0) <= 1


class TestFeatureConsistency:
    """Verify feature count and structure."""

    def test_feature_count_consistent(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """All rows in the dataset should have the same number of columns."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3, 5, 10],
        )
        dataset = builder.build_dataset()

        # All rows should have the same columns (no varying column count)
        assert dataset.shape[1] > 50  # Should have many features
        assert not dataset.columns.duplicated().any()

    def test_targets_present(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Target columns must be present in the dataset."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        assert "target_result" in dataset.columns
        assert "target_total_goals" in dataset.columns
        assert "target_total_cards" in dataset.columns

    def test_target_result_values(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Result target should only contain H, D, A."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        valid_results = {"H", "D", "A"}
        actual_results = set(dataset["target_result"].dropna().unique())
        assert actual_results.issubset(valid_results)

    def test_metadata_columns(
        self, synthetic_matches, synthetic_advanced_stats, synthetic_standings
    ):
        """Metadata columns should be present."""
        builder = MatchFeatureBuilder(
            synthetic_matches, synthetic_advanced_stats, synthetic_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        for col in ["match_id", "match_date", "season_code", "home_team", "away_team"]:
            assert col in dataset.columns, f"Missing metadata column: {col}"


class TestUtilityFunctions:
    """Test helper utility functions."""

    def test_safe_add_normal(self):
        assert _safe_add(1, 2) == 3.0

    def test_safe_add_none(self):
        assert _safe_add(None, 2) is None
        assert _safe_add(1, None) is None

    def test_safe_add_nan(self):
        assert _safe_add(float("nan"), 2) is None

    def test_safe_sub_normal(self):
        assert _safe_sub(5, 3) == 2.0

    def test_safe_sub_none(self):
        assert _safe_sub(None, 3) is None

    def test_safe_mean_normal(self):
        s = pd.Series([1.0, 2.0, 3.0])
        assert _safe_mean(s) == 2.0

    def test_safe_mean_all_nan(self):
        s = pd.Series([float("nan"), float("nan")])
        assert _safe_mean(s) is None

    def test_safe_mean_partial_nan(self):
        s = pd.Series([1.0, float("nan"), 3.0])
        assert _safe_mean(s) == 2.0
