from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from process_optimizer.prediction import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_prediction_features,
    prior_corrected_probability,
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


def test_prediction_features_reject_orphan_events_and_duplicate_cases(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    events, cases = sample_frames
    with pytest.raises(ValueError, match="unique, non-null"):
        build_prediction_features(events, pd.concat([cases, cases.iloc[[0]]], ignore_index=True))
    orphan = events.iloc[[0]].assign(case_id="UNKNOWN")
    with pytest.raises(ValueError, match="unknown case_id"):
        build_prediction_features(pd.concat([events, orphan], ignore_index=True), cases)


def test_prediction_features_reject_cases_without_po_creation(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    events, cases = sample_frames
    case_id = cases.iloc[0]["case_id"]
    without_po = events.loc[
        ~((events["case_id"] == case_id) & (events["activity"] == "Purchase Order Created"))
    ].copy()

    with pytest.raises(
        ValueError,
        match="every case must contain a Purchase Order Created event",
    ):
        build_prediction_features(without_po, cases)


def test_temporal_sla_model_is_explainable(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    result = train_sla_model(*sample_frames)
    assert result.metrics["validation"] == "temporal_holdout"
    assert 0.5 <= result.metrics["roc_auc"] <= 1
    assert set(result.predictions["risk_band"]).issubset({"Low", "Medium", "High", "Critical"})
    assert result.feature_importance["absolute_importance"].is_monotonic_decreasing


def test_prior_correction_maps_balanced_cutoff_to_training_rate() -> None:
    scores = np.array([0.05, 0.3, 0.5, 0.7, 0.95])
    corrected = prior_corrected_probability(scores, 0.2)
    # Balanced 0.50 becomes the training breach rate; the ranking is preserved.
    assert corrected[2] == pytest.approx(0.2)
    assert np.all(np.diff(corrected) > 0)
    # Odds scale by pi / (1 - pi): 0.7 -> (0.7/0.3) * 0.25 = 0.5833 odds.
    assert corrected[3] == pytest.approx(0.5833333 / 1.5833333)
    assert np.allclose(prior_corrected_probability(scores, 0.5), scores)
    assert np.isfinite(prior_corrected_probability(np.array([0.0, 1.0]), 0.3)).all()


@pytest.mark.parametrize("rate", [0.0, 1.0, -0.1, 1.2])
def test_prior_correction_rejects_degenerate_rates(rate: float) -> None:
    with pytest.raises(ValueError, match="training_rate"):
        prior_corrected_probability(np.array([0.5]), rate)


def test_risk_scores_are_calibrated_and_decisions_unchanged(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    result = train_sla_model(*sample_frames)
    metrics = result.metrics
    predictions = result.predictions
    threshold = metrics["decision_threshold_risk"]
    assert threshold == pytest.approx(metrics["positive_rate_train"])
    # Review decisions are the balanced 0.50 cut-off, i.e. calibrated risk >= training rate.
    assert (
        predictions["predicted_breach"] == (predictions["risk_score"] >= threshold - 1e-12)
    ).all()
    assert metrics["mean_predicted_risk_holdout"] == pytest.approx(predictions["risk_score"].mean())


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
        {"replications": 2, "cases_per_replication": 120, "arrival_rate_per_hour": np.nan},
        {"replications": 2, "cases_per_replication": 120, "annual_volume": 0},
        {"replications": 2, "cases_per_replication": 120, "scenarios": ()},
    ],
)
def test_capacity_simulation_validates_inputs(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        simulate_capacity(**kwargs)


@pytest.mark.parametrize(
    "scenario",
    [
        Scenario("", "test", (Stage("Review", 1, 1.0),)),
        Scenario("Invalid", "test", (Stage("Review", True, 1.0),)),
        Scenario("Invalid", "test", (Stage("Review", 1, np.nan),)),
        Scenario("Invalid", "test", (Stage("Review", 1, 1.0),), invoice_rework_probability=1.1),
        Scenario("Invalid", "test", (Stage("Review", 1, 1.0),), one_time_investment_usd=-1),
    ],
)
def test_capacity_simulation_rejects_invalid_scenario_contract(scenario: Scenario) -> None:
    with pytest.raises(ValueError):
        simulate_capacity((scenario,), replications=2, cases_per_replication=100)


@pytest.mark.parametrize(
    "field", ["replications", "cases_per_replication", "seed", "annual_volume"]
)
def test_capacity_simulation_rejects_non_integer_controls(field: str) -> None:
    kwargs = {"replications": 2, "cases_per_replication": 120, field: 2.5}
    with pytest.raises(TypeError, match=field):
        simulate_capacity(**kwargs)


def test_demo_risk_scores_match_observed_breach_rate(
    full_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    # The class-weighted scores averaged 0.451 against a 0.369 holdout breach rate, and
    # the "High" band (0.60-0.80) breached only 56% of the time.
    predictions = train_sla_model(*full_frames).predictions
    assert predictions["risk_score"].mean() == pytest.approx(
        predictions["sla_breached"].mean(), abs=0.02
    )
    bands = pd.cut(predictions["risk_score"], [0, 0.3, 0.6, 0.8, 1.0])
    by_band = predictions.groupby(bands, observed=True).agg(
        predicted=("risk_score", "mean"), observed=("sla_breached", "mean")
    )
    assert (by_band["predicted"] - by_band["observed"]).abs().max() < 0.05
