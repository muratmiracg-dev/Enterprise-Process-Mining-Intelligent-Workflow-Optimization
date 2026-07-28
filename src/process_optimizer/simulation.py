"""Reproducible queue-based capacity simulation for workflow scenarios."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Stage:
    """One capacity-constrained workflow stage."""

    name: str
    capacity: int
    mean_service_hours: float
    variability: float = 0.45


@dataclass(frozen=True)
class Scenario:
    """Capacity and automation assumptions for one what-if scenario."""

    name: str
    description: str
    stages: tuple[Stage, ...]
    external_lead_time_multiplier: float = 1.0
    invoice_rework_probability: float = 0.16
    one_time_investment_usd: float = 0.0


BASE_STAGES = (
    Stage("Manager Approval", capacity=7, mean_service_hours=1.15),
    Stage("Procurement Review", capacity=6, mean_service_hours=1.45),
    Stage("Purchase Order Created", capacity=5, mean_service_hours=0.95),
    Stage("Goods Received", capacity=7, mean_service_hours=0.80),
    Stage("Invoice Matched", capacity=4, mean_service_hours=1.55),
    Stage("Payment Authorized", capacity=3, mean_service_hours=1.05),
)


def default_scenarios() -> tuple[Scenario, ...]:
    """Return the governed scenario catalog."""

    baseline = Scenario(
        name="Baseline",
        description="Observed staffing, manual approval, and invoice rework assumptions.",
        stages=BASE_STAGES,
    )
    approval_automation = Scenario(
        name="Approval Automation",
        description="Rules-based low-risk approvals and faster purchase-order preparation.",
        stages=tuple(
            replace(stage, mean_service_hours=stage.mean_service_hours * 0.58)
            if stage.name in {"Manager Approval", "Purchase Order Created"}
            else stage
            for stage in BASE_STAGES
        ),
        external_lead_time_multiplier=0.97,
        invoice_rework_probability=0.13,
        one_time_investment_usd=95_000,
    )
    ap_capacity = Scenario(
        name="AP Capacity",
        description="Two additional invoice-match seats and one treasury seat.",
        stages=tuple(
            replace(stage, capacity=6)
            if stage.name == "Invoice Matched"
            else replace(stage, capacity=4)
            if stage.name == "Payment Authorized"
            else stage
            for stage in BASE_STAGES
        ),
        invoice_rework_probability=0.11,
        one_time_investment_usd=150_000,
    )
    combined = Scenario(
        name="Combined Optimization",
        description="Approval automation, AP capacity, and supplier lead-time intervention.",
        stages=tuple(
            replace(
                stage,
                capacity=(
                    6
                    if stage.name == "Invoice Matched"
                    else 4
                    if stage.name == "Payment Authorized"
                    else stage.capacity
                ),
                mean_service_hours=(
                    stage.mean_service_hours * 0.55
                    if stage.name in {"Manager Approval", "Purchase Order Created"}
                    else stage.mean_service_hours * 0.82
                    if stage.name == "Invoice Matched"
                    else stage.mean_service_hours
                ),
            )
            for stage in BASE_STAGES
        ),
        external_lead_time_multiplier=0.82,
        invoice_rework_probability=0.07,
        one_time_investment_usd=225_000,
    )
    return baseline, approval_automation, ap_capacity, combined


def _lognormal_parameters(mean: float, sigma: float) -> tuple[float, float]:
    variance = sigma**2
    mu = np.log(mean / np.sqrt(1 + variance))
    shape = np.sqrt(np.log(1 + variance))
    return float(mu), float(shape)


def _simulate_replication(
    scenario: Scenario,
    *,
    cases: int,
    seed: int,
    arrival_rate_per_hour: float,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    arrivals = np.cumsum(rng.exponential(1 / arrival_rate_per_hour, size=cases))
    completion = arrivals.copy()
    manual_hours = np.zeros(cases)

    for stage in scenario.stages:
        available = [0.0] * stage.capacity
        heapq.heapify(available)
        mu, sigma = _lognormal_parameters(stage.mean_service_hours, stage.variability)
        services = rng.lognormal(mu, sigma, size=cases)
        next_completion = np.empty(cases)
        stage_arrival_order = np.argsort(completion, kind="stable")
        for index in stage_arrival_order:
            server_available = heapq.heappop(available)
            start = max(float(completion[index]), server_available)
            service = float(services[index])
            finish = start + service
            next_completion[index] = finish
            manual_hours[index] += service
            heapq.heappush(available, finish)
        completion = next_completion

        if stage.name == "Purchase Order Created":
            transit_mu, transit_sigma = _lognormal_parameters(
                195 * scenario.external_lead_time_multiplier, 0.42
            )
            completion += rng.lognormal(transit_mu, transit_sigma, size=cases)

        if stage.name == "Invoice Matched":
            rework = rng.random(cases) < scenario.invoice_rework_probability
            completion += rework * rng.lognormal(mu, sigma, size=cases)
            manual_hours += rework * rng.lognormal(mu, sigma, size=cases)

    cycle_hours = completion - arrivals
    target_draw = rng.random(cases)
    targets = np.where(target_draw < 0.18, 120.0, np.where(target_draw < 0.86, 240.0, 336.0))
    breached = cycle_hours > targets
    elapsed_window = max(float(completion.max() - arrivals.min()), 1.0)
    return {
        "mean_cycle_hours": float(cycle_hours.mean()),
        "median_cycle_hours": float(np.median(cycle_hours)),
        "p90_cycle_hours": float(np.quantile(cycle_hours, 0.90)),
        "sla_adherence": float(1 - breached.mean()),
        "manual_hours_per_case": float(manual_hours.mean()),
        "throughput_cases_per_8h": float(cases / elapsed_window * 8),
    }


def simulate_capacity(
    scenarios: tuple[Scenario, ...] | None = None,
    *,
    replications: int = 24,
    cases_per_replication: int = 900,
    seed: int = 20260728,
    annual_volume: int = 8_000,
    arrival_rate_per_hour: float = 2.85,
) -> pd.DataFrame:
    """Run replicated capacity scenarios and quantify operational value."""

    if replications < 2 or cases_per_replication < 100:
        raise ValueError("simulation requires at least 2 replications and 100 cases")
    if arrival_rate_per_hour <= 0:
        raise ValueError("arrival_rate_per_hour must be positive")

    catalog = scenarios or default_scenarios()
    rows: list[dict[str, float | str]] = []
    for scenario in catalog:
        outcomes = [
            _simulate_replication(
                scenario,
                cases=cases_per_replication,
                seed=seed + replication,
                arrival_rate_per_hour=arrival_rate_per_hour,
            )
            for replication in range(replications)
        ]
        frame = pd.DataFrame(outcomes)
        row: dict[str, float | str] = {
            "scenario": scenario.name,
            "description": scenario.description,
            "one_time_investment_usd": scenario.one_time_investment_usd,
        }
        for column in frame.columns:
            row[column] = float(frame[column].mean())
        rows.append(row)

    result = pd.DataFrame(rows)
    baseline = result.iloc[0]
    result["cycle_time_reduction_pct"] = (
        1 - result["mean_cycle_hours"] / float(baseline["mean_cycle_hours"])
    ).clip(lower=0)
    result["sla_adherence_uplift_pp"] = (
        result["sla_adherence"] - float(baseline["sla_adherence"])
    ) * 100
    result["manual_hours_saved_per_case"] = (
        float(baseline["manual_hours_per_case"]) - result["manual_hours_per_case"]
    ).clip(lower=0)
    delay_hours_saved = (float(baseline["mean_cycle_hours"]) - result["mean_cycle_hours"]).clip(
        lower=0
    )
    breach_reduction = (result["sla_adherence"] - float(baseline["sla_adherence"])).clip(lower=0)
    result["estimated_annual_value_usd"] = (
        delay_hours_saved * 5.5 * annual_volume
        + result["manual_hours_saved_per_case"] * 32 * annual_volume
        + breach_reduction * 85 * annual_volume
    )
    investment = result["one_time_investment_usd"]
    result["first_year_roi"] = 0.0
    invested = investment > 0
    result.loc[invested, "first_year_roi"] = (
        result.loc[invested, "estimated_annual_value_usd"] - investment[invested]
    ) / investment[invested]
    return result
