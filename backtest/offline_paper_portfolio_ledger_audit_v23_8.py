"""V23.8 Offline Paper Portfolio Integrity Ledger Audit.

Audits a V23.7 in-memory ledger without mutating it. This module deliberately
contains no market-data, account, network, broker, order, or live-execution
integration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

from backtest.offline_paper_portfolio_integrity_ledger_v23_7 import (
    GENESIS_HASH,
    PortfolioIntegrityLedgerEntryV237,
    PortfolioIntegrityLedgerV237Result,
    ledger_snapshot_hash,
    verify_integrity_certificate_ledger,
)


VERSION = "V23.8"
CONFIRMATION_TEXT = "AUDIT OFFLINE PAPER PORTFOLIO INTEGRITY LEDGER V23.8"
OUTPUT_DIRECTORY = Path("backtest_outputs")


def sha256_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PortfolioLedgerAuditV238Policy:
    required_source_version: str = "V23.7"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_confirmation_text: str = CONFIRMATION_TEXT
    immutable_audit: bool = True
    source_mutation_disabled: bool = True
    ledger_mutation_disabled: bool = True
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
class PortfolioLedgerAuditFindingV238:
    sequence: int
    entry_id: str
    sequence_valid: bool
    previous_hash_valid: bool
    entry_hash_valid: bool
    entry_id_unique: bool
    chronology_valid: bool
    source_linkage_valid: bool
    safety_valid: bool
    finding_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioLedgerAuditCertificateV238:
    audit_certificate_id: str
    audited_at: str
    audit_status: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_latest_entry_hash: str
    source_total_entry_count: int
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    findings: tuple[PortfolioLedgerAuditFindingV238, ...]
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash")
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioLedgerAuditV238Result:
    version: str
    created_at: str
    audit_result_id: str
    result_status: str
    source_ledger_result_id: str | None
    source_ledger_snapshot_hash: str | None
    source_latest_entry_hash: str | None
    source_total_entry_count: int
    audit_certificate: PortfolioLedgerAuditCertificateV238 | None
    policy_checks_passed: bool
    source_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    source_linkage_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    entry_safety_checks_passed: bool
    snapshot_hash_checks_passed: bool
    source_unchanged_checks_passed: bool
    certificate_hash_checks_passed: bool
    all_checks_passed: bool
    audit_completed: bool
    source_modified: bool
    ledger_modified: bool
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
    audit_policy: PortfolioLedgerAuditV238Policy
    findings: tuple[PortfolioLedgerAuditFindingV238, ...]
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_policy"] = self.audit_policy.to_dict()
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        payload["audit_certificate"] = (
            self.audit_certificate.to_dict()
            if self.audit_certificate is not None else None)
        return payload


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("시간 형식 오류입니다.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("시간대가 필요합니다.")
    return parsed.astimezone(timezone.utc)


def validate_policy(policy: PortfolioLedgerAuditV238Policy) -> list[str]:
    if not isinstance(policy, PortfolioLedgerAuditV238Policy):
        return ["V23.8 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V23.7":
        errors.append("V23.8 Source Version 정책 오류입니다.")
    if policy.required_source_status != "RECORDED_IN_MEMORY":
        errors.append("V23.8 Source Status 정책 오류입니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.8 확인 문구 정책 오류입니다.")
    for name, value in policy.to_dict().items():
        if (name.startswith("immutable_")
                or name.endswith(("_disabled", "_forbidden"))):
            if value is not True:
                errors.append(f"{name}는 True여야 합니다.")
    return errors


def _entry_safe(entry: PortfolioIntegrityLedgerEntryV237) -> bool:
    return bool(
        entry.execution_blocked and not entry.funds_reserved
        and not entry.holdings_reserved and not entry.transmit
        and not entry.credentials_used and not entry.market_data_api_called
        and not entry.account_api_called and not entry.network_accessed
        and not entry.broker_api_called and not entry.broker_order_created
        and not entry.order_submitted and not entry.live_execution_authorized)


def _build_findings(
    entries: tuple[PortfolioIntegrityLedgerEntryV237, ...],
) -> tuple[PortfolioLedgerAuditFindingV238, ...]:
    findings: list[PortfolioLedgerAuditFindingV238] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    seen_ids: set[str] = set()
    for expected, entry in enumerate(entries, start=1):
        sequence_valid = entry.sequence == expected
        previous_hash_valid = entry.previous_entry_hash == previous_hash
        entry_hash_valid = (
            entry.entry_hash == sha256_payload(entry.payload_without_hash()))
        entry_id_unique = entry.entry_id not in seen_ids
        seen_ids.add(entry.entry_id)
        try:
            current_time = _parse_utc(entry.recorded_at)
            chronology_valid = (
                previous_time is None or current_time >= previous_time)
            previous_time = current_time
        except (TypeError, ValueError):
            chronology_valid = False
        source_linkage_valid = bool(
            entry.source_ledger_result_id
            and entry.source_ledger_snapshot_hash
            and entry.source_latest_entry_hash
            and entry.source_certificate_hash)
        safety_valid = _entry_safe(entry)
        passed = all((
            sequence_valid, previous_hash_valid, entry_hash_valid,
            entry_id_unique, chronology_valid, source_linkage_valid,
            safety_valid))
        findings.append(PortfolioLedgerAuditFindingV238(
            sequence=entry.sequence, entry_id=entry.entry_id,
            sequence_valid=sequence_valid,
            previous_hash_valid=previous_hash_valid,
            entry_hash_valid=entry_hash_valid,
            entry_id_unique=entry_id_unique,
            chronology_valid=chronology_valid,
            source_linkage_valid=source_linkage_valid,
            safety_valid=safety_valid,
            finding_status="PASSED" if passed else "FAILED"))
        previous_hash = entry.entry_hash
    return tuple(findings)


def verify_audit_certificate(
    certificate: PortfolioLedgerAuditCertificateV238,
) -> list[str]:
    if not isinstance(certificate, PortfolioLedgerAuditCertificateV238):
        return ["V23.8 Audit Certificate 형식 오류입니다."]
    errors: list[str] = []
    if certificate.certificate_hash != sha256_payload(
            certificate.payload_without_hash()):
        errors.append("V23.8 Audit Certificate Hash 오류입니다.")
    if certificate.audit_status != "PASSED":
        errors.append("V23.8 Audit Status 오류입니다.")
    if (not certificate.execution_blocked or certificate.funds_reserved
            or certificate.holdings_reserved):
        errors.append("V23.8 Audit Certificate 안전성 오류입니다.")
    if any(f.finding_status != "PASSED" for f in certificate.findings):
        errors.append("V23.8 Finding 오류입니다.")
    return errors


def audit_portfolio_integrity_ledger_v23_8(
    source: PortfolioIntegrityLedgerV237Result,
    operator: str,
    confirmation_text: str,
    *,
    policy: PortfolioLedgerAuditV238Policy | None = None,
    now: datetime | None = None,
) -> PortfolioLedgerAuditV238Result:
    policy = policy or PortfolioLedgerAuditV238Policy()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    errors = validate_policy(policy)
    checks = {"policy": not errors}
    before = source.to_dict() if isinstance(
        source, PortfolioIntegrityLedgerV237Result) else None

    if not isinstance(operator, str) or not operator.strip():
        errors.append("V23.8 Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        errors.append("V23.8 확인 문구가 일치하지 않습니다.")
    if type(source) is not PortfolioIntegrityLedgerV237Result:
        errors.append("V23.8 Source 형식 오류입니다.")
        entries: tuple[PortfolioIntegrityLedgerEntryV237, ...] = ()
    else:
        entries = source.entries
        if source.version != policy.required_source_version:
            errors.append("V23.8 Source Version 오류입니다.")
        if source.result_status != policy.required_source_status:
            errors.append("V23.8 Source Status 오류입니다.")
        if not source.all_checks_passed or not source.certificate_recorded:
            errors.append("V23.8 Source 검증 상태 오류입니다.")
        if not entries:
            errors.append("V23.8 Source Ledger가 비어 있습니다.")
        try:
            if entries and now.astimezone(timezone.utc) < _parse_utc(
                    entries[-1].recorded_at):
                errors.append("V23.8 Audit 시간이 원장보다 빠릅니다.")
        except (TypeError, ValueError):
            errors.append("V23.8 Source 시간 오류입니다.")

    findings = _build_findings(entries) if entries else ()
    chain_ok = bool(entries) and not verify_integrity_certificate_ledger(entries)
    duplicate_ok = bool(entries) and len({
        entry.entry_id for entry in entries}) == len(entries)
    chronology_ok = bool(findings) and all(
        finding.chronology_valid for finding in findings)
    linkage_ok = bool(findings) and all(
        finding.source_linkage_valid for finding in findings)
    safety_ok = bool(findings) and all(
        finding.safety_valid for finding in findings)
    snapshot_ok = bool(entries) and isinstance(
        source, PortfolioIntegrityLedgerV237Result) and (
            source.ledger_snapshot_hash == ledger_snapshot_hash(entries)
            and source.latest_entry_hash == entries[-1].entry_hash
            and source.total_entry_count == len(entries))
    for ok, message in (
        (chain_ok, "V23.8 Ledger Hash Chain 오류입니다."),
        (duplicate_ok, "V23.8 중복 Entry ID 오류입니다."),
        (chronology_ok, "V23.8 Ledger 시간 순서 오류입니다."),
        (linkage_ok, "V23.8 Source Linkage 오류입니다."),
        (safety_ok, "V23.8 Entry 안전성 오류입니다."),
        (snapshot_ok, "V23.8 Snapshot Hash 오류입니다.")):
        if not ok:
            errors.append(message)

    source_ok = isinstance(source, PortfolioIntegrityLedgerV237Result) and not any(
        text for text in errors if "Source " in text and "Linkage" not in text)
    unchanged_ok = before is not None and source.to_dict() == before
    if not unchanged_ok:
        errors.append("V23.8 Source가 변경되었습니다.")
    checks.update(
        source=source_ok, chain=chain_ok, linkage=linkage_ok,
        duplicate=duplicate_ok, chronology=chronology_ok, safety=safety_ok,
        snapshot=snapshot_ok, unchanged=unchanged_ok)

    certificate = None
    eligible = all(checks.values()) and not errors
    if eligible:
        certificate = PortfolioLedgerAuditCertificateV238(
            audit_certificate_id=str(uuid.uuid4()),
            audited_at=now.isoformat(), audit_status="PASSED",
            source_ledger_result_id=source.ledger_result_id,
            source_ledger_snapshot_hash=source.ledger_snapshot_hash or "",
            source_latest_entry_hash=source.latest_entry_hash or "",
            source_total_entry_count=source.total_entry_count,
            execution_blocked=True, funds_reserved=False,
            holdings_reserved=False, findings=findings, certificate_hash="")
        certificate = replace(
            certificate,
            certificate_hash=sha256_payload(certificate.payload_without_hash()))
    certificate_ok = certificate is not None and not verify_audit_certificate(
        certificate)
    if eligible and not certificate_ok:
        errors.append("V23.8 Audit Certificate 생성 오류입니다.")
    passed = eligible and certificate_ok and not errors
    return PortfolioLedgerAuditV238Result(
        version=VERSION, created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()),
        result_status="AUDITED_IN_MEMORY" if passed else "BLOCKED",
        source_ledger_result_id=getattr(source, "ledger_result_id", None),
        source_ledger_snapshot_hash=getattr(
            source, "ledger_snapshot_hash", None),
        source_latest_entry_hash=getattr(source, "latest_entry_hash", None),
        source_total_entry_count=getattr(source, "total_entry_count", 0),
        audit_certificate=certificate if passed else None,
        policy_checks_passed=checks["policy"],
        source_checks_passed=checks["source"],
        ledger_hash_chain_checks_passed=checks["chain"],
        source_linkage_checks_passed=checks["linkage"],
        duplicate_checks_passed=checks["duplicate"],
        chronology_checks_passed=checks["chronology"],
        entry_safety_checks_passed=checks["safety"],
        snapshot_hash_checks_passed=checks["snapshot"],
        source_unchanged_checks_passed=checks["unchanged"],
        certificate_hash_checks_passed=certificate_ok,
        all_checks_passed=passed, audit_completed=passed,
        source_modified=False, ledger_modified=False,
        funds_reserved=False, holdings_reserved=False,
        execution_blocked=True, transmit=False, credentials_used=False,
        market_data_api_called=False, account_api_called=False,
        network_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_execution_authorized=False, audit_policy=policy,
        findings=findings, reasons=errors or [
            "V23.7 Portfolio Integrity Ledger 읽기 전용 감사를 완료했습니다.",
            "Network·Broker·실제 주문·Live Execution은 차단되었습니다."])


def save_audit_result(
    result: PortfolioLedgerAuditV238Result,
    output_directory: str | Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    report = directory / f"portfolio_ledger_audit_{result.audit_result_id}.json"
    latest = directory / "latest_portfolio_ledger_audit_v23_8.json"
    text = json.dumps(
        result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    report.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_audit_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
