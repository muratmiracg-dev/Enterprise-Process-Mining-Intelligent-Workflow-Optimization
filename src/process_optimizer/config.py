"""Shared configuration and process semantics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

IDEAL_PROCESS = (
    "Purchase Request Created",
    "Manager Approval",
    "Procurement Review",
    "Purchase Order Created",
    "Purchase Order Sent",
    "Supplier Confirmation",
    "Goods Received",
    "Invoice Received",
    "Invoice Duplicate Check",
    "Invoice Matched",
    "Payment Authorized",
    "Payment Executed",
    "Case Closed",
)

AUTOMATED_ACTIVITIES = {
    "Purchase Request Created",
    "Purchase Order Sent",
    "Invoice Duplicate Check",
    "Payment Executed",
    "Case Closed",
}

ACTIVITY_ROLES = {
    "Purchase Request Created": "Requester",
    "Manager Approval": "Approver",
    "Request Reworked": "Requester",
    "Procurement Review": "Buyer",
    "Purchase Order Created": "Buyer",
    "Purchase Order Sent": "ERP Bot",
    "Supplier Confirmation": "Supplier",
    "Delivery Delayed": "Supplier",
    "Goods Received": "Receiving Clerk",
    "Invoice Received": "Accounts Payable",
    "Invoice Duplicate Check": "AP Bot",
    "Duplicate Check Failed": "Accounts Payable",
    "Invoice Rejected": "Accounts Payable",
    "Corrected Invoice Received": "Supplier",
    "Three-Way Match Failed": "Accounts Payable",
    "Invoice Blocked": "Accounts Payable",
    "Invoice Corrected": "Supplier",
    "Invoice Matched": "Accounts Payable",
    "Payment Authorized": "Treasury Analyst",
    "Payment Rejected": "Treasury Analyst",
    "Payment Executed": "Payment Bot",
    "Case Closed": "ERP Bot",
}


@dataclass(frozen=True)
class ProjectPaths:
    """Repository paths used by the analysis pipeline."""

    root: Path

    @property
    def data_dir(self) -> Path:
        return self.root / "data" / "demo"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def tables_dir(self) -> Path:
        return self.reports_dir / "tables"

    @property
    def event_log(self) -> Path:
        return self.data_dir / "p2p_event_log.csv.gz"

    @property
    def cases(self) -> Path:
        return self.data_dir / "case_master.csv.gz"

    @property
    def resources(self) -> Path:
        return self.data_dir / "resources.csv"

    @property
    def analysis(self) -> Path:
        return self.reports_dir / "demo-analysis.json"


def repository_root() -> Path:
    """Return the repository root from the installed source layout."""

    return Path(__file__).resolve().parents[2]
