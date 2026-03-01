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
from src.laliga_predictor.models.calibration import (
    CalibratedPredictor,
    optimize_classification_thresholds,
)
from src.laliga_predictor.models.classifiers import (
    HomeAlwaysWinsBaseline,
    LightGBMWinner,
    RandomForestWinner,
    XGBoostWinner,
)
from src.laliga_predictor.models.over_under import (
    LightGBMOverUnder,
    OverUnderBaseline,
    XGBoostOverUnder,
)
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


@pytest.fixture
def sample_binary_data():
    """Small binary dataset for over/under tests."""
    rng = np.random.default_rng(42)
    n = 100
    X = pd.DataFrame({
        f"feat_{i}": rng.normal(0, 1, n) for i in range(10)
    })
    y = pd.Series(rng.choice([0, 1], n, p=[0.45, 0.55]))
    return X, y


class TestClassifierInterface:
    """All classifiers must implement BasePredictor correctly."""

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
        LightGBMWinner,
    ])
    def test_is_base_predictor(self, model_cls):
        model = model_cls()
        assert isinstance(model, BasePredictor)

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
        LightGBMWinner,
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
        LightGBMWinner,
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
        LightGBMWinner,
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
        LightGBMWinner,
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
        LightGBMWinner,
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
        LightGBMWinner,
    ])
    def test_feature_names_stored(self, model_cls, sample_classification_data):
        X, y = sample_classification_data
        model = model_cls()
        model.fit(X, y)
        assert model.feature_names == list(X.columns)
        assert model.is_fitted is True


class TestOverUnderInterface:
    """Over/under binary classifiers must implement BasePredictor correctly."""

    def test_baseline_is_base_predictor(self):
        model = OverUnderBaseline(stat_type="goals", line=2.5)
        assert isinstance(model, BasePredictor)

    def test_xgboost_is_base_predictor(self):
        model = XGBoostOverUnder(stat_type="goals", line=2.5)
        assert isinstance(model, BasePredictor)

    def test_baseline_predict_shape(self, sample_binary_data):
        X, y = sample_binary_data
        model = OverUnderBaseline(stat_type="goals", line=2.5)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)

    def test_xgboost_predict_shape(self, sample_binary_data):
        X, y = sample_binary_data
        model = XGBoostOverUnder(stat_type="goals", line=2.5)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)

    def test_predict_binary_values(self, sample_binary_data):
        X, y = sample_binary_data
        model = XGBoostOverUnder(stat_type="goals", line=2.5)
        model.fit(X, y)
        preds = model.predict(X)
        assert set(preds).issubset({0, 1})

    def test_predict_proba_shape(self, sample_binary_data):
        """predict_proba must return shape (n_samples, 2) with probs summing to ~1."""
        X, y = sample_binary_data
        model = XGBoostOverUnder(stat_type="goals", line=2.5)
        model.fit(X, y)
        proba = model.predict_proba(X)

        assert proba.shape == (len(X), 2)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)
        assert (proba >= 0).all()

    def test_baseline_predict_proba_shape(self, sample_binary_data):
        X, y = sample_binary_data
        model = OverUnderBaseline(stat_type="goals", line=2.5)
        model.fit(X, y)
        proba = model.predict_proba(X)

        assert proba.shape == (len(X), 2)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)

    def test_feature_importance(self, sample_binary_data):
        X, y = sample_binary_data
        model = XGBoostOverUnder(stat_type="goals", line=2.5)
        model.fit(X, y)
        importance = model.get_feature_importance()

        assert isinstance(importance, pd.DataFrame)
        assert "feature" in importance.columns
        assert "importance" in importance.columns
        assert len(importance) == X.shape[1]

    def test_metadata_stores_line(self, sample_binary_data):
        X, y = sample_binary_data
        model = XGBoostOverUnder(stat_type="cards", line=4.5)
        model.fit(X, y)
        assert model.metadata["line"] == 4.5
        assert model.metadata["stat_type"] == "cards"

    @pytest.mark.parametrize("line", [1.5, 2.5, 3.5])
    def test_different_lines(self, line, sample_binary_data):
        X, y = sample_binary_data
        model = XGBoostOverUnder(stat_type="goals", line=line)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)
        assert set(preds).issubset({0, 1})


