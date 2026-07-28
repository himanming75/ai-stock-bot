import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_ledger_v21_5 import (
    GENESIS_HASH,
    OfflinePaperAuditCertLedgerV215Entry,
    OfflinePaperAuditCertLedgerV215Result,
    sha256_payload,
    verify_audit_cert_ledger_chain,
)
from backtest.offline_paper_trading_account_v21_0 import canonical_json


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "offline_paper_audit_cert_integrity_v21_6"
)
REQUIRED_AUDIT_TEXT = (
    "AUDIT OFFLINE PAPER AUDIT CERTIFICATE LEDGER V21.5"
)


@dataclass(frozen=True)
class OfflinePaperAuditCertIntegrityV216Policy:
    required_source_version: str = "V21.5"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_AUDIT_TEXT
    require_non_empty_ledger: bool = True
    require_latest_operator_match: bool = True
    require_source_linkage: bool = True
    require_valid_hash_chain: bool = True
    require_unique_certificate_ids: bool = True
    require_chronological_order: bool = True
    require_passed_audit_status: bool = True
    require_safe_entries: bool = True
    require_ledger_unchanged: bool = True
    read_only_audit: bool = True
    funds_reservation_disabled: bool = True
    holdings_reservation_disabled: bool = True
    order_execution_disabled: bool = True
    automatic_execution_disabled: bool = True
    credentials_forbidden: bool = True
    market_data_api_disabled: bool = True
    account_api_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    broker_order_creation_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePaperAuditCertIntegrityFindingV216:
    sequence: int
    ledger_entry_id: str
    audit_certificate_id: str
    sequence_valid: bool
    previous_hash_valid: bool
    entry_hash_valid: bool
    certificate_id_unique: bool
    chronology_valid: bool
    audit_status_valid: bool
    safety_valid: bool
    finding_status: str
    messages: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["messages"] = list(self.messages)
        return payload


@dataclass(frozen=True)
class OfflinePaperAuditCertIntegrityCertificateV216:
    audit_certificate_id: str
    audited_at: str
    audit_status: str
    source_ledger_result_id: str
    total_ledger_entry_count: int
    genesis_hash: str
    latest_ledger_entry_id: str
    latest_ledger_entry_hash: str
    latest_audit_result_id: str
    latest_audit_certificate_id: str
    latest_audit_certificate_hash: str
    latest_source_validation_ledger_result_id: str
    latest_ledger_snapshot_hash: str
    latest_validation_ledger_entry_id: str
    latest_validation_ledger_entry_hash: str
    latest_validation_result_id: str
    latest_validation_certificate_id: str
    latest_validation_certificate_hash: str
    latest_paper_order_id: str
    latest_order_hash: str
    latest_account_id: str
    latest_account_hash: str
    audit_certificate_ledger_snapshot_hash: str
    ledger_hash_chain_valid: bool
    source_linkage_valid: bool
    unique_certificate_ids_valid: bool
    chronology_valid: bool
    audit_status_valid: bool
    entry_safety_valid: bool
    ledger_unchanged: bool
    funds_reserved: bool
    holdings_reserved: bool
    paper_order_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    findings: tuple[OfflinePaperAuditCertIntegrityFindingV216, ...]
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash", None)
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["certificate_hash"] = self.certificate_hash
        return payload


@dataclass
class OfflinePaperAuditCertIntegrityV216Result:
    version: str
    created_at: str
    audit_result_id: str
    result_status: str
    result_status_label: str
    audit_status: str
    source_ledger_result_id: str | None
    audited_entry_count: int
    latest_ledger_entry_id: str | None
    latest_ledger_entry_hash: str | None
    latest_audit_certificate_hash: str | None
    latest_ledger_snapshot_hash: str | None
    latest_validation_certificate_hash: str | None
    latest_order_hash: str | None
    latest_account_hash: str | None
    audit_certificate_ledger_snapshot_hash: str | None
    audit_certificate_id: str | None
    audit_certificate_hash: str | None
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    source_linkage_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    audit_status_checks_passed: bool
    entry_safety_checks_passed: bool
    snapshot_hash_checks_passed: bool
    ledger_unchanged_checks_passed: bool
    certificate_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    audit_completed: bool
    ledger_modified: bool
    funds_reserved: bool
    holdings_reserved: bool
    paper_order_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    audit_policy: OfflinePaperAuditCertIntegrityV216Policy
    certificate: OfflinePaperAuditCertIntegrityCertificateV216 | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_policy"] = self.audit_policy.to_dict()
        payload["certificate"] = (
            self.certificate.to_dict() if self.certificate else None
        )
        return payload


