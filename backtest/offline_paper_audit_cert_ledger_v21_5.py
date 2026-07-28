import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_order_ledger_audit_v21_4 import (
    OfflinePaperOrderLedgerAuditV214Result,
    verify_audit_certificate,
)
from backtest.offline_paper_trading_account_v21_0 import canonical_json


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "offline_paper_audit_cert_ledger_v21_5"
)
REQUIRED_LEDGER_TEXT = "RECORD OFFLINE PAPER LEDGER AUDIT CERTIFICATE V21.5"
GENESIS_HASH = "0" * 64


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
class OfflinePaperAuditCertLedgerV215Policy:
    required_source_version: str = "V21.4"
    required_source_status: str = "AUDITED_IN_MEMORY"
    required_audit_status: str = "PASSED"
    required_confirmation_text: str = REQUIRED_LEDGER_TEXT
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
class OfflinePaperAuditCertLedgerV215Entry:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    audit_result_id: str
    audit_certificate_id: str
    audit_certificate_hash: str
    source_validation_ledger_result_id: str
    ledger_snapshot_hash: str
    audited_entry_count: int
    latest_validation_ledger_entry_id: str
    latest_validation_ledger_entry_hash: str
    latest_validation_result_id: str
    latest_validation_certificate_id: str
    latest_validation_certificate_hash: str
    latest_paper_order_id: str
    latest_order_hash: str
    latest_account_id: str
    latest_account_hash: str
    audit_status: str
    operator: str
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
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["entry_hash"] = self.entry_hash
        return payload


@dataclass
class OfflinePaperAuditCertLedgerV215Result:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    result_status_label: str
    latest_ledger_entry_id: str | None
    latest_ledger_entry_hash: str | None
    latest_audit_result_id: str | None
    latest_audit_certificate_id: str | None
    latest_audit_certificate_hash: str | None
    latest_source_validation_ledger_result_id: str | None
    latest_ledger_snapshot_hash: str | None
    latest_validation_ledger_entry_id: str | None
    latest_validation_ledger_entry_hash: str | None
    latest_validation_certificate_hash: str | None
    latest_order_hash: str | None
    latest_account_hash: str | None
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
    ledger_policy: OfflinePaperAuditCertLedgerV215Policy
    entries: tuple[OfflinePaperAuditCertLedgerV215Entry, ...]
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


