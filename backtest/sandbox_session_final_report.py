import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_risk_decision_ledger import (
    SandboxRiskDecisionLedgerResult,
    verify_ledger_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "sandbox_session_final_report"
)
REQUIRED_FINAL_REPORT_TEXT = (
    "GENERATE IN MEMORY SANDBOX SESSION FINAL REPORT"
)
VALID_GATE_ACTIONS = {"PROCEED", "REVIEW", "PAUSE", "BLOCK"}


@dataclass(frozen=True)
class SandboxSessionFinalReportPolicy:
    required_source_version: str = "V14.9"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_FINAL_REPORT_TEXT
    require_non_empty_ledger: bool = True
    require_same_operator: bool = True
    require_single_session: bool = True
    require_chronological_order: bool = True
    require_valid_hash_chain: bool = True
    require_source_linkage: bool = True
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
class SandboxSessionDecisionSummary:
    sequence: int
    ledger_entry_id: str
    gate_decision_id: str
    recorded_at: str
    source_risk_status: str
    source_risk_action: str
    gate_action: str
    manual_review_required: bool
    sandbox_progress_allowed: bool
    entry_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxSessionReport:
    session_report_id: str
    finalized_at: str
    report_status: str
    session_id: str
    operator: str
    source_ledger_result_id: str
    source_latest_entry_id: str
    source_latest_entry_hash: str
    total_decision_count: int
    proceed_count: int
    review_count: int
    pause_count: int
    block_count: int
    final_gate_action: str
    final_session_outcome: str
    manual_review_required: bool
    sandbox_progress_allowed: bool
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
    decision_summaries: tuple[SandboxSessionDecisionSummary, ...]
    report_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("report_hash", None)
        payload["decision_summaries"] = [
            summary.to_dict() for summary in self.decision_summaries
        ]
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["report_hash"] = self.report_hash
        return payload


@dataclass
class SandboxSessionFinalReportResult:
    version: str
    created_at: str
    final_report_result_id: str
    result_status: str
    result_status_label: str
    session_id: str | None
    operator: str | None
    source_ledger_result_id: str | None
    source_latest_entry_id: str | None
    source_latest_entry_hash: str | None
    report_id: str | None
    report_hash: str | None
    final_gate_action: str
    final_session_outcome: str
    total_decision_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    ledger_checks_passed: bool
    hash_chain_checks_passed: bool
    session_checks_passed: bool
    operator_checks_passed: bool
    chronology_checks_passed: bool
    linkage_checks_passed: bool
    report_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    final_report_generated: bool
    manual_review_required: bool
    sandbox_progress_allowed: bool
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
    report_policy: SandboxSessionFinalReportPolicy
    report: SandboxSessionReport | None
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
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_policy(
    policy: SandboxSessionFinalReportPolicy,
) -> list[str]:
    if not isinstance(policy, SandboxSessionFinalReportPolicy):
        return ["Sandbox Session Final Report Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.9",
        "required_source_status": "RECORDED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_FINAL_REPORT_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V15.0 기준과 다릅니다.")
    for name in (
        "require_non_empty_ledger",
        "require_same_operator",
        "require_single_session",
        "require_chronological_order",
        "require_valid_hash_chain",
        "require_source_linkage",
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
            errors.append(f"{name}는 V15.0에서 True여야 합니다.")
    return errors


def verify_session_report(
    report: SandboxSessionReport,
) -> tuple[bool, list[str]]:
    if not isinstance(report, SandboxSessionReport):
        return False, ["Sandbox Session Report 형식이 올바르지 않습니다."]
    errors: list[str] = []
    if report.report_status != "FINALIZED_IN_MEMORY":
        errors.append("Session Report Status가 올바르지 않습니다.")
    if report.final_gate_action not in VALID_GATE_ACTIONS:
        errors.append("Final Gate Action이 올바르지 않습니다.")
    expected_outcome = {
        "PROCEED": "SANDBOX_COMPLETE",
        "REVIEW": "MANUAL_REVIEW_REQUIRED",
        "PAUSE": "PAUSED",
        "BLOCK": "BLOCKED",
    }.get(report.final_gate_action)
    if report.final_session_outcome != expected_outcome:
        errors.append("Final Session Outcome 매핑이 올바르지 않습니다.")
    counts = (
        report.proceed_count
        + report.review_count
        + report.pause_count
        + report.block_count
    )
    if counts != report.total_decision_count:
        errors.append("Gate Action 합계가 Total Decision Count와 다릅니다.")
    if len(report.decision_summaries) != report.total_decision_count:
        errors.append("Decision Summary 개수가 올바르지 않습니다.")
    if report.report_hash != sha256_payload(report.payload_without_hash()):
        errors.append("Session Report Hash가 일치하지 않습니다.")
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
        errors.append("Session Report 실행 안전장치가 올바르지 않습니다.")
    return not errors, errors


def _safe_source(source: SandboxRiskDecisionLedgerResult) -> bool:
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
    report_policy: SandboxSessionFinalReportPolicy,
    now: datetime,
    status: str,
    reasons: list[str],
    **checks: bool,
) -> SandboxSessionFinalReportResult:
    return SandboxSessionFinalReportResult(
        version="V15.0",
        created_at=now.isoformat(),
        final_report_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Final Report 차단" if status == "BLOCKED" else "Final Report 실패"
        ),
        session_id=None,
        operator=None,
        source_ledger_result_id=None,
        source_latest_entry_id=None,
        source_latest_entry_hash=None,
        report_id=None,
        report_hash=None,
        final_gate_action="BLOCK",
        final_session_outcome="BLOCKED",
        total_decision_count=0,
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        ledger_checks_passed=checks.get("ledger", False),
        hash_chain_checks_passed=checks.get("chain", False),
        session_checks_passed=checks.get("session", False),
        operator_checks_passed=checks.get("operator", False),
        chronology_checks_passed=checks.get("chronology", False),
        linkage_checks_passed=checks.get("linkage", False),
        report_hash_checks_passed=False,
        safety_checks_passed=True,
        all_checks_passed=False,
        final_report_generated=False,
        manual_review_required=True,
        sandbox_progress_allowed=False,
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
            "V15.0은 In-Memory Sandbox 최종 보고서만 생성합니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=["입력과 V14.9 Ledger 무결성을 수동으로 확인합니다."],
    )


