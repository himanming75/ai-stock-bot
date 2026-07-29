"""V24.0 offline-only portfolio audit certificate ledger.

This module records verified V23.9 certificates in an in-memory SHA-256
ledger. It contains no market-data, account, network, broker, or live-order
integration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from backtest.offline_paper_portfolio_audit_certificate_v23_9 import (
    OfflinePortfolioAuditCertificateV239,
    PortfolioAuditCertificationV239Result,
    verify_certificate,
)


VERSION = "V24.0"
SOURCE_VERSION = "V23.9"
CONFIRMATION_TEXT = "RECORD OFFLINE PAPER PORTFOLIO AUDIT CERTIFICATE V24.0"
GENESIS_HASH = "0" * 64
OUTPUT_DIRECTORY = Path("backtest_outputs")


@dataclass(frozen=True)
class PortfolioAuditCertificateLedgerV240Policy:
    source_version: str = SOURCE_VERSION
    required_source_status: str = "CERTIFIED_IN_MEMORY"
    required_certificate_status: str = "CERTIFIED"
    required_confirmation_text: str = CONFIRMATION_TEXT
    max_entries: int = 100
    require_source_immutability: bool = True
    allow_market_data_api: bool = False
    allow_account_api: bool = False
    allow_network: bool = False
    allow_broker_api: bool = False
    allow_broker_order: bool = False
    allow_order_submission: bool = False
    allow_live_execution: bool = False


DEFAULT_POLICY = PortfolioAuditCertificateLedgerV240Policy()


@dataclass(frozen=True)
class PortfolioAuditCertificateLedgerEntryV240:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    source_certification_result_id: str
    source_certificate_id: str
    source_certificate_hash: str
    source_audit_result_id: str
    source_audit_certificate_hash: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_latest_entry_hash: str
    source_total_entry_count: int
    operator: str
    certificate_status: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    entry_hash: str


@dataclass
class PortfolioAuditCertificateLedgerV240Result:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    ledger_snapshot_hash: str
    latest_entry_hash: str
    total_entry_count: int
    source_certificate_recorded: bool
    source_remained_unchanged: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    policy: PortfolioAuditCertificateLedgerV240Policy
    entries: tuple[PortfolioAuditCertificateLedgerEntryV240, ...] = field(
        default_factory=tuple
    )
    reasons: tuple[str, ...] = field(default_factory=tuple)
    report_path: str | None = None
    latest_path: str | None = None


def sha256_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_policy(policy: PortfolioAuditCertificateLedgerV240Policy) -> bool:
    return (
        isinstance(policy, PortfolioAuditCertificateLedgerV240Policy)
        and policy.source_version == SOURCE_VERSION
        and policy.required_source_status == "CERTIFIED_IN_MEMORY"
        and policy.required_certificate_status == "CERTIFIED"
        and policy.required_confirmation_text == CONFIRMATION_TEXT
        and isinstance(policy.max_entries, int)
        and 1 <= policy.max_entries <= 1000
        and policy.require_source_immutability is True
        and policy.allow_market_data_api is False
        and policy.allow_account_api is False
        and policy.allow_network is False
        and policy.allow_broker_api is False
        and policy.allow_broker_order is False
        and policy.allow_order_submission is False
        and policy.allow_live_execution is False
    )


def _entry_payload(
    entry: PortfolioAuditCertificateLedgerEntryV240,
) -> dict[str, Any]:
    payload = asdict(entry)
    payload.pop("entry_hash", None)
    return payload


def verify_entry(entry: PortfolioAuditCertificateLedgerEntryV240) -> bool:
    return (
        isinstance(entry, PortfolioAuditCertificateLedgerEntryV240)
        and entry.sequence >= 1
        and bool(entry.ledger_entry_id)
        and bool(entry.operator.strip())
        and entry.certificate_status == "CERTIFIED"
        and entry.execution_blocked is True
        and entry.funds_reserved is False
        and entry.holdings_reserved is False
        and entry.entry_hash == sha256_payload(_entry_payload(entry))
    )


def verify_portfolio_audit_cert_ledger(
    entries: Sequence[PortfolioAuditCertificateLedgerEntryV240],
) -> bool:
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        try:
            recorded_at = _parse_utc(entry.recorded_at)
        except (TypeError, ValueError):
            return False
        if (
            not verify_entry(entry)
            or entry.sequence != expected_sequence
            or entry.previous_entry_hash != previous_hash
            or entry.source_certificate_id in certificate_ids
            or (previous_time is not None and recorded_at < previous_time)
        ):
            return False
        certificate_ids.add(entry.source_certificate_id)
        previous_hash = entry.entry_hash
        previous_time = recorded_at
    return True


def ledger_snapshot_hash(
    entries: Sequence[PortfolioAuditCertificateLedgerEntryV240],
) -> str:
    return sha256_payload({"entries": [asdict(entry) for entry in entries]})


def _source_is_safe(
    source: PortfolioAuditCertificationV239Result,
    certificate: OfflinePortfolioAuditCertificateV239,
    policy: PortfolioAuditCertificateLedgerV240Policy,
) -> bool:
    return (
        type(source) is PortfolioAuditCertificationV239Result
        and source.version == policy.source_version
        and source.result_status == policy.required_source_status
        and source.policy_check_passed is True
        and source.source_check_passed is True
        and source.linkage_check_passed is True
        and source.chronology_check_passed is True
        and source.source_unchanged is True
        and source.certificate_hash_passed is True
        and source.all_checks_passed is True
        and source.certificate_created is True
        and source.execution_blocked is True
        and source.market_data_api_called is False
        and source.account_api_called is False
        and source.network_accessed is False
        and source.broker_api_called is False
        and source.order_submitted is False
        and source.live_execution_authorized is False
        and type(certificate) is OfflinePortfolioAuditCertificateV239
        and certificate.certificate_status == policy.required_certificate_status
        and certificate.certificate_id
        and not verify_certificate(certificate)
        and source.certification_result_id
        and source.source_audit_result_id == certificate.source_audit_result_id
        and source.source_audit_certificate_hash
        == certificate.source_audit_certificate_hash
        and source.source_ledger_result_id == certificate.source_ledger_result_id
        and source.source_ledger_snapshot_hash
        == certificate.source_ledger_snapshot_hash
        and source.source_latest_entry_hash
        == certificate.source_latest_entry_hash
        and source.source_total_entry_count
        == certificate.source_total_entry_count
    )


def record_portfolio_audit_certificate_v24_0(
    source: PortfolioAuditCertificationV239Result,
    *,
    operator: str,
    confirmation_text: str,
    recorded_at: datetime | None = None,
    existing_entries: Sequence[PortfolioAuditCertificateLedgerEntryV240] = (),
    policy: PortfolioAuditCertificateLedgerV240Policy = DEFAULT_POLICY,
) -> PortfolioAuditCertificateLedgerV240Result:
    if not validate_policy(policy):
        raise ValueError("invalid immutable V24.0 policy")
    if confirmation_text != policy.required_confirmation_text:
        raise PermissionError("wrong confirmation text")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("operator is required")
    if type(source) is not PortfolioAuditCertificationV239Result:
        raise TypeError("source must be an exact V23.9 certification result")
    certificate = source.certificate
    if certificate is None or not _source_is_safe(source, certificate, policy):
        raise ValueError("unsafe or invalid V23.9 source")

    entries = tuple(existing_entries)
    if len(entries) >= policy.max_entries:
        raise ValueError("ledger retention limit reached")
    if not verify_portfolio_audit_cert_ledger(entries):
        raise ValueError("existing ledger integrity check failed")
    if any(
        entry.source_certificate_id == certificate.certificate_id for entry in entries
    ):
        raise ValueError("duplicate certificate")

    moment = recorded_at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("recorded_at must include a timezone")
    moment = moment.astimezone(timezone.utc)
    if moment < _parse_utc(certificate.issued_at):
        raise ValueError("recorded_at precedes certificate issuance")
    if entries and moment < _parse_utc(entries[-1].recorded_at):
        raise ValueError("recorded_at breaks ledger chronology")

    source_before = sha256_payload(asdict(source))
    entry_without_hash = {
        "ledger_entry_id": f"PAC-{uuid4().hex}",
        "sequence": len(entries) + 1,
        "recorded_at": moment.isoformat(),
        "previous_entry_hash": entries[-1].entry_hash if entries else GENESIS_HASH,
        "source_certification_result_id": source.certification_result_id,
        "source_certificate_id": certificate.certificate_id,
        "source_certificate_hash": certificate.certificate_hash,
        "source_audit_result_id": certificate.source_audit_result_id,
        "source_audit_certificate_hash": certificate.source_audit_certificate_hash,
        "source_ledger_result_id": certificate.source_ledger_result_id,
        "source_ledger_snapshot_hash": certificate.source_ledger_snapshot_hash,
        "source_latest_entry_hash": certificate.source_latest_entry_hash,
        "source_total_entry_count": certificate.source_total_entry_count,
        "operator": operator.strip(),
        "certificate_status": certificate.certificate_status,
        "execution_blocked": True,
        "funds_reserved": False,
        "holdings_reserved": False,
    }
    entry = PortfolioAuditCertificateLedgerEntryV240(
        **entry_without_hash,
        entry_hash=sha256_payload(entry_without_hash),
    )
    updated_entries = entries + (entry,)
    if not verify_portfolio_audit_cert_ledger(updated_entries):
        raise RuntimeError("new ledger entry verification failed")
    source_unchanged = source_before == sha256_payload(asdict(source))
    if policy.require_source_immutability and not source_unchanged:
        raise RuntimeError("source changed while recording")

    latest_hash = updated_entries[-1].entry_hash
    return PortfolioAuditCertificateLedgerV240Result(
        version=VERSION,
        created_at=moment.isoformat(),
        ledger_result_id=f"PAL-{uuid4().hex}",
        result_status="RECORDED_IN_MEMORY",
        ledger_snapshot_hash=ledger_snapshot_hash(updated_entries),
        latest_entry_hash=latest_hash,
        total_entry_count=len(updated_entries),
        source_certificate_recorded=True,
        source_remained_unchanged=source_unchanged,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_execution_authorized=False,
        execution_blocked=True,
        funds_reserved=False,
        holdings_reserved=False,
        policy=policy,
        entries=updated_entries,
        reasons=(
            "Verified V23.9 certificate recorded in an offline immutable ledger.",
            "Network, broker, order submission, and live execution remain blocked.",
        ),
    )


def save_ledger_result(
    result: PortfolioAuditCertificateLedgerV240Result,
    path: str | Path,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_ledger_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


__all__ = [
    "CONFIRMATION_TEXT",
    "DEFAULT_POLICY",
    "GENESIS_HASH",
    "PortfolioAuditCertificateLedgerEntryV240",
    "PortfolioAuditCertificateLedgerV240Policy",
    "PortfolioAuditCertificateLedgerV240Result",
    "VERSION",
    "ledger_snapshot_hash",
    "load_ledger_result",
    "record_portfolio_audit_certificate_v24_0",
    "save_ledger_result",
    "validate_policy",
    "verify_entry",
    "verify_portfolio_audit_cert_ledger",
]
