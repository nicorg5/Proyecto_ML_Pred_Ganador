"""
Integration tests for the ML pipeline.

End-to-end: synthetic data -> features -> train -> evaluate -> predict.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.laliga_predictor.features.feature_engineering import MatchFeatureBuilder
from src.laliga_predictor.features.feature_store import load_features, save_features
from src.laliga_predictor.models.classifiers import RandomForestWinner, XGBoostWinner
from src.laliga_predictor.models.evaluate import evaluate_classifier, evaluate_regressor
from src.laliga_predictor.models.regressors import MeanBaseline, XGBoostGoals
from src.laliga_predictor.models.train import META_COLS, prepare_data


class TestFeatureToTrainPipeline:
    """Test feature engineering -> training flow end-to-end."""

    def test_features_to_classifier(
        self,
        synthetic_3season_matches,
        synthetic_3season_advanced,
        synthetic_3season_standings,
    ):
        """Build features from synthetic data, then train a classifier."""
        builder = MatchFeatureBuilder(
            synthetic_3season_matches,
            synthetic_3season_advanced,
            synthetic_3season_standings,
            rolling_windows=[3, 5],
        )
        dataset = builder.build_dataset()
        assert len(dataset) > 0

        # Split by season
        X_train, y_train, X_val, y_val, X_test, y_test = prepare_data(
            dataset, "result",
            train_seasons=["2223"],
            val_seasons=["2324"],
            test_seasons=["2425"],
        )

        assert len(X_train) > 0
        assert len(X_val) > 0
        assert len(X_test) > 0

        # Train classifier
        model = RandomForestWinner()
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        assert len(preds) == len(X_test)
        assert set(preds).issubset({"H", "D", "A"})

    def test_features_to_regressor(
        self,
        synthetic_3season_matches,
        synthetic_3season_advanced,
        synthetic_3season_standings,
    ):
        """Build features from synthetic data, then train a regressor."""
        builder = MatchFeatureBuilder(
            synthetic_3season_matches,
            synthetic_3season_advanced,
            synthetic_3season_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        X_train, y_train, X_val, y_val, X_test, y_test = prepare_data(
            dataset, "total_goals",
            train_seasons=["2223"],
            val_seasons=["2324"],
            test_seasons=["2425"],
        )

        model = MeanBaseline(target_name="goals")
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        assert len(preds) == len(X_test)
        assert (preds >= 0).all()


class TestEvaluationPipeline:
    """Test evaluation metrics computation."""

    def test_classifier_evaluation(
        self,
        synthetic_3season_matches,
        synthetic_3season_advanced,
        synthetic_3season_standings,
    ):
        builder = MatchFeatureBuilder(
            synthetic_3season_matches,
            synthetic_3season_advanced,
            synthetic_3season_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        X_train, y_train, X_val, y_val, _, _ = prepare_data(
            dataset, "result",
            train_seasons=["2223"],
            val_seasons=["2324"],
            test_seasons=["2425"],
        )

        model = RandomForestWinner()
        model.fit(X_train, y_train)

        metrics = evaluate_classifier(model, X_val, y_val)

        assert "accuracy" in metrics
        assert "f1_macro" in metrics
        assert "confusion_matrix" in metrics
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["f1_macro"] <= 1

    def test_regressor_evaluation(
        self,
        synthetic_3season_matches,
        synthetic_3season_advanced,
        synthetic_3season_standings,
    ):
        builder = MatchFeatureBuilder(
            synthetic_3season_matches,
            synthetic_3season_advanced,
            synthetic_3season_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        X_train, y_train, X_val, y_val, _, _ = prepare_data(
            dataset, "total_goals",
            train_seasons=["2223"],
            val_seasons=["2324"],
            test_seasons=["2425"],
        )

        model = MeanBaseline(target_name="goals")
        model.fit(X_train, y_train)

        metrics = evaluate_regressor(model, X_val, y_val)

        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics
        assert metrics["rmse"] >= 0
        assert metrics["mae"] >= 0


class TestFeatureStore:
    """Test feature save/load round-trip."""

    def test_parquet_round_trip(
        self,
        synthetic_3season_matches,
        synthetic_3season_advanced,
        synthetic_3season_standings,
    ):
        builder = MatchFeatureBuilder(
            synthetic_3season_matches,
            synthetic_3season_advanced,
            synthetic_3season_standings,
            rolling_windows=[3],
        )
        dataset = builder.build_dataset()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "features.parquet")
            save_features(dataset, path)
            loaded = load_features(path)

        assert loaded.shape == dataset.shape
        assert list(loaded.columns) == list(dataset.columns)


class TestPredictionPipeline:
    """Test prediction for future matches."""

    def test_build_features_for_prediction(
        self,
        synthetic_3season_matches,
        synthetic_3season_advanced,
        synthetic_3season_standings,
    ):
        """Test building features for a hypothetical future match."""
        builder = MatchFeatureBuilder(
            synthetic_3season_matches,
            synthetic_3season_advanced,
            synthetic_3season_standings,
            rolling_windows=[3],
        )

        # Predict a match after the last match in the dataset
        last_date = synthetic_3season_matches["match_date"].max()
        future_date = last_date + pd.Timedelta(days=7)

        features = builder.build_features_for_prediction(
            home_team_id=1,
            away_team_id=2,
            match_date=future_date,
            season_code="2425",
            home_team="Team A",
            away_team="Team B",
        )

        assert features is not None
        assert "h_win_rate_3" in features
        assert "a_win_rate_3" in features
        assert "target_result" not in features  # No targets for prediction
