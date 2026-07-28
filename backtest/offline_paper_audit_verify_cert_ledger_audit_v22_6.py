import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_ledger_v21_5 import sha256_payload
from backtest.offline_paper_audit_verify_cert_ledger_v22_5 import (
    OfflinePaperAuditVerifyCertLedgerV225Entry,
    OfflinePaperAuditVerifyCertLedgerV225Result,
    ledger_snapshot_hash,
    verify_ledger_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "offline_paper_audit_verify_cert_ledger_audit_v22_6"
)
CONFIRMATION_TEXT = "AUDIT OFFLINE PAPER AUDIT VERIFICATION CERTIFICATE LEDGER V22.6"


@dataclass(frozen=True)
class OfflinePaperAuditVerifyCertLedgerAuditV226Policy:
    required_source_version: str = "V22.5"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_confirmation_text: str = CONFIRMATION_TEXT
    require_operator: bool = True
    require_non_empty_ledger: bool = True
    require_valid_hash_chain: bool = True
    require_unique_certificate_ids: bool = True
    require_chronological_order: bool = True
    require_safe_entries: bool = True
    require_snapshot_hash: bool = True
    require_source_unchanged: bool = True
    read_only_audit: bool = True
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
class OfflinePaperAuditVerifyCertLedgerAuditFindingV226:
    sequence: int
    ledger_entry_id: str
    sequence_valid: bool
    previous_hash_valid: bool
    entry_hash_valid: bool
    certificate_id_unique: bool
    chronology_valid: bool
    safety_valid: bool
    finding_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePaperAuditVerifyCertLedgerAuditCertificateV226:
    audit_certificate_id: str
    audited_at: str
    audit_status: str
    source_ledger_result_id: str
    source_ledger_snapshot_hash: str
    latest_ledger_entry_hash: str
    latest_source_verification_certificate_hash: str
    total_ledger_entry_count: int
    ledger_hash_chain_valid: bool
    snapshot_hash_valid: bool
    source_unchanged: bool
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    network_accessed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    findings: tuple[OfflinePaperAuditVerifyCertLedgerAuditFindingV226, ...]
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash")
        payload["findings"] = [finding.to_dict() for finding in self.findings]
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OfflinePaperAuditVerifyCertLedgerAuditV226Result:
    version: str
    created_at: str
    audit_result_id: str
    result_status: str
    source_ledger_result_id: str | None
    audited_entry_count: int
    source_ledger_snapshot_hash: str | None
    audit_certificate_id: str | None
    audit_certificate_hash: str | None
    policy_checks_passed: bool
    source_checks_passed: bool
    ledger_hash_chain_checks_passed: bool
    snapshot_hash_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
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
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    audit_policy: OfflinePaperAuditVerifyCertLedgerAuditV226Policy
    certificate: OfflinePaperAuditVerifyCertLedgerAuditCertificateV226 | None
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_policy"] = self.audit_policy.to_dict()
        payload["certificate"] = self.certificate.to_dict() if self.certificate else None
        return payload


def validate_policy(policy: OfflinePaperAuditVerifyCertLedgerAuditV226Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperAuditVerifyCertLedgerAuditV226Policy):
        return ["V22.6 Policy 형식 오류입니다."]
    errors: list[str] = []
    if policy.required_source_version != "V22.5":
        errors.append("V22.6 Source Version은 V22.5여야 합니다.")
    if policy.required_source_status != "RECORDED_IN_MEMORY":
        errors.append("V22.6 Source Status가 올바르지 않습니다.")
    if policy.required_confirmation_text != CONFIRMATION_TEXT:
        errors.append("V22.6 확인 문구 정책이 올바르지 않습니다.")
    for name, value in policy.to_dict().items():
        if name.startswith(("require_", "read_only_")) or name.endswith("_disabled"):
            if value is not True:
                errors.append(f"{name}는 V22.6에서 True여야 합니다.")
    return errors


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_entry(entry: OfflinePaperAuditVerifyCertLedgerV225Entry) -> bool:
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