def ledger_snapshot_hash(
    entries: tuple[OfflinePaperAuditCertLedgerV215Entry, ...],
) -> str:
    return hashlib.sha256(
        canonical_json(
            {"entries": [entry.to_dict() for entry in entries]}
        ).encode("utf-8")
    ).hexdigest()


def validate_policy(
    policy: OfflinePaperAuditCertIntegrityV216Policy,
) -> list[str]:
    if not isinstance(policy, OfflinePaperAuditCertIntegrityV216Policy):
        return ["V21.6 Audit Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V21.5",
        "required_source_status": "RECORDED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_AUDIT_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V21.6 기준과 다릅니다.")
    for name in (
        "require_non_empty_ledger",
        "require_latest_operator_match",
        "require_source_linkage",
        "require_valid_hash_chain",
        "require_unique_certificate_ids",
        "require_chronological_order",
        "require_passed_audit_status",
        "require_safe_entries",
        "require_ledger_unchanged",
        "read_only_audit",
        "funds_reservation_disabled",
        "holdings_reservation_disabled",
        "order_execution_disabled",
        "automatic_execution_disabled",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_api_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "broker_order_creation_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V21.6에서 True여야 합니다.")
    return errors


def _safe_entry(entry: OfflinePaperAuditCertLedgerV215Entry) -> bool:
    return not any(
        (
            entry.funds_reserved,
            entry.holdings_reserved,
            entry.order_execution_authorized,
            entry.automatic_execution_authorized,
            not entry.execution_blocked,
            entry.transmit,
            entry.credentials_used,
            entry.market_data_api_called,
            entry.account_api_called,
            entry.network_accessed,
            entry.broker_api_called,
            entry.broker_order_created,
            entry.order_submitted,
            entry.live_order_created,
            entry.live_execution_authorized,
        )
    )


def _safe_source(source: OfflinePaperAuditCertLedgerV215Result) -> bool:
    return not any(
        (
            source.funds_reserved,
            source.holdings_reserved,
            source.paper_order_execution_authorized,
            source.automatic_execution_authorized,
            not source.execution_blocked,
            source.transmit,
            source.credentials_used,
            source.market_data_api_called,
            source.account_api_called,
            source.network_accessed,
            source.broker_api_called,
            source.broker_order_created,
            source.order_submitted,
            source.live_order_created,
            source.live_execution_authorized,
        )
    )


