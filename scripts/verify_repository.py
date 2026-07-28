"""Repository-level acceptance checks for the committed portfolio evidence."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable
from pathlib import Path

import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG = ROOT / "data/demo/p2p_event_log.csv.gz"
CASE_MASTER = ROOT / "data/demo/case_master.csv.gz"
ANALYSIS = ROOT / "reports/demo-analysis.json"
PPTX = ROOT / "output/presentation/Enterprise_Process_Mining_Executive_Deck_EN_TR.pptx"
PDF = ROOT / "output/pdf/Enterprise_Process_Mining_Executive_Report_EN_TR.pdf"
XLSX = ROOT / "output/Process_Mining_Decision_Workbook.xlsx"


class AcceptanceFailure(RuntimeError):
    """Raised when a repository acceptance gate fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceFailure(message)


def close(actual: float, expected: float, tolerance: float = 1e-4) -> None:
    require(
        math.isclose(actual, expected, abs_tol=tolerance),
        f"Expected {expected}, received {actual}",
    )


def xml_text(document: bytes) -> str:
    root = ET.fromstring(document)
    return " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))


def check_required_files() -> str:
    required = [
        ".dockerignore",
        ".env.example",
        ".gitattributes",
        ".github/CODEOWNERS",
        ".github/dependabot.yml",
        ".github/workflows/ci.yml",
        ".github/workflows/codeql.yml",
        ".github/workflows/security.yml",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "Dockerfile",
        "LICENSE",
        "README.md",
        "README_TR.md",
        "ROADMAP.md",
        "SECURITY.md",
        "bpmn/purchase-to-pay-reference.bpmn",
        "compose.yaml",
        "docs/architecture.md",
        "docs/data-contracts.md",
        "docs/methodology.md",
        "docs/security-threat-model.md",
        "docs/simulation-methodology.md",
        "docs/sla-model-card.md",
        "docs/sources.md",
        "docs/validation.md",
        "observability/grafana/dashboards/process-intelligence.json",
        "observability/prometheus/alert-rules.yml",
        "powerbi/Process_Intelligence.pbip",
        "powerbi/Process_Intelligence.Report/definition.pbir",
        "powerbi/Process_Intelligence.SemanticModel/definition.pbism",
        "powerbi/Process_Intelligence.SemanticModel/definition/model.tmdl",
        "pyproject.toml",
        "sql/001_schema.sql",
        "sql/002_analytics_views.sql",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    require(not missing, f"Missing required files: {missing}")
    require(PPTX.stat().st_size > 200_000, "Presentation is unexpectedly small")
    require(PDF.stat().st_size > 250_000, "Report is unexpectedly small")
    require(XLSX.stat().st_size > 30_000, "Workbook is unexpectedly small")
    return f"{len(required) + 3} required files and artifact size gates"


def check_json_yaml_xml() -> str:
    json_files = sorted(
        path
        for path in ROOT.rglob("*.json")
        if not any(part in {".git", ".venv", "node_modules", "tmp"} for part in path.parts)
    )
    yaml_files = sorted([*ROOT.rglob("*.yml"), *ROOT.rglob("*.yaml")])
    yaml_files = [
        path
        for path in yaml_files
        if not any(part in {".git", ".venv", "node_modules", "tmp"} for part in path.parts)
    ]
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    for path in yaml_files:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    ET.parse(ROOT / "bpmn/purchase-to-pay-reference.bpmn")
    for path in sorted((ROOT / "docs/images").glob("*.svg")):
        ET.parse(path)
    return f"{len(json_files)} JSON, {len(yaml_files)} YAML and 4 XML/SVG documents"


def check_event_data() -> str:
    required_fields = {"case_id", "event_index", "activity", "timestamp"}
    keys: set[tuple[str, str]] = set()
    event_case_ids: set[str] = set()
    last_timestamp: dict[str, str] = {}
    event_count = 0
    required_nulls = 0

    with gzip.open(EVENT_LOG, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(
            required_fields.issubset(reader.fieldnames or []),
            "Event schema is incomplete",
        )
        for row in reader:
            event_count += 1
            required_nulls += sum(not row[field].strip() for field in required_fields)
            key = (row["case_id"], row["event_index"])
            require(key not in keys, f"Duplicate event key: {key}")
            keys.add(key)
            event_case_ids.add(row["case_id"])
            previous = last_timestamp.get(row["case_id"])
            require(
                previous is None or row["timestamp"] >= previous,
                f"Timestamp regression in {row['case_id']}",
            )
            last_timestamp[row["case_id"]] = row["timestamp"]

    case_ids: set[str] = set()
    declared_event_count = 0
    with gzip.open(CASE_MASTER, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            require(row["case_id"] not in case_ids, f"Duplicate case: {row['case_id']}")
            case_ids.add(row["case_id"])
            declared_event_count += int(row["event_count"])

    require(event_count == 166_551, f"Unexpected event count: {event_count}")
    require(len(case_ids) == 12_000, f"Unexpected case count: {len(case_ids)}")
    require(required_nulls == 0, f"Required event-field nulls: {required_nulls}")
    require(event_case_ids == case_ids, "Event and case identifiers do not reconcile")
    require(declared_event_count == event_count, "Case event counts do not reconcile")
    return "166,551 events, 12,000 cases, unique keys, ordered timestamps"


def check_analysis() -> str:
    report = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    quality = report["data_quality"]
    require(quality["event_count"] == 166_551, "Report event count drifted")
    require(quality["case_count"] == 12_000, "Report case count drifted")
    require(quality["activity_count"] == 22, "Report activity count drifted")
    require(quality["resource_count"] == 150, "Report resource count drifted")
    require(quality["variant_count"] == 14, "Report variant count drifted")
    require(quality["event_case_reconciliation"], "Report reconciliation failed")
    require(quality["duplicate_case_event_keys"] == 0, "Report contains duplicate keys")
    require(quality["null_required_fields"] == 0, "Report contains required-field nulls")

    kpis = report["kpis"]
    expected_kpis = {
        "median_cycle_hours": 205.57,
        "p90_cycle_hours": 307.54,
        "p95_cycle_hours": 351.40,
        "sla_adherence": 0.6208,
        "straight_through_rate": 0.4232,
        "mean_conformance_fitness": 0.9162,
        "rework_case_rate": 0.2198,
        "automation_event_rate": 0.3647,
        "wait_time_share": 0.9840,
    }
    for key, expected in expected_kpis.items():
        close(float(kpis[key]), expected)

    model = report["sla_prediction"]["metrics"]
    require(model["validation"] == "temporal_holdout", "Model split is not temporal")
    require(model["train_cases"] == 9_600, "Training population drifted")
    require(model["holdout_cases"] == 2_400, "Holdout population drifted")
    close(float(model["roc_auc"]), 0.8220036618, tolerance=1e-8)
    close(float(model["average_precision"]), 0.7546884529, tolerance=1e-8)
    close(float(model["brier_score"]), 0.1693245062, tolerance=1e-8)

    simulation = report["capacity_simulation"]
    require(
        simulation["recommended_scenario"] == "Combined Optimization",
        "Recommended scenario drifted",
    )
    close(float(simulation["recommended_cycle_reduction_pct"]), 0.1942)
    close(float(simulation["recommended_sla_uplift_pp"]), 13.63)
    close(
        float(simulation["estimated_annual_value_usd"]),
        2_213_037.02,
        tolerance=0.01,
    )
    close(float(simulation["first_year_roi"]), 8.8357)
    return "KPI, temporal model and simulation evidence reconciled"


def check_bpmn() -> str:
    ideal = json.loads((ROOT / "data/demo/ideal_process.json").read_text(encoding="utf-8"))
    root = ET.parse(ROOT / "bpmn/purchase-to-pay-reference.bpmn").getroot()
    task_types = {
        "businessRuleTask",
        "manualTask",
        "receiveTask",
        "scriptTask",
        "sendTask",
        "serviceTask",
        "task",
        "userTask",
    }
    task_names = {
        element.attrib["name"]
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] in task_types and element.attrib.get("name")
    }
    missing = set(ideal["activities"]) - task_names
    require(not missing, f"BPMN is missing ideal activities: {sorted(missing)}")
    require(
        any(element.tag.endswith("}exclusiveGateway") for element in root.iter()),
        "BPMN has no exception gateway",
    )
    return f"{len(ideal['activities'])} ideal activities plus governed exception path"


def check_power_bi() -> str:
    project = json.loads((ROOT / "powerbi/Process_Intelligence.pbip").read_text(encoding="utf-8"))
    report_path = project["artifacts"][0]["report"]["path"]
    require(
        (ROOT / "powerbi" / report_path / "definition.pbir").is_file(),
        "PBIP report reference is broken",
    )
    definition = json.loads(
        (ROOT / "powerbi/Process_Intelligence.Report/definition.pbir").read_text(encoding="utf-8")
    )
    semantic_path = (
        ROOT
        / "powerbi/Process_Intelligence.Report"
        / definition["datasetReference"]["byPath"]["path"]
    ).resolve()
    require(
        (semantic_path / "definition.pbism").is_file(),
        "PBIR semantic-model reference is broken",
    )
    tables = sorted((semantic_path / "definition/tables").glob("*.tmdl"))
    require(len(tables) == 6, f"Expected 6 semantic tables, received {len(tables)}")
    measures = (semantic_path / "definition/tables/Measures.tmdl").read_text(encoding="utf-8")
    for name in ["SLA Adherence %", "Median Cycle Hours", "Straight Through %"]:
        require(name in measures, f"Missing DAX measure: {name}")
    return "PBIP references, semantic model, 6 TMDL tables and core measures"


def check_presentation() -> str:
    with zipfile.ZipFile(PPTX) as archive:
        names = archive.namelist()
        slide_names = sorted(
            name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
        note_names = sorted(
            name for name in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)
        )
        require(
            len(slide_names) == 20,
            f"Expected 20 slides, received {len(slide_names)}",
        )
        require(
            len(note_names) == 20,
            f"Expected 20 note pages, received {len(note_names)}",
        )
        for name in note_names:
            text = xml_text(archive.read(name))
            require(
                "[Sources]" in text and "[/Sources]" in text,
                f"Missing source block in {name}",
            )
    return "20 slides with 20 slide-level source-note blocks"


def check_pdf() -> str:
    reader = PdfReader(PDF)
    require(
        len(reader.pages) == 20,
        f"Expected 20 PDF pages, received {len(reader.pages)}",
    )
    title = str(reader.metadata.title or "")
    require("Enterprise Process Mining" in title, "PDF title metadata is missing")
    return "20-page bilingual report with document metadata"


def check_workbook() -> str:
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    expected = [
        "Executive Dashboard",
        "Scenario Simulator",
        "KPI Evidence",
        "Bottlenecks",
        "Process Variants",
        "SLA Risk",
        "Data Dictionary",
        "Sources",
    ]
    with zipfile.ZipFile(XLSX) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = [sheet.attrib["name"] for sheet in workbook.findall(".//m:sheet", namespace)]
        require(sheets == expected, f"Unexpected workbook sheets: {sheets}")
        formula_count = 0
        error_count = 0
        for name in archive.namelist():
            if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name):
                continue
            sheet = ET.fromstring(archive.read(name))
            formula_count += len(sheet.findall(".//m:f", namespace))
            error_count += sum(
                cell.attrib.get("t") == "e" for cell in sheet.findall(".//m:c", namespace)
            )
        require(formula_count >= 10, f"Expected decision formulas, found {formula_count}")
        require(error_count == 0, f"Workbook contains {error_count} formula errors")
    return f"8 decision sheets, {formula_count} formulas, zero error cells"


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    require(header[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG signature: {path}")
    return struct.unpack(">II", header[16:24])


def check_images() -> str:
    expected = {
        "dashboard-preview.png": (1920, 1080),
        "architecture.png": (1600, 900),
        "process-flow.png": (1800, 600),
    }
    for name, dimensions in expected.items():
        actual = png_dimensions(ROOT / "docs/images" / name)
        require(
            actual == dimensions,
            f"{name}: expected {dimensions}, received {actual}",
        )
    return "3 publication visuals at committed target dimensions"


def check_delivery_controls() -> str:
    workflows = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
    )
    for action in [
        "actions/checkout@v7.0.1",
        "actions/setup-python@v7.0.0",
        "github/codeql-action/init@v3.37.1",
        "github/codeql-action/analyze@v3.37.1",
        "aquasecurity/trivy-action@0.36.0",
    ]:
        require(action in workflows, f"Missing pinned workflow action: {action}")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    require(
        "USER 10001:10001" in dockerfile,
        "Container does not declare a nonroot user",
    )
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    for control in ["read_only: true", "no-new-privileges:true", "cap_drop: [ALL]"]:
        require(control in compose, f"Missing Compose hardening control: {control}")
    return "Pinned CI/security actions and nonroot, read-only container controls"


def text_files() -> Iterable[Path]:
    suffixes = {
        ".bpmn",
        ".dax",
        ".json",
        ".md",
        ".mjs",
        ".pbip",
        ".pbir",
        ".pbism",
        ".py",
        ".sql",
        ".svg",
        ".tmdl",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    excluded = {".git", ".venv", "node_modules", "tmp"}
    for current, directories, files in os.walk(ROOT, followlinks=False):
        directories[:] = [name for name in directories if name not in excluded]
        directory = Path(current)
        for filename in files:
            path = directory / filename
            if path.suffix.lower() in suffixes:
                yield path


def check_secret_patterns() -> str:
    patterns = {
        "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
        "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    }
    findings: list[str] = []
    scanned = 0
    for path in text_files():
        scanned += 1
        content = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in patterns.items():
            if pattern.search(content):
                findings.append(f"{label}: {path.relative_to(ROOT)}")
    require(not findings, f"Potential secrets found: {findings}")
    return f"{scanned} text files scanned for high-confidence secret patterns"


def optional_render_checks(skip: bool) -> str:
    if skip:
        return "External office rendering skipped by explicit flag"

    rendered: list[str] = []
    unavailable: list[str] = []
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        with tempfile.TemporaryDirectory(prefix="process-report-render-") as directory:
            prefix = Path(directory) / "page"
            subprocess.run(
                [pdftoppm, "-png", "-r", "72", str(PDF), str(prefix)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            pages = list(Path(directory).glob("page-*.png"))
            require(len(pages) == 20, "Rendered PDF page count drifted")
        rendered.append("PDF")

    office = shutil.which("soffice") or shutil.which("libreoffice")
    if office:
        with tempfile.TemporaryDirectory(prefix="process-deck-render-") as directory:
            try:
                subprocess.run(
                    [
                        office,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        directory,
                        str(PPTX),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                )
                converted = Path(directory) / f"{PPTX.stem}.pdf"
                require(converted.is_file(), "Presentation renderer produced no PDF")
                require(
                    len(PdfReader(converted).pages) == 20,
                    "Rendered slide count drifted",
                )
                rendered.append("PPTX")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                unavailable.append("PPTX")

    if rendered:
        status = f"External render completed for {', '.join(rendered)}"
        if unavailable:
            status += f"; unavailable for {', '.join(unavailable)}"
        return status
    return "No usable optional office renderer found; structural gates completed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-office-render",
        action="store_true",
        help="Skip optional Poppler/LibreOffice rendering in portable CI jobs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checks = [
        ("Required files", check_required_files),
        ("Syntax", check_json_yaml_xml),
        ("Event data", check_event_data),
        ("Analysis", check_analysis),
        ("BPMN", check_bpmn),
        ("Power BI", check_power_bi),
        ("Presentation", check_presentation),
        ("PDF", check_pdf),
        ("Workbook", check_workbook),
        ("Images", check_images),
        ("Delivery controls", check_delivery_controls),
        ("Secret scan", check_secret_patterns),
    ]
    for name, check in checks:
        print(f"[PASS] {name}: {check()}")
    print(f"[PASS] Render: {optional_render_checks(args.skip_office_render)}")
    print(f"\nRepository acceptance passed: {len(checks) + 1} gates.")


if __name__ == "__main__":
    main()