def create_findings(
    entries: tuple[OfflinePaperAuditVerifyCertLedgerV225Entry, ...],
) -> tuple[OfflinePaperAuditVerifyCertLedgerAuditFindingV226, ...]:
    findings = []
    previous_hash = "0" * 64
    previous_time: datetime | None = None
    seen: set[str] = set()
    for expected, entry in enumerate(entries, start=1):
        try:
            current_time = _parse_time(entry.recorded_at)
            chronology_valid = previous_time is None or current_time >= previous_time
        except (TypeError, ValueError):
            current_time = None
            chronology_valid = False
        unique = entry.source_verification_certificate_id not in seen
        checks = (
            entry.sequence == expected,
            entry.previous_entry_hash == previous_hash,
            entry.entry_hash == sha256_payload(entry.payload_without_hash()),
            unique,
            chronology_valid,
            _safe_entry(entry),
        )
        findings.append(
            OfflinePaperAuditVerifyCertLedgerAuditFindingV226(
                sequence=entry.sequence,
                ledger_entry_id=entry.ledger_entry_id,
                sequence_valid=checks[0],
                previous_hash_valid=checks[1],
                entry_hash_valid=checks[2],
                certificate_id_unique=checks[3],
                chronology_valid=checks[4],
                safety_valid=checks[5],
                finding_status="PASSED" if all(checks) else "FAILED",
            )
        )
        seen.add(entry.source_verification_certificate_id)
        previous_hash = entry.entry_hash
        if current_time is not None:
            previous_time = current_time
    return tuple(findings)


def verify_audit_certificate(
    certificate: OfflinePaperAuditVerifyCertLedgerAuditCertificateV226 | None,
) -> tuple[bool, list[str]]:
    if not isinstance(certificate, OfflinePaperAuditVerifyCertLedgerAuditCertificateV226):
        return False, ["V22.6 Audit Certificate 형식 오류입니다."]
    expected = sha256_payload(certificate.payload_without_hash())
    return (
        certificate.certificate_hash == expected,
        [] if certificate.certificate_hash == expected else ["V22.6 Certificate Hash 오류입니다."],
    )


def _result(
    policy: OfflinePaperAuditVerifyCertLedgerAuditV226Policy,
    now: datetime,
    source: OfflinePaperAuditVerifyCertLedgerV225Result | None,
    errors: list[str],
    certificate: OfflinePaperAuditVerifyCertLedgerAuditCertificateV226 | None = None,
) -> OfflinePaperAuditVerifyCertLedgerAuditV226Result:
    passed = not errors and certificate is not None
    entries = source.entries if source else ()
    findings = certificate.findings if certificate else ()
    return OfflinePaperAuditVerifyCertLedgerAuditV226Result(
        version="V22.6", created_at=now.isoformat(), audit_result_id=str(uuid.uuid4()),
        result_status="AUDITED_IN_MEMORY" if passed else "BLOCKED",
        source_ledger_result_id=source.ledger_result_id if source else None,
        audited_entry_count=len(entries),
        source_ledger_snapshot_hash=source.ledger_snapshot_hash if source else None,
        audit_certificate_id=certificate.audit_certificate_id if certificate else None,
        audit_certificate_hash=certificate.certificate_hash if certificate else None,
        policy_checks_passed=not validate_policy(policy),
        source_checks_passed=bool(source and source.all_checks_passed),
        ledger_hash_chain_checks_passed=bool(source and verify_ledger_chain(entries)[0]),
        snapshot_hash_checks_passed=bool(
            source and source.ledger_snapshot_hash == ledger_snapshot_hash(entries)
        ),
        duplicate_checks_passed=bool(findings and all(x.certificate_id_unique for x in findings)),
        chronology_checks_passed=bool(findings and all(x.chronology_valid for x in findings)),
        entry_safety_checks_passed=bool(findings and all(x.safety_valid for x in findings)),
        source_unchanged_checks_passed=passed,
        certificate_hash_checks_passed=bool(certificate and verify_audit_certificate(certificate)[0]),
        safety_checks_passed=True, all_checks_passed=passed, audit_completed=passed,
        ledger_modified=False, funds_reserved=False, holdings_reserved=False,
        execution_blocked=True, market_data_api_called=False, account_api_called=False,
        network_accessed=False, broker_api_called=False, broker_order_created=False,
        order_submitted=False, live_execution_authorized=False, audit_policy=policy,
        certificate=certificate, reasons=errors or [
            "V22.5 Certificate Ledger가 읽기 전용으로 감사되었습니다.",
            "외부 API·Network·Broker 주문·Live Execution은 차단되었습니다.",
        ],
    )