def build_findings(
    entries: tuple[OfflinePaperAuditCertLedgerV215Entry, ...],
) -> tuple[OfflinePaperAuditCertIntegrityFindingV216, ...]:
    findings: list[OfflinePaperAuditCertIntegrityFindingV216] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        sequence_valid = entry.sequence == expected_sequence
        previous_hash_valid = entry.previous_entry_hash == previous_hash
        entry_hash_valid = (
            entry.entry_hash == sha256_payload(entry.payload_without_hash())
        )
        certificate_id_unique = (
            entry.audit_certificate_id not in certificate_ids
        )
        certificate_ids.add(entry.audit_certificate_id)
        chronology_valid = True
        try:
            recorded_at = datetime.fromisoformat(entry.recorded_at)
            if recorded_at.tzinfo is None:
                raise ValueError
            if previous_time and recorded_at < previous_time:
                chronology_valid = False
            previous_time = recorded_at
        except (TypeError, ValueError):
            chronology_valid = False
        audit_status_valid = entry.audit_status == "PASSED"
        safety_valid = _safe_entry(entry)
        messages: list[str] = []
        for passed, message in (
            (sequence_valid, "Sequence 불일치"),
            (previous_hash_valid, "Previous Hash 불일치"),
            (entry_hash_valid, "Entry Hash 불일치"),
            (certificate_id_unique, "중복 Audit Certificate ID"),
            (chronology_valid, "Ledger 시간 순서 오류"),
            (audit_status_valid, "Audit Status 오류"),
            (safety_valid, "실행 안전장치 오류"),
        ):
            if not passed:
                messages.append(message)
        findings.append(
            OfflinePaperAuditCertIntegrityFindingV216(
                sequence=entry.sequence,
                ledger_entry_id=entry.ledger_entry_id,
                audit_certificate_id=entry.audit_certificate_id,
                sequence_valid=sequence_valid,
                previous_hash_valid=previous_hash_valid,
                entry_hash_valid=entry_hash_valid,
                certificate_id_unique=certificate_id_unique,
                chronology_valid=chronology_valid,
                audit_status_valid=audit_status_valid,
                safety_valid=safety_valid,
                finding_status="PASSED" if not messages else "FAILED",
                messages=tuple(messages),
            )
        )
        previous_hash = entry.entry_hash
    return tuple(findings)


def verify_integrity_audit_certificate(
    certificate: OfflinePaperAuditCertIntegrityCertificateV216,
) -> tuple[bool, list[str]]:
    if not isinstance(
        certificate, OfflinePaperAuditCertIntegrityCertificateV216
    ):
        return False, ["V21.6 Audit Certificate 형식 오류입니다."]
    errors: list[str] = []
    if certificate.audit_status != "PASSED":
        errors.append("Audit Status가 PASSED가 아닙니다.")
    if certificate.total_ledger_entry_count != len(certificate.findings):
        errors.append("Finding 개수와 Ledger Entry 개수가 다릅니다.")
    if not all(
        (
            certificate.ledger_hash_chain_valid,
            certificate.source_linkage_valid,
            certificate.unique_certificate_ids_valid,
            certificate.chronology_valid,
            certificate.audit_status_valid,
            certificate.entry_safety_valid,
            certificate.ledger_unchanged,
            all(
                finding.finding_status == "PASSED"
                for finding in certificate.findings
            ),
        )
    ):
        errors.append("Audit Certificate 검사 결과 오류입니다.")
    if certificate.certificate_hash != sha256_payload(
        certificate.payload_without_hash()
    ):
        errors.append("V21.6 Audit Certificate Hash가 일치하지 않습니다.")
    if any(
        (
            certificate.funds_reserved,
            certificate.holdings_reserved,
            certificate.paper_order_execution_authorized,
            certificate.automatic_execution_authorized,
            not certificate.execution_blocked,
            certificate.transmit,
            certificate.credentials_used,
            certificate.market_data_api_called,
            certificate.account_api_called,
            certificate.network_accessed,
            certificate.broker_api_called,
            certificate.broker_order_created,
            certificate.order_submitted,
            certificate.live_order_created,
            certificate.live_execution_authorized,
        )
    ):
        errors.append("V21.6 Audit Certificate 실행 안전장치 오류입니다.")
    return not errors, errors


