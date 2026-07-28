"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from process_optimizer.config import ProjectPaths, repository_root
from process_optimizer.pipeline import analyze_event_log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="process-optimizer",
        description="Run enterprise process mining and workflow optimization.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Run the analytical pipeline")
    analyze.add_argument("--root", type=Path, default=repository_root())
    analyze.add_argument(
        "--without-pm4py",
        action="store_true",
        help="Skip the PM4Py reference discovery boundary.",
    )

    serve = subparsers.add_parser("serve", help="Serve the read-only API")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "analyze":
        paths = ProjectPaths(args.root.resolve())
        report = analyze_event_log(
            paths.event_log,
            paths.cases,
            output_path=paths.analysis,
            tables_dir=paths.tables_dir,
            include_pm4py=not args.without_pm4py,
        )
        print(
            "Analysis complete: "
            f"{report['data_quality']['case_count']:,} cases, "
            f"{report['data_quality']['event_count']:,} events, "
            f"SLA adherence {report['kpis']['sla_adherence']:.1%}."
        )
        return 0

    import uvicorn

    uvicorn.run(
        "process_optimizer.api:app",
        host=args.host,
        port=args.port,
        reload=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
