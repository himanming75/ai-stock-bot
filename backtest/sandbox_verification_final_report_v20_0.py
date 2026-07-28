import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_verification_certificate_ledger_v19_9 import (
    SandboxVerificationCertificateLedgerV199Entry as SourceCertificateLedgerEntry,
    SandboxVerificationCertificateLedgerV199Result as SourceCertificateLedgerResult,
    verify_certificate_ledger_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "sandbox_verification_final_report_v20_0"
)
REQUIRED_FINAL_REPORT_TEXT = (
    "GENERATE IN MEMORY SANDBOX VERIFICATION FINAL REPORT V20.0"
)


@dataclass(frozen=True)
class SandboxVerificationFinalReportV200Policy:
    required_source_version: str = "V19.9"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_FINAL_REPORT_TEXT
    require_non_empty_ledger: bool = True
    require_same_operator: bool = True
    require_chronological_order: bool = True
    require_valid_hash_chain: bool = True
    require_source_linkage: bool = True
    require_source_unchanged: bool = True
    final_report_only: bool = True
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
class SandboxVerificationCertificateSummaryV200:
    sequence: int
    ledger_entry_id: str
    recorded_at: str
    verification_certificate_id: str
    verification_certificate_hash: str
    ledger_snapshot_hash: str
    verified_entry_count: int
    source_audit_ledger_result_id: str
    latest_audit_ledger_entry_id: str
    latest_audit_ledger_entry_hash: str
    latest_verification_ledger_snapshot_hash: str
    latest_final_report_hash: str
    latest_linked_final_report_hash: str
    latest_previous_final_report_hash: str
    latest_source_certificate_ledger_snapshot_hash: str
    latest_certificate_ledger_snapshot_hash: str
    latest_archived_certificate_ledger_snapshot_hash: str
    latest_carried_final_report_hash: str
    verification_status: str
    entry_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxVerificationFinalReportV200:
    final_report_id: str
    finalized_at: str
    report_status: str
    final_verification_status: str
    operator: str
    source_ledger_result_id: str
    source_latest_entry_id: str
    source_latest_entry_hash: str
    total_certificate_count: int
    latest_verification_certificate_id: str
    latest_verification_certificate_hash: str
    latest_source_ledger_snapshot_hash: str
    latest_verification_ledger_snapshot_hash: str
    latest_final_report_hash: str
    latest_linked_final_report_hash: str
    latest_previous_final_report_hash: str
    latest_source_certificate_ledger_snapshot_hash: str
    latest_certificate_ledger_snapshot_hash: str
    latest_archived_certificate_ledger_snapshot_hash: str
    latest_carried_final_report_hash: str
    certificate_ledger_snapshot_hash: str
    ledger_hash_chain_valid: bool
    source_linkage_valid: bool
    source_unchanged: bool
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
    certificate_summaries: tuple[
        SandboxVerificationCertificateSummaryV200,
        ...,
    ]
    report_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("report_hash", None)
        payload["certificate_summaries"] = [
            summary.to_dict() for summary in self.certificate_summaries
        ]
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["report_hash"] = self.report_hash
        return payload


@dataclass
class SandboxVerificationFinalReportV200Result:
    version: str
    created_at: str
    final_report_result_id: str
    result_status: str
    result_status_label: str
    final_verification_status: str
    operator: str | None
    source_ledger_result_id: str | None
    source_latest_entry_id: str | None
    source_latest_entry_hash: str | None
    latest_verification_ledger_snapshot_hash: str | None
    latest_final_report_hash: str | None
    latest_linked_final_report_hash: str | None
    latest_previous_final_report_hash: str | None
    latest_source_certificate_ledger_snapshot_hash: str | None
    latest_certificate_ledger_snapshot_hash: str | None
    latest_archived_certificate_ledger_snapshot_hash: str | None
    latest_carried_final_report_hash: str | None
    certificate_ledger_snapshot_hash: str | None
    report_id: str | None
    report_hash: str | None
    total_certificate_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    ledger_checks_passed: bool
    hash_chain_checks_passed: bool
    operator_checks_passed: bool
    chronology_checks_passed: bool
    linkage_checks_passed: bool
    source_unchanged_checks_passed: bool
    report_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    final_report_generated: bool
    source_modified: bool
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
    report_policy: SandboxVerificationFinalReportV200Policy
    report: SandboxVerificationFinalReportV200 | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["report_policy"] = self.report_policy.to_dict()
        payload["report"] = self.report.to_dict() if self.report else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def certificate_ledger_snapshot_hash(
    entries: tuple[
        SourceCertificateLedgerEntry,
        ...,
    ],
) -> str:
    return sha256_payload({"entries": [entry.to_dict() for entry in entries]})


