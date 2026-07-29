"""V23.9 offline-only portfolio audit certificate.

This module seals a successful V23.8 audit result in a deterministic SHA-256
certificate.  It intentionally contains no market-data, account, network,
broker, order-submission, or live-execution integration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from backtest.offline_paper_portfolio_ledger_audit_v23_8 import (
    PortfolioLedgerAuditV238Result,
    verify_audit_certificate,
)


VERSION = "V23.9"
CONFIRMATION_TEXT = "CERTIFY OFFLINE PAPER PORTFOLIO AUDIT V23.9"
OUTPUT_DIRECTORY = Path("backtest_outputs")


def sha256_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class PortfolioAuditCertificateV239Policy:
    required_confirmation_text: str = CONFIRMATION_TEXT
    required_source_version: str = "V23.8"
    required_source_status: str = "AUDITED_IN_MEMORY"
    certificate_is_immutable: bool = True
    source_mutation_allowed: bool = False
    market_data_api_allowed: bool = False
    account_api_allowed: bool = False
    network_access_allowed: bool = False
    broker_api_allowed: bool = False
    broker_order_creation_allowed: bool = False
    order_submission_allowed: bool = False
    live_execution_allowed: bool = False


DEFAULT_POLICY = PortfolioAuditCertificateV239Policy()


def validate_policy(policy: PortfolioAuditCertificateV239Policy) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(policy, PortfolioAuditCertificateV239Policy):
        return ("policy type is invalid",)
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("confirmation policy is invalid")
    if policy.required_source_version != "V23.8":
        errors.append("source version policy is invalid")
    if policy.required_source_status != "AUDITED_IN_MEMORY":
        errors.append("source status policy is invalid")
    if not policy.certificate_is_immutable or policy.source_mutation_allowed:
        errors.append("immutability policy is invalid")
    blocked = (
        policy.market_data_api_allowed,
        policy.account_api_allowed,
        policy.network_access_allowed,
        policy.broker_api_allowed,
        policy.broker_order_creation_allowed,
        policy.order_submission_allowed,
        policy.live_execution_allowed,
    )
    if any(blocked):
        errors.append("external execution policy is invalid")
    return tuple(errors)


@dataclass(frozen=True)
class OfflinePortfolioAuditCertificateV239:
    certificate_id: str
    issued_at: str
    certificate_status: str
    operator: str
    confirmation_text: str
    source_audit_result_id: str
    source_audit_certificate_hash: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_latest_entry_hash: str
    source_total_entry_count: int
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash")
        return payload


@dataclass
class PortfolioAuditCertificationV239Result:
    version: str
    created_at: str
    certification_result_id: str
    result_status: str
    source_audit_result_id: str
    source_audit_certificate_hash: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_latest_entry_hash: str
    source_total_entry_count: int
    certificate: OfflinePortfolioAuditCertificateV239 | None
    policy_check_passed: bool
    source_check_passed: bool
    linkage_check_passed: bool
    chronology_check_passed: bool
    source_unchanged: bool
    certificate_hash_passed: bool
    all_checks_passed: bool
    certificate_created: bool
    source_modified: bool = False
    ledger_modified: bool = False
    funds_reserved: bool = False
    holdings_reserved: bool = False
    execution_blocked: bool = True
    transmit: bool = False
    credentials_used: bool = False
    market_data_api_called: bool = False
    account_api_called: bool = False
    network_accessed: bool = False
    broker_api_called: bool = False
    broker_order_created: bool = False
    order_submitted: bool = False
    live_execution_authorized: bool = False
    policy: PortfolioAuditCertificateV239Policy = field(default_factory=lambda: DEFAULT_POLICY)
    reasons: tuple[str, ...] = ()
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_certificate(
    certificate: OfflinePortfolioAuditCertificateV239,
) -> tuple[str, ...]:
    if not isinstance(certificate, OfflinePortfolioAuditCertificateV239):
        return ("certificate type is invalid",)
    errors: list[str] = []
    if certificate.certificate_hash != sha256_payload(
        certificate.payload_without_hash()
    ):
        errors.append("certificate hash is invalid")
    if certificate.certificate_status != "CERTIFIED":
        errors.append("certificate status is invalid")
    if certificate.confirmation_text != CONFIRMATION_TEXT:
        errors.append("certificate confirmation is invalid")
    if not certificate.operator.strip():
        errors.append("certificate operator is empty")
    if (
        not certificate.execution_blocked
        or certificate.funds_reserved
        or certificate.holdings_reserved
    ):
        errors.append("certificate safety state is invalid")
    return tuple(errors)


def certify_portfolio_audit_v23_9(
    source: PortfolioLedgerAuditV238Result,
    *,
    operator: str,
    confirmation_text: str,
    now: datetime | None = None,
    policy: PortfolioAuditCertificateV239Policy = DEFAULT_POLICY,
) -> PortfolioAuditCertificationV239Result:
    issued = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued_at = issued.isoformat()
    reasons: list[str] = list(validate_policy(policy))
    policy_ok = not reasons

    if confirmation_text != CONFIRMATION_TEXT:
        reasons.append("confirmation text is invalid")
    if not isinstance(operator, str) or not operator.strip():
        reasons.append("operator is empty")
    if not isinstance(source, PortfolioLedgerAuditV238Result):
        reasons.append("source type is invalid")
        return _failed_result(issued_at, policy, reasons, policy_ok)

    source_before = json.dumps(source.to_dict(), sort_keys=True, default=str)
    source_cert = source.audit_certificate
    source_errors: list[str] = []
    if source.version != policy.required_source_version:
        source_errors.append("source version is invalid")
    if source.result_status != policy.required_source_status:
        source_errors.append("source status is invalid")
    if not source.all_checks_passed or not source.audit_completed:
        source_errors.append("source audit is incomplete")
    if source_cert is None:
        source_errors.append("source certificate is missing")
    else:
        source_errors.extend(verify_audit_certificate(source_cert))
        if source_cert.source_ledger_result_id != source.source_ledger_result_id:
            source_errors.append("source ledger result linkage is invalid")
        if source_cert.source_ledger_snapshot_hash != source.source_ledger_snapshot_hash:
            source_errors.append("source snapshot linkage is invalid")
        if source_cert.source_latest_entry_hash != source.source_latest_entry_hash:
            source_errors.append("source latest hash linkage is invalid")
        if source_cert.source_total_entry_count != source.source_total_entry_count:
            source_errors.append("source entry count linkage is invalid")
    source_ok = not source_errors
    reasons.extend(source_errors)

    chronology_ok = True
    try:
        if issued < _utc(source.created_at):
            chronology_ok = False
        if source_cert is not None and issued < _utc(source_cert.audited_at):
            chronology_ok = False
    except (TypeError, ValueError):
        chronology_ok = False
    if not chronology_ok:
        reasons.append("certificate time precedes its source")

    linkage_ok = source_cert is not None and source_ok
    certificate = None
    if policy_ok and not reasons:
        payload = {
            "certificate_id": f"pac-{uuid4()}",
            "issued_at": issued_at,
            "certificate_status": "CERTIFIED",
            "operator": operator.strip(),
            "confirmation_text": confirmation_text,
            "source_audit_result_id": source.audit_result_id,
            "source_audit_certificate_hash": source_cert.certificate_hash,
            "source_ledger_result_id": source.source_ledger_result_id,
            "source_ledger_snapshot_hash": source.source_ledger_snapshot_hash,
            "source_latest_entry_hash": source.source_latest_entry_hash,
            "source_total_entry_count": source.source_total_entry_count,
            "execution_blocked": True,
            "funds_reserved": False,
            "holdings_reserved": False,
        }
        certificate = OfflinePortfolioAuditCertificateV239(
            **payload, certificate_hash=sha256_payload(payload)
        )

    source_after = json.dumps(source.to_dict(), sort_keys=True, default=str)
    unchanged = source_before == source_after
    cert_hash_ok = certificate is not None and not verify_certificate(certificate)
    all_ok = bool(
        policy_ok
        and source_ok
        and linkage_ok
        and chronology_ok
        and unchanged
        and cert_hash_ok
        and not reasons
    )
    return PortfolioAuditCertificationV239Result(
        version=VERSION,
        created_at=issued_at,
        certification_result_id=f"pcr-{uuid4()}",
        result_status="CERTIFIED_IN_MEMORY" if all_ok else "REJECTED",
        source_audit_result_id=source.audit_result_id,
        source_audit_certificate_hash=(
            source_cert.certificate_hash if source_cert else ""
        ),
        source_ledger_result_id=source.source_ledger_result_id,
        source_ledger_snapshot_hash=source.source_ledger_snapshot_hash,
        source_latest_entry_hash=source.source_latest_entry_hash,
        source_total_entry_count=source.source_total_entry_count,
        certificate=certificate,
        policy_check_passed=policy_ok,
        source_check_passed=source_ok,
        linkage_check_passed=linkage_ok,
        chronology_check_passed=chronology_ok,
        source_unchanged=unchanged,
        certificate_hash_passed=cert_hash_ok,
        all_checks_passed=all_ok,
        certificate_created=certificate is not None,
        policy=policy,
        reasons=tuple(reasons),
    )


def _failed_result(
    issued_at: str,
    policy: PortfolioAuditCertificateV239Policy,
    reasons: list[str],
    policy_ok: bool,
) -> PortfolioAuditCertificationV239Result:
    return PortfolioAuditCertificationV239Result(
        version=VERSION,
        created_at=issued_at,
        certification_result_id=f"pcr-{uuid4()}",
        result_status="REJECTED",
        source_audit_result_id="",
        source_audit_certificate_hash="",
        source_ledger_result_id="",
        source_ledger_snapshot_hash="",
        source_latest_entry_hash="",
        source_total_entry_count=0,
        certificate=None,
        policy_check_passed=policy_ok,
        source_check_passed=False,
        linkage_check_passed=False,
        chronology_check_passed=False,
        source_unchanged=True,
        certificate_hash_passed=False,
        all_checks_passed=False,
        certificate_created=False,
        policy=policy,
        reasons=tuple(reasons),
    )


def save_certification_result(
    result: PortfolioAuditCertificationV239Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    report = output_directory / f"offline_portfolio_audit_certificate_{result.certification_result_id}.json"
    latest = output_directory / "offline_portfolio_audit_certificate_v23_9_latest.json"
    payload = json.dumps(result.to_dict(), indent=2, sort_keys=True)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_certification_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
