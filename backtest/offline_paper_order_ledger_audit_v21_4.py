import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_order_validation_ledger_v21_3 import (
    GENESIS_HASH,
    OfflinePaperOrderValidationLedgerV213Entry,
    OfflinePaperOrderValidationLedgerV213Result,
    verify_validation_ledger_chain,
)
from backtest.offline_paper_trading_account_v21_0 import canonical_json


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "offline_paper_order_ledger_audit_v21_4"
)
REQUIRED_AUDIT_TEXT = "AUDIT OFFLINE PAPER ORDER VALIDATION LEDGER V21.4"


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class OfflinePaperOrderLedgerAuditV214Policy:
    required_source_version: str = "V21.3"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_certificate_status: str = "VALIDATED_IN_MEMORY"
    required_validation_scope: str = "OFFLINE_PAPER_ONLY"
    required_confirmation_text: str = REQUIRED_AUDIT_TEXT
    require_nonempty_ledger: bool = True
    require_same_operator: bool = True
    require_source_linkage: bool = True
    require_source_unchanged: bool = True
    require_hash_chain: bool = True
    require_unique_certificate_ids: bool = True
    require_chronology: bool = True
    require_safe_entries: bool = True
    audit_read_only: bool = True
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
class OfflinePaperOrderLedgerFindingV214:
    sequence: int
    ledger_entry_id: str
    validation_certificate_id: str
    sequence_valid: bool
    previous_hash_valid: bool
    entry_hash_valid: bool
    certificate_id_unique: bool
    chronology_valid: bool
    certificate_status_valid: bool
    validation_scope_valid: bool
    safety_valid: bool
    finding_status: str
    messages: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["messages"] = list(self.messages)
        return payload


@dataclass(frozen=True)
class OfflinePaperOrderLedgerAuditCertificateV214:
    audit_certificate_id: str
    audited_at: str
    audit_status: str
    source_ledger_result_id: str
    total_ledger_entry_count: int
    genesis_hash: str
    latest_ledger_entry_id: str
    latest_ledger_entry_hash: str
    latest_validation_result_id: str
    latest_validation_certificate_id: str
    latest_validation_certificate_hash: str
    latest_paper_order_id: str
    latest_order_hash: str
    latest_account_id: str
    latest_account_hash: str
    ledger_snapshot_hash: str
    ledger_hash_chain_valid: bool
    source_linkage_valid: bool
    unique_certificate_ids_valid: bool
    chronology_valid: bool
    certificate_status_valid: bool
    validation_scope_valid: bool
    entry_safety_valid: bool
    source_unchanged: bool
    funds_reserved: bool
    holdings_reserved: bool
    order_execution_authorized: bool
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
    findings: tuple[OfflinePaperOrderLedgerFindingV214, ...]
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
class OfflinePaperOrderLedgerAuditV214Result:
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
    latest_validation_result_id: str | None
    latest_validation_certificate_id: str | None
    latest_validation_certificate_hash: str | None
    latest_paper_order_id: str | None
    latest_order_hash: str | None
    latest_account_id: str | None
    latest_account_hash: str | None
    ledger_snapshot_hash: str | None
    audit_certificate_id: str | None
    audit_certificate_hash: str | None
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    source_linkage_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    certificate_status_checks_passed: bool
    validation_scope_checks_passed: bool
    entry_safety_checks_passed: bool
    snapshot_hash_checks_passed: bool
    source_unchanged_checks_passed: bool
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
    audit_policy: OfflinePaperOrderLedgerAuditV214Policy
    certificate: OfflinePaperOrderLedgerAuditCertificateV214 | None
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


