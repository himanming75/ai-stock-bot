import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_archive_integrity_audit import (
    SandboxArchiveIntegrityAuditResult,
    verify_audit_certificate,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine" / "sandbox_archive_audit_ledger"
)
REQUIRED_LEDGER_TEXT = "RECORD IN MEMORY SANDBOX ARCHIVE AUDIT"
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class SandboxArchiveAuditLedgerPolicy:
    required_source_version: str = "V15.2"
    required_source_status: str = "AUDITED_IN_MEMORY"
    required_audit_status: str = "PASSED"
    required_confirmation_text: str = REQUIRED_LEDGER_TEXT
    maximum_ledger_entries: int = 100
    require_operator: bool = True
    require_valid_certificate_hash: bool = True
    require_source_linkage: bool = True
    require_chronological_order: bool = True
    reject_duplicate_certificate_id: bool = True
    verify_ledger_hash_chain: bool = True
    ledger_recording_only: bool = True
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
class SandboxArchiveAuditLedgerEntry:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    audit_result_id: str
    audit_certificate_id: str
    audit_certificate_hash: str
    source_archive_result_id: str
    archive_snapshot_hash: str
    audited_entry_count: int
    latest_archive_entry_id: str
    latest_archive_entry_hash: str
    audit_status: str
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
class SandboxArchiveAuditLedgerResult:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    result_status_label: str
    latest_ledger_entry_id: str | None
    latest_ledger_entry_hash: str | None
    latest_audit_certificate_id: str | None
    latest_audit_certificate_hash: str | None
    latest_archive_snapshot_hash: str | None
    total_ledger_entry_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    certificate_hash_checks_passed: bool
    linkage_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    existing_ledger_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    ledger_entry_recorded: bool
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
    ledger_policy: SandboxArchiveAuditLedgerPolicy
    entries: tuple[SandboxArchiveAuditLedgerEntry, ...]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ledger_policy"] = self.ledger_policy.to_dict()
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_policy(policy: SandboxArchiveAuditLedgerPolicy) -> list[str]:
    if not isinstance(policy, SandboxArchiveAuditLedgerPolicy):
        return ["Sandbox Archive Audit Ledger Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V15.2",
        "required_source_status": "AUDITED_IN_MEMORY",
        "required_audit_status": "PASSED",
        "required_confirmation_text": REQUIRED_LEDGER_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V15.3 기준과 다릅니다.")
    if policy.maximum_ledger_entries <= 0:
        errors.append("Audit Ledger 보관 한도는 0보다 커야 합니다.")
    for name in (
        "require_operator",
        "require_valid_certificate_hash",
        "require_source_linkage",
        "require_chronological_order",
        "reject_duplicate_certificate_id",
        "verify_ledger_hash_chain",
        "ledger_recording_only",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_access_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V15.3에서 True여야 합니다.")
    return errors


def normalize_entries(existing: Any) -> tuple[SandboxArchiveAuditLedgerEntry, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("Existing Audit Ledger는 tuple 또는 list여야 합니다.")
    if not all(isinstance(x, SandboxArchiveAuditLedgerEntry) for x in existing):
        raise TypeError("Existing Audit Ledger Entry 형식이 올바르지 않습니다.")
    return tuple(existing)


def verify_audit_ledger_chain(
    entries: tuple[SandboxArchiveAuditLedgerEntry, ...],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence != expected_sequence:
            errors.append(f"Audit Ledger Sequence {expected_sequence} 오류입니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append(f"Sequence {entry.sequence} Previous Hash 오류입니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append(f"Sequence {entry.sequence} Entry Hash 오류입니다.")
        if entry.audit_certificate_id in certificate_ids:
            errors.append(
                f"중복 Audit Certificate ID: {entry.audit_certificate_id}"
            )
        certificate_ids.add(entry.audit_certificate_id)
        try:
            recorded_at = datetime.fromisoformat(entry.recorded_at)
            if previous_time and recorded_at < previous_time:
                errors.append("Audit Ledger 기록 시간이 역순입니다.")
            previous_time = recorded_at
        except (TypeError, ValueError):
            errors.append("Audit Ledger 기록 시간이 올바르지 않습니다.")
        if entry.audit_status != "PASSED":
            errors.append("Audit Ledger Status가 PASSED가 아닙니다.")
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
            errors.append("Audit Ledger Entry 실행 안전장치 오류입니다.")
        previous_hash = entry.entry_hash
    return not errors, errors


def _safe_source(source: SandboxArchiveIntegrityAuditResult) -> bool:
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
    ledger_policy: SandboxArchiveAuditLedgerPolicy,
    now: datetime,
    status: str,
    entries: tuple[SandboxArchiveAuditLedgerEntry, ...],
    reasons: list[str],
    **checks: bool,
) -> SandboxArchiveAuditLedgerResult:
    latest = entries[-1] if entries else None
    return SandboxArchiveAuditLedgerResult(
        version="V15.3",
        created_at=now.isoformat(),
        ledger_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Sandbox Archive Audit Ledger 기록 완료"
            if status == "RECORDED_IN_MEMORY"
            else "Audit Ledger 차단"
            if status == "BLOCKED"
            else "Audit Ledger 실패"
        ),
        latest_ledger_entry_id=latest.ledger_entry_id if latest else None,
        latest_ledger_entry_hash=latest.entry_hash if latest else None,
        latest_audit_certificate_id=(
            latest.audit_certificate_id if latest else None
        ),
        latest_audit_certificate_hash=(
            latest.audit_certificate_hash if latest else None
        ),
        latest_archive_snapshot_hash=(
            latest.archive_snapshot_hash if latest else None
        ),
        total_ledger_entry_count=len(entries),
        records_trimmed=0,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        certificate_hash_checks_passed=checks.get("certificate", False),
        linkage_checks_passed=checks.get("linkage", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        existing_ledger_checks_passed=checks.get("existing", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        safety_checks_passed=True,
        all_checks_passed=status == "RECORDED_IN_MEMORY",
        ledger_entry_recorded=status == "RECORDED_IN_MEMORY",
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
        ledger_policy=ledger_policy,
        entries=entries,
        reasons=reasons,
        warnings=[
            "V15.3은 V15.2 Audit Certificate를 In-Memory Ledger에 기록만 합니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "Audit Ledger Sequence와 SHA-256 Hash Chain을 확인합니다.",
            "Certificate 및 Archive Snapshot Hash 연결을 수동 검토합니다.",
        ],
    )


def record_sandbox_archive_audit(
    source: Any,
    operator: str,
    confirmation_text: str,
    existing: Any = None,
    policy: SandboxArchiveAuditLedgerPolicy | None = None,
    now: datetime | None = None,
) -> SandboxArchiveAuditLedgerResult:
    policy = policy or SandboxArchiveAuditLedgerPolicy()
    now = now or datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator가 비어 있습니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("수동 확인 문구가 올바르지 않습니다.")
    if policy_errors or input_errors:
        return _result(
            policy, now, "BLOCKED", (), policy_errors + input_errors,
            policy=not policy_errors, input=not input_errors,
        )
    try:
        entries = normalize_entries(existing)
    except TypeError as error:
        return _result(
            policy, now, "BLOCKED", (), [str(error)], policy=True, input=True
        )
    chain_valid, chain_errors = verify_audit_ledger_chain(entries)
    if not chain_valid:
        return _result(
            policy, now, "BLOCKED", entries, chain_errors,
            policy=True, input=True,
        )
    if not isinstance(source, SandboxArchiveIntegrityAuditResult):
        return _result(
            policy, now, "FAILED", entries,
            ["Source는 V15.2 Sandbox Archive Integrity Audit Result여야 합니다."],
            policy=True, input=True, existing=True, chain=True,
        )
    certificate = source.certificate
    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.audit_status == policy.required_audit_status
        and source.all_checks_passed
        and source.audit_completed
        and certificate is not None
    ):
        source_errors.append("정상 V15.2 Audit Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V15.2 Source 실행 안전장치가 올바르지 않습니다.")
    if source_errors or certificate is None:
        return _result(
            policy, now, "FAILED", entries, source_errors,
            policy=True, input=True, existing=True, chain=True,
        )
    certificate_valid, certificate_errors = verify_audit_certificate(certificate)
    if not certificate_valid:
        return _result(
            policy, now, "FAILED", entries, certificate_errors,
            policy=True, input=True, source=True, existing=True, chain=True,
        )
    linkage_errors: list[str] = []
    if source.audit_certificate_id != certificate.audit_certificate_id:
        linkage_errors.append("Source Audit Certificate ID 연결이 다릅니다.")
    if source.audit_certificate_hash != certificate.certificate_hash:
        linkage_errors.append("Source Audit Certificate Hash 연결이 다릅니다.")
    if source.source_archive_result_id != certificate.source_archive_result_id:
        linkage_errors.append("Source Archive Result ID 연결이 다릅니다.")
    if source.archive_snapshot_hash != certificate.archive_snapshot_hash:
        linkage_errors.append("Source Archive Snapshot Hash 연결이 다릅니다.")
    if source.audited_entry_count != certificate.total_archive_entry_count:
        linkage_errors.append("Source Audited Entry Count 연결이 다릅니다.")
    if source.latest_archive_entry_id != certificate.latest_archive_entry_id:
        linkage_errors.append("Source Latest Archive Entry ID 연결이 다릅니다.")
    if source.latest_archive_entry_hash != certificate.latest_archive_entry_hash:
        linkage_errors.append("Source Latest Archive Entry Hash 연결이 다릅니다.")
    if linkage_errors:
        return _result(
            policy, now, "BLOCKED", entries, linkage_errors,
            policy=True, input=True, source=True, certificate=True,
            existing=True, chain=True,
        )
    if any(
        x.audit_certificate_id == certificate.audit_certificate_id
        for x in entries
    ):
        return _result(
            policy, now, "BLOCKED", entries,
            ["중복 Audit Certificate ID가 차단되었습니다."],
            policy=True, input=True, source=True, certificate=True,
            linkage=True, existing=True, chain=True,
        )
    try:
        audited_at = datetime.fromisoformat(certificate.audited_at)
        if now < audited_at or (
            entries and now < datetime.fromisoformat(entries[-1].recorded_at)
        ):
            return _result(
                policy, now, "BLOCKED", entries,
                ["역순 Audit Ledger 기록 시간이 차단되었습니다."],
                policy=True, input=True, source=True, certificate=True,
                linkage=True, duplicate=True, existing=True, chain=True,
            )
    except (TypeError, ValueError):
        return _result(
            policy, now, "BLOCKED", entries,
            ["Audit Certificate 또는 Ledger 시간이 올바르지 않습니다."],
            policy=True, input=True, source=True, certificate=True,
            linkage=True, duplicate=True, existing=True, chain=True,
        )
    payload = {
        "ledger_entry_id": str(uuid.uuid4()),
        "sequence": len(entries) + 1,
        "recorded_at": now.isoformat(),
        "previous_entry_hash": (
            entries[-1].entry_hash if entries else GENESIS_HASH
        ),
        "audit_result_id": source.audit_result_id,
        "audit_certificate_id": certificate.audit_certificate_id,
        "audit_certificate_hash": certificate.certificate_hash,
        "source_archive_result_id": certificate.source_archive_result_id,
        "archive_snapshot_hash": certificate.archive_snapshot_hash,
        "audited_entry_count": certificate.total_archive_entry_count,
        "latest_archive_entry_id": certificate.latest_archive_entry_id,
        "latest_archive_entry_hash": certificate.latest_archive_entry_hash,
        "audit_status": certificate.audit_status,
        "operator": operator.strip(),
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
    new_entry = SandboxArchiveAuditLedgerEntry(
        **payload, entry_hash=sha256_payload(payload)
    )
    combined = entries + (new_entry,)
    trimmed_count = max(0, len(combined) - policy.maximum_ledger_entries)
    if trimmed_count:
        kept = combined[-policy.maximum_ledger_entries:]
        rebuilt: list[SandboxArchiveAuditLedgerEntry] = []
        previous_hash = GENESIS_HASH
        for sequence, item in enumerate(kept, start=1):
            item_payload = item.payload_without_hash()
            item_payload.update(sequence=sequence, previous_entry_hash=previous_hash)
            item = SandboxArchiveAuditLedgerEntry(
                **item_payload, entry_hash=sha256_payload(item_payload)
            )
            rebuilt.append(item)
            previous_hash = item.entry_hash
        combined = tuple(rebuilt)
    valid, errors = verify_audit_ledger_chain(combined)
    result = _result(
        policy, now, "RECORDED_IN_MEMORY" if valid else "FAILED",
        combined,
        [
            f"Audit Certificate {certificate.audit_certificate_id}를 기록했습니다.",
            f"현재 Audit Ledger Entry는 {len(combined)}개입니다.",
        ] + errors,
        policy=True, input=True, source=True, certificate=True,
        linkage=True, duplicate=True, chronology=True,
        existing=True, chain=valid,
    )
    result.records_trimmed = trimmed_count
    return result


def save_audit_ledger_result(
    result: SandboxArchiveAuditLedgerResult,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report = output_directory / f"sandbox_archive_audit_ledger_{stamp}.json"
    latest = output_directory / "latest_sandbox_archive_audit_ledger.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_audit_ledger_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Audit Ledger JSON 최상위 값은 object여야 합니다.")
    return payload
