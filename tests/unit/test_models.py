"""
Unit tests for ML model classes.

Tests BasePredictor interface, prediction shapes,
model serialization, and temporal cross-validation.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.laliga_predictor.models.base import BasePredictor
from src.laliga_predictor.models.classifiers import (
    HomeAlwaysWinsBaseline,
    RandomForestWinner,
    XGBoostWinner,
)
from src.laliga_predictor.models.regressors import MeanBaseline, XGBoostGoals
from src.laliga_predictor.models.temporal_cv import SeasonalTimeSeriesSplit


@pytest.fixture
def sample_classification_data():
    """Small classification dataset for quick tests."""
    rng = np.random.default_rng(42)
    n = 100
    X = pd.DataFrame({
        f"feat_{i}": rng.normal(0, 1, n) for i in range(10)
    })
    y = pd.Series(rng.choice(["H", "D", "A"], n, p=[0.45, 0.27, 0.28]))
    return X, y


@pytest.fixture
def sample_regression_data():
    """Small regression dataset for quick tests."""
    rng = np.random.default_rng(42)
    n = 100
    X = pd.DataFrame({
        f"feat_{i}": rng.normal(0, 1, n) for i in range(10)
    })
    y = pd.Series(rng.poisson(2.7, n).astype(float))
    return X, y


class TestClassifierInterface:
    """All classifiers must implement BasePredictor correctly."""

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_is_base_predictor(self, model_cls):
        model = model_cls()
        assert isinstance(model, BasePredictor)

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_fit_returns_self(self, model_cls, sample_classification_data):
        X, y = sample_classification_data
        model = model_cls()
        result = model.fit(X, y)
        assert result is model

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_predict_shape(self, model_cls, sample_classification_data):
        X, y = sample_classification_data
        model = model_cls()
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_predict_valid_classes(self, model_cls, sample_classification_data):
        X, y = sample_classification_data
        model = model_cls()
        model.fit(X, y)
        preds = model.predict(X)
        valid = {"H", "D", "A"}
        assert set(preds).issubset(valid)

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_predict_proba_shape(self, model_cls, sample_classification_data):
        """predict_proba must return shape (n_samples, 3) with probabilities summing to ~1."""
        X, y = sample_classification_data
        model = model_cls()
        model.fit(X, y)
        proba = model.predict_proba(X)

        assert proba.shape == (len(X), 3)
        # Probabilities should sum to approximately 1
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)
        # All probabilities should be non-negative
        assert (proba >= 0).all()

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_feature_importance(self, model_cls, sample_classification_data):
        X, y = sample_classification_data
        model = model_cls()
        model.fit(X, y)
        importance = model.get_feature_importance()

        assert isinstance(importance, pd.DataFrame)
        assert "feature" in importance.columns
        assert "importance" in importance.columns
        assert len(importance) == X.shape[1]

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_feature_names_stored(self, model_cls, sample_classification_data):
        X, y = sample_classification_data
        model = model_cls()
        model.fit(X, y)
        assert model.feature_names == list(X.columns)
        assert model.is_fitted is True


class TestRegressorInterface:
    """All regressors must implement BasePredictor correctly."""

    @pytest.mark.parametrize("model_cls,kwargs", [
        (MeanBaseline, {"target_name": "goals"}),
        (XGBoostGoals, {}),
    ])
    def test_predict_shape(self, model_cls, kwargs, sample_regression_data):
        X, y = sample_regression_data
        model = model_cls(**kwargs)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)

    @pytest.mark.parametrize("model_cls,kwargs", [
        (MeanBaseline, {"target_name": "goals"}),
        (XGBoostGoals, {}),
    ])
    def test_predict_non_negative(self, model_cls, kwargs, sample_regression_data):
        """Goals and cards predictions must be non-negative."""
        X, y = sample_regression_data
        model = model_cls(**kwargs)
        model.fit(X, y)
        preds = model.predict(X)
        assert (preds >= 0).all()

    def test_mean_baseline_predicts_mean(self, sample_regression_data):
        X, y = sample_regression_data
        model = MeanBaseline(target_name="goals")
        model.fit(X, y)
        preds = model.predict(X)
        np.testing.assert_allclose(preds, y.mean(), atol=1e-5)

    def test_regressor_no_predict_proba(self, sample_regression_data):
        X, y = sample_regression_data
        model = MeanBaseline(target_name="test")
        model.fit(X, y)
        with pytest.raises(NotImplementedError):
            model.predict_proba(X)


class TestModelSaveLoad:
    """Test model serialization and deserialization."""

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
    ])
    def test_classifier_save_load_produces_same_predictions(
        self, model_cls, sample_classification_data
    ):
        X, y = sample_classification_data
        model = model_cls()
        model.fit(X, y)

        original_preds = model.predict(X)
        original_proba = model.predict_proba(X)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.joblib"
            model.save(path)

            # Verify files were created
            assert path.exists()
            assert path.with_suffix(".json").exists()

            loaded = BasePredictor.load(path)
            loaded_preds = loaded.predict(X)
            loaded_proba = loaded.predict_proba(X)

        np.testing.assert_array_equal(original_preds, loaded_preds)
        np.testing.assert_array_almost_equal(original_proba, loaded_proba)

    def test_regressor_save_load(self, sample_regression_data):
        X, y = sample_regression_data
        model = XGBoostGoals()
        model.fit(X, y)
        original_preds = model.predict(X)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.joblib"
            model.save(path)
            loaded = BasePredictor.load(path)
            loaded_preds = loaded.predict(X)

        np.testing.assert_array_almost_equal(original_preds, loaded_preds)


class TestTemporalCV:
    """Test SeasonalTimeSeriesSplit."""

    def test_splits_respect_temporal_order(self):
        """Train seasons must always come before validation season."""
        seasons = pd.Series(["1718"] * 10 + ["1819"] * 10 + ["1920"] * 10 +
                            ["2021"] * 10 + ["2122"] * 10)
        X = pd.DataFrame({"feat": range(50)})
        cv = SeasonalTimeSeriesSplit(min_train_seasons=3)

        for train_idx, val_idx in cv.split(X, seasons):
            train_seasons = set(seasons.iloc[train_idx])
            val_season = seasons.iloc[val_idx].unique()
            assert len(val_season) == 1
            val_s = val_season[0]

            # All training seasons must come before the validation season
            for ts in train_seasons:
                assert ts < val_s, f"Train season {ts} >= val season {val_s}"

    def test_no_train_val_overlap(self):
        """Train and validation indices must not overlap."""
        seasons = pd.Series(["1718"] * 10 + ["1819"] * 10 + ["1920"] * 10 +
                            ["2021"] * 10 + ["2122"] * 10)
        X = pd.DataFrame({"feat": range(50)})
        cv = SeasonalTimeSeriesSplit(min_train_seasons=3)

        for train_idx, val_idx in cv.split(X, seasons):
            assert len(set(train_idx) & set(val_idx)) == 0

    def test_expanding_window(self):
        """Each fold should have more training data than the previous."""
        seasons = pd.Series(["1718"] * 10 + ["1819"] * 10 + ["1920"] * 10 +
                            ["2021"] * 10 + ["2122"] * 10)
        X = pd.DataFrame({"feat": range(50)})
        cv = SeasonalTimeSeriesSplit(min_train_seasons=3)

        train_sizes = []
        for train_idx, _ in cv.split(X, seasons):
            train_sizes.append(len(train_idx))

        # Each subsequent fold should have more training data
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] > train_sizes[i - 1]

    def test_n_splits(self):
        seasons = pd.Series(["1718"] * 10 + ["1819"] * 10 + ["1920"] * 10 +
                            ["2021"] * 10 + ["2122"] * 10)
        cv = SeasonalTimeSeriesSplit(min_train_seasons=3)

        assert cv.get_n_splits(seasons) == 2  # 5 seasons - 3 min = 2 splits

    def test_too_few_seasons_raises(self):
        seasons = pd.Series(["1718"] * 10 + ["1819"] * 10)
        X = pd.DataFrame({"feat": range(20)})
        cv = SeasonalTimeSeriesSplit(min_train_seasons=3)

        with pytest.raises(ValueError, match="Need at least"):
            list(cv.split(X, seasons))
