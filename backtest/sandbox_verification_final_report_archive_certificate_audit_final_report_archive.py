import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_verification_final_report_archive_certificate_audit_final_report import (
    SandboxVerificationFinalReportArchiveCertificateAuditFinalReportResult,
    verify_final_report,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "sandbox_verification_final_report_archive_certificate_audit_final_report_archive"
)
REQUIRED_ARCHIVE_TEXT = (
    "ARCHIVE IN MEMORY SANDBOX VERIFICATION FINAL REPORT ARCHIVE CERTIFICATE AUDIT FINAL REPORT"
)
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy:
    required_source_version: str = "V17.0"
    required_source_status: str = "FINALIZED_IN_MEMORY"
    required_report_status: str = "FINALIZED_IN_MEMORY"
    required_final_verification_status: str = "SANDBOX_VERIFICATION_COMPLETE"
    required_confirmation_text: str = REQUIRED_ARCHIVE_TEXT
    maximum_archive_entries: int = 100
    require_same_operator: bool = True
    require_valid_report_hash: bool = True
    require_source_linkage: bool = True
    require_chronological_order: bool = True
    reject_duplicate_report_id: bool = True
    verify_archive_hash_chain: bool = True
    archive_only: bool = True
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
class SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry:
    archive_entry_id: str
    sequence: int
    archived_at: str
    previous_entry_hash: str
    final_report_result_id: str
    final_report_id: str
    final_report_hash: str
    source_ledger_result_id: str
    source_latest_entry_id: str
    source_latest_entry_hash: str
    latest_verification_ledger_snapshot_hash: str
    previous_final_report_hash: str
    source_certificate_ledger_snapshot_hash: str
    certificate_ledger_snapshot_hash: str
    latest_verification_certificate_id: str
    latest_verification_certificate_hash: str
    total_certificate_count: int
    final_verification_status: str
    operator: str
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
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveResult:
    version: str
    created_at: str
    archive_result_id: str
    result_status: str
    result_status_label: str
    latest_archive_entry_id: str | None
    latest_archive_entry_hash: str | None
    latest_final_report_id: str | None
    latest_final_report_hash: str | None
    latest_verification_ledger_snapshot_hash: str | None
    latest_previous_final_report_hash: str | None
    latest_source_certificate_ledger_snapshot_hash: str | None
    latest_certificate_ledger_snapshot_hash: str | None
    latest_final_verification_status: str
    total_archive_entry_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    report_hash_checks_passed: bool
    linkage_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    existing_archive_checks_passed: bool
    archive_hash_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    archive_entry_recorded: bool
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
    archive_policy: SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy
    entries: tuple[SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry, ...]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["archive_policy"] = self.archive_policy.to_dict()
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(
    policy: SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy,
) -> list[str]:
    if not isinstance(policy, SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy):
        return ["Sandbox Verification Final Report Archive Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V17.0",
        "required_source_status": "FINALIZED_IN_MEMORY",
        "required_report_status": "FINALIZED_IN_MEMORY",
        "required_final_verification_status": "SANDBOX_VERIFICATION_COMPLETE",
        "required_confirmation_text": REQUIRED_ARCHIVE_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V17.1 기준과 다릅니다.")
    if policy.maximum_archive_entries <= 0:
        errors.append("Archive 보관 한도는 0보다 커야 합니다.")
    for name in (
        "require_same_operator",
        "require_valid_report_hash",
        "require_source_linkage",
        "require_chronological_order",
        "reject_duplicate_report_id",
        "verify_archive_hash_chain",
        "archive_only",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_access_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V17.1에서 True여야 합니다.")
    return errors


def normalize_entries(
    existing: Any,
) -> tuple[SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("Existing Archive는 tuple/list여야 합니다.")
    if not all(
        isinstance(entry, SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry)
        for entry in existing
    ):
        raise TypeError("Existing Archive Entry 형식 오류입니다.")
    return tuple(existing)


def verify_archive_chain(
    entries: tuple[SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry, ...],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    report_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence != expected_sequence:
            errors.append(f"Archive Sequence {expected_sequence} 오류입니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append(f"Sequence {entry.sequence} Previous Hash 오류입니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append(f"Sequence {entry.sequence} Entry Hash 오류입니다.")
        if entry.final_report_id in report_ids:
            errors.append(f"중복 Final Report ID: {entry.final_report_id}")
        report_ids.add(entry.final_report_id)
        try:
            archived_at = datetime.fromisoformat(entry.archived_at)
            if previous_time and archived_at < previous_time:
                errors.append("Archive 기록 시간이 역순입니다.")
            previous_time = archived_at
        except (TypeError, ValueError):
            errors.append("Archive 기록 시간이 올바르지 않습니다.")
        if entry.final_verification_status != "SANDBOX_VERIFICATION_COMPLETE":
            errors.append("Final Verification Status 오류입니다.")
        if any(
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
        ):
            errors.append("Archive Entry 실행 안전장치 오류입니다.")
        previous_hash = entry.entry_hash
    return not errors, errors


def _safe_source(source: SandboxVerificationFinalReportArchiveCertificateAuditFinalReportResult) -> bool:
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


def _result(
    archive_policy: SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy,
    now: datetime,
    status: str,
    entries: tuple[SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry, ...],
    reasons: list[str],
    **checks: bool,
) -> SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveResult:
    latest = entries[-1] if entries else None
    return SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveResult(
        version="V17.1",
        created_at=now.isoformat(),
        archive_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Sandbox Verification Final Report Archive 기록 완료"
            if status == "ARCHIVED_IN_MEMORY"
            else "Verification Report Archive 차단"
            if status == "BLOCKED"
            else "Verification Report Archive 실패"
        ),
        latest_archive_entry_id=(
            latest.archive_entry_id if latest else None
        ),
        latest_archive_entry_hash=latest.entry_hash if latest else None,
        latest_final_report_id=latest.final_report_id if latest else None,
        latest_final_report_hash=latest.final_report_hash if latest else None,
        latest_verification_ledger_snapshot_hash=(
            latest.latest_verification_ledger_snapshot_hash
            if latest else None
        ),
        latest_previous_final_report_hash=(
            latest.previous_final_report_hash if latest else None
        ),
        latest_source_certificate_ledger_snapshot_hash=(
            latest.source_certificate_ledger_snapshot_hash
            if latest else None
        ),
        latest_certificate_ledger_snapshot_hash=(
            latest.certificate_ledger_snapshot_hash if latest else None
        ),
        latest_final_verification_status=(
            latest.final_verification_status if latest else "BLOCKED"
        ),
        total_archive_entry_count=len(entries),
        records_trimmed=0,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        report_hash_checks_passed=checks.get("report_hash", False),
        linkage_checks_passed=checks.get("linkage", False),
        operator_checks_passed=checks.get("operator", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        existing_archive_checks_passed=checks.get("existing", False),
        archive_hash_chain_checks_passed=checks.get("chain", False),
        safety_checks_passed=True,
        all_checks_passed=status == "ARCHIVED_IN_MEMORY",
        archive_entry_recorded=status == "ARCHIVED_IN_MEMORY",
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
        archive_policy=archive_policy,
        entries=entries,
        reasons=reasons,
        warnings=[
            "V17.1은 V17.0 Final Report를 In-Memory Archive에 기록만 합니다.",
            "Archive는 Paper 또는 Live 주문 권한을 부여하지 않습니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "Archive Sequence와 SHA-256 Hash Chain을 확인합니다.",
            "Final Report Hash와 Certificate Ledger Snapshot 연결을 검토합니다.",
        ],
    )


def archive_sandbox_verification_final_report_archive_certificate_audit_final_report(
    source: Any,
    operator: str,
    confirmation_text: str,
    existing: Any = None,
    policy: SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy | None = None,
    now: datetime | None = None,
) -> SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveResult:
    policy = policy or SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy()
    now = now or datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator가 비어 있습니다.")
    if confirmation_text != getattr(policy, "required_confirmation_text", None):
        input_errors.append("수동 확인 문구가 올바르지 않습니다.")
    if policy_errors or input_errors:
        safe_policy = (
            policy
            if isinstance(policy, SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy)
            else SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchivePolicy()
        )
        return _result(
            safe_policy, now, "BLOCKED", (), policy_errors + input_errors,
            policy=not policy_errors, input=not input_errors,
        )
    try:
        entries = normalize_entries(existing)
    except TypeError as error:
        return _result(
            policy, now, "BLOCKED", (), [str(error)], policy=True, input=True
        )
    chain_valid, chain_errors = verify_archive_chain(entries)
    if not chain_valid:
        return _result(
            policy, now, "BLOCKED", entries, chain_errors,
            policy=True, input=True,
        )
    if not isinstance(source, SandboxVerificationFinalReportArchiveCertificateAuditFinalReportResult):
        return _result(
            policy, now, "FAILED", entries,
            ["Source는 V17.0 Sandbox Verification Final Report Result여야 합니다."],
            policy=True, input=True, existing=True, chain=True,
        )
    report = source.report
    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.final_verification_status
        == policy.required_final_verification_status
        and source.all_checks_passed
        and source.final_report_generated
        and not source.source_modified
        and report is not None
    ):
        source_errors.append("정상 V17.0 Verification Final Report가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V17.0 Source 실행 안전장치 오류입니다.")
    if source_errors or report is None:
        return _result(
            policy, now, "FAILED", entries, source_errors,
            policy=True, input=True, existing=True, chain=True,
        )
    report_valid, report_errors = verify_final_report(report)
    if not report_valid:
        return _result(
            policy, now, "FAILED", entries, report_errors,
            policy=True, input=True, source=True, existing=True, chain=True,
        )
    linkage_errors: list[str] = []
    for actual, expected, label in (
        (source.report_id, report.final_report_id, "Final Report ID"),
        (source.report_hash, report.report_hash, "Final Report Hash"),
        (
            source.source_ledger_result_id,
            report.source_ledger_result_id,
            "Source Ledger Result ID",
        ),
        (
            source.source_latest_entry_id,
            report.source_latest_entry_id,
            "Source Latest Entry ID",
        ),
        (
            source.source_latest_entry_hash,
            report.source_latest_entry_hash,
            "Source Latest Entry Hash",
        ),
        (
            source.certificate_ledger_snapshot_hash,
            report.certificate_ledger_snapshot_hash,
            "Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_verification_ledger_snapshot_hash,
            report.latest_verification_ledger_snapshot_hash,
            "Verification Ledger Snapshot Hash",
        ),
        (
            source.latest_previous_final_report_hash,
            report.latest_previous_final_report_hash,
            "Previous Final Report Hash",
        ),
        (
            source.latest_certificate_ledger_snapshot_hash,
            report.latest_certificate_ledger_snapshot_hash,
            "Source Certificate Ledger Snapshot Hash",
        ),
        (
            source.final_verification_status,
            report.final_verification_status,
            "Final Verification Status",
        ),
    ):
        if actual != expected:
            linkage_errors.append(f"Source {label} 연결이 다릅니다.")
    if linkage_errors:
        return _result(
            policy, now, "BLOCKED", entries, linkage_errors,
            policy=True, input=True, source=True, report_hash=True,
            existing=True, chain=True,
        )
    if operator != report.operator:
        return _result(
            policy, now, "BLOCKED", entries,
            ["Operator가 V17.0 Final Report와 다릅니다."],
            policy=True, input=True, source=True, report_hash=True,
            linkage=True, existing=True, chain=True,
        )
    if any(entry.final_report_id == report.final_report_id for entry in entries):
        return _result(
            policy, now, "BLOCKED", entries,
            ["중복 Final Report ID가 차단되었습니다."],
            policy=True, input=True, source=True, report_hash=True,
            linkage=True, operator=True, existing=True, chain=True,
        )
    try:
        if now < datetime.fromisoformat(report.finalized_at) or (
            entries and now < datetime.fromisoformat(entries[-1].archived_at)
        ):
            return _result(
                policy, now, "BLOCKED", entries,
                ["역순 Archive 기록 시간이 차단되었습니다."],
                policy=True, input=True, source=True, report_hash=True,
                linkage=True, operator=True, duplicate=True,
                existing=True, chain=True,
            )
    except (TypeError, ValueError):
        return _result(
            policy, now, "BLOCKED", entries,
            ["Final Report 또는 Archive 시간이 올바르지 않습니다."],
            policy=True, input=True, source=True, report_hash=True,
            linkage=True, operator=True, duplicate=True,
            existing=True, chain=True,
        )
    latest_summary = report.certificate_summaries[-1]
    payload = {
        "archive_entry_id": str(uuid.uuid4()),
        "sequence": len(entries) + 1,
        "archived_at": now.isoformat(),
        "previous_entry_hash": (
            entries[-1].entry_hash if entries else GENESIS_HASH
        ),
        "final_report_result_id": source.final_report_result_id,
        "final_report_id": report.final_report_id,
        "final_report_hash": report.report_hash,
        "source_ledger_result_id": report.source_ledger_result_id,
        "source_latest_entry_id": report.source_latest_entry_id,
        "source_latest_entry_hash": report.source_latest_entry_hash,
        "latest_verification_ledger_snapshot_hash": (
            report.latest_verification_ledger_snapshot_hash
        ),
        "previous_final_report_hash": (
            report.latest_previous_final_report_hash
        ),
        "source_certificate_ledger_snapshot_hash": (
            report.latest_certificate_ledger_snapshot_hash
        ),
        "certificate_ledger_snapshot_hash": (
            report.certificate_ledger_snapshot_hash
        ),
        "latest_verification_certificate_id": (
            latest_summary.verification_certificate_id
        ),
        "latest_verification_certificate_hash": (
            latest_summary.verification_certificate_hash
        ),
        "total_certificate_count": report.total_certificate_count,
        "final_verification_status": report.final_verification_status,
        "operator": operator,
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
    }
    combined = entries + (
        SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry(
            **payload, entry_hash=sha256_payload(payload)
        ),
    )
    trimmed_count = max(0, len(combined) - policy.maximum_archive_entries)
    if trimmed_count:
        kept = combined[-policy.maximum_archive_entries:]
        rebuilt: list[SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry] = []
        previous_hash = GENESIS_HASH
        for sequence, item in enumerate(kept, start=1):
            item_payload = item.payload_without_hash()
            item_payload.update(
                sequence=sequence, previous_entry_hash=previous_hash
            )
            item = SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveEntry(
                **item_payload, entry_hash=sha256_payload(item_payload)
            )
            rebuilt.append(item)
            previous_hash = item.entry_hash
        combined = tuple(rebuilt)
    valid, errors = verify_archive_chain(combined)
    result = _result(
        policy, now, "ARCHIVED_IN_MEMORY" if valid else "FAILED",
        combined,
        [
            f"V17.0 Final Report {report.final_report_id}를 보관했습니다.",
            f"현재 Archive Entry는 {len(combined)}개입니다.",
        ] + errors,
        policy=True, input=True, source=True, report_hash=True,
        linkage=True, operator=True, duplicate=True, chronology=True,
        existing=True, chain=valid,
    )
    result.records_trimmed = trimmed_count
    return result


def save_archive_result(
    result: SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveResult,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report_path = output_directory / (
        f"verification_final_report_archive_certificate_audit_"
        f"final_report_archive_{stamp}.json"
    )
    latest_path = output_directory / (
        "latest_verification_final_report_archive_certificate_audit_"
        "final_report_archive.json"
    )
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_archive_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Verification Final Report Archive JSON은 object여야 합니다.")
    return payload
