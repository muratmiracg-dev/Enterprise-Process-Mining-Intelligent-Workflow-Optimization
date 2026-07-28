"""Explainable temporal holdout model for SLA breach risk."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC_FEATURES = [
    "amount_usd",
    "elapsed_to_po_hours",
    "early_event_count",
    "approval_count",
    "early_rework_count",
    "early_manual_minutes",
]

CATEGORICAL_FEATURES = [
    "business_unit",
    "department",
    "country",
    "vendor_tier",
    "material_category",
    "priority",
    "channel",
]


@dataclass(frozen=True)
class PredictionResult:
    """Model outputs used by the API and reporting layer."""

    metrics: dict[str, object]
    predictions: pd.DataFrame
    feature_importance: pd.DataFrame


def build_prediction_features(events: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    """Build features available by purchase-order creation time."""

    ordered = events.sort_values(["case_id", "timestamp", "event_index"]).copy()
    po_time = (
        ordered[ordered["activity"] == "Purchase Order Created"]
        .groupby("case_id")["timestamp"]
        .min()
        .rename("po_created_at")
    )
    early = ordered.merge(po_time, on="case_id", how="left")
    early = early[
        early["po_created_at"].isna() | (early["timestamp"] <= early["po_created_at"])
    ].copy()
    early["is_approval"] = early["activity"].eq("Manager Approval").astype(int)
    early["is_rework"] = early["activity"].eq("Request Reworked").astype(int)
    early["manual_minutes"] = early["processing_minutes"].where(~early["automated"], 0)
    aggregates = early.groupby("case_id", as_index=False).agg(
        early_event_count=("activity", "size"),
        approval_count=("is_approval", "sum"),
        early_rework_count=("is_rework", "sum"),
        early_manual_minutes=("manual_minutes", "sum"),
    )

    frame = cases.merge(po_time, on="case_id", how="left").merge(
        aggregates, on="case_id", how="left"
    )
    frame["elapsed_to_po_hours"] = (
        frame["po_created_at"] - frame["created_at"]
    ).dt.total_seconds() / 3600
    frame["elapsed_to_po_hours"] = frame["elapsed_to_po_hours"].fillna(frame["cycle_time_hours"])
    for column in (
        "early_event_count",
        "approval_count",
        "early_rework_count",
        "early_manual_minutes",
    ):
        frame[column] = frame[column].fillna(0)
    return frame


def _model_pipeline() -> Pipeline:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    transformer = ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        verbose_feature_names_out=False,
    )
    return Pipeline(
        [
            ("features", transformer),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )


def _metric_or_default(function, y_true, score, default: float = 0.5) -> float:
    try:
        return float(function(y_true, score))
    except ValueError:
        return default


def train_sla_model(
    events: pd.DataFrame,
    cases: pd.DataFrame,
    *,
    holdout_share: float = 0.20,
) -> PredictionResult:
    """Train and evaluate a temporal SLA-breach classifier."""

    if not 0.10 <= holdout_share <= 0.40:
        raise ValueError("holdout_share must be between 0.10 and 0.40")

    frame = build_prediction_features(events, cases).sort_values(["created_at", "case_id"])
    split_index = max(1, min(len(frame) - 1, int(len(frame) * (1 - holdout_share))))
    train = frame.iloc[:split_index]
    holdout = frame.iloc[split_index:]
    if train["sla_breached"].nunique() < 2:
        raise ValueError("training data must contain both SLA outcome classes")

    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    model = _model_pipeline()
    model.fit(train[feature_columns], train["sla_breached"].astype(int))
    scores = model.predict_proba(holdout[feature_columns])[:, 1]
    predictions = scores >= 0.50
    actual = holdout["sla_breached"].astype(int).to_numpy()
    matrix = confusion_matrix(actual, predictions, labels=[0, 1])

    metrics: dict[str, object] = {
        "model": "LogisticRegression",
        "validation": "temporal_holdout",
        "train_cases": int(len(train)),
        "holdout_cases": int(len(holdout)),
        "positive_rate_holdout": float(actual.mean()),
        "roc_auc": _metric_or_default(roc_auc_score, actual, scores),
        "average_precision": _metric_or_default(
            average_precision_score, actual, scores, default=float(actual.mean())
        ),
        "accuracy": float(accuracy_score(actual, predictions)),
        "precision": float(precision_score(actual, predictions, zero_division=0)),
        "recall": float(recall_score(actual, predictions, zero_division=0)),
        "f1": float(f1_score(actual, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(actual, scores)),
        "confusion_matrix": {
            "true_negative": int(matrix[0, 0]),
            "false_positive": int(matrix[0, 1]),
            "false_negative": int(matrix[1, 0]),
            "true_positive": int(matrix[1, 1]),
        },
    }

    scored = holdout[
        [
            "case_id",
            "created_at",
            "business_unit",
            "vendor_id",
            "amount_usd",
            "sla_breached",
        ]
    ].copy()
    scored["risk_score"] = scores
    scored["predicted_breach"] = predictions
    scored["risk_band"] = pd.cut(
        scores,
        bins=[-np.inf, 0.30, 0.60, 0.80, np.inf],
        labels=["Low", "Medium", "High", "Critical"],
    ).astype(str)

    transformer = model.named_steps["features"]
    classifier = model.named_steps["model"]
    names = transformer.get_feature_names_out()
    importance = pd.DataFrame(
        {
            "feature": names,
            "coefficient": classifier.coef_[0],
        }
    )
    importance["absolute_importance"] = importance["coefficient"].abs()
    importance["direction"] = np.where(importance["coefficient"] >= 0, "higher_risk", "lower_risk")
    importance = importance.sort_values(
        ["absolute_importance", "feature"], ascending=[False, True]
    ).reset_index(drop=True)
    return PredictionResult(metrics=metrics, predictions=scored, feature_importance=importance)
