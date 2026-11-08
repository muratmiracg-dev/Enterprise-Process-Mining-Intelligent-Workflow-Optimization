from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "compare_reports", ROOT / "scripts/compare_reports.py"
)
compare_reports = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_reports)


def _copy_reports(tmp_path: Path) -> tuple[Path, Path]:
    committed = tmp_path / "committed"
    regenerated = tmp_path / "regenerated"
    shutil.copytree(ROOT / "reports", committed)
    shutil.copytree(ROOT / "reports", regenerated)
    return committed, regenerated


def _edit_json(path: Path, edit) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    edit(report)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def test_committed_reports_match_themselves(tmp_path: Path) -> None:
    committed, regenerated = _copy_reports(tmp_path)
    assert compare_reports.compare_trees(committed, regenerated) == []
    assert compare_reports.main([str(committed), str(regenerated)]) == 0


def test_float_noise_and_pm4py_version_are_ignored(tmp_path: Path) -> None:
    committed, regenerated = _copy_reports(tmp_path)

    def edit(report: dict) -> None:
        report["kpis"]["median_cycle_hours"] *= 1 + 1e-12
        report["process_discovery"]["pm4py_reference"]["pm4py_version"] = "9.9.9"

    _edit_json(regenerated / "demo-analysis.json", edit)
    assert compare_reports.compare_trees(committed, regenerated) == []


def test_changed_kpi_is_reported(tmp_path: Path) -> None:
    committed, regenerated = _copy_reports(tmp_path)

    def edit(report: dict) -> None:
        report["kpis"]["sla_adherence"] = 0.65

    _edit_json(regenerated / "demo-analysis.json", edit)
    problems = compare_reports.compare_trees(committed, regenerated)
    assert len(problems) == 1
    assert problems[0].startswith("demo-analysis.json: $.kpis.sla_adherence:")
    assert compare_reports.main([str(committed), str(regenerated)]) == 1


def test_changed_decision_table_is_reported(tmp_path: Path) -> None:
    committed, regenerated = _copy_reports(tmp_path)
    table = regenerated / "tables" / "bottlenecks.csv"
    lines = table.read_text(encoding="utf-8").splitlines()
    header, first = lines[0].split(","), lines[1].split(",")
    column = header.index("bottleneck_score")
    first[column] = str(float(first[column]) - 0.1)
    lines[1] = ",".join(first)
    table.write_text("\n".join(lines) + "\n", encoding="utf-8")

    problems = compare_reports.compare_trees(committed, regenerated)
    assert problems == [problems[0]] and problems[0].startswith(
        "tables/bottlenecks.csv: column 'bottleneck_score'"
    )


def test_missing_and_structural_changes_are_reported(tmp_path: Path) -> None:
    committed, regenerated = _copy_reports(tmp_path)
    (regenerated / "tables" / "rework.csv").unlink()
    variants = regenerated / "tables" / "variants.csv"
    variants.write_text(
        "\n".join(variants.read_text(encoding="utf-8").splitlines()[:-1]) + "\n",
        encoding="utf-8",
    )

    problems = "\n".join(compare_reports.compare_trees(committed, regenerated))
    assert "tables/rework.csv: missing after regeneration" in problems
    assert "tables/variants.csv: row count" in problems


def test_empty_committed_tree_fails(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert compare_reports.main([str(empty), str(ROOT / "reports")]) == 1