class TestCalibratedPredictor:
    """Test CalibratedPredictor wrapper."""

    def test_calibrated_predict_proba_sums_to_one(self, sample_classification_data):
        X, y = sample_classification_data
        X_train, X_val = X[:70], X[70:]
        y_train, y_val = y[:70], y[70:]

        inner = XGBoostWinner()
        model = CalibratedPredictor(inner, n_classes=3)
        model.fit(X_train, y_train, X_val, y_val)

        proba = model.predict_proba(X_val)
        assert proba.shape == (len(X_val), 3)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)
        assert (proba >= 0).all()

    def test_calibrated_predict_valid_classes(self, sample_classification_data):
        X, y = sample_classification_data
        X_train, X_val = X[:70], X[70:]
        y_train, y_val = y[:70], y[70:]

        inner = XGBoostWinner()
        model = CalibratedPredictor(inner, n_classes=3)
        model.fit(X_train, y_train, X_val, y_val)

        preds = model.predict(X_val)
        assert set(preds).issubset({"H", "D", "A"})

    def test_calibrated_save_load(self, sample_classification_data):
        X, y = sample_classification_data
        X_train, X_val = X[:70], X[70:]
        y_train, y_val = y[:70], y[70:]

        inner = XGBoostWinner()
        model = CalibratedPredictor(inner, n_classes=3)
        model.fit(X_train, y_train, X_val, y_val)
        original_proba = model.predict_proba(X_val)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "calibrated.joblib"
            model.save(path)
            assert path.exists()

            loaded = BasePredictor.load(path)
            loaded_proba = loaded.predict_proba(X_val)

        np.testing.assert_array_almost_equal(original_proba, loaded_proba)

    def test_calibrated_binary(self, sample_binary_data):
        X, y = sample_binary_data
        X_train, X_val = X[:70], X[70:]
        y_train, y_val = y[:70], y[70:]

        inner = XGBoostOverUnder(stat_type="goals", line=2.5)
        model = CalibratedPredictor(inner, n_classes=2)
        model.fit(X_train, y_train, X_val, y_val)

        proba = model.predict_proba(X_val)
        assert proba.shape == (len(X_val), 2)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)

    def test_threshold_optimization_returns_valid_thresholds(
        self, sample_classification_data
    ):
        X, y = sample_classification_data
        X_train, X_val = X[:70], X[70:]
        y_train, y_val = y[:70], y[70:]

        inner = XGBoostWinner()
        model = CalibratedPredictor(inner, n_classes=3)
        model.fit(X_train, y_train, X_val, y_val)

        thresholds = model._thresholds
        assert thresholds is not None
        assert len(thresholds) == 3
        assert thresholds[0] == 1.0  # A multiplier stays 1.0
        assert thresholds[2] == 1.0  # H multiplier stays 1.0
        assert thresholds[1] >= 1.0  # D multiplier >= 1.0

    def test_feature_importance_delegates(self, sample_classification_data):
        X, y = sample_classification_data
        X_train, X_val = X[:70], X[70:]
        y_train, y_val = y[:70], y[70:]

        inner = XGBoostWinner()
        model = CalibratedPredictor(inner, n_classes=3)
        model.fit(X_train, y_train, X_val, y_val)

        importance = model.get_feature_importance()
        assert isinstance(importance, pd.DataFrame)
        assert len(importance) == X.shape[1]


class TestModelSaveLoad:
    """Test model serialization and deserialization."""

    @pytest.mark.parametrize("model_cls", [
        HomeAlwaysWinsBaseline,
        RandomForestWinner,
        XGBoostWinner,
        LightGBMWinner,
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

    def test_over_under_save_load(self, sample_binary_data):
        """Over/under model must save and load correctly."""
        X, y = sample_binary_data
        model = XGBoostOverUnder(stat_type="goals", line=2.5)
        model.fit(X, y)
        original_preds = model.predict(X)
        original_proba = model.predict_proba(X)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.joblib"
            model.save(path)

            assert path.exists()
            loaded = BasePredictor.load(path)
            loaded_preds = loaded.predict(X)
            loaded_proba = loaded.predict_proba(X)

        np.testing.assert_array_equal(original_preds, loaded_preds)
        np.testing.assert_array_almost_equal(original_proba, loaded_proba)
        assert loaded.metadata["line"] == 2.5
        assert loaded.metadata["stat_type"] == "goals"


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

