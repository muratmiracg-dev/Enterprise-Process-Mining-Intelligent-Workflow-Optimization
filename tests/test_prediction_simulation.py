from __future__ import annotations

import pandas as pd
import pytest

from process_optimizer.prediction import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_prediction_features,
    train_sla_model,
)
from process_optimizer.simulation import (
    Scenario,
    Stage,
    _lognormal_parameters,
    _simulate_replication,
    default_scenarios,
    simulate_capacity,
)


def test_prediction_feature_contract(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    events, cases = sample_frames
    frame = build_prediction_features(events, cases)
    assert set(NUMERIC_FEATURES + CATEGORICAL_FEATURES).issubset(frame.columns)
    assert len(frame) == len(cases)
    assert frame["early_event_count"].ge(1).all()


def test_temporal_sla_model_is_explainable(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    result = train_sla_model(*sample_frames)
    assert result.metrics["validation"] == "temporal_holdout"
    assert 0.5 <= result.metrics["roc_auc"] <= 1
    assert set(result.predictions["risk_band"]).issubset({"Low", "Medium", "High", "Critical"})
    assert result.feature_importance["absolute_importance"].is_monotonic_decreasing


@pytest.mark.parametrize("share", [0.09, 0.41])
def test_sla_model_rejects_invalid_holdout(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame], share: float
) -> None:
    with pytest.raises(ValueError, match="holdout_share"):
        train_sla_model(*sample_frames, holdout_share=share)


def test_sla_model_requires_two_training_classes(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    events, cases = sample_frames
    with pytest.raises(ValueError, match="both SLA"):
        train_sla_model(events, cases.assign(sla_breached=False))


def test_lognormal_parameters() -> None:
    mu, sigma = _lognormal_parameters(10, 0.4)
    assert mu > 0
    assert sigma > 0


def test_scenario_catalog_has_governed_baseline() -> None:
    catalog = default_scenarios()
    assert [item.name for item in catalog] == [
        "Baseline",
        "Approval Automation",
        "AP Capacity",
        "Combined Optimization",
    ]
    assert catalog[0].one_time_investment_usd == 0


def test_single_replication_is_deterministic() -> None:
    scenario = Scenario("Tiny", "test", (Stage("Review", 2, 1.0),))
    first = _simulate_replication(scenario, cases=120, seed=7, arrival_rate_per_hour=1.5)
    second = _simulate_replication(scenario, cases=120, seed=7, arrival_rate_per_hour=1.5)
    assert first == second
    assert first["mean_cycle_hours"] > 0


def test_capacity_simulation_ranks_combined_scenario() -> None:
    result = simulate_capacity(replications=3, cases_per_replication=120)
    baseline = result.iloc[0]
    combined = result.iloc[-1]
    assert baseline["first_year_roi"] == 0
    assert combined["mean_cycle_hours"] < baseline["mean_cycle_hours"]
    assert combined["sla_adherence"] > baseline["sla_adherence"]
    assert combined["estimated_annual_value_usd"] > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"replications": 1, "cases_per_replication": 120},
        {"replications": 2, "cases_per_replication": 99},
        {"replications": 2, "cases_per_replication": 120, "arrival_rate_per_hour": 0},
    ],
)
def test_capacity_simulation_validates_inputs(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        simulate_capacity(**kwargs)
