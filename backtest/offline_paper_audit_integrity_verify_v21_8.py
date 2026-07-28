import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_ledger_v21_5 import sha256_payload
from backtest.offline_paper_audit_integrity_ledger_v21_7 import (
    GENESIS_HASH,
    OfflinePaperAuditIntegrityLedgerV217Entry,
    OfflinePaperAuditIntegrityLedgerV217Result,
    verify_audit_integrity_ledger_chain,
)
from backtest.offline_paper_trading_account_v21_0 import canonical_json


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "offline_paper_audit_integrity_verify_v21_8"
)
REQUIRED_VERIFICATION_TEXT = (
    "VERIFY OFFLINE PAPER AUDIT INTEGRITY LEDGER V21.8"
)


@dataclass(frozen=True)
class OfflinePaperAuditIntegrityVerifyV218Policy:
    required_source_version: str = "V21.7"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_audit_status: str = "PASSED"
    required_confirmation_text: str = REQUIRED_VERIFICATION_TEXT
    require_non_empty_ledger: bool = True
    require_latest_operator_match: bool = True
    require_source_linkage: bool = True
    require_valid_hash_chain: bool = True
    require_unique_certificate_ids: bool = True
    require_chronological_order: bool = True
    require_passed_audit_status: bool = True
    require_safe_entries: bool = True
    require_ledger_unchanged: bool = True
    read_only_verification: bool = True
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
class OfflinePaperAuditIntegrityFindingV218:
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
class OfflinePaperAuditIntegrityCertificateV218:
    verification_certificate_id: str
    verified_at: str
    verification_status: str
    source_ledger_result_id: str
    total_ledger_entry_count: int
    genesis_hash: str
    latest_ledger_entry_id: str
    latest_ledger_entry_hash: str
    latest_audit_result_id: str
    latest_audit_certificate_id: str
    latest_audit_certificate_hash: str
    latest_source_audit_cert_ledger_result_id: str
    latest_audit_certificate_ledger_snapshot_hash: str
    latest_v21_4_audit_certificate_hash: str
    latest_v21_3_ledger_snapshot_hash: str
    latest_v21_2_validation_certificate_hash: str
    latest_v21_1_order_hash: str
    latest_v21_0_account_hash: str
    audit_integrity_ledger_snapshot_hash: str
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
    findings: tuple[OfflinePaperAuditIntegrityFindingV218, ...]
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
class OfflinePaperAuditIntegrityVerifyV218Result:
    version: str
    created_at: str
    verification_result_id: str
    result_status: str
    result_status_label: str
    verification_status: str
    source_ledger_result_id: str | None
    verified_entry_count: int
    latest_ledger_entry_id: str | None
    latest_ledger_entry_hash: str | None
    latest_audit_certificate_hash: str | None
    latest_audit_certificate_ledger_snapshot_hash: str | None
    latest_v21_4_audit_certificate_hash: str | None
    latest_v21_3_ledger_snapshot_hash: str | None
    latest_v21_2_validation_certificate_hash: str | None
    latest_v21_1_order_hash: str | None
    latest_v21_0_account_hash: str | None
    audit_integrity_ledger_snapshot_hash: str | None
    verification_certificate_id: str | None
    verification_certificate_hash: str | None
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
    verification_completed: bool
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
    verification_policy: OfflinePaperAuditIntegrityVerifyV218Policy
    certificate: OfflinePaperAuditIntegrityCertificateV218 | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verification_policy"] = self.verification_policy.to_dict()
        payload["certificate"] = (
            self.certificate.to_dict() if self.certificate else None
        )
        return payload


def ledger_snapshot_hash(
    entries: tuple[OfflinePaperAuditIntegrityLedgerV217Entry, ...],
) -> str:
    return hashlib.sha256(
        canonical_json(
            {"entries": [entry.to_dict() for entry in entries]}
        ).encode("utf-8")
    ).hexdigest()


