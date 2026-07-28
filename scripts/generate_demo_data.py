"""Generate a deterministic, business-realistic purchase-to-pay event log."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from process_optimizer.config import (
    ACTIVITY_ROLES,
    AUTOMATED_ACTIVITIES,
    IDEAL_PROCESS,
)
from process_optimizer.contracts import CASE_COLUMNS, EVENT_COLUMNS

SEED = 20260728
DEFAULT_CASES = 12_000

BUSINESS_UNITS = ("Industrial Systems", "Consumer Products", "Corporate Services")
DEPARTMENTS = (
    "Operations",
    "Engineering",
    "Information Technology",
    "Facilities",
    "Finance",
)
COUNTRIES = ("Türkiye", "Germany", "Poland", "Netherlands")
MATERIAL_CATEGORIES = (
    "Direct Materials",
    "MRO",
    "Professional Services",
    "IT Equipment",
    "Facilities",
)
CHANNELS = ("ERP Portal", "Catalog", "Email Intake")
PRIORITIES = ("Urgent", "Standard", "Strategic")

DELAY_HOURS = {
    "Purchase Request Created": 0.0,
    "Manager Approval": 13.0,
    "Request Reworked": 20.0,
    "Procurement Review": 11.0,
    "Purchase Order Created": 7.0,
    "Purchase Order Sent": 0.4,
    "Supplier Confirmation": 11.0,
    "Delivery Delayed": 90.0,
    "Goods Received": 68.0,
    "Invoice Received": 30.0,
    "Invoice Duplicate Check": 0.3,
    "Duplicate Check Failed": 2.0,
    "Invoice Rejected": 8.0,
    "Corrected Invoice Received": 30.0,
    "Three-Way Match Failed": 10.0,
    "Invoice Blocked": 18.0,
    "Invoice Corrected": 28.0,
    "Invoice Matched": 9.0,
    "Payment Authorized": 14.0,
    "Payment Rejected": 20.0,
    "Payment Executed": 22.0,
    "Case Closed": 2.0,
}

PROCESSING_MINUTES = {
    "Purchase Request Created": 8,
    "Manager Approval": 16,
    "Request Reworked": 28,
    "Procurement Review": 38,
    "Purchase Order Created": 24,
    "Purchase Order Sent": 2,
    "Supplier Confirmation": 12,
    "Delivery Delayed": 18,
    "Goods Received": 22,
    "Invoice Received": 11,
    "Invoice Duplicate Check": 1,
    "Duplicate Check Failed": 14,
    "Invoice Rejected": 16,
    "Corrected Invoice Received": 13,
    "Three-Way Match Failed": 30,
    "Invoice Blocked": 26,
    "Invoice Corrected": 20,
    "Invoice Matched": 34,
    "Payment Authorized": 18,
    "Payment Rejected": 24,
    "Payment Executed": 2,
    "Case Closed": 1,
}

ROLE_COUNTS = {
    "Requester": 18,
    "Approver": 12,
    "Buyer": 10,
    "ERP Bot": 2,
    "Supplier": 1,
    "Receiving Clerk": 8,
    "Accounts Payable": 10,
    "AP Bot": 2,
    "Treasury Analyst": 6,
    "Payment Bot": 2,
}

BASE_VARIANTS = (
    ("happy_path", 0.48),
    ("fast_track", 0.10),
    ("approval_rework", 0.11),
    ("invoice_discrepancy", 0.10),
    ("three_way_match_failure", 0.07),
    ("duplicate_invoice", 0.06),
    ("payment_rework", 0.05),
    ("missing_approval", 0.03),
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_resources() -> tuple[list[dict[str, object]], dict[str, list[str]]]:
    resources: list[dict[str, object]] = []
    role_map: dict[str, list[str]] = defaultdict(list)
    for role, count in ROLE_COUNTS.items():
        prefix = "".join(part[0] for part in role.split()).upper()
        for number in range(1, count + 1):
            resource_id = f"{prefix}-{number:02d}"
            role_map[role].append(resource_id)
            resources.append(
                {
                    "resource_id": resource_id,
                    "resource_role": role,
                    "team": (
                        "Automation"
                        if "Bot" in role
                        else "External"
                        if role == "Supplier"
                        else role
                    ),
                    "fte_capacity": 0 if "Bot" in role or role == "Supplier" else 1,
                    "hourly_cost_usd": (
                        0
                        if "Bot" in role or role == "Supplier"
                        else 46
                        if role in {"Approver", "Buyer"}
                        else 34
                    ),
                }
            )
    return resources, role_map


def weighted_choice(randomizer: random.Random, options: tuple[tuple[str, float], ...]) -> str:
    draw = randomizer.random()
    cumulative = 0.0
    for name, weight in options:
        cumulative += weight
        if draw <= cumulative:
            return name
    return options[-1][0]


def build_sequence(base_variant: str, late_delivery: bool) -> list[str]:
    sequence = list(IDEAL_PROCESS)
    if base_variant in {"fast_track", "missing_approval"}:
        sequence.remove("Manager Approval")
    elif base_variant == "approval_rework":
        approval_index = sequence.index("Manager Approval")
        sequence[approval_index + 1 : approval_index + 1] = [
            "Request Reworked",
            "Manager Approval",
        ]
    elif base_variant == "invoice_discrepancy":
        match_index = sequence.index("Invoice Matched")
        sequence[match_index:match_index] = ["Invoice Blocked", "Invoice Corrected"]
    elif base_variant == "three_way_match_failure":
        sequence.remove("Goods Received")
        invoice_index = sequence.index("Invoice Received")
        sequence[invoice_index + 2 : invoice_index + 2] = [
            "Three-Way Match Failed",
            "Goods Received",
        ]
    elif base_variant == "duplicate_invoice":
        check_index = sequence.index("Invoice Duplicate Check")
        sequence[check_index + 1 : check_index + 1] = [
            "Duplicate Check Failed",
            "Invoice Rejected",
            "Corrected Invoice Received",
            "Invoice Duplicate Check",
        ]
    elif base_variant == "payment_rework":
        authorization_index = sequence.index("Payment Authorized")
        sequence[authorization_index + 1 : authorization_index + 1] = [
            "Payment Rejected",
            "Invoice Matched",
            "Payment Authorized",
        ]

    if late_delivery:
        confirmation_index = sequence.index("Supplier Confirmation")
        sequence.insert(confirmation_index + 1, "Delivery Delayed")
    return sequence


def lognormal(randomizer: random.Random, mean: float, sigma: float = 0.42) -> float:
    if mean == 0:
        return 0.0
    mu = math.log(mean / math.sqrt(1 + sigma**2))
    shape = math.sqrt(math.log(1 + sigma**2))
    return randomizer.lognormvariate(mu, shape)


def select_variant(
    randomizer: random.Random,
    *,
    amount_usd: float,
    vendor_tier: str,
    channel: str,
) -> tuple[str, bool]:
    base = weighted_choice(randomizer, BASE_VARIANTS)
    risk_boost = (
        0.07 * (vendor_tier == "C")
        + 0.05 * (amount_usd > 75_000)
        + 0.03 * (channel == "Email Intake")
    )
    late_delivery = randomizer.random() < 0.10 + risk_boost
    return base, late_delivery


def transition_delay(
    randomizer: random.Random,
    activity: str,
    *,
    amount_usd: float,
    vendor_tier: str,
    priority: str,
    country: str,
) -> float:
    mean = DELAY_HOURS[activity]
    if activity in {"Manager Approval", "Procurement Review"}:
        mean *= 1 + min(amount_usd / 180_000, 0.90)
    if activity in {
        "Supplier Confirmation",
        "Delivery Delayed",
        "Goods Received",
        "Corrected Invoice Received",
    }:
        mean *= {"A": 0.78, "B": 1.0, "C": 1.42}[vendor_tier]
        mean *= 1.12 if country in {"Germany", "Netherlands"} else 1.0
    if activity in {
        "Invoice Matched",
        "Invoice Blocked",
        "Payment Authorized",
    }:
        mean *= {"A": 0.88, "B": 1.0, "C": 1.25}[vendor_tier]
    mean *= {"Urgent": 0.68, "Standard": 1.0, "Strategic": 1.12}[priority]
    return lognormal(randomizer, mean)


def processing_time(randomizer: random.Random, activity: str, amount_usd: float) -> float:
    base = PROCESSING_MINUTES[activity]
    amount_multiplier = (
        1.25 if amount_usd > 100_000 and activity not in AUTOMATED_ACTIVITIES else 1.0
    )
    return max(0.2, lognormal(randomizer, base * amount_multiplier, sigma=0.30))


def write_csv(
    path: Path,
    columns: tuple[str, ...],
    rows: list[dict[str, object]],
    *,
    compressed: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compressed:
        with (
            path.open("wb") as binary,
            gzip.GzipFile(filename="", mode="wb", fileobj=binary, mtime=0) as zipped,
            io.TextIOWrapper(zipped, encoding="utf-8", newline="") as stream,
        ):
            writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def generate(
    case_count: int = DEFAULT_CASES,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    randomizer = random.Random(SEED)
    resources, role_map = build_resources()
    vendors = [
        {
            "vendor_id": f"V-{number:03d}",
            "vendor_tier": ("A" if number <= 18 else "B" if number <= 58 else "C"),
        }
        for number in range(1, 81)
    ]
    start = datetime(2025, 1, 1, 7, 0, tzinfo=UTC)
    horizon_seconds = int(timedelta(days=545).total_seconds())

    event_rows: list[dict[str, object]] = []
    case_rows: list[dict[str, object]] = []

    for case_number in range(1, case_count + 1):
        case_id = f"P2P-{case_number:06d}"
        business_unit = randomizer.choices(BUSINESS_UNITS, weights=(0.43, 0.35, 0.22))[0]
        department = randomizer.choices(DEPARTMENTS, weights=(0.31, 0.24, 0.17, 0.14, 0.14))[0]
        country = randomizer.choices(COUNTRIES, weights=(0.55, 0.17, 0.16, 0.12))[0]
        vendor = randomizer.choice(vendors)
        category = randomizer.choices(MATERIAL_CATEGORIES, weights=(0.32, 0.24, 0.18, 0.16, 0.10))[
            0
        ]
        channel = randomizer.choices(CHANNELS, weights=(0.66, 0.24, 0.10))[0]
        priority = randomizer.choices(PRIORITIES, weights=(0.18, 0.68, 0.14))[0]
        amount_usd = min(300_000.0, max(250.0, randomizer.lognormvariate(9.65, 1.05)))
        created_at = start + timedelta(seconds=randomizer.randrange(horizon_seconds))
        variant, late_delivery = select_variant(
            randomizer,
            amount_usd=amount_usd,
            vendor_tier=str(vendor["vendor_tier"]),
            channel=channel,
        )
        sequence = build_sequence(variant, late_delivery)
        variant_label = f"{variant}+late_delivery" if late_delivery else variant

        current = created_at
        activity_counts: dict[str, int] = defaultdict(int)
        for event_index, activity in enumerate(sequence, start=1):
            current += timedelta(
                hours=transition_delay(
                    randomizer,
                    activity,
                    amount_usd=amount_usd,
                    vendor_tier=str(vendor["vendor_tier"]),
                    priority=priority,
                    country=country,
                )
            )
            role = ACTIVITY_ROLES[activity]
            resource_pool = [str(vendor["vendor_id"])] if role == "Supplier" else role_map[role]
            activity_counts[activity] += 1
            event_rows.append(
                {
                    "case_id": case_id,
                    "event_index": event_index,
                    "activity": activity,
                    "timestamp": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "resource_id": randomizer.choice(resource_pool),
                    "resource_role": role,
                    "business_unit": business_unit,
                    "department": department,
                    "country": country,
                    "vendor_id": vendor["vendor_id"],
                    "vendor_tier": vendor["vendor_tier"],
                    "material_category": category,
                    "amount_usd": f"{amount_usd:.2f}",
                    "priority": priority,
                    "channel": channel,
                    "automated": str(activity in AUTOMATED_ACTIVITIES).lower(),
                    "processing_minutes": (
                        f"{processing_time(randomizer, activity, amount_usd):.2f}"
                    ),
                    "source_system": (
                        "Supplier Network"
                        if role == "Supplier"
                        else "Workflow Orchestrator"
                        if activity in AUTOMATED_ACTIVITIES
                        else "Enterprise ERP"
                    ),
                }
            )

        cycle_hours = (current - created_at).total_seconds() / 3600
        sla_target = {"Urgent": 120.0, "Standard": 240.0, "Strategic": 336.0}[priority]
        rework_count = sum(max(0, count - 1) for count in activity_counts.values())
        case_rows.append(
            {
                "case_id": case_id,
                "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "completed_at": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "business_unit": business_unit,
                "department": department,
                "country": country,
                "vendor_id": vendor["vendor_id"],
                "vendor_tier": vendor["vendor_tier"],
                "material_category": category,
                "amount_usd": f"{amount_usd:.2f}",
                "priority": priority,
                "channel": channel,
                "variant_ground_truth": variant_label,
                "event_count": len(sequence),
                "rework_count": rework_count,
                "cycle_time_hours": f"{cycle_hours:.4f}",
                "sla_target_hours": f"{sla_target:.1f}",
                "sla_breached": str(cycle_hours > sla_target).lower(),
            }
        )
    return event_rows, case_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=repository_root() / "data" / "demo")
    args = parser.parse_args()
    if args.cases < 1_000:
        parser.error("--cases must be at least 1000 for a representative demo")

    event_rows, case_rows = generate(args.cases)
    resources, _ = build_resources()
    output = args.output
    write_csv(output / "p2p_event_log.csv.gz", EVENT_COLUMNS, event_rows, compressed=True)
    write_csv(output / "case_master.csv.gz", CASE_COLUMNS, case_rows, compressed=True)
    write_csv(
        output / "p2p_event_log_sample.csv",
        EVENT_COLUMNS,
        event_rows[:750],
    )
    resource_columns = (
        "resource_id",
        "resource_role",
        "team",
        "fte_capacity",
        "hourly_cost_usd",
    )
    write_csv(output / "resources.csv", resource_columns, resources)
    (output / "ideal_process.json").write_text(
        json.dumps(
            {
                "process": "Purchase-to-Pay",
                "version": "1.0.0",
                "activities": list(IDEAL_PROCESS),
                "sla_targets_hours": {"Urgent": 120, "Standard": 240, "Strategic": 336},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(case_rows):,} cases and {len(event_rows):,} events in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