def audit_offline_paper_audit_verification_certificate_ledger_v22_6(
    source: OfflinePaperAuditVerifyCertLedgerV225Result,
    *,
    operator: str,
    confirmation_text: str,
    policy: OfflinePaperAuditVerifyCertLedgerAuditV226Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperAuditVerifyCertLedgerAuditV226Result:
    selected = policy or OfflinePaperAuditVerifyCertLedgerAuditV226Policy()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors = validate_policy(selected)
    if not isinstance(operator, str) or not operator.strip():
        errors.append("V22.6 Operator가 필요합니다.")
    if confirmation_text != CONFIRMATION_TEXT:
        errors.append("V22.6 확인 문구가 일치하지 않습니다.")
    if not isinstance(source, OfflinePaperAuditVerifyCertLedgerV225Result):
        errors.append("Source는 V22.5 Ledger Result여야 합니다.")
        return _result(selected, current, None, errors)
    before = source.to_dict()
    if source.version != selected.required_source_version:
        errors.append("V22.5 Source Version 오류입니다.")
    if source.result_status != selected.required_source_status or not source.all_checks_passed:
        errors.append("V22.5 Source Status 오류입니다.")
    if not source.entries:
        errors.append("V22.5 Ledger가 비어 있습니다.")
    chain_valid, chain_errors = verify_ledger_chain(source.entries)
    if not chain_valid:
        errors.extend(chain_errors)
    if source.ledger_snapshot_hash != ledger_snapshot_hash(source.entries):
        errors.append("V22.5 Ledger Snapshot Hash 오류입니다.")
    findings = create_findings(source.entries)
    if not all(item.finding_status == "PASSED" for item in findings):
        errors.append("V22.5 Ledger Entry 감사 실패입니다.")
    if source.entries and current < _parse_time(source.entries[-1].recorded_at):
        errors.append("V22.6 감사 시간이 역순입니다.")
    if source.to_dict() != before:
        errors.append("V22.5 Source가 변경되었습니다.")
    if errors:
        return _result(selected, current, source, errors)
    payload = {
        "audit_certificate_id": str(uuid.uuid4()),
        "audited_at": current.isoformat(),
        "audit_status": "PASSED",
        "source_ledger_result_id": source.ledger_result_id,
        "source_ledger_snapshot_hash": source.ledger_snapshot_hash,
        "latest_ledger_entry_hash": source.latest_ledger_entry_hash,
        "latest_source_verification_certificate_hash": (
            source.latest_source_verification_certificate_hash
        ),
        "total_ledger_entry_count": len(source.entries),
        "ledger_hash_chain_valid": True,
        "snapshot_hash_valid": True,
        "source_unchanged": True,
        "execution_blocked": True,
        "funds_reserved": False,
        "holdings_reserved": False,
        "network_accessed": False,
        "broker_api_called": False,
        "order_submitted": False,
        "live_execution_authorized": False,
        "findings": findings,
    }
    certificate = OfflinePaperAuditVerifyCertLedgerAuditCertificateV226(
        **payload, certificate_hash=sha256_payload({
            **payload, "findings": [finding.to_dict() for finding in findings]
        })
    )
    return _result(selected, current, source, [], certificate)


def save_result(
    result: OfflinePaperAuditVerifyCertLedgerAuditV226Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report = output_directory / f"audit_{stamp}.json"
    latest = output_directory / "latest_audit.json"
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    result.report_path, result.latest_path = str(report), str(latest)
    return report, latest


def load_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V22.6 Audit JSON은 object여야 합니다.")
    return payload