def validate_policy(policy: OfflinePaperAuditCertLedgerV215Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperAuditCertLedgerV215Policy):
        return ["Offline Paper Audit Certificate Ledger Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V21.4",
        "required_source_status": "AUDITED_IN_MEMORY",
        "required_audit_status": "PASSED",
        "required_confirmation_text": REQUIRED_LEDGER_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V21.5 기준과 다릅니다.")
    if (
        isinstance(policy.maximum_ledger_entries, bool)
        or not isinstance(policy.maximum_ledger_entries, int)
        or policy.maximum_ledger_entries <= 0
    ):
        errors.append("Audit Certificate Ledger 보관 한도는 양의 정수여야 합니다.")
    for name in (
        "require_operator",
        "require_valid_certificate_hash",
        "require_source_linkage",
        "require_source_unchanged",
        "require_chronological_order",
        "reject_duplicate_certificate_id",
        "verify_ledger_hash_chain",
        "ledger_recording_only",
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
            errors.append(f"{name}는 V21.5에서 True여야 합니다.")
    return errors


def normalize_entries(
    existing: Any,
) -> tuple[OfflinePaperAuditCertLedgerV215Entry, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("Existing Audit Certificate Ledger는 tuple/list여야 합니다.")
    if not all(
        isinstance(entry, OfflinePaperAuditCertLedgerV215Entry)
        for entry in existing
    ):
        raise TypeError("Existing Audit Certificate Ledger Entry 형식 오류입니다.")
    return tuple(existing)


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


def _safe_source(source: OfflinePaperOrderLedgerAuditV214Result) -> bool:
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


def verify_audit_cert_ledger_chain(
    entries: tuple[OfflinePaperAuditCertLedgerV215Entry, ...],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence != expected_sequence:
            errors.append(f"Audit Certificate Ledger Sequence {expected_sequence} 오류입니다.")
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
            if recorded_at.tzinfo is None:
                raise ValueError
            if previous_time and recorded_at < previous_time:
                errors.append("Audit Certificate Ledger 기록 시간이 역순입니다.")
            previous_time = recorded_at
        except (TypeError, ValueError):
            errors.append("Audit Certificate Ledger 기록 시간이 올바르지 않습니다.")
        if entry.audit_status != "PASSED":
            errors.append("Audit Certificate Ledger Status 오류입니다.")
        if not _safe_entry(entry):
            errors.append("Audit Certificate Ledger Entry 실행 안전장치 오류입니다.")
        previous_hash = entry.entry_hash
    return not errors, errors


def _result(
    ledger_policy: OfflinePaperAuditCertLedgerV215Policy,
    now: datetime,
    status: str,
    entries: tuple[OfflinePaperAuditCertLedgerV215Entry, ...],
    reasons: list[str],
    **checks: bool,
) -> OfflinePaperAuditCertLedgerV215Result:
    latest = entries[-1] if entries else None
    recorded = status == "RECORDED_IN_MEMORY"
    return OfflinePaperAuditCertLedgerV215Result(
        version="V21.5",
        created_at=now.isoformat(),
        ledger_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Offline Paper Order Ledger Audit Certificate 기록 완료"
            if recorded
            else "Offline Paper Order Ledger Audit Certificate Ledger 차단"
            if status == "BLOCKED"
            else "Offline Paper Order Ledger Audit Certificate Ledger 실패"
        ),
        latest_ledger_entry_id=latest.ledger_entry_id if latest else None,
        latest_ledger_entry_hash=latest.entry_hash if latest else None,
        latest_audit_result_id=latest.audit_result_id if latest else None,
        latest_audit_certificate_id=(
            latest.audit_certificate_id if latest else None
        ),
        latest_audit_certificate_hash=(
            latest.audit_certificate_hash if latest else None
        ),
        latest_source_validation_ledger_result_id=(
            latest.source_validation_ledger_result_id if latest else None
        ),
        latest_ledger_snapshot_hash=(
            latest.ledger_snapshot_hash if latest else None
        ),
        latest_validation_ledger_entry_id=(
            latest.latest_validation_ledger_entry_id if latest else None
        ),
        latest_validation_ledger_entry_hash=(
            latest.latest_validation_ledger_entry_hash if latest else None
        ),
        latest_validation_certificate_hash=(
            latest.latest_validation_certificate_hash if latest else None
        ),
        latest_order_hash=latest.latest_order_hash if latest else None,
        latest_account_hash=latest.latest_account_hash if latest else None,
        total_ledger_entry_count=len(entries),
        records_trimmed=0,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        certificate_hash_checks_passed=checks.get("certificate", False),
        linkage_checks_passed=checks.get("linkage", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        existing_ledger_checks_passed=checks.get("existing", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        safety_checks_passed=True,
        all_checks_passed=recorded,
        ledger_entry_recorded=recorded,
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
        ledger_policy=ledger_policy,
        entries=entries,
        reasons=reasons,
        warnings=[
            "V21.5는 V21.4 Audit Certificate를 In-Memory Ledger에 기록합니다.",
            "Ledger 기록은 주문 체결 또는 Broker 전송 승인을 의미하지 않습니다.",
            "잔액·보유수량 변경, 시세·계좌 API, Network 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "V21.6 Audit Certificate Ledger Integrity Audit 단계에서 "
            "Ledger Chain을 읽기 전용으로 감사합니다."
        ],
    )


def _source_linkage(
    source: OfflinePaperOrderLedgerAuditV214Result,
) -> list[str]:
    certificate = source.certificate
    if certificate is None:
        return ["V21.4 Audit Certificate가 없습니다."]
    errors: list[str] = []
    for actual, expected, label in (
        (
            source.audit_certificate_id,
            certificate.audit_certificate_id,
            "Audit Certificate ID",
        ),
        (
            source.audit_certificate_hash,
            certificate.certificate_hash,
            "Audit Certificate Hash",
        ),
        (
            source.source_ledger_result_id,
            certificate.source_ledger_result_id,
            "Source Validation Ledger Result ID",
        ),
        (
            source.ledger_snapshot_hash,
            certificate.ledger_snapshot_hash,
            "Ledger Snapshot Hash",
        ),
        (
            source.audited_entry_count,
            certificate.total_ledger_entry_count,
            "Audited Entry Count",
        ),
        (
            source.latest_ledger_entry_id,
            certificate.latest_ledger_entry_id,
            "Latest Validation Ledger Entry ID",
        ),
        (
            source.latest_ledger_entry_hash,
            certificate.latest_ledger_entry_hash,
            "Latest Validation Ledger Entry Hash",
        ),
        (
            source.latest_validation_result_id,
            certificate.latest_validation_result_id,
            "Validation Result ID",
        ),
        (
            source.latest_validation_certificate_id,
            certificate.latest_validation_certificate_id,
            "Validation Certificate ID",
        ),
        (
            source.latest_validation_certificate_hash,
            certificate.latest_validation_certificate_hash,
            "Validation Certificate Hash",
        ),
        (
            source.latest_paper_order_id,
            certificate.latest_paper_order_id,
            "Paper Order ID",
        ),
        (source.latest_order_hash, certificate.latest_order_hash, "Order Hash"),
        (
            source.latest_account_id,
            certificate.latest_account_id,
            "Account ID",
        ),
        (
            source.latest_account_hash,
            certificate.latest_account_hash,
            "Account Hash",
        ),
    ):
        if actual != expected:
            errors.append(f"Source {label} 연결이 다릅니다.")
    return errors


def record_offline_paper_audit_certificate_v21_5(
    source: Any,
    operator: Any,
    confirmation_text: Any,
    existing: Any = None,
    policy: OfflinePaperAuditCertLedgerV215Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperAuditCertLedgerV215Result:
    policy = policy or OfflinePaperAuditCertLedgerV215Policy()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        now = datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    if confirmation_text != getattr(policy, "required_confirmation_text", None):
        input_errors.append("V21.5 확인 문구가 일치하지 않습니다.")
    if policy_errors or input_errors:
        safe_policy = (
            policy
            if isinstance(policy, OfflinePaperAuditCertLedgerV215Policy)
            else OfflinePaperAuditCertLedgerV215Policy()
        )
        return _result(
            safe_policy,
            now,
            "BLOCKED",
            (),
            policy_errors + input_errors,
            policy=not policy_errors,
            input=not input_errors,
        )

    try:
        entries = normalize_entries(existing)
    except TypeError as error:
        return _result(
            policy,
            now,
            "BLOCKED",
            (),
            [str(error)],
            policy=True,
            input=True,
        )
    chain_valid, chain_errors = verify_audit_cert_ledger_chain(entries)
    if not chain_valid:
        return _result(
            policy,
            now,
            "BLOCKED",
            entries,
            chain_errors,
            policy=True,
            input=True,
        )
    if not isinstance(source, OfflinePaperOrderLedgerAuditV214Result):
        return _result(
            policy,
            now,
            "FAILED",
            entries,
            ["Source는 V21.4 Offline Paper Order Ledger Audit Result여야 합니다."],
            policy=True,
            input=True,
            existing=True,
            chain=True,
        )

    source_before = canonical_json(source.to_dict())
    certificate = source.certificate
    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.audit_status == policy.required_audit_status
        and source.all_checks_passed
        and source.audit_completed
        and not source.ledger_modified
        and certificate is not None
    ):
        source_errors.append("정상 V21.4 Ledger Audit Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V21.4 Source 실행 안전장치 오류입니다.")
    if source_errors or certificate is None:
        return _result(
            policy,
            now,
            "FAILED",
            entries,
            source_errors,
            policy=True,
            input=True,
            existing=True,
            chain=True,
        )
    certificate_valid, certificate_errors = verify_audit_certificate(certificate)
    if not certificate_valid:
        return _result(
            policy,
            now,
            "FAILED",
            entries,
            certificate_errors,
            policy=True,
            input=True,
            source=True,
            existing=True,
            chain=True,
        )

    linkage_errors = _source_linkage(source)
    if certificate.audit_status != policy.required_audit_status:
        linkage_errors.append("Audit Certificate Status가 V21.5 기준과 다릅니다.")
    if linkage_errors:
        return _result(
            policy,
            now,
            "BLOCKED",
            entries,
            linkage_errors,
            policy=True,
            input=True,
            source=True,
            certificate=True,
            existing=True,
            chain=True,
        )
    if any(
        entry.audit_certificate_id == certificate.audit_certificate_id
        for entry in entries
    ):
        return _result(
            policy,
            now,
            "BLOCKED",
            entries,
            ["중복 Audit Certificate ID가 차단되었습니다."],
            policy=True,
            input=True,
            source=True,
            certificate=True,
            linkage=True,
            existing=True,
            chain=True,
        )
    try:
        audited_at = datetime.fromisoformat(certificate.audited_at)
        if audited_at.tzinfo is None:
            raise ValueError
        if now < audited_at or (
            entries and now < datetime.fromisoformat(entries[-1].recorded_at)
        ):
            raise ValueError("backward")
    except (TypeError, ValueError):
        return _result(
            policy,
            now,
            "BLOCKED",
            entries,
            ["역순 또는 잘못된 Audit Certificate Ledger 시간이 차단되었습니다."],
            policy=True,
            input=True,
            source=True,
            certificate=True,
            linkage=True,
            duplicate=True,
            existing=True,
            chain=True,
        )
    if source_before != canonical_json(source.to_dict()):
        return _result(
            policy,
            now,
            "FAILED",
            entries,
            ["V21.5 기록 중 V21.4 Source가 변경되었습니다."],
            policy=True,
            input=True,
            source=True,
            certificate=True,
            linkage=True,
            duplicate=True,
            chronology=True,
            existing=True,
            chain=True,
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
        "source_validation_ledger_result_id": (
            certificate.source_ledger_result_id
        ),
        "ledger_snapshot_hash": certificate.ledger_snapshot_hash,
        "audited_entry_count": certificate.total_ledger_entry_count,
        "latest_validation_ledger_entry_id": (
            certificate.latest_ledger_entry_id
        ),
        "latest_validation_ledger_entry_hash": (
            certificate.latest_ledger_entry_hash
        ),
        "latest_validation_result_id": certificate.latest_validation_result_id,
        "latest_validation_certificate_id": (
            certificate.latest_validation_certificate_id
        ),
        "latest_validation_certificate_hash": (
            certificate.latest_validation_certificate_hash
        ),
        "latest_paper_order_id": certificate.latest_paper_order_id,
        "latest_order_hash": certificate.latest_order_hash,
        "latest_account_id": certificate.latest_account_id,
        "latest_account_hash": certificate.latest_account_hash,
        "audit_status": certificate.audit_status,
        "operator": operator.strip(),
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
    }
    new_entry = OfflinePaperAuditCertLedgerV215Entry(
        **payload,
        entry_hash=sha256_payload(payload),
    )
    combined = entries + (new_entry,)
    trimmed_count = max(0, len(combined) - policy.maximum_ledger_entries)
    if trimmed_count:
        kept = combined[-policy.maximum_ledger_entries :]
        rebuilt: list[OfflinePaperAuditCertLedgerV215Entry] = []
        previous_hash = GENESIS_HASH
        for sequence, item in enumerate(kept, start=1):
            item = replace(
                item,
                sequence=sequence,
                previous_entry_hash=previous_hash,
                entry_hash="",
            )
            item = replace(
                item,
                entry_hash=sha256_payload(item.payload_without_hash()),
            )
            rebuilt.append(item)
            previous_hash = item.entry_hash
        combined = tuple(rebuilt)

    valid_chain, final_errors = verify_audit_cert_ledger_chain(combined)
    result = _result(
        policy,
        now,
        "RECORDED_IN_MEMORY" if valid_chain else "FAILED",
        combined,
        [
            f"Audit Certificate {certificate.audit_certificate_id}를 기록했습니다.",
            f"현재 Audit Certificate Ledger Entry는 {len(combined)}개입니다.",
        ]
        + final_errors,
        policy=True,
        input=True,
        source=True,
        certificate=True,
        linkage=True,
        unchanged=True,
        duplicate=True,
        chronology=True,
        existing=True,
        chain=valid_chain,
    )
    result.records_trimmed = trimmed_count
    return result


def save_audit_cert_ledger_result(
    result: OfflinePaperAuditCertLedgerV215Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = (
        result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    )
    report_path = output_directory / f"audit_cert_ledger_{stamp}.json"
    latest_path = output_directory / "latest_audit_cert_ledger.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_audit_cert_ledger_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V21.5 Audit Certificate Ledger JSON은 object여야 합니다.")
    return payload