def validate_policy(
    policy: OfflinePaperAuditIntegrityVerifyV218Policy,
) -> list[str]:
    if not isinstance(policy, OfflinePaperAuditIntegrityVerifyV218Policy):
        return ["V21.8 Verification Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V21.7",
        "required_source_status": "RECORDED_IN_MEMORY",
        "required_audit_status": "PASSED",
        "required_confirmation_text": REQUIRED_VERIFICATION_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V21.8 기준과 다릅니다.")
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
        "read_only_verification",
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
            errors.append(f"{name}는 V21.8에서 True여야 합니다.")
    return errors


def _safe_entry(entry: OfflinePaperAuditIntegrityLedgerV217Entry) -> bool:
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


def _safe_source(source: OfflinePaperAuditIntegrityLedgerV217Result) -> bool:
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


def _findings(
    entries: tuple[OfflinePaperAuditIntegrityLedgerV217Entry, ...],
) -> tuple[OfflinePaperAuditIntegrityFindingV218, ...]:
    output: list[OfflinePaperAuditIntegrityFindingV218] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    seen: set[str] = set()
    for expected, entry in enumerate(entries, start=1):
        messages: list[str] = []
        sequence_valid = entry.sequence == expected
        previous_hash_valid = entry.previous_entry_hash == previous_hash
        entry_hash_valid = (
            entry.entry_hash == sha256_payload(entry.payload_without_hash())
        )
        unique = entry.audit_certificate_id not in seen
        seen.add(entry.audit_certificate_id)
        try:
            recorded_at = datetime.fromisoformat(entry.recorded_at)
            chronology = (
                recorded_at.tzinfo is not None
                and (previous_time is None or recorded_at >= previous_time)
            )
        except (TypeError, ValueError):
            recorded_at = None
            chronology = False
        status_valid = entry.audit_status == "PASSED"
        safety_valid = _safe_entry(entry)
        checks = (
            sequence_valid,
            previous_hash_valid,
            entry_hash_valid,
            unique,
            chronology,
            status_valid,
            safety_valid,
        )
        labels = (
            "Sequence",
            "Previous Hash",
            "Entry Hash",
            "Certificate ID Unique",
            "Chronology",
            "Audit Status",
            "Safety",
        )
        messages.extend(
            f"{label} 검증 실패" for label, valid in zip(labels, checks)
            if not valid
        )
        output.append(
            OfflinePaperAuditIntegrityFindingV218(
                sequence=entry.sequence,
                ledger_entry_id=entry.ledger_entry_id,
                audit_certificate_id=entry.audit_certificate_id,
                sequence_valid=sequence_valid,
                previous_hash_valid=previous_hash_valid,
                entry_hash_valid=entry_hash_valid,
                certificate_id_unique=unique,
                chronology_valid=chronology,
                audit_status_valid=status_valid,
                safety_valid=safety_valid,
                finding_status="PASSED" if all(checks) else "FAILED",
                messages=tuple(messages),
            )
        )
        previous_hash = entry.entry_hash
        if recorded_at is not None:
            previous_time = recorded_at
    return tuple(output)


def verify_verification_certificate(
    certificate: Any,
) -> tuple[bool, list[str]]:
    if not isinstance(certificate, OfflinePaperAuditIntegrityCertificateV218):
        return False, ["V21.8 Verification Certificate 형식 오류입니다."]
    errors: list[str] = []
    if certificate.certificate_hash != sha256_payload(
        certificate.payload_without_hash()
    ):
        errors.append("V21.8 Verification Certificate Hash 오류입니다.")
    if certificate.verification_status != "PASSED":
        errors.append("V21.8 Verification Certificate Status 오류입니다.")
    if not all(
        (
            certificate.ledger_hash_chain_valid,
            certificate.source_linkage_valid,
            certificate.unique_certificate_ids_valid,
            certificate.chronology_valid,
            certificate.audit_status_valid,
            certificate.entry_safety_valid,
            certificate.ledger_unchanged,
        )
    ):
        errors.append("V21.8 Verification Certificate 검증 항목 오류입니다.")
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
        errors.append("V21.8 Verification Certificate 안전장치 오류입니다.")
    return not errors, errors


def _empty_result(
    policy: OfflinePaperAuditIntegrityVerifyV218Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    **checks: bool,
) -> OfflinePaperAuditIntegrityVerifyV218Result:
    return OfflinePaperAuditIntegrityVerifyV218Result(
        version="V21.8",
        created_at=now.isoformat(),
        verification_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Offline Paper Audit Integrity Ledger 검증 차단"
            if status == "BLOCKED"
            else "Offline Paper Audit Integrity Ledger 검증 실패"
        ),
        verification_status="NOT_VERIFIED",
        source_ledger_result_id=None,
        verified_entry_count=0,
        latest_ledger_entry_id=None,
        latest_ledger_entry_hash=None,
        latest_audit_certificate_hash=None,
        latest_audit_certificate_ledger_snapshot_hash=None,
        latest_v21_4_audit_certificate_hash=None,
        latest_v21_3_ledger_snapshot_hash=None,
        latest_v21_2_validation_certificate_hash=None,
        latest_v21_1_order_hash=None,
        latest_v21_0_account_hash=None,
        audit_integrity_ledger_snapshot_hash=None,
        verification_certificate_id=None,
        verification_certificate_hash=None,
        policy_checks_passed=checks.get("policy_ok", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        audit_status_checks_passed=checks.get("status_ok", False),
        entry_safety_checks_passed=checks.get("entry_safety", False),
        snapshot_hash_checks_passed=checks.get("snapshot", False),
        ledger_unchanged_checks_passed=checks.get("unchanged", False),
        certificate_hash_checks_passed=checks.get("certificate", False),
        safety_checks_passed=True,
        all_checks_passed=False,
        verification_completed=False,
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
        verification_policy=policy,
        certificate=None,
        reasons=reasons,
        warnings=[
            "V21.8은 V21.7 Ledger를 읽기 전용으로 검증합니다.",
            "검증은 주문 체결 또는 Broker 전송 승인을 의미하지 않습니다.",
            "잔액·보유수량 변경, API, Network 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "차단 또는 실패 원인을 수정한 뒤 V21.8 검증을 다시 실행합니다."
        ],
    )


def _linkage_errors(
    source: OfflinePaperAuditIntegrityLedgerV217Result,
    latest: OfflinePaperAuditIntegrityLedgerV217Entry,
) -> list[str]:
    checks = (
        (source.latest_ledger_entry_id, latest.ledger_entry_id, "Ledger Entry ID"),
        (source.latest_ledger_entry_hash, latest.entry_hash, "Ledger Entry Hash"),
        (source.latest_audit_result_id, latest.audit_result_id, "Audit Result ID"),
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
            source.latest_source_audit_cert_ledger_result_id,
            latest.source_audit_cert_ledger_result_id,
            "V21.5 Ledger Result ID",
        ),
        (
            source.latest_audit_certificate_ledger_snapshot_hash,
            latest.audit_certificate_ledger_snapshot_hash,
            "V21.5 Ledger Snapshot Hash",
        ),
        (
            source.latest_v21_4_audit_certificate_hash,
            latest.latest_v21_4_audit_certificate_hash,
            "V21.4 Audit Certificate Hash",
        ),
        (
            source.latest_v21_3_ledger_snapshot_hash,
            latest.latest_v21_3_ledger_snapshot_hash,
            "V21.3 Ledger Snapshot Hash",
        ),
        (
            source.latest_v21_2_validation_certificate_hash,
            latest.latest_v21_2_validation_certificate_hash,
            "V21.2 Validation Certificate Hash",
        ),
        (
            source.latest_v21_1_order_hash,
            latest.latest_v21_1_order_hash,
            "V21.1 Order Hash",
        ),
        (
            source.latest_v21_0_account_hash,
            latest.latest_v21_0_account_hash,
            "V21.0 Account Hash",
        ),
    )
    return [
        f"V21.7 Source {label} 연결이 다릅니다."
        for actual, expected, label in checks
        if actual != expected
    ]


