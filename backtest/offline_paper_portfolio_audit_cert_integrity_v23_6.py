"""V23.6 Offline Paper Portfolio Audit Certificate Ledger Integrity Audit.

Performs a read-only integrity audit of a V23.5 in-memory ledger.  This
module intentionally contains no market-data, account, network, broker,
order-submission, or live-execution capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

from backtest.offline_paper_portfolio_audit_cert_ledger_v23_5 import (
    PortfolioAuditCertLedgerV235Result,
    ledger_snapshot_hash,
    sha256_payload,
    verify_portfolio_audit_cert_ledger,
)


VERSION = "V23.6"
CONFIRMATION_TEXT = "AUDIT OFFLINE PAPER PORTFOLIO CERTIFICATE LEDGER V23.6"
OUTPUT_DIRECTORY = Path("backtest_outputs")


@dataclass(frozen=True)
class PortfolioAuditCertIntegrityV236Policy:
    required_source_version: str = "V23.5"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_audit_status: str = "PASSED"
    required_confirmation_text: str = CONFIRMATION_TEXT
    read_only_audit: bool = True
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
class PortfolioAuditCertIntegrityCertificateV236:
    audit_certificate_id: str
    audited_at: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    source_latest_entry_hash: str
    source_first_entry_hash: str
    source_total_entry_count: int
    source_audit_certificate_hashes: tuple[str, ...]
    audit_status: str
    operator: str
    source_modified: bool
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
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioAuditCertIntegrityV236Result:
    version: str
    created_at: str
    audit_result_id: str
    result_status: str
    source_ledger_result_id: str | None
    source_ledger_snapshot_hash: str | None
    source_latest_entry_hash: str | None
    source_total_entry_count: int
    policy_checks_passed: bool
    source_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    snapshot_hash_checks_passed: bool
    latest_hash_checks_passed: bool
    entry_count_checks_passed: bool
    source_linkage_checks_passed: bool
    chronology_checks_passed: bool
    source_unchanged_checks_passed: bool
    certificate_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    audit_completed: bool
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
    audit_policy: PortfolioAuditCertIntegrityV236Policy
    certificate: PortfolioAuditCertIntegrityCertificateV236 | None
    findings: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_policy"] = self.audit_policy.to_dict()
        payload["certificate"] = (
            self.certificate.to_dict() if self.certificate else None)
        return payload


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("시간 형식 오류입니다.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("시간대가 필요합니다.")
    return parsed.astimezone(timezone.utc)


def validate_policy(policy: PortfolioAuditCertIntegrityV236Policy) -> list[str]:
    if not isinstance(policy, PortfolioAuditCertIntegrityV236Policy):
        return ["V23.6 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V23.5":
        errors.append("V23.6 Source Version 정책 오류입니다.")
    if policy.required_source_status != "RECORDED_IN_MEMORY":
        errors.append("V23.6 Source Status 정책 오류입니다.")
    if policy.required_audit_status != "PASSED":
        errors.append("V23.6 Audit Status 정책 오류입니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.6 확인 문구 정책 오류입니다.")
    for name, value in policy.to_dict().items():
        if (name == "read_only_audit" or name.endswith(
                ("_disabled", "_forbidden"))) and value is not True:
            errors.append(f"{name}는 True여야 합니다.")
    return errors


def _source_is_safe(source: PortfolioAuditCertLedgerV235Result) -> bool:
    return bool(
        source.execution_blocked and not source.source_modified
        and not source.funds_reserved and not source.holdings_reserved
        and not source.transmit and not source.credentials_used
        and not source.market_data_api_called and not source.account_api_called
        and not source.network_accessed and not source.broker_api_called
        and not source.broker_order_created and not source.order_submitted
        and not source.live_execution_authorized
    )


def verify_integrity_audit_certificate(
    certificate: PortfolioAuditCertIntegrityCertificateV236 | None,
) -> list[str]:
    if not isinstance(certificate, PortfolioAuditCertIntegrityCertificateV236):
        return ["V23.6 Integrity Certificate 형식 오류입니다."]
    errors: list[str] = []
    if certificate.certificate_hash != sha256_payload(
            certificate.payload_without_hash()):
        errors.append("V23.6 Integrity Certificate Hash 오류입니다.")
    if certificate.audit_status != "PASSED":
        errors.append("V23.6 Integrity Audit Status 오류입니다.")
    safe = bool(
        certificate.execution_blocked and not certificate.source_modified
        and not certificate.funds_reserved and not certificate.holdings_reserved
        and not certificate.transmit and not certificate.credentials_used
        and not certificate.market_data_api_called
        and not certificate.account_api_called
        and not certificate.network_accessed and not certificate.broker_api_called
        and not certificate.broker_order_created
        and not certificate.order_submitted
        and not certificate.live_execution_authorized
    )
    if not safe:
        errors.append("V23.6 Integrity Certificate 안전성 오류입니다.")
    return errors


def _result(policy, now, status, source, checks, errors, certificate=None):
    passed = status == "AUDITED_IN_MEMORY" and not errors
    return PortfolioAuditCertIntegrityV236Result(
        version=VERSION, created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()), result_status=status,
        source_ledger_result_id=getattr(source, "ledger_result_id", None),
        source_ledger_snapshot_hash=getattr(
            source, "ledger_snapshot_hash", None),
        source_latest_entry_hash=getattr(source, "latest_entry_hash", None),
        source_total_entry_count=getattr(source, "total_entry_count", 0),
        policy_checks_passed=checks.get("policy", False),
        source_checks_passed=checks.get("source", False),
        ledger_hash_chain_checks_passed=checks.get("chain", False),
        snapshot_hash_checks_passed=checks.get("snapshot", False),
        latest_hash_checks_passed=checks.get("latest", False),
        entry_count_checks_passed=checks.get("count", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        chronology_checks_passed=checks.get("chronology", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        certificate_hash_checks_passed=checks.get("certificate", False),
        safety_checks_passed=checks.get("safety", True),
        all_checks_passed=passed, audit_completed=passed,
        source_modified=False, funds_reserved=False, holdings_reserved=False,
        execution_blocked=True, transmit=False, credentials_used=False,
        market_data_api_called=False, account_api_called=False,
        network_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_execution_authorized=False, audit_policy=policy,
        certificate=certificate,
        findings=errors or [
            "V23.5 Portfolio Audit Certificate Ledger 무결성이 검증되었습니다.",
            "원장은 변경되지 않았고 외부 실행 기능은 차단되었습니다.",
        ],
    )


def audit_portfolio_audit_cert_ledger_v23_6(
    source: PortfolioAuditCertLedgerV235Result,
    operator: str,
    confirmation_text: str,
    *,
    policy: PortfolioAuditCertIntegrityV236Policy | None = None,
    now: datetime | None = None,
) -> PortfolioAuditCertIntegrityV236Result:
    selected = policy or PortfolioAuditCertIntegrityV236Policy()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors = validate_policy(selected)
    checks = {"policy": not errors, "safety": True}
    if not isinstance(operator, str) or not operator.strip():
        errors.append("V23.6 Operator가 필요합니다.")
    if confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.6 확인 문구가 일치하지 않습니다.")
    if not isinstance(source, PortfolioAuditCertLedgerV235Result):
        return _result(selected, current, "BLOCKED", source, checks, errors + [
            "Source는 V23.5 Portfolio Audit Certificate Ledger여야 합니다."])

    before = source.to_dict()
    checks["source"] = bool(
        source.version == selected.required_source_version
        and source.result_status == selected.required_source_status
        and source.all_checks_passed and source.certificate_recorded
        and _source_is_safe(source) and bool(source.entries)
    )
    if not checks["source"]:
        errors.append("V23.5 Source 상태 또는 실행 안전성 오류입니다.")

    chain_errors = verify_portfolio_audit_cert_ledger(source.entries)
    checks["chain"] = not chain_errors
    errors.extend(chain_errors)

    calculated_snapshot = ledger_snapshot_hash(source.entries)
    checks["snapshot"] = source.ledger_snapshot_hash == calculated_snapshot
    if not checks["snapshot"]:
        errors.append("V23.5 Ledger Snapshot Hash 오류입니다.")
    checks["latest"] = bool(
        source.entries and
        source.latest_entry_hash == source.entries[-1].entry_hash)
    if not checks["latest"]:
        errors.append("V23.5 Latest Entry Hash 오류입니다.")
    checks["count"] = source.total_entry_count == len(source.entries)
    if not checks["count"]:
        errors.append("V23.5 Ledger Entry Count 오류입니다.")
    checks["linkage"] = all(
        entry.source_audit_result_id
        and entry.source_audit_certificate_id
        and entry.source_audit_certificate_hash
        and entry.source_ledger_result_id
        and entry.source_ledger_hash
        and entry.source_ledger_snapshot_hash
        and entry.source_portfolio_hash
        and entry.audit_status == selected.required_audit_status
        for entry in source.entries
    )
    if not checks["linkage"]:
        errors.append("V23.5 Ledger Source Linkage 오류입니다.")
    try:
        checks["chronology"] = (
            current >= _parse_utc(source.created_at)
            and current >= _parse_utc(source.entries[-1].recorded_at))
    except (TypeError, ValueError):
        checks["chronology"] = False
    if not checks["chronology"]:
        errors.append("V23.6 감사 시간이 역순입니다.")
    checks["unchanged"] = source.to_dict() == before

    if errors:
        return _result(selected, current, "BLOCKED", source, checks, errors)
    payload = {
        "audit_certificate_id": str(uuid.uuid4()),
        "audited_at": current.isoformat(),
        "source_ledger_result_id": source.ledger_result_id,
        "source_ledger_snapshot_hash": calculated_snapshot,
        "source_latest_entry_hash": source.entries[-1].entry_hash,
        "source_first_entry_hash": source.entries[0].entry_hash,
        "source_total_entry_count": len(source.entries),
        "source_audit_certificate_hashes": tuple(
            entry.source_audit_certificate_hash for entry in source.entries),
        "audit_status": "PASSED", "operator": operator.strip(),
        "source_modified": False, "execution_blocked": True,
        "funds_reserved": False, "holdings_reserved": False,
        "transmit": False, "credentials_used": False,
        "market_data_api_called": False, "account_api_called": False,
        "network_accessed": False, "broker_api_called": False,
        "broker_order_created": False, "order_submitted": False,
        "live_execution_authorized": False,
    }
    certificate = PortfolioAuditCertIntegrityCertificateV236(
        **payload, certificate_hash=sha256_payload(payload))
    cert_errors = verify_integrity_audit_certificate(certificate)
    checks["certificate"] = not cert_errors
    errors.extend(cert_errors)
    checks["unchanged"] = source.to_dict() == before
    if not checks["unchanged"]:
        errors.append("V23.5 Source 변경이 감지되었습니다.")
    return _result(
        selected, current,
        "AUDITED_IN_MEMORY" if not errors else "BLOCKED",
        source, checks, errors, certificate if not errors else None)


def save_integrity_audit_result(
    result: PortfolioAuditCertIntegrityV236Result,
    output_directory: str | Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report = directory / f"portfolio_audit_cert_integrity_v23_6_{stamp}.json"
    latest = directory / "latest_portfolio_audit_cert_integrity_v23_6.json"
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path, result.latest_path = str(report), str(latest)
    return report, latest


def load_integrity_audit_result(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V23.6 Integrity Audit JSON은 object여야 합니다.")
    return payload