def validate_policy(
    policy: SandboxVerificationFinalReportV200Policy,
) -> list[str]:
    if not isinstance(policy, SandboxVerificationFinalReportV200Policy):
        return ["Sandbox Verification Final Report Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V19.9",
        "required_source_status": "RECORDED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_FINAL_REPORT_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V20.0 기준과 다릅니다.")
    for name in (
        "require_non_empty_ledger",
        "require_same_operator",
        "require_chronological_order",
        "require_valid_hash_chain",
        "require_source_linkage",
        "require_source_unchanged",
        "final_report_only",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_access_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V20.0에서 True여야 합니다.")
    return errors


def verify_final_report(
    report: SandboxVerificationFinalReportV200,
) -> tuple[bool, list[str]]:
    if not isinstance(report, SandboxVerificationFinalReportV200):
        return False, ["Sandbox Verification Final Report 형식 오류입니다."]
    errors: list[str] = []
    if report.report_status != "FINALIZED_IN_MEMORY":
        errors.append("Final Report Status가 올바르지 않습니다.")
    if report.final_verification_status != "SANDBOX_VERIFICATION_COMPLETE":
        errors.append("Final Verification Status가 올바르지 않습니다.")
    if report.total_certificate_count != len(report.certificate_summaries):
        errors.append("Certificate Summary 개수가 올바르지 않습니다.")
    if not all(
        (
            report.ledger_hash_chain_valid,
            report.source_linkage_valid,
            report.source_unchanged,
            all(
                summary.verification_status == "PASSED"
                for summary in report.certificate_summaries
            ),
        )
    ):
        errors.append("Final Report 검증 결과가 올바르지 않습니다.")
    if report.report_hash != sha256_payload(report.payload_without_hash()):
        errors.append("Final Report Hash가 일치하지 않습니다.")
    if any(
        (
            report.paper_execution_authorized,
            report.automatic_execution_authorized,
            not report.execution_blocked,
            report.credentials_used,
            report.market_data_api_called,
            report.network_accessed,
            report.account_accessed,
            report.broker_api_called,
            report.order_submitted,
            report.live_execution_authorized,
        )
    ):
        errors.append("Final Report 실행 안전장치 오류입니다.")
    return not errors, errors


def _safe_source(
    source: (
        SourceCertificateLedgerResult
    ),
) -> bool:
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


def _empty_result(
    report_policy: SandboxVerificationFinalReportV200Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    **checks: bool,
) -> SandboxVerificationFinalReportV200Result:
    return SandboxVerificationFinalReportV200Result(
        version="V20.0",
        created_at=now.isoformat(),
        final_report_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Verification Final Report 차단"
            if status == "BLOCKED"
            else "Verification Final Report 실패"
        ),
        final_verification_status="BLOCKED",
        operator=None,
        source_ledger_result_id=None,
        source_latest_entry_id=None,
        source_latest_entry_hash=None,
        latest_verification_ledger_snapshot_hash=None,
        latest_final_report_hash=None,
        latest_linked_final_report_hash=None,
        latest_previous_final_report_hash=None,
        latest_source_certificate_ledger_snapshot_hash=None,
        latest_certificate_ledger_snapshot_hash=None,
        latest_archived_certificate_ledger_snapshot_hash=None,
        latest_carried_final_report_hash=None,
        certificate_ledger_snapshot_hash=None,
        report_id=None,
        report_hash=None,
        total_certificate_count=0,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        ledger_checks_passed=checks.get("ledger", False),
        hash_chain_checks_passed=checks.get("chain", False),
        operator_checks_passed=checks.get("operator", False),
        chronology_checks_passed=checks.get("chronology", False),
        linkage_checks_passed=checks.get("linkage", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        report_hash_checks_passed=False,
        safety_checks_passed=True,
        all_checks_passed=False,
        final_report_generated=False,
        source_modified=False,
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
        report_policy=report_policy,
        report=None,
        reasons=reasons,
        warnings=[
            "V20.0은 In-Memory Sandbox Verification 최종 보고서만 생성합니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=["입력과 V19.9 Certificate Ledger를 수동 확인합니다."],
    )


def generate_sandbox_verification_final_report_v20_0(
    source: Any,
    operator: str,
    confirmation_text: str,
    policy: SandboxVerificationFinalReportV200Policy | None = None,
    now: datetime | None = None,
) -> SandboxVerificationFinalReportV200Result:
    policy = policy or SandboxVerificationFinalReportV200Policy()
    now = now or datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator가 비어 있습니다.")
    if confirmation_text != getattr(policy, "required_confirmation_text", None):
        input_errors.append("수동 확인 문구가 올바르지 않습니다.")
    if policy_errors or input_errors:
        safe_policy = (
            policy
            if isinstance(policy, SandboxVerificationFinalReportV200Policy)
            else SandboxVerificationFinalReportV200Policy()
        )
        return _empty_result(
            safe_policy, now, "BLOCKED", policy_errors + input_errors,
            policy=not policy_errors, input=not input_errors,
        )
    if not isinstance(
        source,
        SourceCertificateLedgerResult,
    ):
        return _empty_result(
            policy, now, "FAILED",
            ["Source는 V19.9 Verification Certificate Ledger Result여야 합니다."],
            policy=True, input=True,
        )
    entries = tuple(source.entries)
    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.all_checks_passed
        and source.ledger_entry_recorded
        and entries
    ):
        source_errors.append("정상 V19.9 Certificate Ledger Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V19.9 Source 실행 안전장치 오류입니다.")
    if source_errors:
        return _empty_result(
            policy, now, "FAILED", source_errors, policy=True, input=True
        )
    source_before = canonical_json(source.to_dict())
    chain_valid, chain_errors = verify_certificate_ledger_chain(entries)
    if not chain_valid:
        return _empty_result(
            policy, now, "FAILED", chain_errors,
            policy=True, input=True, source=True, ledger=True,
        )
    latest = entries[-1]
    operators = {entry.operator for entry in entries}
    validation_errors: list[str] = []
    if len(operators) != 1 or operator not in operators:
        validation_errors.append("Operator가 V19.9 Certificate Ledger와 다릅니다.")
    try:
        if now < datetime.fromisoformat(latest.recorded_at):
            validation_errors.append("Final Report 시간이 최신 Ledger보다 빠릅니다.")
    except (TypeError, ValueError):
        validation_errors.append("최신 Ledger 시간이 올바르지 않습니다.")
    linkage_errors: list[str] = []
    for actual, expected, label in (
        (source.total_ledger_entry_count, len(entries), "Entry Count"),
        (source.latest_ledger_entry_id, latest.ledger_entry_id, "Entry ID"),
        (source.latest_ledger_entry_hash, latest.entry_hash, "Entry Hash"),
        (
            source.latest_verification_certificate_id,
            latest.verification_certificate_id,
            "Verification Certificate ID",
        ),
        (
            source.latest_verification_certificate_hash,
            latest.verification_certificate_hash,
            "Verification Certificate Hash",
        ),
        (
            source.latest_ledger_snapshot_hash,
            latest.ledger_snapshot_hash,
            "Ledger Snapshot Hash",
        ),
        (
            source.latest_verification_ledger_snapshot_hash,
            latest.latest_verification_ledger_snapshot_hash,
            "Verification Ledger Snapshot Hash",
        ),
        (
            source.latest_final_report_hash,
            latest.latest_final_report_hash,
            "Final Report Hash",
        ),
        (
            source.latest_linked_final_report_hash,
            latest.latest_linked_final_report_hash,
            "Linked Final Report Hash",
        ),
        (
            source.latest_previous_final_report_hash,
            latest.latest_previous_final_report_hash,
            "Previous Final Report Hash",
        ),
        (
            source.latest_source_certificate_ledger_snapshot_hash,
            latest.latest_source_certificate_ledger_snapshot_hash,
            "Source Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_certificate_ledger_snapshot_hash,
            latest.latest_certificate_ledger_snapshot_hash,
            "Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_archived_certificate_ledger_snapshot_hash,
            latest.latest_archived_certificate_ledger_snapshot_hash,
            "Archived Certificate Ledger Snapshot Hash",
        ),
        (
            source.latest_carried_final_report_hash,
            latest.latest_carried_final_report_hash,
            "Carried Final Report Hash",
        ),
    ):
        if actual != expected:
            linkage_errors.append(f"Source Latest {label} 연결이 다릅니다.")
    if validation_errors or linkage_errors:
        return _empty_result(
            policy, now, "BLOCKED", validation_errors + linkage_errors,
            policy=True, input=True, source=True, ledger=True, chain=True,
            operator=not any("Operator" in error for error in validation_errors),
            chronology=not any("시간" in error for error in validation_errors),
            linkage=not linkage_errors,
        )
    snapshot_hash = certificate_ledger_snapshot_hash(entries)
    summaries = tuple(
        SandboxVerificationCertificateSummaryV200(
            sequence=entry.sequence,
            ledger_entry_id=entry.ledger_entry_id,
            recorded_at=entry.recorded_at,
            verification_certificate_id=entry.verification_certificate_id,
            verification_certificate_hash=entry.verification_certificate_hash,
            ledger_snapshot_hash=entry.ledger_snapshot_hash,
            verified_entry_count=entry.verified_entry_count,
            source_audit_ledger_result_id=(
                entry.source_audit_ledger_result_id
            ),
            latest_audit_ledger_entry_id=(
                entry.latest_audit_ledger_entry_id
            ),
            latest_audit_ledger_entry_hash=(
                entry.latest_audit_ledger_entry_hash
            ),
            latest_verification_ledger_snapshot_hash=(
                entry.latest_verification_ledger_snapshot_hash
            ),
            latest_final_report_hash=entry.latest_final_report_hash,
            latest_linked_final_report_hash=(
                entry.latest_linked_final_report_hash
            ),
            latest_previous_final_report_hash=(
                entry.latest_previous_final_report_hash
            ),
            latest_source_certificate_ledger_snapshot_hash=(
                entry.latest_source_certificate_ledger_snapshot_hash
            ),
            latest_certificate_ledger_snapshot_hash=(
                entry.latest_certificate_ledger_snapshot_hash
            ),
            latest_archived_certificate_ledger_snapshot_hash=(
                entry.latest_archived_certificate_ledger_snapshot_hash
            ),
            latest_carried_final_report_hash=(
                entry.latest_carried_final_report_hash
            ),
            verification_status=entry.verification_status,
            entry_hash=entry.entry_hash,
        )
        for entry in entries
    )
    unchanged = source_before == canonical_json(source.to_dict())
    if not unchanged:
        return _empty_result(
            policy, now, "FAILED", ["Final Report 생성 중 Source가 변경되었습니다."],
            policy=True, input=True, source=True, ledger=True, chain=True,
            operator=True, chronology=True, linkage=True,
        )
    report_payload = {
        "final_report_id": str(uuid.uuid4()),
        "finalized_at": now.isoformat(),
        "report_status": "FINALIZED_IN_MEMORY",
        "final_verification_status": "SANDBOX_VERIFICATION_COMPLETE",
        "operator": operator,
        "source_ledger_result_id": source.ledger_result_id,
        "source_latest_entry_id": latest.ledger_entry_id,
        "source_latest_entry_hash": latest.entry_hash,
        "total_certificate_count": len(entries),
        "latest_verification_certificate_id": (
            latest.verification_certificate_id
        ),
        "latest_verification_certificate_hash": (
            latest.verification_certificate_hash
        ),
        "latest_source_ledger_snapshot_hash": latest.ledger_snapshot_hash,
        "latest_verification_ledger_snapshot_hash": (
            latest.latest_verification_ledger_snapshot_hash
        ),
        "latest_final_report_hash": latest.latest_final_report_hash,
        "latest_linked_final_report_hash": (
            latest.latest_linked_final_report_hash
        ),
        "latest_previous_final_report_hash": (
            latest.latest_previous_final_report_hash
        ),
        "latest_source_certificate_ledger_snapshot_hash": (
            latest.latest_source_certificate_ledger_snapshot_hash
        ),
        "latest_certificate_ledger_snapshot_hash": (
            latest.latest_certificate_ledger_snapshot_hash
        ),
        "latest_archived_certificate_ledger_snapshot_hash": (
            latest.latest_archived_certificate_ledger_snapshot_hash
        ),
        "latest_carried_final_report_hash": (
            latest.latest_carried_final_report_hash
        ),
        "certificate_ledger_snapshot_hash": snapshot_hash,
        "ledger_hash_chain_valid": True,
        "source_linkage_valid": True,
        "source_unchanged": True,
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
        "certificate_summaries": summaries,
    }
    hash_payload = dict(report_payload)
    hash_payload["certificate_summaries"] = [
        summary.to_dict() for summary in summaries
    ]
    report = SandboxVerificationFinalReportV200(
        **report_payload, report_hash=sha256_payload(hash_payload)
    )
    report_valid, report_errors = verify_final_report(report)
    if not report_valid:
        return _empty_result(
            policy, now, "FAILED", report_errors,
            policy=True, input=True, source=True, ledger=True, chain=True,
            operator=True, chronology=True, linkage=True, unchanged=True,
        )
    return SandboxVerificationFinalReportV200Result(
        version="V20.0",
        created_at=now.isoformat(),
        final_report_result_id=str(uuid.uuid4()),
        result_status="FINALIZED_IN_MEMORY",
        result_status_label=(
            "Sandbox Verification Final Report Archive Certificate Audit "
            "Final Report 생성 완료"
        ),
        final_verification_status="SANDBOX_VERIFICATION_COMPLETE",
        operator=operator,
        source_ledger_result_id=source.ledger_result_id,
        source_latest_entry_id=latest.ledger_entry_id,
        source_latest_entry_hash=latest.entry_hash,
        latest_verification_ledger_snapshot_hash=(
            latest.latest_verification_ledger_snapshot_hash
        ),
        latest_final_report_hash=latest.latest_final_report_hash,
        latest_linked_final_report_hash=(
            latest.latest_linked_final_report_hash
        ),
        latest_previous_final_report_hash=(
            latest.latest_previous_final_report_hash
        ),
        latest_source_certificate_ledger_snapshot_hash=(
            latest.latest_source_certificate_ledger_snapshot_hash
        ),
        latest_certificate_ledger_snapshot_hash=(
            latest.latest_certificate_ledger_snapshot_hash
        ),
        latest_archived_certificate_ledger_snapshot_hash=(
            latest.latest_archived_certificate_ledger_snapshot_hash
        ),
        latest_carried_final_report_hash=(
            latest.latest_carried_final_report_hash
        ),
        certificate_ledger_snapshot_hash=snapshot_hash,
        report_id=report.final_report_id,
        report_hash=report.report_hash,
        total_certificate_count=len(entries),
        policy_checks_passed=True,
        input_checks_passed=True,
        source_checks_passed=True,
        ledger_checks_passed=True,
        hash_chain_checks_passed=True,
        operator_checks_passed=True,
        chronology_checks_passed=True,
        linkage_checks_passed=True,
        source_unchanged_checks_passed=True,
        report_hash_checks_passed=True,
        safety_checks_passed=True,
        all_checks_passed=True,
        final_report_generated=True,
        source_modified=False,
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
        report_policy=policy,
        report=report,
        reasons=[
            f"V19.9 Certificate Ledger Entry {len(entries)}개를 검증했습니다.",
            "Certificate Ledger Hash Chain과 Source Linkage가 유효합니다.",
            "최종 상태는 SANDBOX_VERIFICATION_COMPLETE입니다.",
        ],
        warnings=[
            "V20.0 Final Report는 실행 또는 주문 권한을 부여하지 않습니다.",
            "V19.9 Certificate Ledger는 변경되지 않았습니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "Final Report Hash와 Certificate Ledger Snapshot Hash를 보관합니다.",
            "실제 거래와 분리된 상태로 결과를 수동 검토합니다.",
        ],
    )


def save_final_report_result(
    result: SandboxVerificationFinalReportV200Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report_path = output_directory / (
        f"sandbox_verification_final_report_v20_0_{stamp}.json"
    )
    latest_path = output_directory / (
        "latest_sandbox_verification_final_report_v20_0.json"
    )
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_final_report_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Verification Final Report JSON은 object여야 합니다.")
    return payload
