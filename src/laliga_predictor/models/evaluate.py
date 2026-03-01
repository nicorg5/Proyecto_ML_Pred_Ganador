"""
Model evaluation for La Liga prediction models.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from .base import BasePredictor

logger = logging.getLogger(__name__)


def evaluate_classifier(
    model: BasePredictor, X: pd.DataFrame, y_true: pd.Series
) -> dict:
    """Evaluate a classifier on a dataset.

    Returns dict with: accuracy, f1_macro, f1_weighted, log_loss,
    confusion_matrix, per_class_accuracy.
    """
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)

    classes = ["A", "D", "H"]

    # Encode y_true for log_loss
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    le.fit(classes)
    y_true_enc = le.transform(y_true)

    metrics: dict = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }

    # Log loss (safe)
    try:
        metrics["log_loss"] = float(log_loss(y_true_enc, y_proba, labels=[0, 1, 2]))
    except Exception:
        metrics["log_loss"] = None

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    metrics["confusion_matrix"] = cm.tolist()

    # Per-class accuracy
    for i, cls in enumerate(classes):
        mask = y_true == cls
        if mask.sum() > 0:
            metrics[f"accuracy_{cls}"] = float((y_pred[mask] == cls).mean())
        else:
            metrics[f"accuracy_{cls}"] = None

    return metrics


def evaluate_binary_classifier(
    model: BasePredictor, X: pd.DataFrame, y_true: pd.Series
) -> dict:
    """Evaluate a binary classifier (over/under) on a dataset.

    Args:
        model: Trained binary classifier
        X: Feature matrix
        y_true: Binary labels (0=under, 1=over)

    Returns dict with: accuracy, f1, precision, recall, auc_roc, log_loss.
    """
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)

    metrics: dict = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
    }

    # AUC-ROC (use probability of the positive class = over)
    try:
        # y_proba[:, 1] = P(over)
        p_over = y_proba[:, 1] if y_proba.ndim == 2 else y_proba
        metrics["auc_roc"] = float(roc_auc_score(y_true, p_over))
    except Exception:
        metrics["auc_roc"] = 0.5

    # Log loss
    try:
        metrics["log_loss"] = float(log_loss(y_true, y_proba))
    except Exception:
        metrics["log_loss"] = None

    # Class distribution info
    metrics["over_rate_true"] = float(y_true.mean())
    metrics["over_rate_pred"] = float(np.mean(y_pred))

    return metrics


def evaluate_regressor(
    model: BasePredictor, X: pd.DataFrame, y_true: pd.Series
) -> dict:
    """Evaluate a regressor on a dataset.

    Returns dict with: rmse, mae, r2, mean_pred, mean_true.
    """
    y_pred = model.predict(X)

    metrics: dict = {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
        "mean_pred": float(np.mean(y_pred)),
        "mean_true": float(np.mean(y_true)),
    }

    # Over/Under 2.5 accuracy (for goals)
    if y_true.mean() > 1.5:  # Likely goals target
        over_true = (y_true > 2.5).astype(int)
        over_pred = (y_pred > 2.5).astype(int)
        metrics["over_2_5_accuracy"] = float(accuracy_score(over_true, over_pred))

    return metrics


def print_evaluation_report(results: dict) -> None:
    """Print a formatted evaluation report."""
    for target, models in results.items():
        print(f"\n{'='*60}")
        print(f"Target: {target}")
        print(f"{'='*60}")

        for model_name, metrics in models.items():
            test = metrics.get("test", {})
            val = metrics.get("val", {})

            print(f"\n  Model: {model_name}")
            if "f1_macro" in test:
                # Multi-class (winner)
                print(f"    Test  - Accuracy: {test['accuracy']:.3f}, "
                      f"F1 Macro: {test['f1_macro']:.3f}, "
                      f"Log Loss: {test.get('log_loss', 'N/A')}")
                if val:
                    print(f"    Val   - Accuracy: {val['accuracy']:.3f}, "
                          f"F1 Macro: {val['f1_macro']:.3f}")
                # Per-class
                for cls in ["H", "D", "A"]:
                    acc = test.get(f"accuracy_{cls}")
                    if acc is not None:
                        print(f"    Class {cls}: {acc:.3f}")
            elif "auc_roc" in test:
                # Binary (over/under)
                print(f"    Test  - Accuracy: {test['accuracy']:.3f}, "
                      f"F1: {test['f1']:.3f}, AUC: {test['auc_roc']:.3f}")
                if val:
                    print(f"    Val   - Accuracy: {val['accuracy']:.3f}, "
                          f"F1: {val['f1']:.3f}, AUC: {val['auc_roc']:.3f}")
            elif "rmse" in test:
                print(f"    Test  - RMSE: {test['rmse']:.3f}, "
                      f"MAE: {test['mae']:.3f}, R2: {test['r2']:.3f}")
                if val:
                    print(f"    Val   - RMSE: {val['rmse']:.3f}, "
                          f"MAE: {val['mae']:.3f}")
                if "over_2_5_accuracy" in test:
                    print(f"    Over 2.5 Accuracy: {test['over_2_5_accuracy']:.3f}")