def _empty_result(
    audit_policy: OfflinePaperAuditCertIntegrityV216Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    **checks: bool,
) -> OfflinePaperAuditCertIntegrityV216Result:
    return OfflinePaperAuditCertIntegrityV216Result(
        version="V21.6",
        created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Offline Paper Audit Certificate Ledger Integrity Audit 차단"
            if status == "BLOCKED"
            else "Offline Paper Audit Certificate Ledger Integrity Audit 실패"
        ),
        audit_status="FAILED",
        source_ledger_result_id=None,
        audited_entry_count=0,
        latest_ledger_entry_id=None,
        latest_ledger_entry_hash=None,
        latest_audit_certificate_hash=None,
        latest_ledger_snapshot_hash=None,
        latest_validation_certificate_hash=None,
        latest_order_hash=None,
        latest_account_hash=None,
        audit_certificate_ledger_snapshot_hash=None,
        audit_certificate_id=None,
        audit_certificate_hash=None,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        audit_status_checks_passed=checks.get("audit_status", False),
        entry_safety_checks_passed=checks.get("entry_safety", False),
        snapshot_hash_checks_passed=checks.get("snapshot", False),
        ledger_unchanged_checks_passed=checks.get("unchanged", False),
        certificate_hash_checks_passed=False,
        safety_checks_passed=True,
        all_checks_passed=False,
        audit_completed=False,
        ledger_modified=False,
        funds_reserved=False,
        holdings_reserved=False,
        paper_order_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        transmit=False,
        credentials_used=False,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        audit_policy=audit_policy,
        certificate=None,
        reasons=reasons,
        warnings=[
            "V21.6은 V21.5 Audit Certificate Ledger를 읽기 전용으로 감사합니다.",
            "잔액·보유수량 변경, API, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=["V21.5 Audit Certificate Ledger Source를 확인합니다."],
    )


