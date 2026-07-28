import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_final_report_archive_v19_1 import (
    GENESIS_HASH,
    SandboxFinalReportArchiveV191Entry as SourceArchiveEntry,
    SandboxFinalReportArchiveV191Result as SourceArchiveResult,
    sha256_payload as archive_sha256_payload,
    verify_archive_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "sandbox_archive_integrity_audit_v19_2"
)
REQUIRED_AUDIT_TEXT = (
    "AUDIT IN MEMORY SANDBOX FINAL REPORT ARCHIVE V19.1"
)


@dataclass(frozen=True)
class SandboxArchiveIntegrityAuditV192Policy:
    required_source_version: str = "V19.1"
    required_source_status: str = "ARCHIVED_IN_MEMORY"
    required_final_verification_status: str = (
        "SANDBOX_VERIFICATION_COMPLETE"
    )
    required_confirmation_text: str = REQUIRED_AUDIT_TEXT
    require_non_empty_archive: bool = True
    require_latest_operator_match: bool = True
    require_source_linkage: bool = True
    require_valid_archive_hash_chain: bool = True
    require_unique_final_report_ids: bool = True
    require_chronological_order: bool = True
    require_safe_entries: bool = True
    require_archive_unchanged: bool = True
    read_only_audit: bool = True
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
class SandboxArchiveIntegrityFindingV192:
    sequence: int
    archive_entry_id: str
    final_report_id: str
    sequence_valid: bool
    previous_hash_valid: bool
    entry_hash_valid: bool
    final_report_id_unique: bool
    chronology_valid: bool
    final_verification_status_valid: bool
    safety_valid: bool
    finding_status: str
    messages: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["messages"] = list(self.messages)
        return payload


@dataclass(frozen=True)
class SandboxArchiveIntegrityCertificateV192:
    audit_certificate_id: str
    audited_at: str
    audit_status: str
    source_archive_result_id: str
    total_archive_entry_count: int
    genesis_hash: str
    latest_archive_entry_id: str
    latest_archive_entry_hash: str
    latest_final_report_id: str
    latest_final_report_hash: str
    latest_verification_ledger_snapshot_hash: str
    latest_carried_final_report_hash: str
    latest_linked_final_report_hash: str
    latest_previous_final_report_hash: str
    latest_source_certificate_ledger_snapshot_hash: str
    latest_certificate_ledger_snapshot_hash: str
    latest_archived_certificate_ledger_snapshot_hash: str
    archive_snapshot_hash: str
    archive_hash_chain_valid: bool
    source_linkage_valid: bool
    unique_final_report_ids_valid: bool
    chronology_valid: bool
    final_verification_status_valid: bool
    entry_safety_valid: bool
    archive_unchanged: bool
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
        SandboxArchiveIntegrityFindingV192, ...
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
class SandboxArchiveIntegrityAuditV192Result:
    version: str
    created_at: str
    audit_result_id: str
    result_status: str
    result_status_label: str
    audit_status: str
    source_archive_result_id: str | None
    audited_entry_count: int
    latest_archive_entry_id: str | None
    latest_archive_entry_hash: str | None
    latest_final_report_id: str | None
    latest_final_report_hash: str | None
    latest_verification_ledger_snapshot_hash: str | None
    latest_carried_final_report_hash: str | None
    latest_linked_final_report_hash: str | None
    latest_previous_final_report_hash: str | None
    latest_source_certificate_ledger_snapshot_hash: str | None
    latest_certificate_ledger_snapshot_hash: str | None
    latest_archived_certificate_ledger_snapshot_hash: str | None
    archive_snapshot_hash: str | None
    audit_certificate_id: str | None
    audit_certificate_hash: str | None
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    archive_hash_chain_checks_passed: bool
    source_linkage_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    final_verification_status_checks_passed: bool
    entry_safety_checks_passed: bool
    snapshot_hash_checks_passed: bool
    archive_unchanged_checks_passed: bool
    certificate_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    audit_completed: bool
    archive_modified: bool
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
    audit_policy: (
        SandboxArchiveIntegrityAuditV192Policy
    )
    certificate: (
        SandboxArchiveIntegrityCertificateV192 | None
    )
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


