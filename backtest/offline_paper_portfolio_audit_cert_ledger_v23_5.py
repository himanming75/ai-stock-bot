"""V23.5 Offline Paper Portfolio Audit Certificate Ledger.

Records a successful V23.4 audit certificate in an immutable in-memory
SHA-256 chain. It has no network, broker, account, order-submission, or live
execution capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

from backtest.offline_paper_portfolio_audit_v23_4 import (
    PortfolioLedgerAuditV234Result,
    sha256_payload,
    verify_audit_certificate,
)


VERSION = "V23.5"
CONFIRMATION_TEXT = "RECORD OFFLINE PAPER PORTFOLIO AUDIT CERTIFICATE V23.5"
GENESIS_HASH = "0" * 64
OUTPUT_DIRECTORY = Path("backtest_outputs")


@dataclass(frozen=True)
class PortfolioAuditCertLedgerV235Policy:
    required_source_version: str = "V23.4"
    required_source_status: str = "AUDITED_IN_MEMORY"
    required_audit_status: str = "PASSED"
    required_confirmation_text: str = CONFIRMATION_TEXT
    maximum_ledger_entries: int = 100
    immutable_ledger: bool = True
    source_mutation_disabled: bool = True
    funds_reservation_disabled: bool = True
    holdings_reservation_disabled: bool = True
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
class PortfolioAuditCertLedgerEntryV235:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    source_audit_result_id: str
    source_audit_certificate_id: str
    source_audit_certificate_hash: str
    source_ledger_result_id: str
    source_ledger_hash: str
    source_ledger_snapshot_hash: str
    source_portfolio_hash: str
    audited_entry_count: int
    audit_status: str
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    transmit: bool
    credentials_used: bool
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
class PortfolioAuditCertLedgerV235Result:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    ledger_snapshot_hash: str | None
    latest_entry_hash: str | None
    total_entry_count: int
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
    source_modified: bool
    funds_reserved: bool
    holdings_reserved: bool
    execution_blocked: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    ledger_policy: PortfolioAuditCertLedgerV235Policy
    entries: tuple[PortfolioAuditCertLedgerEntryV235, ...]
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ledger_policy"] = self.ledger_policy.to_dict()
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("시간 형식 오류입니다.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("시간대가 필요합니다.")
    return parsed.astimezone(timezone.utc)


def validate_policy(policy: PortfolioAuditCertLedgerV235Policy) -> list[str]:
    if not isinstance(policy, PortfolioAuditCertLedgerV235Policy):
        return ["V23.5 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V23.4":
        errors.append("V23.5 Source Version 정책 오류입니다.")
    if policy.required_source_status != "AUDITED_IN_MEMORY":
        errors.append("V23.5 Source Status 정책 오류입니다.")
    if policy.required_audit_status != "PASSED":
        errors.append("V23.5 Audit Status 정책 오류입니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.5 확인 문구 정책 오류입니다.")
    if (isinstance(policy.maximum_ledger_entries, bool)
            or not isinstance(policy.maximum_ledger_entries, int)
            or policy.maximum_ledger_entries <= 0):
        errors.append("V23.5 Ledger 보관 한도는 양의 정수여야 합니다.")
    for name, value in policy.to_dict().items():
        if name.startswith("immutable_") or name.endswith(("_disabled", "_forbidden")):
            if value is not True:
                errors.append(f"{name}는 True여야 합니다.")
    return errors


def _entry_is_safe(entry: PortfolioAuditCertLedgerEntryV235) -> bool:
    return bool(
        entry.execution_blocked
        and not entry.funds_reserved and not entry.holdings_reserved
        and not entry.transmit and not entry.credentials_used
        and not entry.market_data_api_called and not entry.account_api_called
        and not entry.network_accessed and not entry.broker_api_called
        and not entry.broker_order_created and not entry.order_submitted
        and not entry.live_execution_authorized
    )


def _source_is_safe(source: PortfolioLedgerAuditV234Result) -> bool:
    return bool(
        source.execution_blocked and not source.ledger_modified
        and not source.funds_reserved and not source.holdings_reserved
        and not source.transmit and not source.credentials_used
        and not source.market_data_api_called and not source.account_api_called
        and not source.network_accessed and not source.broker_api_called
        and not source.broker_order_created and not source.order_submitted
        and not source.live_execution_authorized
    )


def verify_portfolio_audit_cert_ledger(
    entries: tuple[PortfolioAuditCertLedgerEntryV235, ...],
) -> list[str]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected, entry in enumerate(entries, start=1):
        if not isinstance(entry, PortfolioAuditCertLedgerEntryV235):
            errors.append("V23.5 Ledger Entry 형식 오류입니다.")
            continue
        if entry.sequence != expected:
            errors.append(f"V23.5 Sequence {expected} 오류입니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append(f"V23.5 Sequence {entry.sequence} Previous Hash 오류입니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append(f"V23.5 Sequence {entry.sequence} Entry Hash 오류입니다.")
        if entry.source_audit_certificate_id in certificate_ids:
            errors.append("V23.5 중복 Audit Certificate ID입니다.")
        certificate_ids.add(entry.source_audit_certificate_id)
        try:
            current = _parse_utc(entry.recorded_at)
            if previous_time and current < previous_time:
                errors.append("V23.5 Ledger 시간이 역순입니다.")
            previous_time = current
        except (TypeError, ValueError):
            errors.append("V23.5 Ledger 시간이 올바르지 않습니다.")
        if entry.audit_status != "PASSED" or not _entry_is_safe(entry):
            errors.append("V23.5 Ledger Entry 안전성 오류입니다.")
        previous_hash = entry.entry_hash
    return errors


def ledger_snapshot_hash(
    entries: tuple[PortfolioAuditCertLedgerEntryV235, ...],
) -> str:
    return sha256_payload({"entries": [entry.to_dict() for entry in entries]})


def _result(policy, now, status, entries, errors, checks):
    passed = status == "RECORDED_IN_MEMORY" and not errors
    return PortfolioAuditCertLedgerV235Result(
        version=VERSION, created_at=now.isoformat(),
        ledger_result_id=str(uuid.uuid4()), result_status=status,
        ledger_snapshot_hash=ledger_snapshot_hash(entries) if entries else None,
        latest_entry_hash=entries[-1].entry_hash if entries else None,
        total_entry_count=len(entries),
        policy_checks_passed=checks.get("policy", False),
        source_checks_passed=checks.get("source", False),
        certificate_hash_checks_passed=checks.get("certificate", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        duplicate_checks_passed=checks.get("duplicate", False),
        chronology_checks_passed=checks.get("chronology", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        safety_checks_passed=True, all_checks_passed=passed,
        certificate_recorded=passed, source_modified=False,
        funds_reserved=False, holdings_reserved=False, execution_blocked=True,
        transmit=False, credentials_used=False, market_data_api_called=False,
        account_api_called=False, network_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_execution_authorized=False, ledger_policy=policy, entries=entries,
        reasons=errors or [
            "V23.4 Portfolio Audit Certificate를 SHA-256 Ledger에 기록했습니다.",
            "Network·Broker API·실제 주문·Live Execution은 차단되었습니다.",
        ],
    )


def record_portfolio_audit_certificate_v23_5(
    source: PortfolioLedgerAuditV234Result,
    operator: str,
    confirmation_text: str,
    *,
    existing_entries: Any = None,
    policy: PortfolioAuditCertLedgerV235Policy | None = None,
    now: datetime | None = None,
) -> PortfolioAuditCertLedgerV235Result:
    selected = policy or PortfolioAuditCertLedgerV235Policy()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors = validate_policy(selected)
    checks = {"policy": not errors}
    if not isinstance(operator, str) or not operator.strip():
        errors.append("V23.5 Operator가 필요합니다.")
    if confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.5 확인 문구가 일치하지 않습니다.")
    if existing_entries is None:
        entries: tuple[PortfolioAuditCertLedgerEntryV235, ...] = ()
    elif isinstance(existing_entries, (tuple, list)) and all(
        isinstance(item, PortfolioAuditCertLedgerEntryV235) for item in existing_entries
    ):
        entries = tuple(existing_entries)
    else:
        return _result(selected, current, "BLOCKED", (), errors + [
            "V23.5 Existing Ledger 형식 오류입니다."], checks)
    chain_errors = verify_portfolio_audit_cert_ledger(entries)
    checks["chain"] = not chain_errors
    errors.extend(chain_errors)
    if not isinstance(source, PortfolioLedgerAuditV234Result):
        return _result(selected, current, "BLOCKED", entries, errors + [
            "Source는 V23.4 Audit Result여야 합니다."], checks)
    before = source.to_dict()
    checks["source"] = bool(
        source.version == selected.required_source_version
        and source.result_status == selected.required_source_status
        and source.all_checks_passed and source.audit_completed
        and _source_is_safe(source)
    )
    if not checks["source"]:
        errors.append("V23.4 Source 상태 또는 실행 안전성 오류입니다.")
    certificate_errors = verify_audit_certificate(source.certificate)
    checks["certificate"] = not certificate_errors
    errors.extend(certificate_errors)
    certificate = source.certificate
    checks["linkage"] = bool(
        certificate
        and source.audit_certificate_id == certificate.audit_certificate_id
        and source.audit_certificate_hash == certificate.certificate_hash
        and source.source_ledger_result_id == certificate.source_ledger_result_id
        and source.source_ledger_hash == certificate.source_ledger_hash
        and source.source_ledger_snapshot_hash == certificate.source_ledger_snapshot_hash
        and certificate.audit_status == selected.required_audit_status
    )
    if not checks["linkage"]:
        errors.append("V23.4 Audit Certificate 연결 Hash 오류입니다.")
    checks["duplicate"] = bool(
        source.audit_certificate_id and all(
            entry.source_audit_certificate_id != source.audit_certificate_id
            for entry in entries
        )
    )
    if not checks["duplicate"]:
        errors.append("V23.4 Audit Certificate가 이미 기록되었습니다.")
    try:
        chronology = (
            (not entries or current >= _parse_utc(entries[-1].recorded_at))
            and bool(certificate)
            and current >= _parse_utc(certificate.audited_at)
        )
    except (TypeError, ValueError):
        chronology = False
    checks["chronology"] = chronology
    if not chronology:
        errors.append("V23.5 기록 시간이 역순입니다.")
    checks["unchanged"] = source.to_dict() == before
    if errors:
        return _result(selected, current, "BLOCKED", entries, errors, checks)
    payload = {
        "ledger_entry_id": str(uuid.uuid4()), "sequence": len(entries) + 1,
        "recorded_at": current.isoformat(),
        "previous_entry_hash": entries[-1].entry_hash if entries else GENESIS_HASH,
        "source_audit_result_id": source.audit_result_id,
        "source_audit_certificate_id": certificate.audit_certificate_id,
        "source_audit_certificate_hash": certificate.certificate_hash,
        "source_ledger_result_id": certificate.source_ledger_result_id,
        "source_ledger_hash": certificate.source_ledger_hash,
        "source_ledger_snapshot_hash": certificate.source_ledger_snapshot_hash,
        "source_portfolio_hash": certificate.source_portfolio_hash,
        "audited_entry_count": source.audited_entry_count,
        "audit_status": certificate.audit_status, "operator": operator.strip(),
        "execution_blocked": True, "funds_reserved": False,
        "holdings_reserved": False, "transmit": False, "credentials_used": False,
        "market_data_api_called": False, "account_api_called": False,
        "network_accessed": False, "broker_api_called": False,
        "broker_order_created": False, "order_submitted": False,
        "live_execution_authorized": False,
    }
    entry = PortfolioAuditCertLedgerEntryV235(
        **payload, entry_hash=sha256_payload(payload))
    new_entries = entries + (entry,)
    if len(new_entries) > selected.maximum_ledger_entries:
        return _result(selected, current, "BLOCKED", entries, [
            "V23.5 Ledger 보관 한도를 초과했습니다."], checks)
    final_errors = verify_portfolio_audit_cert_ledger(new_entries)
    if source.to_dict() != before:
        final_errors.append("V23.4 Source 변경이 감지되었습니다.")
    checks["chain"] = not final_errors
    checks["unchanged"] = source.to_dict() == before
    return _result(
        selected, current,
        "RECORDED_IN_MEMORY" if not final_errors else "BLOCKED",
        new_entries if not final_errors else entries, final_errors, checks,
    )


def save_ledger_result(
    result: PortfolioAuditCertLedgerV235Result,
    output_directory: str | Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report = directory / f"portfolio_audit_cert_ledger_v23_5_{stamp}.json"
    latest = directory / "latest_portfolio_audit_cert_ledger_v23_5.json"
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path, result.latest_path = str(report), str(latest)
    return report, latest


def load_ledger_result(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V23.5 Ledger JSON은 object여야 합니다.")
    return payload