def audit_offline_paper_audit_cert_ledger_v21_6(
    source: Any,
    operator: Any,
    confirmation_text: Any,
    policy: OfflinePaperAuditCertIntegrityV216Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperAuditCertIntegrityV216Result:
    policy = policy or OfflinePaperAuditCertIntegrityV216Policy()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        now = datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    if confirmation_text != getattr(policy, "required_confirmation_text", None):
        input_errors.append("V21.6 확인 문구가 일치하지 않습니다.")
    if policy_errors or input_errors:
        safe_policy = (
            policy
            if isinstance(policy, OfflinePaperAuditCertIntegrityV216Policy)
            else OfflinePaperAuditCertIntegrityV216Policy()
        )
        return _empty_result(
            safe_policy,
            now,
            "BLOCKED",
            policy_errors + input_errors,
            policy=not policy_errors,
            input=not input_errors,
        )
    if not isinstance(source, OfflinePaperAuditCertLedgerV215Result):
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["Source는 V21.5 Audit Certificate Ledger Result여야 합니다."],
            policy=True,
            input=True,
        )
    try:
        entries = tuple(source.entries)
    except TypeError:
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["V21.5 Source Entries 형식이 올바르지 않습니다."],
            policy=True,
            input=True,
        )
    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.all_checks_passed
        and source.ledger_entry_recorded
        and entries
    ):
        source_errors.append("정상 V21.5 Audit Certificate Ledger Source가 아닙니다.")
    if not all(
        isinstance(entry, OfflinePaperAuditCertLedgerV215Entry)
        for entry in entries
    ):
        source_errors.append("V21.5 Ledger Entry 형식 오류입니다.")
    if not _safe_source(source):
        source_errors.append("V21.5 Source 실행 안전장치 오류입니다.")
    if source_errors:
        return _empty_result(
            policy,
            now,
            "FAILED",
            source_errors,
            policy=True,
            input=True,
        )

    source_before = canonical_json(source.to_dict())
    chain_valid, chain_errors = verify_audit_cert_ledger_chain(entries)
    findings = build_findings(entries)
    if not chain_valid or any(
        finding.finding_status != "PASSED" for finding in findings
    ):
        return _empty_result(
            policy,
            now,
            "FAILED",
            chain_errors
            + [message for finding in findings for message in finding.messages],
            policy=True,
            input=True,
            source=True,
        )

    latest = entries[-1]
    linkage_errors: list[str] = []
    for actual, expected, label in (
        (source.total_ledger_entry_count, len(entries), "Entry Count"),
        (source.latest_ledger_entry_id, latest.ledger_entry_id, "Entry ID"),
        (source.latest_ledger_entry_hash, latest.entry_hash, "Entry Hash"),
        (
            source.latest_audit_result_id,
            latest.audit_result_id,
            "Audit Result ID",
        ),
        (
            source.latest_audit_certificate_id,
            latest.audit_certificate_id,
            "Audit Certificate ID",
        ),
        (
            source.latest_audit_certificate_hash,
            latest.audit_certificate_hash,
            "Audit Certificate Hash",
        ),
        (
            source.latest_source_validation_ledger_result_id,
            latest.source_validation_ledger_result_id,
            "Source Validation Ledger Result ID",
        ),
        (
            source.latest_ledger_snapshot_hash,
            latest.ledger_snapshot_hash,
            "Ledger Snapshot Hash",
        ),
        (
            source.latest_validation_ledger_entry_id,
            latest.latest_validation_ledger_entry_id,
            "Validation Ledger Entry ID",
        ),
        (
            source.latest_validation_ledger_entry_hash,
            latest.latest_validation_ledger_entry_hash,
            "Validation Ledger Entry Hash",
        ),
        (
            source.latest_validation_certificate_hash,
            latest.latest_validation_certificate_hash,
            "Validation Certificate Hash",
        ),
        (source.latest_order_hash, latest.latest_order_hash, "Order Hash"),
        (source.latest_account_hash, latest.latest_account_hash, "Account Hash"),
    ):
        if actual != expected:
            linkage_errors.append(f"Source Latest {label} 연결이 다릅니다.")
    if linkage_errors:
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            linkage_errors,
            policy=True,
            input=True,
            source=True,
            chain=True,
        )
    if operator.strip() != latest.operator:
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            ["Operator가 V21.5 Latest Ledger Entry와 다릅니다."],
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
        )
    try:
        latest_time = datetime.fromisoformat(latest.recorded_at)
        if latest_time.tzinfo is None or now < latest_time:
            raise ValueError
    except (TypeError, ValueError):
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            ["Audit 시간이 최신 Ledger Entry보다 빠르거나 올바르지 않습니다."],
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
        )

    snapshot_hash = ledger_snapshot_hash(entries)
    unchanged = source_before == canonical_json(source.to_dict())
    if not unchanged:
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["읽기 전용 Audit 중 V21.5 Ledger가 변경되었습니다."],
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=True,
            chronology=True,
            audit_status=True,
            entry_safety=True,
            snapshot=True,
        )

    unique_valid = len(
        {entry.audit_certificate_id for entry in entries}
    ) == len(entries)
    chronology_valid = all(finding.chronology_valid for finding in findings)
    status_valid = all(finding.audit_status_valid for finding in findings)
    entry_safety_valid = all(finding.safety_valid for finding in findings)
    certificate_payload = {
        "audit_certificate_id": str(uuid.uuid4()),
        "audited_at": now.isoformat(),
        "audit_status": "PASSED",
        "source_ledger_result_id": source.ledger_result_id,
        "total_ledger_entry_count": len(entries),
        "genesis_hash": GENESIS_HASH,
        "latest_ledger_entry_id": latest.ledger_entry_id,
        "latest_ledger_entry_hash": latest.entry_hash,
        "latest_audit_result_id": latest.audit_result_id,
        "latest_audit_certificate_id": latest.audit_certificate_id,
        "latest_audit_certificate_hash": latest.audit_certificate_hash,
        "latest_source_validation_ledger_result_id": (
            latest.source_validation_ledger_result_id
        ),
        "latest_ledger_snapshot_hash": latest.ledger_snapshot_hash,
        "latest_validation_ledger_entry_id": (
            latest.latest_validation_ledger_entry_id
        ),
        "latest_validation_ledger_entry_hash": (
            latest.latest_validation_ledger_entry_hash
        ),
        "latest_validation_result_id": latest.latest_validation_result_id,
        "latest_validation_certificate_id": (
            latest.latest_validation_certificate_id
        ),
        "latest_validation_certificate_hash": (
            latest.latest_validation_certificate_hash
        ),
        "latest_paper_order_id": latest.latest_paper_order_id,
        "latest_order_hash": latest.latest_order_hash,
        "latest_account_id": latest.latest_account_id,
        "latest_account_hash": latest.latest_account_hash,
        "audit_certificate_ledger_snapshot_hash": snapshot_hash,
        "ledger_hash_chain_valid": chain_valid,
        "source_linkage_valid": not linkage_errors,
        "unique_certificate_ids_valid": unique_valid,
        "chronology_valid": chronology_valid,
        "audit_status_valid": status_valid,
        "entry_safety_valid": entry_safety_valid,
        "ledger_unchanged": unchanged,
        "funds_reserved": False,
        "holdings_reserved": False,
        "paper_order_execution_authorized": False,
        "automatic_execution_authorized": False,
        "execution_blocked": True,
        "transmit": False,
        "credentials_used": False,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "broker_order_created": False,
        "order_submitted": False,
        "live_order_created": False,
        "live_execution_authorized": False,
        "findings": findings,
    }
    hash_payload = dict(certificate_payload)
    hash_payload["findings"] = [finding.to_dict() for finding in findings]
    certificate = OfflinePaperAuditCertIntegrityCertificateV216(
        **certificate_payload,
        certificate_hash=sha256_payload(hash_payload),
    )
    certificate_valid, certificate_errors = (
        verify_integrity_audit_certificate(certificate)
    )
    if not certificate_valid:
        return _empty_result(
            policy,
            now,
            "FAILED",
            certificate_errors,
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=unique_valid,
            chronology=chronology_valid,
            audit_status=status_valid,
            entry_safety=entry_safety_valid,
            snapshot=True,
            unchanged=True,
        )

    return OfflinePaperAuditCertIntegrityV216Result(
        version="V21.6",
        created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()),
        result_status="AUDITED_IN_MEMORY",
        result_status_label=(
            "Offline Paper Audit Certificate Ledger Integrity Audit 완료"
        ),
        audit_status="PASSED",
        source_ledger_result_id=source.ledger_result_id,
        audited_entry_count=len(entries),
        latest_ledger_entry_id=latest.ledger_entry_id,
        latest_ledger_entry_hash=latest.entry_hash,
        latest_audit_certificate_hash=latest.audit_certificate_hash,
        latest_ledger_snapshot_hash=latest.ledger_snapshot_hash,
        latest_validation_certificate_hash=(
            latest.latest_validation_certificate_hash
        ),
        latest_order_hash=latest.latest_order_hash,
        latest_account_hash=latest.latest_account_hash,
        audit_certificate_ledger_snapshot_hash=snapshot_hash,
        audit_certificate_id=certificate.audit_certificate_id,
        audit_certificate_hash=certificate.certificate_hash,
        policy_checks_passed=True,
        input_checks_passed=True,
        source_checks_passed=True,
        ledger_hash_chain_checks_passed=True,
        source_linkage_checks_passed=True,
        duplicate_checks_passed=unique_valid,
        chronology_checks_passed=chronology_valid,
        audit_status_checks_passed=status_valid,
        entry_safety_checks_passed=entry_safety_valid,
        snapshot_hash_checks_passed=True,
        ledger_unchanged_checks_passed=unchanged,
        certificate_hash_checks_passed=True,
        safety_checks_passed=True,
        all_checks_passed=True,
        audit_completed=True,
        ledger_modified=False,
        funds_reserved=False,
        holdings_reserved=False,
        paper_order_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        transmit=False,
        credentials_used=False,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        audit_policy=policy,
        certificate=certificate,
        reasons=[
            f"V21.5 Audit Certificate Ledger Entry {len(entries)}개를 감사했습니다.",
            "Hash Chain, Source Linkage, Snapshot Hash 및 Entry Safety가 유효합니다.",
        ],
        warnings=[
            "V21.6은 V21.5 Ledger를 변경하지 않는 읽기 전용 감사입니다.",
            "잔액·보유수량 변경, API, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "V21.7 Audit Certificate Ledger Integrity Audit Ledger 단계에서 "
            "V21.6 Audit Certificate를 In-Memory Ledger에 기록합니다."
        ],
    )


def save_integrity_audit_result(
    result: OfflinePaperAuditCertIntegrityV216Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report_path = output_directory / f"audit_cert_integrity_{stamp}.json"
    latest_path = output_directory / "latest_audit_cert_integrity.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_integrity_audit_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V21.6 Integrity Audit JSON은 object여야 합니다.")
    return payload
