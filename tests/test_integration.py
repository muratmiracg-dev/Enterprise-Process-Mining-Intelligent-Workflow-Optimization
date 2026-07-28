from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from process_optimizer.api import create_app
from process_optimizer.cli import build_parser, main
from process_optimizer.pipeline import analyze_frames
from process_optimizer.pm4py_bridge import (
    PM4PyUnavailable,
    _pm4py,
    discover_reference_model,
    prepare_dataframe,
)
from process_optimizer.repository import EventLogRepository

ROOT = Path(__file__).resolve().parents[1]


def test_repository_loads_committed_demo(
    full_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    events, cases = full_frames
    assert len(events) == 166_551
    assert len(cases) == 12_000
    assert events["case_id"].nunique() == len(cases)


def test_pipeline_produces_decision_outputs(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    report, tables = analyze_frames(*sample_frames, include_pm4py=False)
    assert report["project"]["process"] == "Purchase-to-Pay"
    assert report["data_quality"]["case_count"] == 1_200
    assert report["capacity_simulation"]["recommended_scenario"] == "Combined Optimization"
    assert set(tables) == {
        "activities",
        "bottlenecks",
        "case_conformance",
        "case_performance",
        "deviations",
        "directly_follows_graph",
        "resource_workload",
        "rework",
        "risk_predictions",
        "sla_model_drivers",
        "simulation_scenarios",
        "variants",
    }


def test_pm4py_reference_discovery(
    sample_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    events, _ = sample_frames
    formatted = prepare_dataframe(events.head(100))
    assert "case:concept:name" in formatted
    result = discover_reference_model(events, sample_cases=30)
    assert result["sample_cases"] == 30
    assert result["dfg_edges"] > 0
    assert result["pm4py_version"]


def test_pm4py_unavailable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "pm4py":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    with pytest.raises(PM4PyUnavailable):
        _pm4py()


def test_api_exposes_read_only_outputs() -> None:
    client = TestClient(create_app(ROOT / "reports/demo-analysis.json"))
    assert client.get("/healthz").json() == {"status": "healthy"}
    assert client.get("/readyz").status_code == 200
    assert client.get("/api/v1/summary").json()["data_quality"]["event_count"] == 166_551
    for route in (
        "/api/v1/process-map",
        "/api/v1/conformance",
        "/api/v1/bottlenecks",
        "/api/v1/sla-risk",
        "/api/v1/simulations",
        "/api/v1/governance",
    ):
        assert client.get(route).status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "process_optimizer_analysis_runs_total" in metrics.text


def test_api_readiness_and_missing_report(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "missing.json"))
    assert client.get("/readyz").status_code == 503
    with pytest.raises(FileNotFoundError):
        client.get("/api/v1/summary")


def test_api_honors_environment_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    report = ROOT / "reports/demo-analysis.json"
    target = tmp_path / "report.json"
    target.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("ANALYSIS_PATH", str(target))
    assert TestClient(create_app()).get("/readyz").status_code == 200


def test_cli_parser_and_analyze(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    parser = build_parser()
    args = parser.parse_args(["serve", "--host", "127.0.0.1", "--port", "9000"])
    assert (args.host, args.port) == ("127.0.0.1", 9000)

    source_data = ROOT / "data/demo"
    target_data = tmp_path / "data/demo"
    target_data.mkdir(parents=True)
    for name in ("p2p_event_log.csv.gz", "case_master.csv.gz"):
        (target_data / name).write_bytes((source_data / name).read_bytes())
    assert main(["analyze", "--root", str(tmp_path), "--without-pm4py"]) == 0
    assert (
        json.loads((tmp_path / "reports/demo-analysis.json").read_text())["data_quality"][
            "case_count"
        ]
        == 12_000
    )
    assert "Analysis complete" in capsys.readouterr().out


def test_repository_rejects_bad_reconciliation(tmp_path: Path) -> None:
    events = pd.read_csv(ROOT / "data/demo/p2p_event_log_sample.csv").head(2)
    cases = pd.read_csv(ROOT / "data/demo/case_master.csv.gz").head(1)
    events.to_csv(tmp_path / "events.csv", index=False)
    cases.assign(event_count=99).to_csv(tmp_path / "cases.csv", index=False)
    with pytest.raises(ValueError):
        EventLogRepository(tmp_path / "events.csv", tmp_path / "cases.csv").load()
