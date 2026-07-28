"""V23.7 Offline Paper Portfolio Integrity Certificate Ledger.

Records successful V23.6 integrity certificates in an append-only in-memory
SHA-256 chain. Network, account, broker, order, and live execution are absent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

from backtest.offline_paper_portfolio_audit_cert_integrity_v23_6 import (
    PortfolioAuditCertIntegrityV236Result,
    verify_integrity_audit_certificate,
)


VERSION = "V23.7"
CONFIRMATION_TEXT = "RECORD OFFLINE PAPER PORTFOLIO INTEGRITY CERTIFICATE V23.7"
GENESIS_HASH = "0" * 64
OUTPUT_DIRECTORY = Path("backtest_outputs")


def sha256_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PortfolioIntegrityLedgerV237Policy:
    required_source_version: str = "V23.6"
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
class PortfolioIntegrityLedgerEntryV237:
    entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    source_audit_result_id: str
    source_certificate_id: str
    source_certificate_hash: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_latest_entry_hash: str
    source_total_entry_count: int
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
class PortfolioIntegrityLedgerV237Result:
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
    ledger_policy: PortfolioIntegrityLedgerV237Policy
    entries: tuple[PortfolioIntegrityLedgerEntryV237, ...]
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


def validate_policy(policy: PortfolioIntegrityLedgerV237Policy) -> list[str]:
    if not isinstance(policy, PortfolioIntegrityLedgerV237Policy):
        return ["V23.7 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V23.6":
        errors.append("V23.7 Source Version 정책 오류입니다.")
    if policy.required_source_status != "AUDITED_IN_MEMORY":
        errors.append("V23.7 Source Status 정책 오류입니다.")
    if policy.required_audit_status != "PASSED":
        errors.append("V23.7 Audit Status 정책 오류입니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.7 확인 문구 정책 오류입니다.")
    if (isinstance(policy.maximum_ledger_entries, bool)
            or not isinstance(policy.maximum_ledger_entries, int)
            or policy.maximum_ledger_entries <= 0):
        errors.append("V23.7 Ledger 보관 한도 오류입니다.")
    for name, value in policy.to_dict().items():
        if (name.startswith("immutable_") or
                name.endswith(("_disabled", "_forbidden"))):
            if value is not True:
                errors.append(f"{name}는 True여야 합니다.")
    return errors


def _entry_is_safe(entry: PortfolioIntegrityLedgerEntryV237) -> bool:
    return bool(
        entry.execution_blocked and not entry.funds_reserved
        and not entry.holdings_reserved and not entry.transmit
        and not entry.credentials_used and not entry.market_data_api_called
        and not entry.account_api_called and not entry.network_accessed
        and not entry.broker_api_called and not entry.broker_order_created
        and not entry.order_submitted and not entry.live_execution_authorized)


def verify_integrity_certificate_ledger(
    entries: tuple[PortfolioIntegrityLedgerEntryV237, ...],
) -> list[str]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    certificate_ids: set[str] = set()
    for expected, entry in enumerate(entries, start=1):
        if not isinstance(entry, PortfolioIntegrityLedgerEntryV237):
            errors.append("V23.7 Ledger Entry 형식 오류입니다.")
            continue
        if entry.sequence != expected:
            errors.append(f"V23.7 Sequence {expected} 오류입니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append(f"V23.7 Sequence {expected} 연결 Hash 오류입니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append(f"V23.7 Sequence {expected} Entry Hash 오류입니다.")
        if entry.source_certificate_id in certificate_ids:
            errors.append("V23.7 중복 Integrity Certificate입니다.")
        certificate_ids.add(entry.source_certificate_id)
        try:
            current = _parse_utc(entry.recorded_at)
            if previous_time and current < previous_time:
                errors.append("V23.7 Ledger 시간이 역순입니다.")
            previous_time = current
        except (TypeError, ValueError):
            errors.append("V23.7 Ledger 시간 오류입니다.")
        if entry.audit_status != "PASSED" or not _entry_is_safe(entry):
            errors.append("V23.7 Ledger Entry 안전성 오류입니다.")
        previous_hash = entry.entry_hash
    return errors


def ledger_snapshot_hash(
    entries: tuple[PortfolioIntegrityLedgerEntryV237, ...],
) -> str:
    return sha256_payload({"entries": [entry.to_dict() for entry in entries]})


def _result(policy, now, status, entries, errors, checks):
    passed = status == "RECORDED_IN_MEMORY" and not errors
    return PortfolioIntegrityLedgerV237Result(
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
        funds_reserved=False, holdings_reserved=False,
        execution_blocked=True, transmit=False, credentials_used=False,
        market_data_api_called=False, account_api_called=False,
        network_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_execution_authorized=False, ledger_policy=policy, entries=entries,
        reasons=errors or [
            "V23.6 Portfolio Integrity Certificate를 원장에 기록했습니다.",
            "Network·Broker·실제 주문·Live Execution은 차단되었습니다."])


def record_integrity_certificate_v23_7(
    source: PortfolioAuditCertIntegrityV236Result,
    operator: str,
    confirmation_text: str,
    *,
    existing_entries: Any = None,
    policy: PortfolioIntegrityLedgerV237Policy | None = None,
    now: datetime | None = None,
) -> PortfolioIntegrityLedgerV237Result:
    selected = policy or PortfolioIntegrityLedgerV237Policy()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors = validate_policy(selected)
    checks = {"policy": not errors}
    if not isinstance(operator, str) or not operator.strip():
        errors.append("V23.7 Operator가 필요합니다.")
    if confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.7 확인 문구가 일치하지 않습니다.")
    if existing_entries is None:
        entries: tuple[PortfolioIntegrityLedgerEntryV237, ...] = ()
    elif isinstance(existing_entries, (tuple, list)) and all(
            isinstance(item, PortfolioIntegrityLedgerEntryV237)
            for item in existing_entries):
        entries = tuple(existing_entries)
    else:
        return _result(selected, current, "BLOCKED", (), errors + [
            "V23.7 Existing Ledger 형식 오류입니다."], checks)
    chain_errors = verify_integrity_certificate_ledger(entries)
    checks["chain"] = not chain_errors
    errors.extend(chain_errors)
    if not isinstance(source, PortfolioAuditCertIntegrityV236Result):
        return _result(selected, current, "BLOCKED", entries, errors + [
            "Source는 V23.6 Integrity Audit Result여야 합니다."], checks)

    before = source.to_dict()
    certificate = source.certificate
    checks["source"] = bool(
        source.version == selected.required_source_version
        and source.result_status == selected.required_source_status
        and source.all_checks_passed and source.audit_completed
        and source.execution_blocked and not source.source_modified
        and not source.funds_reserved and not source.holdings_reserved
        and not source.network_accessed and not source.broker_api_called
        and not source.order_submitted and not source.live_execution_authorized)
    if not checks["source"]:
        errors.append("V23.6 Source 상태 또는 안전성 오류입니다.")
    certificate_errors = verify_integrity_audit_certificate(certificate)
    checks["certificate"] = not certificate_errors
    errors.extend(certificate_errors)
    checks["linkage"] = bool(
        certificate and
        source.source_ledger_result_id == certificate.source_ledger_result_id
        and source.source_ledger_snapshot_hash
        == certificate.source_ledger_snapshot_hash
        and source.source_latest_entry_hash
        == certificate.source_latest_entry_hash
        and source.source_total_entry_count
        == certificate.source_total_entry_count
        and certificate.audit_status == selected.required_audit_status)
    if not checks["linkage"]:
        errors.append("V23.6 Integrity Certificate 연결 오류입니다.")
    checks["duplicate"] = bool(
        certificate and all(
            item.source_certificate_id != certificate.audit_certificate_id
            for item in entries))
    if not checks["duplicate"]:
        errors.append("V23.6 Integrity Certificate가 이미 기록되었습니다.")
    try:
        checks["chronology"] = bool(
            certificate
            and (not entries or current >= _parse_utc(entries[-1].recorded_at))
            and current >= _parse_utc(certificate.audited_at))
    except (TypeError, ValueError):
        checks["chronology"] = False
    if not checks["chronology"]:
        errors.append("V23.7 기록 시간이 역순입니다.")
    checks["unchanged"] = source.to_dict() == before
    if errors:
        return _result(selected, current, "BLOCKED", entries, errors, checks)

    payload = {
        "entry_id": str(uuid.uuid4()), "sequence": len(entries) + 1,
        "recorded_at": current.isoformat(),
        "previous_entry_hash": entries[-1].entry_hash if entries else GENESIS_HASH,
        "source_audit_result_id": source.audit_result_id,
        "source_certificate_id": certificate.audit_certificate_id,
        "source_certificate_hash": certificate.certificate_hash,
        "source_ledger_result_id": certificate.source_ledger_result_id,
        "source_ledger_snapshot_hash": certificate.source_ledger_snapshot_hash,
        "source_latest_entry_hash": certificate.source_latest_entry_hash,
        "source_total_entry_count": certificate.source_total_entry_count,
        "audit_status": certificate.audit_status, "operator": operator.strip(),
        "execution_blocked": True, "funds_reserved": False,
        "holdings_reserved": False, "transmit": False,
        "credentials_used": False, "market_data_api_called": False,
        "account_api_called": False, "network_accessed": False,
        "broker_api_called": False, "broker_order_created": False,
        "order_submitted": False, "live_execution_authorized": False}
    entry = PortfolioIntegrityLedgerEntryV237(
        **payload, entry_hash=sha256_payload(payload))
    new_entries = entries + (entry,)
    if len(new_entries) > selected.maximum_ledger_entries:
        return _result(selected, current, "BLOCKED", entries, [
            "V23.7 Ledger 보관 한도를 초과했습니다."], checks)
    final_errors = verify_integrity_certificate_ledger(new_entries)
    if source.to_dict() != before:
        final_errors.append("V23.6 Source 변경이 감지되었습니다.")
    checks["chain"] = not final_errors
    checks["unchanged"] = source.to_dict() == before
    return _result(
        selected, current,
        "RECORDED_IN_MEMORY" if not final_errors else "BLOCKED",
        new_entries if not final_errors else entries, final_errors, checks)


def save_ledger_result(
    result: PortfolioIntegrityLedgerV237Result,
    output_directory: str | Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report = directory / f"portfolio_integrity_ledger_v23_7_{stamp}.json"
    latest = directory / "latest_portfolio_integrity_ledger_v23_7.json"
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path, result.latest_path = str(report), str(latest)
    return report, latest


def load_ledger_result(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V23.7 Ledger JSON은 object여야 합니다.")
    return payload