def archive_snapshot_hash(
    entries: tuple[
        SourceArchiveEntry,
        ...,
    ],
) -> str:
    return sha256_payload(
        {"entries": [entry.to_dict() for entry in entries]}
    )


def validate_policy(
    policy: SandboxArchiveIntegrityAuditV192Policy,
) -> list[str]:
    if not isinstance(
        policy,
        SandboxArchiveIntegrityAuditV192Policy,
    ):
        return ["Verification Final Report Archive Audit Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V19.1",
        "required_source_status": "ARCHIVED_IN_MEMORY",
        "required_final_verification_status": (
            "SANDBOX_VERIFICATION_COMPLETE"
        ),
        "required_confirmation_text": REQUIRED_AUDIT_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V19.2 기준과 다릅니다.")
    for name in (
        "require_non_empty_archive",
        "require_latest_operator_match",
        "require_source_linkage",
        "require_valid_archive_hash_chain",
        "require_unique_final_report_ids",
        "require_chronological_order",
        "require_safe_entries",
        "require_archive_unchanged",
        "read_only_audit",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_access_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V19.2에서 True여야 합니다.")
    return errors


def _safe_entry(
    entry: SourceArchiveEntry,
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
    source: SourceArchiveResult,
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
        SourceArchiveEntry,
        ...,
    ],
) -> tuple[
    SandboxArchiveIntegrityFindingV192, ...
]:
    findings: list[
        SandboxArchiveIntegrityFindingV192
    ] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    report_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        sequence_valid = entry.sequence == expected_sequence
        previous_hash_valid = entry.previous_entry_hash == previous_hash
        entry_hash_valid = (
            entry.entry_hash
            == archive_sha256_payload(entry.payload_without_hash())
        )
        report_id_unique = entry.final_report_id not in report_ids
        report_ids.add(entry.final_report_id)
        chronology_valid = True
        try:
            archived_at = datetime.fromisoformat(entry.archived_at)
            if previous_time and archived_at < previous_time:
                chronology_valid = False
            previous_time = archived_at
        except (TypeError, ValueError):
            chronology_valid = False
        status_valid = (
            entry.final_verification_status
            == "SANDBOX_VERIFICATION_COMPLETE"
        )
        safety_valid = _safe_entry(entry)
        messages: list[str] = []
        for passed, message in (
            (sequence_valid, "Sequence 불일치"),
            (previous_hash_valid, "Previous Hash 불일치"),
            (entry_hash_valid, "Entry Hash 불일치"),
            (report_id_unique, "중복 Final Report ID"),
            (chronology_valid, "Archive 시간 순서 오류"),
            (status_valid, "Final Verification Status 오류"),
            (safety_valid, "실행 안전장치 오류"),
        ):
            if not passed:
                messages.append(message)
        findings.append(
            SandboxArchiveIntegrityFindingV192(
                sequence=entry.sequence,
                archive_entry_id=entry.archive_entry_id,
                final_report_id=entry.final_report_id,
                sequence_valid=sequence_valid,
                previous_hash_valid=previous_hash_valid,
                entry_hash_valid=entry_hash_valid,
                final_report_id_unique=report_id_unique,
                chronology_valid=chronology_valid,
                final_verification_status_valid=status_valid,
                safety_valid=safety_valid,
                finding_status="PASSED" if not messages else "FAILED",
                messages=tuple(messages),
            )
        )
        previous_hash = entry.entry_hash
    return tuple(findings)


def verify_audit_certificate(
    certificate: (
        SandboxArchiveIntegrityCertificateV192
    ),
) -> tuple[bool, list[str]]:
    if not isinstance(
        certificate,
        SandboxArchiveIntegrityCertificateV192,
    ):
        return False, ["Archive Integrity Audit Certificate 형식 오류입니다."]
    errors: list[str] = []
    if certificate.audit_status != "PASSED":
        errors.append("Audit Status가 PASSED가 아닙니다.")
    if certificate.total_archive_entry_count != len(certificate.findings):
        errors.append("Audit Finding 개수가 Archive Entry 개수와 다릅니다.")
    if not all(
        (
            certificate.archive_hash_chain_valid,
            certificate.source_linkage_valid,
            certificate.unique_final_report_ids_valid,
            certificate.chronology_valid,
            certificate.final_verification_status_valid,
            certificate.entry_safety_valid,
            certificate.archive_unchanged,
            all(
                finding.finding_status == "PASSED"
                for finding in certificate.findings
            ),
        )
    ):
        errors.append("Audit Certificate 검사 결과가 올바르지 않습니다.")
    if certificate.certificate_hash != sha256_payload(
        certificate.payload_without_hash()
    ):
        errors.append("Audit Certificate Hash가 일치하지 않습니다.")
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
        errors.append("Audit Certificate 실행 안전장치 오류입니다.")
    return not errors, errors


def _empty_result(
    audit_policy: (
        SandboxArchiveIntegrityAuditV192Policy
    ),
    now: datetime,
    result_status: str,
    reasons: list[str],
    **checks: bool,
) -> SandboxArchiveIntegrityAuditV192Result:
    return SandboxArchiveIntegrityAuditV192Result(
        version="V19.2",
        created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()),
        result_status=result_status,
        result_status_label=(
            "Verification Final Report Archive Integrity Audit 차단"
            if result_status == "BLOCKED"
            else "Verification Final Report Archive Integrity Audit 실패"
        ),
        audit_status="FAILED",
        source_archive_result_id=None,
        audited_entry_count=0,
        latest_archive_entry_id=None,
        latest_archive_entry_hash=None,
        latest_final_report_id=None,
        latest_final_report_hash=None,
        latest_verification_ledger_snapshot_hash=None,
        latest_carried_final_report_hash=None,
        latest_linked_final_report_hash=None,
        latest_previous_final_report_hash=None,
        latest_source_certificate_ledger_snapshot_hash=None,
        latest_certificate_ledger_snapshot_hash=None,
        latest_archived_certificate_ledger_snapshot_hash=None,
        archive_snapshot_hash=None,
        audit_certificate_id=None,
        audit_certificate_hash=None,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        archive_hash_chain_checks_passed=checks.get("chain", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        final_verification_status_checks_passed=checks.get("status", False),
        entry_safety_checks_passed=checks.get("entry_safety", False),
        snapshot_hash_checks_passed=checks.get("snapshot", False),
        archive_unchanged_checks_passed=checks.get("unchanged", False),
        certificate_hash_checks_passed=False,
        safety_checks_passed=True,
        all_checks_passed=False,
        audit_completed=False,
        archive_modified=False,
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
        audit_policy=audit_policy,
        certificate=None,
        reasons=reasons,
        warnings=[
            "V19.2는 V19.1 Archive를 읽기 전용으로 감사합니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=["V19.1 Archive Source와 입력을 수동 확인합니다."],
    )


def audit_sandbox_archive_integrity_v19_2(
    source: Any,
    operator: str,
    confirmation_text: str,
    policy: (
        SandboxArchiveIntegrityAuditV192Policy | None
    ) = None,
    now: datetime | None = None,
) -> SandboxArchiveIntegrityAuditV192Result:
    policy = (
        policy
        or SandboxArchiveIntegrityAuditV192Policy()
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
                SandboxArchiveIntegrityAuditV192Policy,
            )
            else SandboxArchiveIntegrityAuditV192Policy()
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
        SourceArchiveResult,
    ):
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["Source는 V19.1 Verification Final Report Archive여야 합니다."],
            policy=True,
            input=True,
        )

    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.all_checks_passed
        and source.archive_entry_recorded
    ):
        source_errors.append("정상 V19.1 Archive Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V19.1 Source 실행 안전장치 오류입니다.")
    entries = tuple(source.entries)
    if not entries:
        source_errors.append("V19.1 Archive Entry가 비어 있습니다.")
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
    chain_valid, chain_errors = verify_archive_chain(entries)
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
        (
            source.total_archive_entry_count,
            len(entries),
            "Archive Entry Count",
        ),
        (
            source.latest_archive_entry_id,
            latest.archive_entry_id,
            "Latest Archive Entry ID",
        ),
        (
            source.latest_archive_entry_hash,
            latest.entry_hash,
            "Latest Archive Entry Hash",
        ),
        (
            source.latest_final_report_id,
            latest.final_report_id,
            "Latest Final Report ID",
        ),
        (
            source.latest_final_report_hash,
            latest.final_report_hash,
            "Latest Final Report Hash",
        ),
        (
            source.latest_verification_ledger_snapshot_hash,
            latest.latest_verification_ledger_snapshot_hash,
            "Verification Ledger Snapshot Hash",
        ),
        (
            source.latest_carried_final_report_hash,
            latest.carried_final_report_hash,
            "Carried Final Report Hash",
        ),
        (
            source.latest_linked_final_report_hash,
            latest.linked_final_report_hash,
            "Linked Final Report Hash",
        ),
        (
            source.latest_previous_final_report_hash,
            latest.previous_final_report_hash,
            "Previous Final Report Hash",
        ),
        (
            source.latest_source_certificate_ledger_snapshot_hash,
            latest.source_certificate_ledger_snapshot_hash,
            "Source Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_certificate_ledger_snapshot_hash,
            latest.latest_certificate_ledger_snapshot_hash,
            "Latest Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_archived_certificate_ledger_snapshot_hash,
            latest.archived_certificate_ledger_snapshot_hash,
            "Archived Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_final_verification_status,
            latest.final_verification_status,
            "Final Verification Status",
        ),
    ):
        if actual != expected:
            linkage_errors.append(f"Source {label} 연결이 다릅니다.")
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
            ["Operator가 V19.1 Latest Archive Entry와 다릅니다."],
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
        )
    try:
        latest_time = datetime.fromisoformat(latest.archived_at)
        if now < latest_time:
            return _empty_result(
                policy,
                now,
                "BLOCKED",
                ["Audit 시간이 최신 Archive Entry보다 빠릅니다."],
                policy=True,
                input=True,
                source=True,
                chain=True,
                linkage=True,
                duplicate=True,
                chronology=False,
                status=True,
                entry_safety=True,
            )
    except (TypeError, ValueError):
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            ["최신 Archive 시간이 올바르지 않습니다."],
            policy=True,
            input=True,
            source=True,
            chain=True,
            linkage=True,
            duplicate=True,
            status=True,
            entry_safety=True,
        )

    snapshot_hash = archive_snapshot_hash(entries)
    archive_unchanged = source_before == canonical_json(source.to_dict())
    if not archive_unchanged:
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["읽기 전용 Audit 중 Archive Source가 변경되었습니다."],
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
        "audit_certificate_id": str(uuid.uuid4()),
        "audited_at": now.isoformat(),
        "audit_status": "PASSED",
        "source_archive_result_id": source.archive_result_id,
        "total_archive_entry_count": len(entries),
        "genesis_hash": GENESIS_HASH,
        "latest_archive_entry_id": latest.archive_entry_id,
        "latest_archive_entry_hash": latest.entry_hash,
        "latest_final_report_id": latest.final_report_id,
        "latest_final_report_hash": latest.final_report_hash,
        "latest_verification_ledger_snapshot_hash": (
            latest.latest_verification_ledger_snapshot_hash
        ),
        "latest_carried_final_report_hash": (
            latest.carried_final_report_hash
        ),
        "latest_linked_final_report_hash": (
            latest.linked_final_report_hash
        ),
        "latest_previous_final_report_hash": (
            latest.previous_final_report_hash
        ),
        "latest_source_certificate_ledger_snapshot_hash": (
            latest.source_certificate_ledger_snapshot_hash
        ),
        "latest_certificate_ledger_snapshot_hash": (
            latest.latest_certificate_ledger_snapshot_hash
        ),
        "latest_archived_certificate_ledger_snapshot_hash": (
            latest.archived_certificate_ledger_snapshot_hash
        ),
        "archive_snapshot_hash": snapshot_hash,
        "archive_hash_chain_valid": True,
        "source_linkage_valid": True,
        "unique_final_report_ids_valid": True,
        "chronology_valid": True,
        "final_verification_status_valid": True,
        "entry_safety_valid": True,
        "archive_unchanged": True,
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
        SandboxArchiveIntegrityCertificateV192(
            **certificate_payload,
            certificate_hash=sha256_payload(hash_payload),
        )
    )
    certificate_valid, certificate_errors = verify_audit_certificate(
        certificate
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

    return SandboxArchiveIntegrityAuditV192Result(
        version="V19.2",
        created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()),
        result_status="AUDITED_IN_MEMORY",
        result_status_label=(
            "Sandbox Verification Final Report Archive Integrity Audit 완료"
        ),
        audit_status="PASSED",
        source_archive_result_id=source.archive_result_id,
        audited_entry_count=len(entries),
        latest_archive_entry_id=latest.archive_entry_id,
        latest_archive_entry_hash=latest.entry_hash,
        latest_final_report_id=latest.final_report_id,
        latest_final_report_hash=latest.final_report_hash,
        latest_verification_ledger_snapshot_hash=(
            latest.latest_verification_ledger_snapshot_hash
        ),
        latest_carried_final_report_hash=(
            latest.carried_final_report_hash
        ),
        latest_linked_final_report_hash=(
            latest.linked_final_report_hash
        ),
        latest_previous_final_report_hash=(
            latest.previous_final_report_hash
        ),
        latest_source_certificate_ledger_snapshot_hash=(
            latest.source_certificate_ledger_snapshot_hash
        ),
        latest_certificate_ledger_snapshot_hash=(
            latest.latest_certificate_ledger_snapshot_hash
        ),
        latest_archived_certificate_ledger_snapshot_hash=(
            latest.archived_certificate_ledger_snapshot_hash
        ),
        archive_snapshot_hash=snapshot_hash,
        audit_certificate_id=certificate.audit_certificate_id,
        audit_certificate_hash=certificate.certificate_hash,
        policy_checks_passed=True,
        input_checks_passed=True,
        source_checks_passed=True,
        archive_hash_chain_checks_passed=True,
        source_linkage_checks_passed=True,
        duplicate_checks_passed=True,
        chronology_checks_passed=True,
        final_verification_status_checks_passed=True,
        entry_safety_checks_passed=True,
        snapshot_hash_checks_passed=True,
        archive_unchanged_checks_passed=True,
        certificate_hash_checks_passed=True,
        safety_checks_passed=True,
        all_checks_passed=True,
        audit_completed=True,
        archive_modified=False,
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
        audit_policy=policy,
        certificate=certificate,
        reasons=[
            f"V19.1 Archive Entry {len(entries)}개를 읽기 전용으로 감사했습니다.",
            "Archive SHA-256 Hash Chain과 Source Linkage가 유효합니다.",
            "Archive Snapshot과 Audit Certificate Hash를 생성했습니다.",
        ],
        warnings=[
            "V19.2 Audit는 V19.1 Archive를 변경하지 않습니다.",
            "Audit Certificate는 거래 권한을 부여하지 않습니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "Archive Snapshot Hash와 Audit Certificate Hash를 보관합니다.",
            "감사 결과를 실제 거래와 분리하여 수동 검토합니다.",
        ],
    )


def save_audit_result(
    result: SandboxArchiveIntegrityAuditV192Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = (
        result.created_at
        .replace(":", "")
        .replace("-", "")
        .replace("+", "_")
    )
    report_path = output_directory / f"archive_integrity_audit_{stamp}.json"
    latest_path = output_directory / "latest_archive_integrity_audit.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_audit_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Archive Integrity Audit JSON은 object여야 합니다.")
    return payload