def generate_sandbox_session_final_report(
    source: Any,
    operator: str,
    confirmation_text: str,
    policy: SandboxSessionFinalReportPolicy | None = None,
    now: datetime | None = None,
) -> SandboxSessionFinalReportResult:
    policy = policy or SandboxSessionFinalReportPolicy()
    now = now or datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator가 비어 있습니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("수동 확인 문구가 올바르지 않습니다.")
    if policy_errors or input_errors:
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            policy_errors + input_errors,
            policy=not policy_errors,
            input=not input_errors,
        )

    if not isinstance(source, SandboxRiskDecisionLedgerResult):
        return _empty_result(
            policy,
            now,
            "FAILED",
            ["Source는 V14.9 Risk Decision Ledger Result여야 합니다."],
            policy=True,
            input=True,
        )

    source_errors: list[str] = []
    if not (
        source.version == policy.required_source_version
        and source.result_status == policy.required_source_status
        and source.all_checks_passed
        and source.ledger_entry_recorded
    ):
        source_errors.append("정상 V14.9 Ledger Source가 아닙니다.")
    if not _safe_source(source):
        source_errors.append("V14.9 Source 실행 안전장치가 올바르지 않습니다.")
    entries = tuple(source.entries)
    if not entries:
        source_errors.append("V14.9 Ledger Entry가 비어 있습니다.")
    if source_errors:
        return _empty_result(
            policy,
            now,
            "FAILED",
            source_errors,
            policy=True,
            input=True,
        )

    chain_valid, chain_errors = verify_ledger_chain(entries)
    if not chain_valid:
        return _empty_result(
            policy,
            now,
            "FAILED",
            chain_errors,
            policy=True,
            input=True,
            source=True,
            ledger=True,
        )

    session_ids = {entry.session_id for entry in entries}
    operators = {entry.operator for entry in entries}
    session_errors: list[str] = []
    if len(session_ids) != 1:
        session_errors.append("Ledger에 둘 이상의 Session ID가 있습니다.")
    if len(operators) != 1:
        session_errors.append("Ledger에 둘 이상의 Operator가 있습니다.")
    if operator not in operators:
        session_errors.append("Operator가 V14.9 Ledger와 다릅니다.")
    try:
        latest_recorded_at = datetime.fromisoformat(entries[-1].recorded_at)
        if now < latest_recorded_at:
            session_errors.append("Final Report 시간이 최신 Ledger보다 빠릅니다.")
    except (TypeError, ValueError):
        session_errors.append("최신 Ledger 시간이 올바르지 않습니다.")

    linkage_errors: list[str] = []
    latest = entries[-1]
    if source.total_entry_count != len(entries):
        linkage_errors.append("Source Total Entry Count 연결이 다릅니다.")
    if source.latest_entry_id != latest.ledger_entry_id:
        linkage_errors.append("Source Latest Entry ID 연결이 다릅니다.")
    if source.latest_entry_hash != latest.entry_hash:
        linkage_errors.append("Source Latest Entry Hash 연결이 다릅니다.")
    if source.latest_decision_id != latest.gate_decision_id:
        linkage_errors.append("Source Latest Decision ID 연결이 다릅니다.")
    if source.latest_gate_action != latest.gate_action:
        linkage_errors.append("Source Latest Gate Action 연결이 다릅니다.")

    if session_errors or linkage_errors:
        return _empty_result(
            policy,
            now,
            "BLOCKED",
            session_errors + linkage_errors,
            policy=True,
            input=True,
            source=True,
            ledger=True,
            chain=True,
            session=not session_errors,
            operator=not any("Operator" in error for error in session_errors),
            chronology=not any("시간" in error for error in session_errors),
            linkage=not linkage_errors,
        )

    summaries = tuple(
        SandboxSessionDecisionSummary(
            sequence=entry.sequence,
            ledger_entry_id=entry.ledger_entry_id,
            gate_decision_id=entry.gate_decision_id,
            recorded_at=entry.recorded_at,
            source_risk_status=entry.source_risk_status,
            source_risk_action=entry.source_risk_action,
            gate_action=entry.gate_action,
            manual_review_required=entry.manual_review_required,
            sandbox_progress_allowed=entry.sandbox_progress_allowed,
            entry_hash=entry.entry_hash,
        )
        for entry in entries
    )
    action_counts = {
        action: sum(entry.gate_action == action for entry in entries)
        for action in VALID_GATE_ACTIONS
    }
    outcome = {
        "PROCEED": "SANDBOX_COMPLETE",
        "REVIEW": "MANUAL_REVIEW_REQUIRED",
        "PAUSE": "PAUSED",
        "BLOCK": "BLOCKED",
    }[latest.gate_action]
    report_payload = {
        "session_report_id": str(uuid.uuid4()),
        "finalized_at": now.isoformat(),
        "report_status": "FINALIZED_IN_MEMORY",
        "session_id": latest.session_id,
        "operator": operator,
        "source_ledger_result_id": source.ledger_result_id,
        "source_latest_entry_id": latest.ledger_entry_id,
        "source_latest_entry_hash": latest.entry_hash,
        "total_decision_count": len(entries),
        "proceed_count": action_counts["PROCEED"],
        "review_count": action_counts["REVIEW"],
        "pause_count": action_counts["PAUSE"],
        "block_count": action_counts["BLOCK"],
        "final_gate_action": latest.gate_action,
        "final_session_outcome": outcome,
        "manual_review_required": latest.manual_review_required,
        "sandbox_progress_allowed": latest.sandbox_progress_allowed,
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
        "decision_summaries": summaries,
    }
    hash_payload = dict(report_payload)
    hash_payload["decision_summaries"] = [
        summary.to_dict() for summary in summaries
    ]
    report = SandboxSessionReport(
        **report_payload,
        report_hash=sha256_payload(hash_payload),
    )
    report_valid, report_errors = verify_session_report(report)
    if not report_valid:
        return _empty_result(
            policy,
            now,
            "FAILED",
            report_errors,
            policy=True,
            input=True,
            source=True,
            ledger=True,
            chain=True,
            session=True,
            operator=True,
            chronology=True,
            linkage=True,
        )

    return SandboxSessionFinalReportResult(
        version="V15.0",
        created_at=now.isoformat(),
        final_report_result_id=str(uuid.uuid4()),
        result_status="FINALIZED_IN_MEMORY",
        result_status_label="Sandbox Session Final Report 생성 완료",
        session_id=latest.session_id,
        operator=operator,
        source_ledger_result_id=source.ledger_result_id,
        source_latest_entry_id=latest.ledger_entry_id,
        source_latest_entry_hash=latest.entry_hash,
        report_id=report.session_report_id,
        report_hash=report.report_hash,
        final_gate_action=latest.gate_action,
        final_session_outcome=outcome,
        total_decision_count=len(entries),
        policy_checks_passed=True,
        input_checks_passed=True,
        source_checks_passed=True,
        ledger_checks_passed=True,
        hash_chain_checks_passed=True,
        session_checks_passed=True,
        operator_checks_passed=True,
        chronology_checks_passed=True,
        linkage_checks_passed=True,
        report_hash_checks_passed=True,
        safety_checks_passed=True,
        all_checks_passed=True,
        final_report_generated=True,
        manual_review_required=latest.manual_review_required,
        sandbox_progress_allowed=latest.sandbox_progress_allowed,
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
            f"V14.9 Ledger Entry {len(entries)}개를 검증했습니다.",
            f"최종 Gate Action은 {latest.gate_action}입니다.",
            f"Session Outcome은 {outcome}입니다.",
        ],
        warnings=[
            "V15.0은 In-Memory Sandbox 최종 보고서만 생성합니다.",
            "이 보고서는 Paper 또는 Live 주문 권한을 부여하지 않습니다.",
            "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "Final Report의 SHA-256 Hash와 V14.9 Ledger 연결을 보관합니다.",
            "실제 거래와 분리된 상태로 결과를 수동 검토합니다.",
        ],
    )


def save_final_report_result(
    result: SandboxSessionFinalReportResult,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = (
        result.created_at
        .replace(":", "")
        .replace("-", "")
        .replace("+", "_")
    )
    report_path = (
        output_directory / f"sandbox_session_final_report_{stamp}.json"
    )
    latest_path = (
        output_directory / "latest_sandbox_session_final_report.json"
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
        raise ValueError("Final Report JSON 최상위 값은 object여야 합니다.")
    return payload
