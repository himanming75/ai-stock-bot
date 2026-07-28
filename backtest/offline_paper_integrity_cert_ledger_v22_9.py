import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_integrity_v22_8 import (
    OfflinePaperAuditCertIntegrityV228Result,
    verify_integrity_certificate,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "trading_engine" / "offline_paper_integrity_cert_ledger_v22_9"
CONFIRMATION_TEXT = "RECORD OFFLINE PAPER INTEGRITY CERTIFICATE V22.9"
GENESIS_HASH = "0" * 64


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class OfflinePaperIntegrityCertLedgerV229Policy:
    required_source_version: str = "V22.8"
    required_source_status: str = "AUDITED_IN_MEMORY"
    required_audit_status: str = "PASSED"
    required_confirmation_text: str = CONFIRMATION_TEXT
    maximum_ledger_entries: int = 100
    require_operator: bool = True
    require_valid_certificate_hash: bool = True
    require_source_linkage: bool = True
    require_source_unchanged: bool = True
    require_chronological_order: bool = True
    reject_duplicate_certificate_id: bool = True
    verify_ledger_hash_chain: bool = True
    ledger_recording_only: bool = True
    funds_reservation_disabled: bool = True
    holdings_reservation_disabled: bool = True
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
class OfflinePaperIntegrityCertLedgerV229Entry:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    source_integrity_result_id: str
    source_integrity_certificate_id: str
    source_integrity_certificate_hash: str
    source_audit_certificate_ledger_result_id: str
    source_audit_certificate_ledger_snapshot_hash: str
    latest_source_audit_certificate_hash: str
    audited_entry_count: int
    audit_status: str
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OfflinePaperIntegrityCertLedgerV229Result:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    latest_ledger_entry_id: str | None
    latest_ledger_entry_hash: str | None
    latest_source_integrity_result_id: str | None
    latest_source_integrity_certificate_id: str | None
    latest_source_integrity_certificate_hash: str | None
    latest_source_audit_certificate_ledger_snapshot_hash: str | None
    total_ledger_entry_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    certificate_hash_checks_passed: bool
    linkage_checks_passed: bool
    source_unchanged_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    existing_ledger_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    ledger_entry_recorded: bool
    ledger_modified: bool
    funds_reserved: bool
    holdings_reserved: bool
    execution_blocked: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    ledger_policy: OfflinePaperIntegrityCertLedgerV229Policy
    entries: tuple[OfflinePaperIntegrityCertLedgerV229Entry, ...]
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        payload["ledger_policy"] = self.ledger_policy.to_dict()
        return payload


def validate_policy(policy: OfflinePaperIntegrityCertLedgerV229Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperIntegrityCertLedgerV229Policy):
        return ["V22.9 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V22.8":
        errors.append("V22.9 Source Version은 V22.8이어야 합니다.")
    if policy.required_source_status != "AUDITED_IN_MEMORY":
        errors.append("V22.9 Source Status 정책 오류입니다.")
    if policy.required_audit_status != "PASSED":
        errors.append("V22.9 Audit Status 정책 오류입니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V22.9 확인 문구 정책 오류입니다.")
    if (
        isinstance(policy.maximum_ledger_entries, bool)
        or not isinstance(policy.maximum_ledger_entries, int)
        or policy.maximum_ledger_entries <= 0
    ):
        errors.append("V22.9 Ledger 보관 한도는 양의 정수여야 합니다.")
    for name, value in policy.to_dict().items():
        if name.startswith(("require_", "reject_", "verify_", "ledger_")) or name.endswith("_disabled"):
            if value is not True:
                errors.append(f"{name}는 V22.9에서 True여야 합니다.")
    return errors


def normalize_entries(existing: Any) -> tuple[OfflinePaperIntegrityCertLedgerV229Entry, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("V22.9 Existing Ledger는 tuple/list여야 합니다.")
    if not all(isinstance(item, OfflinePaperIntegrityCertLedgerV229Entry) for item in existing):
        raise TypeError("V22.9 Existing Ledger Entry 형식 오류입니다.")
    return tuple(existing)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _safe_entry(entry: OfflinePaperIntegrityCertLedgerV229Entry) -> bool:
    return bool(
        entry.execution_blocked
        and not entry.funds_reserved
        and not entry.holdings_reserved
        and not entry.market_data_api_called
        and not entry.account_api_called
        and not entry.network_accessed
        and not entry.broker_api_called
        and not entry.broker_order_created
        and not entry.order_submitted
        and not entry.live_execution_authorized
    )


def _safe_source(source: OfflinePaperAuditCertIntegrityV228Result) -> bool:
    return bool(
        source.execution_blocked
        and not source.ledger_modified
        and not source.funds_reserved
        and not source.holdings_reserved
        and not source.market_data_api_called
        and not source.account_api_called
        and not source.network_accessed
        and not source.broker_api_called
        and not source.broker_order_created
        and not source.order_submitted
        and not source.live_execution_authorized
    )


def verify_ledger_chain(
    entries: tuple[OfflinePaperIntegrityCertLedgerV229Entry, ...],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected, entry in enumerate(entries, start=1):
        if entry.sequence != expected:
            errors.append(f"V22.9 Sequence {expected} 오류입니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append(f"V22.9 Sequence {entry.sequence} Previous Hash 오류입니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append(f"V22.9 Sequence {entry.sequence} Entry Hash 오류입니다.")
        if entry.source_integrity_certificate_id in certificate_ids:
            errors.append("V22.9 중복 Integrity Certificate ID입니다.")
        certificate_ids.add(entry.source_integrity_certificate_id)
        try:
            current = _parse_time(entry.recorded_at)
            if previous_time and current < previous_time:
                errors.append("V22.9 Ledger 시간이 역순입니다.")
            previous_time = current
        except (TypeError, ValueError):
            errors.append("V22.9 Ledger 시간이 올바르지 않습니다.")
        if entry.audit_status != "PASSED" or not _safe_entry(entry):
            errors.append("V22.9 Ledger Entry 안전성 오류입니다.")
        previous_hash = entry.entry_hash
    return not errors, errors


def ledger_snapshot_hash(entries: tuple[OfflinePaperIntegrityCertLedgerV229Entry, ...]) -> str:
    return sha256_payload([entry.to_dict() for entry in entries])


def _result(
    policy: OfflinePaperIntegrityCertLedgerV229Policy,
    now: datetime,
    status: str,
    entries: tuple[OfflinePaperIntegrityCertLedgerV229Entry, ...],
    reasons: list[str],
    trimmed: int = 0,
    **checks: bool,
) -> OfflinePaperIntegrityCertLedgerV229Result:
    latest = entries[-1] if entries else None
    passed = status == "RECORDED_IN_MEMORY"
    return OfflinePaperIntegrityCertLedgerV229Result(
        version="V22.9", created_at=now.isoformat(), ledger_result_id=str(uuid.uuid4()),
        result_status=status,
        latest_ledger_entry_id=latest.ledger_entry_id if latest else None,
        latest_ledger_entry_hash=latest.entry_hash if latest else None,
        latest_source_integrity_result_id=latest.source_integrity_result_id if latest else None,
        latest_source_integrity_certificate_id=latest.source_integrity_certificate_id if latest else None,
        latest_source_integrity_certificate_hash=latest.source_integrity_certificate_hash if latest else None,
        latest_source_audit_certificate_ledger_snapshot_hash=(
            latest.source_audit_certificate_ledger_snapshot_hash if latest else None
        ),
        total_ledger_entry_count=len(entries), records_trimmed=trimmed,
        policy_checks_passed=checks["policy_check"] if "policy_check" in checks else False,
        input_checks_passed=checks["input"] if "input" in checks else False,
        source_checks_passed=checks["source"] if "source" in checks else False,
        certificate_hash_checks_passed=checks["certificate"] if "certificate" in checks else False,
        linkage_checks_passed=checks["linkage"] if "linkage" in checks else False,
        source_unchanged_checks_passed=checks["unchanged"] if "unchanged" in checks else False,
        duplicate_checks_passed=checks["duplicate"] if "duplicate" in checks else False,
        chronology_checks_passed=checks["chronology"] if "chronology" in checks else False,
        existing_ledger_checks_passed=checks["existing"] if "existing" in checks else False,
        ledger_hash_chain_checks_passed=checks["chain"] if "chain" in checks else False,
        safety_checks_passed=True, all_checks_passed=passed,
        ledger_entry_recorded=passed, ledger_modified=False,
        funds_reserved=False, holdings_reserved=False, execution_blocked=True,
        market_data_api_called=False, account_api_called=False, network_accessed=False,
        broker_api_called=False, broker_order_created=False, order_submitted=False,
        live_execution_authorized=False, ledger_policy=policy, entries=entries,
        reasons=reasons,
    )


def _rebuild(entries: tuple[OfflinePaperIntegrityCertLedgerV229Entry, ...]) -> tuple[OfflinePaperIntegrityCertLedgerV229Entry, ...]:
    rebuilt = []
    previous = GENESIS_HASH
    for sequence, old in enumerate(entries, start=1):
        payload = old.payload_without_hash()
        payload.update(sequence=sequence, previous_entry_hash=previous)
        entry = OfflinePaperIntegrityCertLedgerV229Entry(**payload, entry_hash=sha256_payload(payload))
        rebuilt.append(entry)
        previous = entry.entry_hash
    return tuple(rebuilt)


def record_offline_paper_integrity_certificate_v22_9(
    source: OfflinePaperAuditCertIntegrityV228Result,
    *,
    operator: str,
    confirmation_text: str,
    existing: Any = None,
    policy: OfflinePaperIntegrityCertLedgerV229Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperIntegrityCertLedgerV229Result:
    selected = policy or OfflinePaperIntegrityCertLedgerV229Policy()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors = validate_policy(selected)
    input_ok = isinstance(operator, str) and bool(operator.strip()) and confirmation_text == CONFIRMATION_TEXT
    if not isinstance(operator, str) or not operator.strip():
        errors.append("V22.9 Operator가 필요합니다.")
    if confirmation_text != CONFIRMATION_TEXT:
        errors.append("V22.9 확인 문구가 일치하지 않습니다.")
    try:
        entries = normalize_entries(existing)
    except TypeError as exc:
        errors.append(str(exc))
        entries = ()
    existing_ok, existing_errors = verify_ledger_chain(entries)
    if entries and not existing_ok:
        errors.extend(existing_errors)
    if not isinstance(source, OfflinePaperAuditCertIntegrityV228Result):
        return _result(selected, current, "FAILED", entries, errors + ["Source는 V22.8 Result여야 합니다."])
    before = source.to_dict()
    certificate_ok, certificate_errors = verify_integrity_certificate(source.certificate)
    if source.version != "V22.8" or source.result_status != "AUDITED_IN_MEMORY" or not source.all_checks_passed:
        errors.append("V22.8 Source 상태 오류입니다.")
    if not certificate_ok:
        errors.extend(certificate_errors)
    source_safe = _safe_source(source)
    if not source_safe:
        errors.append("V22.8 Source 실행 안전성 오류입니다.")
    linkage_ok = bool(
        source.certificate
        and source.integrity_certificate_id == source.certificate.integrity_certificate_id
        and source.integrity_certificate_hash == source.certificate.certificate_hash
        and source.source_ledger_result_id == source.certificate.source_ledger_result_id
        and source.source_ledger_snapshot_hash == source.certificate.source_ledger_snapshot_hash
    )
    if not linkage_ok:
        errors.append("V22.8 Source 연결 Hash 오류입니다.")
    duplicate_ok = bool(
        source.integrity_certificate_id
        and all(
            entry.source_integrity_certificate_id != source.integrity_certificate_id
            for entry in entries
        )
    )
    if not duplicate_ok:
        errors.append("V22.8 Integrity Certificate가 이미 기록되었습니다.")
    chronology_ok = not entries or current >= _parse_time(entries[-1].recorded_at)
    if not chronology_ok:
        errors.append("V22.9 기록 시간이 역순입니다.")
    if source.certificate and current < _parse_time(source.certificate.audited_at):
        errors.append("V22.9 기록 시간이 감사 시간보다 빠릅니다.")
        chronology_ok = False
    if errors:
        status = "FAILED" if not certificate_ok else "BLOCKED"
        return _result(
            selected, current, status, entries, errors,
            policy_check=not validate_policy(selected), input=input_ok, source=source.all_checks_passed,
            certificate=certificate_ok, linkage=linkage_ok, unchanged=source.to_dict() == before,
            duplicate=duplicate_ok, chronology=chronology_ok, existing=existing_ok, chain=existing_ok,
        )
    payload = {
        "ledger_entry_id": str(uuid.uuid4()), "sequence": len(entries) + 1,
        "recorded_at": current.isoformat(),
        "previous_entry_hash": entries[-1].entry_hash if entries else GENESIS_HASH,
        "source_integrity_result_id": source.audit_result_id,
        "source_integrity_certificate_id": source.integrity_certificate_id,
        "source_integrity_certificate_hash": source.integrity_certificate_hash,
        "source_audit_certificate_ledger_result_id": source.source_ledger_result_id,
        "source_audit_certificate_ledger_snapshot_hash": source.source_ledger_snapshot_hash,
        "latest_source_audit_certificate_hash": (
            source.certificate.latest_source_audit_certificate_hash
        ),
        "audited_entry_count": source.audited_entry_count, "audit_status": "PASSED",
        "operator": operator.strip(), "execution_blocked": True,
        "funds_reserved": False, "holdings_reserved": False,
        "market_data_api_called": False, "account_api_called": False,
        "network_accessed": False, "broker_api_called": False,
        "broker_order_created": False, "order_submitted": False,
        "live_execution_authorized": False,
    }
    entry = OfflinePaperIntegrityCertLedgerV229Entry(**payload, entry_hash=sha256_payload(payload))
    recorded_entries = entries + (entry,)
    trimmed = max(0, len(recorded_entries) - selected.maximum_ledger_entries)
    if trimmed:
        recorded_entries = _rebuild(recorded_entries[trimmed:])
    chain_ok, chain_errors = verify_ledger_chain(recorded_entries)
    unchanged = source.to_dict() == before
    if not chain_ok or not unchanged:
        return _result(selected, current, "FAILED", entries, chain_errors + ["Source 변경 감지"])
    return _result(
        selected, current, "RECORDED_IN_MEMORY", recorded_entries,
        ["V22.8 Integrity Certificate가 Offline Ledger에 기록되었습니다."], trimmed,
        policy_check=True, input=True, source=True, certificate=True, linkage=True,
        unchanged=True, duplicate=True, chronology=True, existing=True, chain=True,
    )


def save_result(
    result: OfflinePaperIntegrityCertLedgerV229Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report = output_directory / f"ledger_{stamp}.json"
    latest = output_directory / "latest_ledger.json"
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path, result.latest_path = str(report), str(latest)
    return report, latest


def load_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V22.9 Ledger JSON은 object여야 합니다.")
    return payload
