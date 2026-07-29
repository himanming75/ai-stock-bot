"""V24.1 offline-only audit certificate ledger integrity audit.

This module verifies a V24.0 in-memory certificate ledger without contacting
market-data, account, network, or broker services.  It cannot submit orders or
authorize live execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from backtest.offline_paper_audit_cert_ledger_v24_0 import (
    PortfolioAuditCertificateLedgerV240Result,
    ledger_snapshot_hash,
    verify_portfolio_audit_cert_ledger,
)


VERSION = "V24.1"
SOURCE_VERSION = "V24.0"
REQUIRED_CONFIRMATION = "AUDIT OFFLINE PAPER AUDIT CERTIFICATE LEDGER V24.1"


def sha256_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class AuditCertificateLedgerIntegrityV241Policy:
    source_version: str = SOURCE_VERSION
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_confirmation: str = REQUIRED_CONFIRMATION
    require_nonempty_ledger: bool = True
    require_valid_hash_chain: bool = True
    require_chronology: bool = True
    require_snapshot_match: bool = True
    require_entry_safety: bool = True
    require_source_immutability: bool = True
    allow_market_data_api: bool = False
    allow_account_api: bool = False
    allow_network: bool = False
    allow_broker_api: bool = False
    allow_broker_order_creation: bool = False
    allow_order_submission: bool = False
    allow_live_execution: bool = False


@dataclass(frozen=True)
class IntegrityFindingV241:
    sequence: int
    check_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class IntegrityAuditCertificateV241:
    certificate_id: str
    issued_at: str
    certificate_status: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_latest_entry_hash: str
    source_total_entry_count: int
    findings_hash: str
    source_result_hash: str
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    certificate_hash: str


@dataclass
class AuditCertificateLedgerIntegrityV241Result:
    version: str
    created_at: str
    audit_result_id: str
    result_status: str
    source_ledger_verified: bool
    hash_chain_verified: bool
    chronology_verified: bool
    snapshot_verified: bool
    entry_safety_verified: bool
    source_remained_unchanged: bool
    certificate_created: bool
    market_data_api_called: bool = False
    account_api_called: bool = False
    network_accessed: bool = False
    broker_api_called: bool = False
    broker_order_created: bool = False
    order_submitted: bool = False
    live_execution_authorized: bool = False
    execution_blocked: bool = True
    funds_reserved: bool = False
    holdings_reserved: bool = False
    policy: AuditCertificateLedgerIntegrityV241Policy = field(
        default_factory=AuditCertificateLedgerIntegrityV241Policy
    )
    findings: tuple[IntegrityFindingV241, ...] = ()
    certificate: IntegrityAuditCertificateV241 | None = None
    reasons: tuple[str, ...] = ()
    source_path: str = ""
    result_path: str = ""


def validate_policy(policy: AuditCertificateLedgerIntegrityV241Policy) -> bool:
    return (
        policy.source_version == SOURCE_VERSION
        and policy.required_source_status == "RECORDED_IN_MEMORY"
        and policy.required_confirmation == REQUIRED_CONFIRMATION
        and policy.require_nonempty_ledger
        and policy.require_valid_hash_chain
        and policy.require_chronology
        and policy.require_snapshot_match
        and policy.require_entry_safety
        and policy.require_source_immutability
        and not policy.allow_market_data_api
        and not policy.allow_account_api
        and not policy.allow_network
        and not policy.allow_broker_api
        and not policy.allow_broker_order_creation
        and not policy.allow_order_submission
        and not policy.allow_live_execution
    )


def _source_result_hash(source: PortfolioAuditCertificateLedgerV240Result) -> str:
    payload = asdict(source)
    payload.pop("source_path", None)
    payload.pop("result_path", None)
    return sha256_payload(payload)


def _finding_hash(findings: Sequence[IntegrityFindingV241]) -> str:
    return sha256_payload({"findings": [asdict(item) for item in findings]})


def _certificate_payload(
    *,
    certificate_id: str,
    issued_at: str,
    certificate_status: str,
    source: PortfolioAuditCertificateLedgerV240Result,
    findings_hash: str,
    source_result_hash: str,
    operator: str,
) -> dict[str, Any]:
    return {
        "certificate_id": certificate_id,
        "issued_at": issued_at,
        "certificate_status": certificate_status,
        "source_ledger_result_id": source.ledger_result_id,
        "source_ledger_snapshot_hash": source.ledger_snapshot_hash,
        "source_latest_entry_hash": source.latest_entry_hash,
        "source_total_entry_count": source.total_entry_count,
        "findings_hash": findings_hash,
        "source_result_hash": source_result_hash,
        "operator": operator,
        "execution_blocked": True,
        "funds_reserved": False,
        "holdings_reserved": False,
    }


def verify_audit_certificate(
    certificate: IntegrityAuditCertificateV241,
) -> list[str]:
    errors: list[str] = []
    payload = asdict(certificate)
    actual_hash = payload.pop("certificate_hash")
    expected_hash = sha256_payload(payload)
    if actual_hash != expected_hash:
        errors.append("certificate SHA-256 hash mismatch")
    if certificate.certificate_status != "INTEGRITY_VERIFIED":
        errors.append("certificate status is invalid")
    if not certificate.operator.strip():
        errors.append("certificate operator is empty")
    try:
        _parse_utc(certificate.issued_at)
    except (TypeError, ValueError):
        errors.append("certificate timestamp is invalid")
    for name in (
        certificate.source_ledger_snapshot_hash,
        certificate.source_latest_entry_hash,
        certificate.findings_hash,
        certificate.source_result_hash,
        certificate.certificate_hash,
    ):
        if len(name) != 64:
            errors.append("certificate contains an invalid SHA-256 value")
            break
    if (
        not certificate.execution_blocked
        or certificate.funds_reserved
        or certificate.holdings_reserved
    ):
        errors.append("certificate safety flags are invalid")
    return errors


def audit_certificate_ledger_integrity_v24_1(
    source: PortfolioAuditCertificateLedgerV240Result,
    *,
    operator: str,
    confirmation: str,
    created_at: str,
    policy: AuditCertificateLedgerIntegrityV241Policy | None = None,
) -> AuditCertificateLedgerIntegrityV241Result:
    selected_policy = policy or AuditCertificateLedgerIntegrityV241Policy()
    if not validate_policy(selected_policy):
        raise ValueError("invalid or unsafe V24.1 policy")
    if confirmation != selected_policy.required_confirmation:
        raise PermissionError("V24.1 confirmation phrase does not match")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("operator must be a non-empty string")
    if not isinstance(source, PortfolioAuditCertificateLedgerV240Result):
        raise TypeError("source must be a V24.0 ledger result")

    audit_time = _parse_utc(created_at)
    source_time = _parse_utc(source.created_at)
    if audit_time < source_time:
        raise ValueError("audit time cannot precede the source ledger")

    before_hash = _source_result_hash(source)
    entries = tuple(source.entries)
    hash_chain_verified = verify_portfolio_audit_cert_ledger(entries)

    chronology_verified = True
    previous_time: datetime | None = None
    for entry in entries:
        try:
            entry_time = _parse_utc(entry.recorded_at)
        except (TypeError, ValueError):
            chronology_verified = False
            break
        if previous_time is not None and entry_time < previous_time:
            chronology_verified = False
            break
        previous_time = entry_time

    calculated_snapshot = ledger_snapshot_hash(entries)
    snapshot_verified = (
        bool(entries)
        and source.total_entry_count == len(entries)
        and source.ledger_snapshot_hash == calculated_snapshot
        and source.latest_entry_hash == entries[-1].entry_hash
    )
    entry_safety_verified = bool(entries) and all(
        entry.execution_blocked
        and not entry.funds_reserved
        and not entry.holdings_reserved
        for entry in entries
    )
    source_ledger_verified = (
        source.version == SOURCE_VERSION
        and source.result_status == selected_policy.required_source_status
        and source.source_certificate_recorded
        and source.source_remained_unchanged
        and not source.market_data_api_called
        and not source.account_api_called
        and not source.network_accessed
        and not source.broker_api_called
        and not source.broker_order_created
        and not source.order_submitted
        and not source.live_execution_authorized
        and source.execution_blocked
        and not source.funds_reserved
        and not source.holdings_reserved
    )

    checks = (
        ("source_ledger", source_ledger_verified, "V24.0 source contract"),
        ("hash_chain", hash_chain_verified, "entry SHA-256 chain"),
        ("chronology", chronology_verified, "entry timestamp ordering"),
        ("snapshot", snapshot_verified, "count, latest hash, and snapshot"),
        ("entry_safety", entry_safety_verified, "offline safety flags"),
    )
    findings = tuple(
        IntegrityFindingV241(index, name, passed, detail)
        for index, (name, passed, detail) in enumerate(checks, start=1)
    )
    after_hash = _source_result_hash(source)
    source_remained_unchanged = before_hash == after_hash
    all_passed = all(item.passed for item in findings) and source_remained_unchanged
    reasons = tuple(
        f"{item.check_name}: {item.detail}"
        for item in findings
        if not item.passed
    )
    if not source_remained_unchanged:
        reasons += ("source ledger changed during audit",)

    certificate: IntegrityAuditCertificateV241 | None = None
    if all_passed:
        findings_hash = _finding_hash(findings)
        certificate_id = sha256_payload(
            {
                "version": VERSION,
                "source_ledger_result_id": source.ledger_result_id,
                "issued_at": audit_time.isoformat(),
                "operator": operator.strip(),
            }
        )
        certificate_data = _certificate_payload(
            certificate_id=certificate_id,
            issued_at=audit_time.isoformat(),
            certificate_status="INTEGRITY_VERIFIED",
            source=source,
            findings_hash=findings_hash,
            source_result_hash=before_hash,
            operator=operator.strip(),
        )
        certificate = IntegrityAuditCertificateV241(
            **certificate_data,
            certificate_hash=sha256_payload(certificate_data),
        )

    result_payload = {
        "version": VERSION,
        "created_at": audit_time.isoformat(),
        "source_ledger_result_id": source.ledger_result_id,
        "source_result_hash": before_hash,
        "findings_hash": _finding_hash(findings),
        "result_status": "INTEGRITY_VERIFIED" if all_passed else "INTEGRITY_FAILED",
    }
    return AuditCertificateLedgerIntegrityV241Result(
        version=VERSION,
        created_at=audit_time.isoformat(),
        audit_result_id=sha256_payload(result_payload),
        result_status=result_payload["result_status"],
        source_ledger_verified=source_ledger_verified,
        hash_chain_verified=hash_chain_verified,
        chronology_verified=chronology_verified,
        snapshot_verified=snapshot_verified,
        entry_safety_verified=entry_safety_verified,
        source_remained_unchanged=source_remained_unchanged,
        certificate_created=certificate is not None,
        policy=selected_policy,
        findings=findings,
        certificate=certificate,
        reasons=reasons,
    )


def save_audit_result(
    result: AuditCertificateLedgerIntegrityV241Result,
    path: str | Path,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result.result_path = str(target)
    return target


def load_audit_result(
    path: str | Path,
) -> AuditCertificateLedgerIntegrityV241Result:
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["policy"] = AuditCertificateLedgerIntegrityV241Policy(
        **payload["policy"]
    )
    payload["findings"] = tuple(
        IntegrityFindingV241(**item) for item in payload["findings"]
    )
    if payload.get("certificate") is not None:
        payload["certificate"] = IntegrityAuditCertificateV241(
            **payload["certificate"]
        )
    payload["reasons"] = tuple(payload["reasons"])
    payload["source_path"] = str(source_path)
    return AuditCertificateLedgerIntegrityV241Result(**payload)


def finite_number(value: Any) -> bool:
    """Kept explicit for defensive consumers; booleans are not numbers here."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )
