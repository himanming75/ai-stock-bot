import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_archive_audit_ledger_v18_3 import (
    GENESIS_HASH,
    SandboxArchiveAuditLedgerV183Entry as SourceLedgerEntry,
    SandboxArchiveAuditLedgerV183Result as SourceLedgerResult,
    sha256_payload as ledger_sha256_payload,
    verify_audit_ledger_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "sandbox_archive_audit_ledger_integrity_v18_4"
)
REQUIRED_VERIFICATION_TEXT = (
    "VERIFY IN MEMORY SANDBOX ARCHIVE AUDIT LEDGER V18.3"
)


@dataclass(frozen=True)
class SandboxArchiveAuditLedgerIntegrityV184Policy:
    required_source_version: str = "V18.3"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_VERIFICATION_TEXT
    require_non_empty_ledger: bool = True
    require_latest_operator_match: bool = True
    require_source_linkage: bool = True
    require_valid_hash_chain: bool = True
    require_unique_certificate_ids: bool = True
    require_chronological_order: bool = True
    require_safe_entries: bool = True
    require_ledger_unchanged: bool = True
    read_only_verification: bool = True
    credentials_forbidden: bool = True
    market_data_api_disabled: bool = True
    account_access_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxArchiveAuditLedgerFindingV184:
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
class SandboxArchiveAuditLedgerCertificateV184:
    verification_certificate_id: str
    verified_at: str
    verification_status: str
    source_ledger_result_id: str
    total_ledger_entry_count: int
    genesis_hash: str
    latest_ledger_entry_id: str
    latest_ledger_entry_hash: str
    latest_audit_certificate_id: str
    latest_audit_certificate_hash: str
    latest_archive_snapshot_hash: str
    latest_final_report_hash: str
    latest_verification_ledger_snapshot_hash: str
    latest_linked_final_report_hash: str
    latest_previous_final_report_hash: str
    latest_source_certificate_ledger_snapshot_hash: str
    latest_certificate_ledger_snapshot_hash: str
    latest_archived_certificate_ledger_snapshot_hash: str
    ledger_snapshot_hash: str
    ledger_hash_chain_valid: bool
    source_linkage_valid: bool
    unique_certificate_ids_valid: bool
    chronology_valid: bool
    audit_status_valid: bool
    entry_safety_valid: bool
    ledger_unchanged: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    findings: tuple[
        SandboxArchiveAuditLedgerFindingV184, ...
    ]
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash", None)
        payload["findings"] = [
            finding.to_dict() for finding in self.findings
        ]
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["certificate_hash"] = self.certificate_hash
        return payload


@dataclass
class SandboxArchiveAuditLedgerIntegrityV184Result:
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
    latest_final_report_hash: str | None
    latest_verification_ledger_snapshot_hash: str | None
    latest_linked_final_report_hash: str | None
    latest_previous_final_report_hash: str | None
    latest_source_certificate_ledger_snapshot_hash: str | None
    latest_certificate_ledger_snapshot_hash: str | None
    latest_archived_certificate_ledger_snapshot_hash: str | None
    ledger_snapshot_hash: str | None
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
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    verification_policy: (
        SandboxArchiveAuditLedgerIntegrityV184Policy
    )
    certificate: (
        SandboxArchiveAuditLedgerCertificateV184 | None
    )
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verification_policy"] = (
            self.verification_policy.to_dict()
        )
        payload["certificate"] = (
            self.certificate.to_dict() if self.certificate else None
        )
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def ledger_snapshot_hash(
    entries: tuple[
        SourceLedgerEntry, ...
    ],
) -> str:
    return sha256_payload(
        {"entries": [entry.to_dict() for entry in entries]}
    )


def validate_policy(
    policy: (
        SandboxArchiveAuditLedgerIntegrityV184Policy
    ),
) -> list[str]:
    if not isinstance(
        policy,
        SandboxArchiveAuditLedgerIntegrityV184Policy,
    ):
        return ["Verification Archive Audit Ledger Integrity Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V18.3",
        "required_source_status": "RECORDED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_VERIFICATION_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V18.4 기준과 다릅니다.")
    for name in (
        "require_non_empty_ledger",
        "require_latest_operator_match",
        "require_source_linkage",
        "require_valid_hash_chain",
        "require_unique_certificate_ids",
        "require_chronological_order",
        "require_safe_entries",
        "require_ledger_unchanged",
        "read_only_verification",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_access_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V18.4에서 True여야 합니다.")
    return errors


def _safe_entry(
    entry: SourceLedgerEntry,
) -> bool:
    return not any(
        (
            entry.paper_execution_authorized,
            entry.automatic_execution_authorized,
            not entry.execution_blocked,
            entry.credentials_used,
            entry.market_data_api_called,
            entry.network_accessed,
            entry.account_accessed,
            entry.broker_api_called,
            entry.order_submitted,
            entry.live_execution_authorized,
        )
    )


def _safe_source(
    source: SourceLedgerResult,
) -> bool:
    return not any(
        (
            source.paper_execution_authorized,
            source.automatic_execution_authorized,
            not source.execution_blocked,
            source.credentials_used,
            source.market_data_api_called,
            source.network_accessed,
            source.account_accessed,
            source.broker_api_called,
            source.broker_order_created,
            source.order_submitted,
            source.live_order_created,
            source.live_execution_authorized,
        )
    )


def build_findings(
    entries: tuple[
        SourceLedgerEntry, ...
    ],
) -> tuple[
    SandboxArchiveAuditLedgerFindingV184, ...
]:
    findings: list[
        SandboxArchiveAuditLedgerFindingV184
    ] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        sequence_valid = entry.sequence == expected_sequence
        previous_hash_valid = entry.previous_entry_hash == previous_hash
        entry_hash_valid = (
            entry.entry_hash
            == ledger_sha256_payload(entry.payload_without_hash())
        )
        certificate_id_unique = (
            entry.audit_certificate_id not in certificate_ids
        )
        certificate_ids.add(entry.audit_certificate_id)
        chronology_valid = True
        try:
            recorded_at = datetime.fromisoformat(entry.recorded_at)
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
            SandboxArchiveAuditLedgerFindingV184(
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


def verify_verification_certificate(
    certificate: (
        SandboxArchiveAuditLedgerCertificateV184
    ),
) -> tuple[bool, list[str]]:
    if not isinstance(
        certificate,
        SandboxArchiveAuditLedgerCertificateV184,
    ):
        return False, ["Verification Certificate 형식 오류입니다."]
    errors: list[str] = []
    if certificate.verification_status != "PASSED":
        errors.append("Verification Status가 PASSED가 아닙니다.")
    if certificate.total_ledger_entry_count != len(certificate.findings):
        errors.append("Finding 개수가 Ledger Entry 개수와 다릅니다.")
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
        errors.append("Verification Certificate 검사 결과 오류입니다.")
    if certificate.certificate_hash != sha256_payload(
        certificate.payload_without_hash()
    ):
        errors.append("Verification Certificate Hash가 일치하지 않습니다.")
    if any(
        (
            certificate.paper_execution_authorized,
            certificate.automatic_execution_authorized,
            not certificate.execution_blocked,
            certificate.credentials_used,
            certificate.market_data_api_called,
            certificate.network_accessed,
            certificate.account_accessed,
            certificate.broker_api_called,
            certificate.order_submitted,
            certificate.live_execution_authorized,
        )
    ):
        errors.append("Verification Certificate 실행 안전장치 오류입니다.")
    return not errors, errors


def _empty_result(
    verification_policy: (
        SandboxArchiveAuditLedgerIntegrityV184Policy
    ),
    now: datetime,
    result_status: str,
    reasons: list[str],
    **checks: bool,
) -> SandboxArchiveAuditLedgerIntegrityV184Result:
    return SandboxArchiveAuditLedgerIntegrityV184Result(
        version="V18.4",
        created_at=now.isoformat(),
        verification_result_id=str(uuid.uuid4()),
        result_status=result_status,
        result_status_label=(
            "Audit Ledger Integrity Verification 차단"
            if result_status == "BLOCKED"
            else "Audit Ledger Integrity Verification 실패"
        ),
        verification_status="FAILED",
        source_ledger_result_id=None,
        verified_entry_count=0,
        latest_ledger_entry_id=None,
        latest_ledger_entry_hash=None,
        latest_final_report_hash=None,
        latest_verification_ledger_snapshot_hash=None,
        latest_linked_final_report_hash=None,
        latest_previous_final_report_hash=None,
        latest_source_certificate_ledger_snapshot_hash=None,
        latest_certificate_ledger_snapshot_hash=None,
        latest_archived_certificate_ledger_snapshot_hash=None,
        ledger_snapshot_hash=None,
        verification_certificate_id=None,
        verification_certificate_hash=None,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        audit_status_checks_passed=checks.get("status", False),
        entry_safety_checks_passed=checks.get("entry_safety", False),
        snapshot_hash_checks_passed=checks.get("snapshot", False),
        ledger_unchanged_checks_passed=checks.get("unchanged", False),
        certificate_hash_checks_passed=False,
        safety_checks_passed=True,
        all_checks_passed=False,
        verification_completed=False,
        ledger_modified=False,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        credentials_used=False,
        market_data_api_called=False,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        verification_policy=verification_policy,
        certificate=None,
        reasons=reasons,
        warnings=[
            "V18.4는 V18.3 Audit Ledger를 읽기 전용으로 검증합니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=["V18.3 Audit Ledger Source와 입력을 확인합니다."],
    )


def verify_sandbox_archive_audit_ledger_v18_4(
    source: Any,
    operator: str,
    confirmation_text: str,
    policy: (
        SandboxArchiveAuditLedgerIntegrityV184Policy
        | None
    ) = None,
    now: datetime | None = None,
) -> SandboxArchiveAuditLedgerIntegrityV184Result:
    policy = (
        policy
        or SandboxArchiveAuditLedgerIntegrityV184Policy()
    )
    now = now or datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator가 비어 있습니다.")
    if confirmation_text != getattr(
        policy, "required_confirmation_text", None
    ):
        input_errors.append("수동 확인 문구가 올바르지 않습니다.")
    if policy_errors or input_errors:
        safe_policy = (
            policy
            if isinstance(
                policy,
                SandboxArchiveAuditLedgerIntegrityV184Policy,
            )
            else SandboxArchiveAuditLedgerIntegrityV184Policy()
        )
        return _empty_result(
            safe_policy,
            now,
            "BLOCKED",
            policy_errors + input_errors,
            policy=not policy_errors,
            input=not input_errors,
        )
    if not isinstance(
        source,
        SourceLedgerResult,
    ):
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["Source는 V18.3 Verification Archive Audit Ledger여야 합니다."],
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
        source_errors.append("정상 V18.3 Audit Ledger Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V18.3 Source 실행 안전장치 오류입니다.")
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
    chain_valid, chain_errors = verify_audit_ledger_chain(entries)
    findings = build_findings(entries)
    if not chain_valid or any(
        finding.finding_status != "PASSED" for finding in findings
    ):
        return _empty_result(
            policy,
            now,
            "FAILED",
            chain_errors
            + [
                message
                for finding in findings
                for message in finding.messages
            ],
            policy=True,
            input=True,
            source=True,
        )

    latest = entries[-1]
    linkage_errors: list[str] = []
    for actual, expected, label in (
        (source.total_ledger_entry_count, len(entries), "Entry Count"),
        (
            source.latest_ledger_entry_id,
            latest.ledger_entry_id,
            "Entry ID",
        ),
        (
            source.latest_ledger_entry_hash,
            latest.entry_hash,
            "Entry Hash",
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
            source.latest_archive_snapshot_hash,
            latest.archive_snapshot_hash,
            "Archive Snapshot Hash",
        ),
        (
            source.latest_final_report_hash,
            latest.latest_final_report_hash,
            "Final Report Hash",
        ),
        (
            source.latest_verification_ledger_snapshot_hash,
            latest.latest_verification_ledger_snapshot_hash,
            "Verification Ledger Snapshot Hash",
        ),
        (
            source.latest_linked_final_report_hash,
            latest.latest_linked_final_report_hash,
            "Linked Final Report Hash",
        ),
        (
            source.latest_previous_final_report_hash,
            latest.latest_previous_final_report_hash,
            "Previous Final Report Hash",
        ),
        (
            source.latest_source_certificate_ledger_snapshot_hash,
            latest.latest_source_certificate_ledger_snapshot_hash,
            "Source Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_certificate_ledger_snapshot_hash,
            latest.latest_certificate_ledger_snapshot_hash,
            "Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_archived_certificate_ledger_snapshot_hash,
            latest.latest_archived_certificate_ledger_snapshot_hash,
            "Archived Certificate Ledger Snapshot Hash",
        ),
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
    if operator != latest.operator:
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            ["Operator가 V18.3 Latest Ledger Entry와 다릅니다."],
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
        )
    try:
        if now < datetime.fromisoformat(latest.recorded_at):
            return _empty_result(
                policy,
                now,
                "BLOCKED",
                ["Verification 시간이 최신 Ledger Entry보다 빠릅니다."],
                policy=True,
                input=True,
                source=True,
                chain=True,
                linkage=True,
                duplicate=True,
                status=True,
                entry_safety=True,
            )
    except (TypeError, ValueError):
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            ["최신 Ledger 시간이 올바르지 않습니다."],
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
            ["읽기 전용 검증 중 Ledger가 변경되었습니다."],
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=True,
            chronology=True,
            status=True,
            entry_safety=True,
            snapshot=True,
        )

    certificate_payload = {
        "verification_certificate_id": str(uuid.uuid4()),
        "verified_at": now.isoformat(),
        "verification_status": "PASSED",
        "source_ledger_result_id": source.ledger_result_id,
        "total_ledger_entry_count": len(entries),
        "genesis_hash": GENESIS_HASH,
        "latest_ledger_entry_id": latest.ledger_entry_id,
        "latest_ledger_entry_hash": latest.entry_hash,
        "latest_audit_certificate_id": latest.audit_certificate_id,
        "latest_audit_certificate_hash": latest.audit_certificate_hash,
        "latest_archive_snapshot_hash": latest.archive_snapshot_hash,
        "latest_final_report_hash": latest.latest_final_report_hash,
        "latest_verification_ledger_snapshot_hash": (
            latest.latest_verification_ledger_snapshot_hash
        ),
        "latest_linked_final_report_hash": (
            latest.latest_linked_final_report_hash
        ),
        "latest_previous_final_report_hash": (
            latest.latest_previous_final_report_hash
        ),
        "latest_source_certificate_ledger_snapshot_hash": (
            latest.latest_source_certificate_ledger_snapshot_hash
        ),
        "latest_certificate_ledger_snapshot_hash": (
            latest.latest_certificate_ledger_snapshot_hash
        ),
        "latest_archived_certificate_ledger_snapshot_hash": (
            latest.latest_archived_certificate_ledger_snapshot_hash
        ),
        "ledger_snapshot_hash": snapshot_hash,
        "ledger_hash_chain_valid": True,
        "source_linkage_valid": True,
        "unique_certificate_ids_valid": True,
        "chronology_valid": True,
        "audit_status_valid": True,
        "entry_safety_valid": True,
        "ledger_unchanged": True,
        "paper_execution_authorized": False,
        "automatic_execution_authorized": False,
        "execution_blocked": True,
        "credentials_used": False,
        "market_data_api_called": False,
        "network_accessed": False,
        "account_accessed": False,
        "broker_api_called": False,
        "order_submitted": False,
        "live_execution_authorized": False,
        "findings": findings,
    }
    hash_payload = dict(certificate_payload)
    hash_payload["findings"] = [
        finding.to_dict() for finding in findings
    ]
    certificate = (
        SandboxArchiveAuditLedgerCertificateV184(
            **certificate_payload,
            certificate_hash=sha256_payload(hash_payload),
        )
    )
    certificate_valid, certificate_errors = (
        verify_verification_certificate(certificate)
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
            duplicate=True,
            chronology=True,
            status=True,
            entry_safety=True,
            snapshot=True,
            unchanged=True,
        )

    return (
        SandboxArchiveAuditLedgerIntegrityV184Result(
            version="V18.4",
            created_at=now.isoformat(),
            verification_result_id=str(uuid.uuid4()),
            result_status="VERIFIED_IN_MEMORY",
            result_status_label=(
                "Sandbox Verification Final Report Archive Audit Ledger "
                "Integrity Verification 완료"
            ),
            verification_status="PASSED",
            source_ledger_result_id=source.ledger_result_id,
            verified_entry_count=len(entries),
            latest_ledger_entry_id=latest.ledger_entry_id,
            latest_ledger_entry_hash=latest.entry_hash,
            latest_final_report_hash=latest.latest_final_report_hash,
            latest_verification_ledger_snapshot_hash=(
                latest.latest_verification_ledger_snapshot_hash
            ),
            latest_linked_final_report_hash=(
                latest.latest_linked_final_report_hash
            ),
            latest_previous_final_report_hash=(
                latest.latest_previous_final_report_hash
            ),
            latest_source_certificate_ledger_snapshot_hash=(
                latest.latest_source_certificate_ledger_snapshot_hash
            ),
            latest_certificate_ledger_snapshot_hash=(
                latest.latest_certificate_ledger_snapshot_hash
            ),
            latest_archived_certificate_ledger_snapshot_hash=(
                latest.latest_archived_certificate_ledger_snapshot_hash
            ),
            ledger_snapshot_hash=snapshot_hash,
            verification_certificate_id=(
                certificate.verification_certificate_id
            ),
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
            paper_execution_authorized=False,
            automatic_execution_authorized=False,
            execution_blocked=True,
            credentials_used=False,
            market_data_api_called=False,
            network_accessed=False,
            account_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_order_created=False,
            live_execution_authorized=False,
            verification_policy=policy,
            certificate=certificate,
            reasons=[
                f"V18.3 Audit Ledger Entry {len(entries)}개를 검증했습니다.",
                "Ledger Hash Chain, Source Linkage 및 Snapshot Hash가 유효합니다.",
            ],
            warnings=[
                "V18.4는 V18.3 Audit Ledger를 변경하지 않습니다.",
                "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
            ],
            next_actions=[
                "Ledger Snapshot 및 Verification Certificate Hash를 보관합니다.",
                "검증 결과를 실제 거래와 분리하여 수동 검토합니다.",
            ],
        )
    )


def save_verification_result(
    result: (
        SandboxArchiveAuditLedgerIntegrityV184Result
    ),
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = (
        result.created_at
        .replace(":", "")
        .replace("-", "")
        .replace("+", "_")
    )
    report_path = output_directory / f"audit_ledger_integrity_{stamp}.json"
    latest_path = output_directory / "latest_audit_ledger_integrity.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_verification_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Audit Ledger Integrity JSON은 object여야 합니다.")
    return payload
