"""V23.4 Offline Paper Portfolio Ledger Integrity Audit.

Performs a read-only integrity audit of a successful V23.3 portfolio
validation ledger. No network, broker, account API, credential, order
submission, fund reservation, or live execution capability is present.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

from backtest.offline_paper_portfolio_ledger_v23_3 import (
    GENESIS_HASH,
    PortfolioValidationEntryV233,
    PortfolioValidationLedgerV233Result,
    sha256_payload,
    verify_portfolio_validation_ledger,
)


VERSION = "V23.4"
CONFIRMATION_TEXT = "AUDIT OFFLINE PAPER PORTFOLIO LEDGER V23.4"
OUTPUT_DIRECTORY = Path("backtest_outputs")


@dataclass(frozen=True)
class PortfolioLedgerAuditV234Policy:
    required_source_version: str = "V23.3"
    required_source_status: str = "RECORDED_IN_MEMORY"
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
class PortfolioLedgerAuditFindingV234:
    sequence: int
    validation_id: str
    sequence_valid: bool
    previous_hash_valid: bool
    entry_hash_valid: bool
    validation_id_unique: bool
    chronology_valid: bool
    source_linkage_valid: bool
    safety_valid: bool
    finding_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioLedgerAuditCertificateV234:
    audit_certificate_id: str
    audited_at: str
    audit_status: str
    source_ledger_result_id: str
    source_ledger_id: str
    source_ledger_hash: str
    source_ledger_snapshot_hash: str
    latest_entry_hash: str
    source_portfolio_hash: str
    total_entry_count: int
    source_unchanged: bool
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
    findings: tuple[PortfolioLedgerAuditFindingV234, ...]
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash")
        payload["findings"] = [item.to_dict() for item in self.findings]
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioLedgerAuditV234Result:
    version: str
    created_at: str
    audit_result_id: str
    result_status: str
    source_ledger_result_id: str | None
    source_ledger_hash: str | None
    source_ledger_snapshot_hash: str | None
    audit_certificate_id: str | None
    audit_certificate_hash: str | None
    audited_entry_count: int
    policy_checks_passed: bool
    source_checks_passed: bool
    ledger_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    source_linkage_checks_passed: bool
    entry_safety_checks_passed: bool
    source_unchanged_checks_passed: bool
    certificate_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    audit_completed: bool
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
    audit_policy: PortfolioLedgerAuditV234Policy
    certificate: PortfolioLedgerAuditCertificateV234 | None
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_policy"] = self.audit_policy.to_dict()
        payload["certificate"] = self.certificate.to_dict() if self.certificate else None
        return payload


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("시간 형식 오류입니다.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("시간대가 필요합니다.")
    return parsed.astimezone(timezone.utc)


def _snapshot_hash(entries: tuple[PortfolioValidationEntryV233, ...]) -> str:
    return sha256_payload({"entries": [entry.to_dict() for entry in entries]})


def _safe_entry(entry: PortfolioValidationEntryV233) -> bool:
    return bool(
        not entry.source_mutated
        and not entry.funds_reserved
        and not entry.holdings_reserved
        and not entry.transmit
        and not entry.credentials_used
        and not entry.market_data_api_called
        and not entry.account_api_called
        and not entry.network_accessed
        and not entry.broker_api_called
        and not entry.broker_order_created
        and not entry.order_submitted
        and not entry.live_execution_authorized
    )


def validate_policy(policy: PortfolioLedgerAuditV234Policy) -> list[str]:
    if not isinstance(policy, PortfolioLedgerAuditV234Policy):
        return ["V23.4 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V23.3":
        errors.append("V23.4 Source Version 정책 오류입니다.")
    if policy.required_source_status != "RECORDED_IN_MEMORY":
        errors.append("V23.4 Source Status 정책 오류입니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.4 확인 문구 정책 오류입니다.")
    for name, value in policy.to_dict().items():
        if name.startswith("read_only_") or name.endswith(("_disabled", "_forbidden")):
            if value is not True:
                errors.append(f"{name}는 True여야 합니다.")
    return errors


def create_findings(
    entries: tuple[PortfolioValidationEntryV233, ...],
) -> tuple[PortfolioLedgerAuditFindingV234, ...]:
    findings = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    seen_ids: set[str] = set()
    for expected, entry in enumerate(entries, start=1):
        try:
            current_time = _parse_utc(entry.created_at)
            chronology = previous_time is None or current_time >= previous_time
        except (TypeError, ValueError):
            current_time, chronology = None, False
        checks = (
            entry.sequence == expected,
            entry.previous_entry_hash == previous_hash,
            entry.entry_hash == sha256_payload(entry.payload_without_hash()),
            entry.validation_id not in seen_ids,
            chronology,
            bool(
                entry.source_update_result_id
                and entry.source_portfolio_snapshot_id
                and isinstance(entry.source_portfolio_hash, str)
                and len(entry.source_portfolio_hash) == 64
                and entry.validation_status == "VERIFIED_OFFLINE"
            ),
            _safe_entry(entry),
        )
        findings.append(
            PortfolioLedgerAuditFindingV234(
                sequence=entry.sequence,
                validation_id=entry.validation_id,
                sequence_valid=checks[0],
                previous_hash_valid=checks[1],
                entry_hash_valid=checks[2],
                validation_id_unique=checks[3],
                chronology_valid=checks[4],
                source_linkage_valid=checks[5],
                safety_valid=checks[6],
                finding_status="PASSED" if all(checks) else "FAILED",
            )
        )
        seen_ids.add(entry.validation_id)
        previous_hash = entry.entry_hash
        if current_time is not None:
            previous_time = current_time
    return tuple(findings)


def verify_audit_certificate(
    certificate: PortfolioLedgerAuditCertificateV234 | None,
) -> list[str]:
    if not isinstance(certificate, PortfolioLedgerAuditCertificateV234):
        return ["V23.4 Audit Certificate 형식 오류입니다."]
    if certificate.certificate_hash != sha256_payload(certificate.payload_without_hash()):
        return ["V23.4 Audit Certificate Hash 오류입니다."]
    return []


def _result(
    policy: PortfolioLedgerAuditV234Policy,
    now: datetime,
    source: PortfolioValidationLedgerV233Result | None,
    errors: list[str],
    certificate: PortfolioLedgerAuditCertificateV234 | None = None,
) -> PortfolioLedgerAuditV234Result:
    passed = not errors and certificate is not None
    ledger = source.ledger if source else None
    findings = certificate.findings if certificate else ()
    snapshot = _snapshot_hash(ledger.entries) if ledger else None
    return PortfolioLedgerAuditV234Result(
        version=VERSION,
        created_at=now.isoformat(),
        audit_result_id=str(uuid.uuid4()),
        result_status="AUDITED_IN_MEMORY" if passed else "BLOCKED",
        source_ledger_result_id=source.ledger_result_id if source else None,
        source_ledger_hash=ledger.ledger_hash if ledger else None,
        source_ledger_snapshot_hash=snapshot,
        audit_certificate_id=certificate.audit_certificate_id if certificate else None,
        audit_certificate_hash=certificate.certificate_hash if certificate else None,
        audited_entry_count=len(ledger.entries) if ledger else 0,
        policy_checks_passed=not validate_policy(policy),
        source_checks_passed=bool(source and source.all_checks_passed),
        ledger_checks_passed=bool(ledger and not verify_portfolio_validation_ledger(ledger)),
        duplicate_checks_passed=bool(findings and all(x.validation_id_unique for x in findings)),
        chronology_checks_passed=bool(findings and all(x.chronology_valid for x in findings)),
        source_linkage_checks_passed=bool(findings and all(x.source_linkage_valid for x in findings)),
        entry_safety_checks_passed=bool(findings and all(x.safety_valid for x in findings)),
        source_unchanged_checks_passed=passed,
        certificate_hash_checks_passed=bool(certificate and not verify_audit_certificate(certificate)),
        safety_checks_passed=True,
        all_checks_passed=passed,
        audit_completed=passed,
        ledger_modified=False,
        funds_reserved=False,
        holdings_reserved=False,
        execution_blocked=True,
        transmit=False,
        credentials_used=False,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_execution_authorized=False,
        audit_policy=policy,
        certificate=certificate,
        reasons=errors or [
            "V23.3 Portfolio Validation Ledger를 읽기 전용으로 감사했습니다.",
            "Network·Broker API·실제 주문·Live Execution은 차단되었습니다.",
        ],
    )


def audit_portfolio_validation_ledger_v23_4(
    source: PortfolioValidationLedgerV233Result,
    operator: str,
    confirmation_text: str,
    *,
    policy: PortfolioLedgerAuditV234Policy | None = None,
    now: datetime | None = None,
) -> PortfolioLedgerAuditV234Result:
    selected = policy or PortfolioLedgerAuditV234Policy()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors = validate_policy(selected)
    if not isinstance(operator, str) or not operator.strip():
        errors.append("V23.4 Operator가 필요합니다.")
    if confirmation_text != CONFIRMATION_TEXT:
        errors.append("V23.4 확인 문구가 일치하지 않습니다.")
    if not isinstance(source, PortfolioValidationLedgerV233Result):
        errors.append("Source는 V23.3 Ledger Result여야 합니다.")
        return _result(selected, current, None, errors)
    before = source.to_dict()
    if source.version != selected.required_source_version:
        errors.append("V23.3 Source Version 오류입니다.")
    if source.result_status != selected.required_source_status or not source.all_checks_passed:
        errors.append("V23.3 Source Status 오류입니다.")
    ledger = source.ledger
    if ledger is None or not ledger.entries:
        errors.append("V23.3 Ledger가 비어 있습니다.")
        return _result(selected, current, source, errors)
    errors.extend(verify_portfolio_validation_ledger(ledger))
    findings = create_findings(ledger.entries)
    if not findings or not all(item.finding_status == "PASSED" for item in findings):
        errors.append("V23.3 Ledger Entry 무결성 감사 실패입니다.")
    if current < _parse_utc(ledger.entries[-1].created_at):
        errors.append("V23.4 감사 시간이 역순입니다.")
    if source.to_dict() != before:
        errors.append("V23.3 Source가 변경되었습니다.")
    if errors:
        return _result(selected, current, source, errors)

    snapshot = _snapshot_hash(ledger.entries)
    payload = {
        "audit_certificate_id": str(uuid.uuid4()),
        "audited_at": current.isoformat(),
        "audit_status": "PASSED",
        "source_ledger_result_id": source.ledger_result_id,
        "source_ledger_id": ledger.ledger_id,
        "source_ledger_hash": ledger.ledger_hash,
        "source_ledger_snapshot_hash": snapshot,
        "latest_entry_hash": ledger.entries[-1].entry_hash,
        "source_portfolio_hash": ledger.source_portfolio_hash,
        "total_entry_count": len(ledger.entries),
        "source_unchanged": source.to_dict() == before,
        "execution_blocked": True,
        "funds_reserved": False,
        "holdings_reserved": False,
        "transmit": False,
        "credentials_used": False,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "broker_order_created": False,
        "order_submitted": False,
        "live_execution_authorized": False,
        "findings": findings,
    }
    certificate = PortfolioLedgerAuditCertificateV234(
        **payload,
        certificate_hash=sha256_payload({
            **payload,
            "findings": [item.to_dict() for item in findings],
        }),
    )
    return _result(selected, current, source, [], certificate)


def save_audit_result(
    result: PortfolioLedgerAuditV234Result,
    output_directory: str | Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report = directory / f"portfolio_audit_v23_4_{stamp}.json"
    latest = directory / "latest_portfolio_audit_v23_4.json"
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path, result.latest_path = str(report), str(latest)
    return report, latest


def load_audit_result(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V23.4 Audit JSON은 object여야 합니다.")
    return payload
