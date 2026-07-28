"""Read-only FastAPI surface for process intelligence outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from process_optimizer.config import repository_root


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"analysis report not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def create_app(analysis_path: str | Path | None = None) -> FastAPI:
    """Create a testable application instance."""

    configured_path = analysis_path or os.getenv("ANALYSIS_PATH")
    path = (
        Path(configured_path)
        if configured_path
        else repository_root() / "reports" / "demo-analysis.json"
    )
    app = FastAPI(
        title="Enterprise Process Optimization API",
        version="1.0.0",
        description=(
            "Read-only access to purchase-to-pay process discovery, conformance, "
            "performance, SLA risk, and capacity simulation outputs."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/healthz", tags=["operations"])
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/readyz", tags=["operations"])
    def ready() -> dict[str, str]:
        if not path.exists():
            raise HTTPException(status_code=503, detail="analysis output is unavailable")
        return {"status": "ready", "analysis": str(path)}

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/summary", tags=["process intelligence"])
    def summary() -> dict[str, Any]:
        report = _load_report(path)
        return {
            "project": report["project"],
            "data_quality": report["data_quality"],
            "kpis": report["kpis"],
            "recommendation": {
                key: value
                for key, value in report["capacity_simulation"].items()
                if key
                in {
                    "recommended_scenario",
                    "recommended_cycle_reduction_pct",
                    "recommended_sla_uplift_pp",
                    "estimated_annual_value_usd",
                    "first_year_roi",
                }
            },
        }

    @app.get("/api/v1/process-map", tags=["process intelligence"])
    def process_map() -> dict[str, Any]:
        report = _load_report(path)
        return report["process_discovery"]

    @app.get("/api/v1/conformance", tags=["process intelligence"])
    def conformance() -> dict[str, Any]:
        return _load_report(path)["conformance"]

    @app.get("/api/v1/bottlenecks", tags=["process intelligence"])
    def bottlenecks() -> dict[str, Any]:
        return _load_report(path)["performance"]

    @app.get("/api/v1/sla-risk", tags=["decision intelligence"])
    def sla_risk() -> dict[str, Any]:
        return _load_report(path)["sla_prediction"]

    @app.get("/api/v1/simulations", tags=["decision intelligence"])
    def simulations() -> dict[str, Any]:
        return _load_report(path)["capacity_simulation"]

    @app.get("/api/v1/governance", tags=["governance"])
    def governance() -> dict[str, Any]:
        return _load_report(path)["governance"]

    return app


app = create_app()
