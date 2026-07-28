import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from backtest.offline_paper_audit_cert_ledger_v21_5 import sha256_payload
from backtest.offline_paper_verify_cert_audit_ledger_verify_v22_4 import (
    OfflinePaperVerifyCertAuditLedgerVerifyV224Result,
    verify_verification_certificate,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine" / "offline_paper_audit_verify_cert_ledger_v22_5"
)
CONFIRMATION_TEXT = "RECORD OFFLINE PAPER AUDIT VERIFICATION CERTIFICATE V22.5"
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class OfflinePaperAuditVerifyCertLedgerV225Policy:
    required_source_version: str = "V22.4"
    required_source_status: str = "VERIFIED_IN_MEMORY"
    required_confirmation_text: str = CONFIRMATION_TEXT
    maximum_ledger_entries: int = 100
    require_operator: bool = True
    reject_duplicate_certificate_id: bool = True
    require_chronological_order: bool = True
    require_source_unchanged: bool = True
    verify_certificate_hash: bool = True
    verify_ledger_hash_chain: bool = True
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
class OfflinePaperAuditVerifyCertLedgerV225Entry:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    source_verification_result_id: str
    source_verification_certificate_id: str
    source_verification_certificate_hash: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_final_report_hash: str
    source_v21_0_account_hash: str
    source_v21_1_order_hash: str
    operator: str
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
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OfflinePaperAuditVerifyCertLedgerV225Result:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    total_ledger_entry_count: int
    latest_ledger_entry_id: str | None
    latest_ledger_entry_hash: str | None
    latest_source_verification_certificate_hash: str | None
    ledger_snapshot_hash: str
    policy_checks_passed: bool
    source_checks_passed: bool
    certificate_hash_checks_passed: bool
    source_linkage_checks_passed: bool
    source_unchanged_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    certificate_recorded: bool
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
    ledger_policy: OfflinePaperAuditVerifyCertLedgerV225Policy
    entries: tuple[OfflinePaperAuditVerifyCertLedgerV225Entry, ...]
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ledger_policy"] = self.ledger_policy.to_dict()
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def validate_policy(policy: OfflinePaperAuditVerifyCertLedgerV225Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperAuditVerifyCertLedgerV225Policy):
        return ["V22.5 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V22.4":
        errors.append("V22.5 Source Version은 V22.4여야 합니다.")
    if policy.required_source_status != "VERIFIED_IN_MEMORY":
        errors.append("V22.5 Source Status가 올바르지 않습니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V22.5 확인 문구 정책이 올바르지 않습니다.")
    if (
        isinstance(policy.maximum_ledger_entries, bool)
        or not isinstance(policy.maximum_ledger_entries, int)
        or policy.maximum_ledger_entries <= 0
    ):
        errors.append("V22.5 Ledger 보관 한도는 양의 정수여야 합니다.")
    for name, value in policy.to_dict().items():
        if name.startswith(("require_", "reject_", "verify_")) or name.endswith("_disabled"):
            if value is not True:
                errors.append(f"{name}는 V22.5에서 True여야 합니다.")
    return errors


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def ledger_snapshot_hash(
    entries: Iterable[OfflinePaperAuditVerifyCertLedgerV225Entry],
) -> str:
    return sha256_payload([entry.to_dict() for entry in entries])


def verify_ledger_chain(
    entries: Iterable[OfflinePaperAuditVerifyCertLedgerV225Entry],
) -> tuple[bool, list[str]]:
    normalized = tuple(entries)
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    seen_ids: set[str] = set()
    for expected_sequence, entry in enumerate(normalized, start=1):
        if not isinstance(entry, OfflinePaperAuditVerifyCertLedgerV225Entry):
            errors.append("V22.5 Ledger Entry 형식 오류입니다.")
            continue
        if entry.sequence != expected_sequence:
            errors.append("V22.5 Ledger Sequence 오류입니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append("V22.5 Ledger Hash 연결 오류입니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append("V22.5 Ledger Entry Hash 오류입니다.")
        if entry.source_verification_certificate_id in seen_ids:
            errors.append("V22.5 중복 Certificate ID입니다.")
        seen_ids.add(entry.source_verification_certificate_id)
        try:
            current_time = _parse_time(entry.recorded_at)
            if previous_time is not None and current_time < previous_time:
                errors.append("V22.5 Ledger 시간이 역순입니다.")
            previous_time = current_time
        except (TypeError, ValueError):
            errors.append("V22.5 Ledger 시간 형식 오류입니다.")
        if (
            entry.funds_reserved
            or entry.holdings_reserved
            or not entry.execution_blocked
            or entry.market_data_api_called
            or entry.account_api_called
            or entry.network_accessed
            or entry.broker_api_called
            or entry.broker_order_created
            or entry.order_submitted
            or entry.live_execution_authorized
        ):
            errors.append("V22.5 Ledger 실행 안전장치 오류입니다.")
        previous_hash = entry.entry_hash
    return not errors, errors


def _safe_source(source: OfflinePaperVerifyCertAuditLedgerVerifyV224Result) -> bool:
    return bool(
        source.all_checks_passed
        and source.execution_blocked
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


def _failed_result(
    policy: OfflinePaperAuditVerifyCertLedgerV225Policy,
    entries: tuple[OfflinePaperAuditVerifyCertLedgerV225Entry, ...],
    now: datetime,
    reasons: list[str],
) -> OfflinePaperAuditVerifyCertLedgerV225Result:
    latest = entries[-1] if entries else None
    return OfflinePaperAuditVerifyCertLedgerV225Result(
        version="V22.5",
        created_at=now.astimezone(timezone.utc).isoformat(),
        ledger_result_id=str(uuid.uuid4()),
        result_status="BLOCKED",
        total_ledger_entry_count=len(entries),
        latest_ledger_entry_id=latest.ledger_entry_id if latest else None,
        latest_ledger_entry_hash=latest.entry_hash if latest else None,
        latest_source_verification_certificate_hash=(
            latest.source_verification_certificate_hash if latest else None
        ),
        ledger_snapshot_hash=ledger_snapshot_hash(entries),
        policy_checks_passed=not validate_policy(policy),
        source_checks_passed=False,
        certificate_hash_checks_passed=False,
        source_linkage_checks_passed=False,
        source_unchanged_checks_passed=False,
        duplicate_checks_passed=False,
        chronology_checks_passed=False,
        ledger_hash_chain_checks_passed=False,
        safety_checks_passed=True,
        all_checks_passed=False,
        certificate_recorded=False,
        funds_reserved=False,
        holdings_reserved=False,
        execution_blocked=True,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_execution_authorized=False,
        ledger_policy=policy,
        entries=entries,
        reasons=reasons,
    )


def record_offline_paper_audit_verification_certificate_v22_5(
    source: OfflinePaperVerifyCertAuditLedgerVerifyV224Result,
    *,
    operator: str,
    confirmation_text: str,
    existing_entries: Iterable[OfflinePaperAuditVerifyCertLedgerV225Entry] = (),
    policy: OfflinePaperAuditVerifyCertLedgerV225Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperAuditVerifyCertLedgerV225Result:
    selected_policy = policy or OfflinePaperAuditVerifyCertLedgerV225Policy()
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        entries = tuple(existing_entries)
    except TypeError:
        entries = ()
        return _failed_result(
            selected_policy, entries, current_time, ["Existing Ledger 형식 오류입니다."]
        )

    errors = validate_policy(selected_policy)
    chain_valid, chain_errors = verify_ledger_chain(entries)
    errors.extend(chain_errors)
    if not isinstance(operator, str) or not operator.strip():
        errors.append("V22.5 Operator가 필요합니다.")
    if confirmation_text != CONFIRMATION_TEXT:
        errors.append("V22.5 확인 문구가 일치하지 않습니다.")
    if not isinstance(source, OfflinePaperVerifyCertAuditLedgerVerifyV224Result):
        errors.append("Source는 V22.4 Integrity Verification Result여야 합니다.")
        return _failed_result(selected_policy, entries, current_time, errors)

    source_before = source.to_dict()
    if source.version != selected_policy.required_source_version:
        errors.append("V22.4 Source Version 오류입니다.")
    if source.result_status != selected_policy.required_source_status:
        errors.append("V22.4 Source Status 오류입니다.")
    if not _safe_source(source):
        errors.append("V22.4 Source 실행 안전장치 오류입니다.")
    if source.certificate is None:
        errors.append("V22.4 Verification Certificate가 없습니다.")
    elif not verify_verification_certificate(source.certificate)[0]:
        errors.append("V22.4 Verification Certificate Hash 오류입니다.")
    if source.verification_certificate_id is None or source.verification_certificate_hash is None:
        errors.append("V22.4 Verification Certificate Linkage 오류입니다.")
    if any(
        entry.source_verification_certificate_id == source.verification_certificate_id
        for entry in entries
    ):
        errors.append("중복 V22.4 Verification Certificate가 차단되었습니다.")
    if entries and current_time < _parse_time(entries[-1].recorded_at):
        errors.append("역순 V22.5 Ledger 시간이 차단되었습니다.")
    if not chain_valid:
        errors.append("Existing V22.5 Ledger 검증 실패입니다.")
    if errors:
        return _failed_result(selected_policy, entries, current_time, errors)

    previous_hash = entries[-1].entry_hash if entries else GENESIS_HASH
    payload = {
        "ledger_entry_id": str(uuid.uuid4()),
        "sequence": len(entries) + 1,
        "recorded_at": current_time.isoformat(),
        "previous_entry_hash": previous_hash,
        "source_verification_result_id": source.verification_result_id,
        "source_verification_certificate_id": source.verification_certificate_id,
        "source_verification_certificate_hash": source.verification_certificate_hash,
        "source_ledger_result_id": source.source_ledger_result_id,
        "source_ledger_snapshot_hash": source.verification_certificate_ledger_snapshot_hash,
        "source_final_report_hash": source.latest_verification_certificate_hash,
        "source_v21_0_account_hash": source.latest_v21_0_account_hash,
        "source_v21_1_order_hash": source.latest_v21_1_order_hash,
        "operator": operator.strip(),
        "funds_reserved": False,
        "holdings_reserved": False,
        "execution_blocked": True,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "broker_order_created": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    entry = OfflinePaperAuditVerifyCertLedgerV225Entry(
        **payload, entry_hash=sha256_payload(payload)
    )
    combined = (*entries, entry)
    if len(combined) > selected_policy.maximum_ledger_entries:
        combined = combined[-selected_policy.maximum_ledger_entries :]
    final_chain_valid, final_chain_errors = verify_ledger_chain(combined)
    if source.to_dict() != source_before:
        return _failed_result(
            selected_policy, entries, current_time, ["V22.4 Source가 변경되었습니다."]
        )
    if not final_chain_valid:
        return _failed_result(selected_policy, entries, current_time, final_chain_errors)

    return OfflinePaperAuditVerifyCertLedgerV225Result(
        version="V22.5",
        created_at=current_time.isoformat(),
        ledger_result_id=str(uuid.uuid4()),
        result_status="RECORDED_IN_MEMORY",
        total_ledger_entry_count=len(combined),
        latest_ledger_entry_id=entry.ledger_entry_id,
        latest_ledger_entry_hash=entry.entry_hash,
        latest_source_verification_certificate_hash=source.verification_certificate_hash,
        ledger_snapshot_hash=ledger_snapshot_hash(combined),
        policy_checks_passed=True,
        source_checks_passed=True,
        certificate_hash_checks_passed=True,
        source_linkage_checks_passed=True,
        source_unchanged_checks_passed=True,
        duplicate_checks_passed=True,
        chronology_checks_passed=True,
        ledger_hash_chain_checks_passed=True,
        safety_checks_passed=True,
        all_checks_passed=True,
        certificate_recorded=True,
        funds_reserved=False,
        holdings_reserved=False,
        execution_blocked=True,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_execution_authorized=False,
        ledger_policy=selected_policy,
        entries=combined,
        reasons=[
            "V22.4 Verification Certificate가 In-Memory Ledger에 기록되었습니다.",
            "실제 계좌·Network·Broker 주문·Live Execution은 차단되었습니다.",
        ],
    )


def save_result(
    result: OfflinePaperAuditVerifyCertLedgerV225Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report_path = output_directory / f"audit_verify_cert_ledger_{stamp}.json"
    latest_path = output_directory / "latest_audit_verify_cert_ledger.json"
    payload = result.to_dict()
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V22.5 Ledger JSON은 object여야 합니다.")
    return payload