def validate_policy(policy: OfflinePaperOrderLedgerAuditV214Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperOrderLedgerAuditV214Policy):
        return ["Offline Paper Order Ledger Audit Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V21.3",
        "required_source_status": "RECORDED_IN_MEMORY",
        "required_certificate_status": "VALIDATED_IN_MEMORY",
        "required_validation_scope": "OFFLINE_PAPER_ONLY",
        "required_confirmation_text": REQUIRED_AUDIT_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V21.4 기준과 다릅니다.")
    for name in (
        "require_nonempty_ledger",
        "require_same_operator",
        "require_source_linkage",
        "require_source_unchanged",
        "require_hash_chain",
        "require_unique_certificate_ids",
        "require_chronology",
        "require_safe_entries",
        "audit_read_only",
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
            errors.append(f"{name}는 V21.4에서 True여야 합니다.")
    return errors


def _safe_entry(entry: OfflinePaperOrderValidationLedgerV213Entry) -> bool:
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


def _safe_source(source: OfflinePaperOrderValidationLedgerV213Result) -> bool:
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


def ledger_snapshot_hash(
    entries: tuple[OfflinePaperOrderValidationLedgerV213Entry, ...],
) -> str:
    return sha256_payload({"entries": [entry.to_dict() for entry in entries]})


def build_findings(
    entries: tuple[OfflinePaperOrderValidationLedgerV213Entry, ...],
) -> tuple[OfflinePaperOrderLedgerFindingV214, ...]:
    findings: list[OfflinePaperOrderLedgerFindingV214] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        messages: list[str] = []
        sequence_valid = entry.sequence == expected_sequence
        previous_hash_valid = entry.previous_entry_hash == previous_hash
        entry_hash_valid = (
            entry.entry_hash == sha256_payload(entry.payload_without_hash())
        )
        certificate_id_unique = (
            entry.validation_certificate_id not in certificate_ids
        )
        certificate_ids.add(entry.validation_certificate_id)
        try:
            recorded_at = datetime.fromisoformat(entry.recorded_at)
            chronology_valid = (
                recorded_at.tzinfo is not None
                and (previous_time is None or recorded_at >= previous_time)
            )
            if recorded_at.tzinfo is not None:
                previous_time = recorded_at
        except (TypeError, ValueError):
            chronology_valid = False
        certificate_status_valid = (
            entry.certificate_status == "VALIDATED_IN_MEMORY"
        )
        validation_scope_valid = (
            entry.validation_scope == "OFFLINE_PAPER_ONLY"
        )
        safety_valid = _safe_entry(entry)
        checks = (
            ("Sequence", sequence_valid),
            ("Previous Hash", previous_hash_valid),
            ("Entry Hash", entry_hash_valid),
            ("Certificate ID Unique", certificate_id_unique),
            ("Chronology", chronology_valid),
            ("Certificate Status", certificate_status_valid),
            ("Validation Scope", validation_scope_valid),
            ("Safety", safety_valid),
        )
        messages.extend(
            f"Sequence {entry.sequence} {label} 오류입니다."
            for label, passed in checks
            if not passed
        )
        findings.append(
            OfflinePaperOrderLedgerFindingV214(
                sequence=entry.sequence,
                ledger_entry_id=entry.ledger_entry_id,
                validation_certificate_id=entry.validation_certificate_id,
                sequence_valid=sequence_valid,
                previous_hash_valid=previous_hash_valid,
                entry_hash_valid=entry_hash_valid,
                certificate_id_unique=certificate_id_unique,
                chronology_valid=chronology_valid,
                certificate_status_valid=certificate_status_valid,
                validation_scope_valid=validation_scope_valid,
                safety_valid=safety_valid,
                finding_status="PASSED" if not messages else "FAILED",
                messages=tuple(messages),
            )
        )
        previous_hash = entry.entry_hash
    return tuple(findings)


def verify_audit_certificate(
    certificate: OfflinePaperOrderLedgerAuditCertificateV214,
) -> tuple[bool, list[str]]:
    if not isinstance(
        certificate,
        OfflinePaperOrderLedgerAuditCertificateV214,
    ):
        return False, ["V21.4 Audit Certificate 형식 오류입니다."]
    errors: list[str] = []
    if not (
        certificate.audit_status == "PASSED"
        and certificate.total_ledger_entry_count > 0
        and certificate.total_ledger_entry_count == len(certificate.findings)
        and certificate.genesis_hash == GENESIS_HASH
        and certificate.ledger_hash_chain_valid
        and certificate.source_linkage_valid
        and certificate.unique_certificate_ids_valid
        and certificate.chronology_valid
        and certificate.certificate_status_valid
        and certificate.validation_scope_valid
        and certificate.entry_safety_valid
        and certificate.source_unchanged
        and all(
            finding.finding_status == "PASSED"
            for finding in certificate.findings
        )
    ):
        errors.append("V21.4 Audit Certificate 검사 결과 오류입니다.")
    if certificate.certificate_hash != sha256_payload(
        certificate.payload_without_hash()
    ):
        errors.append("V21.4 Audit Certificate Hash가 일치하지 않습니다.")
    if any(
        (
            certificate.funds_reserved,
            certificate.holdings_reserved,
            certificate.order_execution_authorized,
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
        errors.append("V21.4 Audit Certificate 실행 안전장치 오류입니다.")
    return not errors, errors


def _result(
    audit_policy: OfflinePaperOrderLedgerAuditV214Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    source_result: OfflinePaperOrderValidationLedgerV213Result | None = None,
    audit_certificate: OfflinePaperOrderLedgerAuditCertificateV214 | None = None,
    snapshot_hash: str | None = None,
    **checks: bool,
) -> OfflinePaperOrderLedgerAuditV214Result:
    completed = status == "AUDITED_IN_MEMORY"
    latest = (
        source_result.entries[-1]
        if source_result and source_result.entries
        else None
    )
    return OfflinePaperOrderLedgerAuditV214Result(
        version="V21.4",
        created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Offline Paper Order Validation Ledger Integrity Audit 완료"
            if completed
            else "Offline Paper Order Validation Ledger Integrity Audit 차단"
            if status == "BLOCKED"
            else "Offline Paper Order Validation Ledger Integrity Audit 실패"
        ),
        audit_status="PASSED" if completed else "FAILED",
        source_ledger_result_id=(
            source_result.ledger_result_id if source_result else None
        ),
        audited_entry_count=(
            len(source_result.entries)
            if completed and source_result
            else 0
        ),
        latest_ledger_entry_id=latest.ledger_entry_id if latest else None,
        latest_ledger_entry_hash=latest.entry_hash if latest else None,
        latest_validation_result_id=(
            latest.validation_result_id if latest else None
        ),
        latest_validation_certificate_id=(
            latest.validation_certificate_id if latest else None
        ),
        latest_validation_certificate_hash=(
            latest.validation_certificate_hash if latest else None
        ),
        latest_paper_order_id=(
            latest.source_paper_order_id if latest else None
        ),
        latest_order_hash=latest.source_order_hash if latest else None,
        latest_account_id=latest.source_account_id if latest else None,
        latest_account_hash=latest.source_account_hash if latest else None,
        ledger_snapshot_hash=snapshot_hash,
        audit_certificate_id=(
            audit_certificate.audit_certificate_id
            if audit_certificate
            else None
        ),
        audit_certificate_hash=(
            audit_certificate.certificate_hash
            if audit_certificate
            else None
        ),
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        certificate_status_checks_passed=checks.get("certificate_status", False),
        validation_scope_checks_passed=checks.get("scope", False),
        entry_safety_checks_passed=checks.get("entry_safety", False),
        snapshot_hash_checks_passed=checks.get("snapshot", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        certificate_hash_checks_passed=checks.get("certificate", False),
        safety_checks_passed=True,
        all_checks_passed=completed,
        audit_completed=completed,
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
        certificate=audit_certificate,
        reasons=reasons,
        warnings=[
            "V21.4는 V21.3 Validation Ledger를 읽기 전용으로 감사합니다.",
            "Ledger 감사는 주문 체결 또는 Broker 전송 승인을 의미하지 않습니다.",
            "잔액·보유수량 변경, 시세·계좌 API, Network 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            (
                "V21.5 Offline Paper Order Ledger Audit Certificate Ledger "
                "단계에서 Audit Certificate를 기록합니다."
                if completed
                else "V21.3 Source Ledger와 감사 입력을 확인합니다."
            )
        ],
    )


def audit_offline_paper_order_ledger_v21_4(
    source: Any,
    operator: Any,
    confirmation_text: Any,
    policy: OfflinePaperOrderLedgerAuditV214Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperOrderLedgerAuditV214Result:
    policy = policy or OfflinePaperOrderLedgerAuditV214Policy()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        now = datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    if confirmation_text != getattr(policy, "required_confirmation_text", None):
        input_errors.append("V21.4 확인 문구가 일치하지 않습니다.")
    if policy_errors or input_errors:
        safe_policy = (
            policy
            if isinstance(policy, OfflinePaperOrderLedgerAuditV214Policy)
            else OfflinePaperOrderLedgerAuditV214Policy()
        )
        return _result(
            safe_policy,
            now,
            "BLOCKED",
            policy_errors + input_errors,
            policy=not policy_errors,
            input=not input_errors,
        )
    if not isinstance(source, OfflinePaperOrderValidationLedgerV213Result):
        return _result(
            policy,
            now,
            "FAILED",
            ["Source는 V21.3 Offline Paper Order Validation Ledger여야 합니다."],
            policy=True,
            input=True,
        )

    entries = tuple(source.entries)
    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.all_checks_passed
        and source.ledger_entry_recorded
        and entries
    ):
        source_errors.append("정상 V21.3 Validation Ledger Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V21.3 Source 실행 안전장치 오류입니다.")
    if source_errors:
        return _result(
            policy,
            now,
            "FAILED",
            source_errors,
            source_result=source,
            policy=True,
            input=True,
        )

    source_before = canonical_json(source.to_dict())
    chain_valid, chain_errors = verify_validation_ledger_chain(entries)
    findings = build_findings(entries)
    if not chain_valid or any(
        finding.finding_status != "PASSED" for finding in findings
    ):
        return _result(
            policy,
            now,
            "FAILED",
            chain_errors
            + [
                message
                for finding in findings
                for message in finding.messages
            ],
            source_result=source,
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
            source.latest_validation_result_id,
            latest.validation_result_id,
            "Validation Result ID",
        ),
        (
            source.latest_validation_certificate_id,
            latest.validation_certificate_id,
            "Validation Certificate ID",
        ),
        (
            source.latest_validation_certificate_hash,
            latest.validation_certificate_hash,
            "Validation Certificate Hash",
        ),
        (
            source.latest_paper_order_id,
            latest.source_paper_order_id,
            "Paper Order ID",
        ),
        (source.latest_order_hash, latest.source_order_hash, "Order Hash"),
        (source.latest_account_id, latest.source_account_id, "Account ID"),
        (source.latest_account_hash, latest.source_account_hash, "Account Hash"),
    ):
        if actual != expected:
            linkage_errors.append(f"Source Latest {label} 연결이 다릅니다.")
    if linkage_errors:
        return _result(
            policy,
            now,
            "BLOCKED",
            linkage_errors,
            source_result=source,
            policy=True,
            input=True,
            source=True,
            chain=True,
        )
    if operator.strip() != latest.operator:
        return _result(
            policy,
            now,
            "BLOCKED",
            ["Operator가 V21.3 Latest Ledger Entry와 다릅니다."],
            source_result=source,
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
        return _result(
            policy,
            now,
            "BLOCKED",
            ["Audit 시간이 최신 Ledger Entry보다 빠르거나 올바르지 않습니다."],
            source_result=source,
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=True,
            certificate_status=True,
            scope=True,
            entry_safety=True,
        )

    snapshot_hash = ledger_snapshot_hash(entries)
    unchanged = source_before == canonical_json(source.to_dict())
    if not unchanged:
        return _result(
            policy,
            now,
            "FAILED",
            ["읽기 전용 감사 중 V21.3 Ledger가 변경되었습니다."],
            source_result=source,
            snapshot_hash=snapshot_hash,
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=True,
            chronology=True,
            certificate_status=True,
            scope=True,
            entry_safety=True,
            snapshot=True,
        )

    certificate_payload = {
        "audit_certificate_id": str(uuid.uuid4()),
        "audited_at": now.isoformat(),
        "audit_status": "PASSED",
        "source_ledger_result_id": source.ledger_result_id,
        "total_ledger_entry_count": len(entries),
        "genesis_hash": GENESIS_HASH,
        "latest_ledger_entry_id": latest.ledger_entry_id,
        "latest_ledger_entry_hash": latest.entry_hash,
        "latest_validation_result_id": latest.validation_result_id,
        "latest_validation_certificate_id": latest.validation_certificate_id,
        "latest_validation_certificate_hash": (
            latest.validation_certificate_hash
        ),
        "latest_paper_order_id": latest.source_paper_order_id,
        "latest_order_hash": latest.source_order_hash,
        "latest_account_id": latest.source_account_id,
        "latest_account_hash": latest.source_account_hash,
        "ledger_snapshot_hash": snapshot_hash,
        "ledger_hash_chain_valid": True,
        "source_linkage_valid": True,
        "unique_certificate_ids_valid": True,
        "chronology_valid": True,
        "certificate_status_valid": True,
        "validation_scope_valid": True,
        "entry_safety_valid": True,
        "source_unchanged": True,
        "funds_reserved": False,
        "holdings_reserved": False,
        "order_execution_authorized": False,
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
    certificate = OfflinePaperOrderLedgerAuditCertificateV214(
        **certificate_payload,
        certificate_hash=sha256_payload(
            {
                **certificate_payload,
                "findings": [finding.to_dict() for finding in findings],
            }
        ),
    )
    certificate_valid, certificate_errors = verify_audit_certificate(certificate)
    if not certificate_valid:
        return _result(
            policy,
            now,
            "FAILED",
            certificate_errors,
            source_result=source,
            snapshot_hash=snapshot_hash,
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=True,
            chronology=True,
            certificate_status=True,
            scope=True,
            entry_safety=True,
            snapshot=True,
            unchanged=True,
        )
    return _result(
        policy,
        now,
        "AUDITED_IN_MEMORY",
        [
            f"V21.3 Validation Ledger Entry {len(entries)}개를 감사했습니다.",
            "Ledger Hash Chain, Source Linkage 및 Snapshot Hash가 유효합니다.",
        ],
        source_result=source,
        audit_certificate=certificate,
        snapshot_hash=snapshot_hash,
        policy=True,
        input=True,
        source=True,
        chain=True,
        linkage=True,
        duplicate=True,
        chronology=True,
        certificate_status=True,
        scope=True,
        entry_safety=True,
        snapshot=True,
        unchanged=True,
        certificate=True,
    )


def save_ledger_audit_result(
    result: OfflinePaperOrderLedgerAuditV214Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = (
        result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    )
    report_path = output_directory / f"ledger_audit_{stamp}.json"
    latest_path = output_directory / "latest_ledger_audit.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_ledger_audit_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V21.4 Ledger Audit JSON은 object여야 합니다.")
    return payload