def verify_offline_paper_audit_integrity_ledger_v21_8(
    source: Any,
    operator: Any,
    confirmation_text: Any,
    policy: OfflinePaperAuditIntegrityVerifyV218Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperAuditIntegrityVerifyV218Result:
    policy = policy or OfflinePaperAuditIntegrityVerifyV218Policy()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        now = datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    if confirmation_text != getattr(policy, "required_confirmation_text", None):
        input_errors.append("V21.8 확인 문구가 일치하지 않습니다.")
    safe_policy = (
        policy
        if isinstance(policy, OfflinePaperAuditIntegrityVerifyV218Policy)
        else OfflinePaperAuditIntegrityVerifyV218Policy()
    )
    if policy_errors or input_errors:
        return _empty_result(
            safe_policy,
            now,
            "BLOCKED",
            policy_errors + input_errors,
            policy_ok=not policy_errors,
            input=not input_errors,
        )
    if not isinstance(source, OfflinePaperAuditIntegrityLedgerV217Result):
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["Source는 V21.7 Audit Integrity Ledger Result여야 합니다."],
            policy_ok=True,
            input=True,
        )

    before = canonical_json(source.to_dict())
    entries = source.entries
    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.all_checks_passed
        and source.ledger_entry_recorded
        and isinstance(entries, tuple)
        and len(entries) > 0
        and source.total_ledger_entry_count == len(entries)
    ):
        source_errors.append("정상 V21.7 Audit Integrity Ledger Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V21.7 Source 실행 안전장치 오류입니다.")
    if source_errors:
        return _empty_result(
            policy,
            now,
            "FAILED",
            source_errors,
            policy_ok=True,
            input=True,
        )

    latest = entries[-1]
    chain_valid, chain_errors = verify_audit_integrity_ledger_chain(entries)
    findings = _findings(entries)
    linkage_errors = _linkage_errors(source, latest)
    if latest.operator != operator.strip():
        linkage_errors.append("Operator가 V21.7 Latest Entry와 다릅니다.")
    try:
        latest_time = datetime.fromisoformat(latest.recorded_at)
        if latest_time.tzinfo is None or now < latest_time:
            raise ValueError
    except (TypeError, ValueError):
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            ["역순 또는 잘못된 V21.8 Verification 시간이 차단되었습니다."],
            policy_ok=True,
            input=True,
            source=True,
        )

    unique_valid = len({item.audit_certificate_id for item in entries}) == len(entries)
    chronology_valid = all(item.chronology_valid for item in findings)
    status_valid = all(item.audit_status_valid for item in findings)
    safety_valid = all(item.safety_valid for item in findings)
    unchanged = before == canonical_json(source.to_dict())
    errors = list(chain_errors) + linkage_errors
    if not unique_valid:
        errors.append("중복 V21.6 Audit Certificate ID가 발견되었습니다.")
    if not chronology_valid:
        errors.append("V21.7 Ledger 시간 순서 오류가 발견되었습니다.")
    if not status_valid:
        errors.append("V21.7 Ledger Audit Status 오류가 발견되었습니다.")
    if not safety_valid:
        errors.append("V21.7 Ledger Entry 안전장치 오류가 발견되었습니다.")
    if not unchanged:
        errors.append("V21.8 검증 중 V21.7 Source가 변경되었습니다.")
    if errors:
        return _empty_result(
            policy,
            now,
            "FAILED",
            errors,
            policy_ok=True,
            input=True,
            source=True,
            chain=chain_valid,
            linkage=not linkage_errors,
            duplicate=unique_valid,
            chronology=chronology_valid,
            status_ok=status_valid,
            entry_safety=safety_valid,
            unchanged=unchanged,
        )

    snapshot_hash = ledger_snapshot_hash(entries)
    certificate_payload = {
        "verification_certificate_id": str(uuid.uuid4()),
        "verified_at": now.isoformat(),
        "verification_status": "PASSED",
        "source_ledger_result_id": source.ledger_result_id,
        "total_ledger_entry_count": len(entries),
        "genesis_hash": GENESIS_HASH,
        "latest_ledger_entry_id": latest.ledger_entry_id,
        "latest_ledger_entry_hash": latest.entry_hash,
        "latest_audit_result_id": latest.audit_result_id,
        "latest_audit_certificate_id": latest.audit_certificate_id,
        "latest_audit_certificate_hash": latest.audit_certificate_hash,
        "latest_source_audit_cert_ledger_result_id": (
            latest.source_audit_cert_ledger_result_id
        ),
        "latest_audit_certificate_ledger_snapshot_hash": (
            latest.audit_certificate_ledger_snapshot_hash
        ),
        "latest_v21_4_audit_certificate_hash": (
            latest.latest_v21_4_audit_certificate_hash
        ),
        "latest_v21_3_ledger_snapshot_hash": (
            latest.latest_v21_3_ledger_snapshot_hash
        ),
        "latest_v21_2_validation_certificate_hash": (
            latest.latest_v21_2_validation_certificate_hash
        ),
        "latest_v21_1_order_hash": latest.latest_v21_1_order_hash,
        "latest_v21_0_account_hash": latest.latest_v21_0_account_hash,
        "audit_integrity_ledger_snapshot_hash": snapshot_hash,
        "ledger_hash_chain_valid": True,
        "source_linkage_valid": True,
        "unique_certificate_ids_valid": True,
        "chronology_valid": True,
        "audit_status_valid": True,
        "entry_safety_valid": True,
        "ledger_unchanged": True,
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
    hash_payload["findings"] = [item.to_dict() for item in findings]
    certificate = OfflinePaperAuditIntegrityCertificateV218(
        **certificate_payload,
        certificate_hash=sha256_payload(hash_payload),
    )
    certificate_valid, certificate_errors = verify_verification_certificate(
        certificate
    )
    if not certificate_valid:
        return _empty_result(
            policy,
            now,
            "FAILED",
            certificate_errors,
            policy_ok=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=True,
            chronology=True,
            status_ok=True,
            entry_safety=True,
            snapshot=True,
            unchanged=True,
        )

    return OfflinePaperAuditIntegrityVerifyV218Result(
        version="V21.8",
        created_at=now.isoformat(),
        verification_result_id=str(uuid.uuid4()),
        result_status="VERIFIED_IN_MEMORY",
        result_status_label="Offline Paper Audit Integrity Ledger 검증 완료",
        verification_status="PASSED",
        source_ledger_result_id=source.ledger_result_id,
        verified_entry_count=len(entries),
        latest_ledger_entry_id=latest.ledger_entry_id,
        latest_ledger_entry_hash=latest.entry_hash,
        latest_audit_certificate_hash=latest.audit_certificate_hash,
        latest_audit_certificate_ledger_snapshot_hash=(
            latest.audit_certificate_ledger_snapshot_hash
        ),
        latest_v21_4_audit_certificate_hash=(
            latest.latest_v21_4_audit_certificate_hash
        ),
        latest_v21_3_ledger_snapshot_hash=(
            latest.latest_v21_3_ledger_snapshot_hash
        ),
        latest_v21_2_validation_certificate_hash=(
            latest.latest_v21_2_validation_certificate_hash
        ),
        latest_v21_1_order_hash=latest.latest_v21_1_order_hash,
        latest_v21_0_account_hash=latest.latest_v21_0_account_hash,
        audit_integrity_ledger_snapshot_hash=snapshot_hash,
        verification_certificate_id=certificate.verification_certificate_id,
        verification_certificate_hash=certificate.certificate_hash,
        policy_checks_passed=True,
        input_checks_passed=True,
        source_checks_passed=True,
        ledger_hash_chain_checks_passed=True,
        source_linkage_checks_passed=True,
        duplicate_checks_passed=True,
        chronology_checks_passed=True,
        audit_status_checks_passed=True,
        entry_safety_checks_passed=True,
        snapshot_hash_checks_passed=True,
        ledger_unchanged_checks_passed=True,
        certificate_hash_checks_passed=True,
        safety_checks_passed=True,
        all_checks_passed=True,
        verification_completed=True,
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
        verification_policy=policy,
        certificate=certificate,
        reasons=[
            f"V21.7 Ledger Entry {len(entries)}개의 무결성을 검증했습니다.",
            "V21.8 Verification Certificate를 생성했습니다.",
        ],
        warnings=[
            "V21.8은 V21.7 Ledger를 읽기 전용으로 검증했습니다.",
            "검증은 주문 체결 또는 Broker 전송 승인을 의미하지 않습니다.",
            "잔액·보유수량 변경, API, Network 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "V21.9 Audit Certificate Ledger Integrity Verification "
            "Certificate Ledger 단계에서 V21.8 Verification Certificate를 "
            "In-Memory Ledger에 기록합니다."
        ],
    )


def save_audit_integrity_verification_result(
    result: OfflinePaperAuditIntegrityVerifyV218Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report_path = output_directory / f"audit_integrity_verify_{stamp}.json"
    latest_path = output_directory / "latest_audit_integrity_verify.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_audit_integrity_verification_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V21.8 Audit Integrity Verification JSON은 object여야 합니다.")
    return payload
