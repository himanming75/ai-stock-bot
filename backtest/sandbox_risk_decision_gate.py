import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_risk_reassessment import (
    SandboxRiskAssessment,
    SandboxRiskReassessmentResult,
    verify_risk_assessment,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "trading_engine" / "sandbox_risk_decision_gate"
REQUIRED_GATE_TEXT = "APPLY IN MEMORY SANDBOX RISK DECISION GATE"


@dataclass(frozen=True)
class SandboxRiskDecisionGatePolicy:
    required_source_version: str = "V14.7"
    required_source_status: str = "ASSESSED_IN_MEMORY"
    required_assessment_status: str = "ASSESSED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_GATE_TEXT
    require_same_operator: bool = True
    require_source_hash_validation: bool = True
    require_manual_review_for_warning: bool = True
    block_pause_and_block_actions: bool = True
    simulation_only: bool = True
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
class SandboxRiskGateDecision:
    gate_decision_id: str
    decided_at: str
    decision_status: str
    gate_action: str
    source_risk_status: str
    source_risk_action: str
    risk_result_id: str
    assessment_id: str
    assessment_hash: str
    session_id: str
    operator: str
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
    decision_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("decision_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SandboxRiskDecisionGateResult:
    version: str
    created_at: str
    gate_result_id: str
    result_status: str
    result_status_label: str
    gate_action: str
    source_risk_status: str
    source_risk_action: str
    decision_id: str | None
    decision_hash: str | None
    manual_review_required: bool
    sandbox_progress_allowed: bool
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    assessment_checks_passed: bool
    mapping_checks_passed: bool
    decision_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    gate_decision_completed: bool
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
    gate_policy: SandboxRiskDecisionGatePolicy
    decision: SandboxRiskGateDecision | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["gate_policy"] = self.gate_policy.to_dict()
        payload["decision"] = self.decision.to_dict() if self.decision else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def map_risk_to_gate(
    risk_status: str, risk_action: str
) -> tuple[str, bool, bool]:
    mappings = {
        ("SAFE", "ALLOW"): ("PROCEED", False, True),
        ("WARNING", "WARN"): ("REVIEW", True, False),
        ("PAUSED", "PAUSE"): ("PAUSE", True, False),
        ("BLOCKED", "BLOCK"): ("BLOCK", True, False),
    }
    return mappings.get((risk_status, risk_action), ("BLOCK", True, False))


def validate_policy(policy: SandboxRiskDecisionGatePolicy) -> list[str]:
    if not isinstance(policy, SandboxRiskDecisionGatePolicy):
        return ["Risk Decision Gate Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.7",
        "required_source_status": "ASSESSED_IN_MEMORY",
        "required_assessment_status": "ASSESSED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_GATE_TEXT,
    }
    for name, expected_value in expected.items():
        if getattr(policy, name) != expected_value:
            errors.append(f"{name} 값이 V14.8 기준과 다릅니다.")
    for name in (
        "require_same_operator", "require_source_hash_validation",
        "require_manual_review_for_warning", "block_pause_and_block_actions",
        "simulation_only", "credentials_forbidden", "market_data_api_disabled",
        "account_access_disabled", "network_access_disabled",
        "broker_api_disabled", "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.8에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[SandboxRiskAssessment | None, list[str]]:
    if not isinstance(source, SandboxRiskReassessmentResult):
        return None, ["Source는 V14.7 Risk Reassessment Result여야 합니다."]
    errors: list[str] = []
    if not (
        source.version == "V14.7"
        and source.result_status == "ASSESSED_IN_MEMORY"
        and source.all_checks_passed
        and source.risk_reassessment_completed
        and source.assessment is not None
    ):
        errors.append("정상 V14.7 Risk Reassessment Source가 아닙니다.")
    if any((
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
    )):
        errors.append("V14.7 Source 실행 안전장치가 올바르지 않습니다.")
    assessment = source.assessment
    if assessment is not None:
        valid, verify_errors = verify_risk_assessment(assessment)
        if not valid:
            errors.extend(verify_errors)
        if source.assessment_id != assessment.assessment_id:
            errors.append("Assessment ID 연결이 다릅니다.")
        if source.assessment_hash != assessment.assessment_hash:
            errors.append("Assessment Hash 연결이 다릅니다.")
        if (source.risk_status, source.risk_action) != (
            assessment.risk_status, assessment.risk_action
        ):
            errors.append("Source와 Assessment의 위험 판단이 다릅니다.")
    return assessment, errors


def verify_gate_decision(
    decision: SandboxRiskGateDecision,
) -> tuple[bool, list[str]]:
    if not isinstance(decision, SandboxRiskGateDecision):
        return False, ["Gate Decision 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = map_risk_to_gate(
        decision.source_risk_status, decision.source_risk_action
    )
    if (
        decision.gate_action,
        decision.manual_review_required,
        decision.sandbox_progress_allowed,
    ) != expected:
        errors.append("Risk-to-Gate 결정 매핑이 올바르지 않습니다.")
    if decision.decision_status != "DECIDED_IN_MEMORY":
        errors.append("Gate Decision Status가 올바르지 않습니다.")
    if decision.decision_hash != sha256_payload(decision.payload_without_hash()):
        errors.append("Gate Decision Hash가 일치하지 않습니다.")
    if any((
        decision.paper_execution_authorized,
        decision.automatic_execution_authorized,
        not decision.execution_blocked,
        decision.credentials_used,
        decision.market_data_api_called,
        decision.network_accessed,
        decision.account_accessed,
        decision.broker_api_called,
        decision.order_submitted,
        decision.live_execution_authorized,
    )):
        errors.append("Gate Decision 실행 안전장치가 올바르지 않습니다.")
    return not errors, errors


def _empty_result(
    policy: SandboxRiskDecisionGatePolicy,
    now: datetime,
    status: str,
    reasons: list[str],
    policy_ok: bool,
    input_ok: bool,
) -> SandboxRiskDecisionGateResult:
    return SandboxRiskDecisionGateResult(
        version="V14.8", created_at=now.isoformat(),
        gate_result_id=str(uuid.uuid4()), result_status=status,
        result_status_label="Gate 차단" if status == "BLOCKED" else "Gate 실패",
        gate_action="BLOCK", source_risk_status="FAILED",
        source_risk_action="BLOCK", decision_id=None, decision_hash=None,
        manual_review_required=True, sandbox_progress_allowed=False,
        policy_checks_passed=policy_ok, input_checks_passed=input_ok,
        source_checks_passed=False, assessment_checks_passed=False,
        mapping_checks_passed=False, decision_hash_checks_passed=False,
        safety_checks_passed=True, all_checks_passed=False,
        gate_decision_completed=False, paper_execution_authorized=False,
        automatic_execution_authorized=False, execution_blocked=True,
        credentials_used=False, market_data_api_called=False,
        network_accessed=False, account_accessed=False,
        broker_api_called=False, broker_order_created=False,
        order_submitted=False, live_order_created=False,
        live_execution_authorized=False, gate_policy=policy, decision=None,
        reasons=reasons,
        warnings=["V14.8 Gate는 실제 주문 또는 Broker 권한을 부여하지 않습니다."],
        next_actions=["입력과 V14.7 Source 무결성을 수동으로 확인합니다."],
    )


def apply_sandbox_risk_decision_gate(
    source: Any,
    operator: str,
    confirmation_text: str,
    policy: SandboxRiskDecisionGatePolicy | None = None,
    now: datetime | None = None,
) -> SandboxRiskDecisionGateResult:
    policy = policy or SandboxRiskDecisionGatePolicy()
    now = now or datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator가 비어 있습니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("수동 확인 문구가 올바르지 않습니다.")
    if policy_errors or input_errors:
        return _empty_result(
            policy, now, "BLOCKED", policy_errors + input_errors,
            not policy_errors, not input_errors,
        )

    assessment, source_errors = validate_source(source)
    if source_errors or assessment is None:
        return _empty_result(policy, now, "FAILED", source_errors, True, True)
    if policy.require_same_operator and operator != assessment.operator:
        return _empty_result(
            policy, now, "BLOCKED",
            ["Operator가 V14.7 Risk Assessment와 다릅니다."], True, False,
        )

    gate_action, review_required, progress_allowed = map_risk_to_gate(
        assessment.risk_status, assessment.risk_action
    )
    payload = {
        "gate_decision_id": str(uuid.uuid4()),
        "decided_at": now.isoformat(),
        "decision_status": "DECIDED_IN_MEMORY",
        "gate_action": gate_action,
        "source_risk_status": assessment.risk_status,
        "source_risk_action": assessment.risk_action,
        "risk_result_id": source.risk_result_id,
        "assessment_id": assessment.assessment_id,
        "assessment_hash": assessment.assessment_hash,
        "session_id": assessment.session_id,
        "operator": operator,
        "manual_review_required": review_required,
        "sandbox_progress_allowed": progress_allowed,
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
    }
    decision = SandboxRiskGateDecision(
        **payload, decision_hash=sha256_payload(payload)
    )
    decision_valid, decision_errors = verify_gate_decision(decision)
    return SandboxRiskDecisionGateResult(
        version="V14.8", created_at=now.isoformat(),
        gate_result_id=str(uuid.uuid4()),
        result_status="DECIDED_IN_MEMORY" if decision_valid else "FAILED",
        result_status_label="Sandbox Risk Gate 결정 완료" if decision_valid else "Gate 실패",
        gate_action=gate_action if decision_valid else "BLOCK",
        source_risk_status=assessment.risk_status,
        source_risk_action=assessment.risk_action,
        decision_id=decision.gate_decision_id,
        decision_hash=decision.decision_hash,
        manual_review_required=review_required,
        sandbox_progress_allowed=progress_allowed if decision_valid else False,
        policy_checks_passed=True, input_checks_passed=True,
        source_checks_passed=True, assessment_checks_passed=True,
        mapping_checks_passed=(
            (gate_action, review_required, progress_allowed)
            == map_risk_to_gate(assessment.risk_status, assessment.risk_action)
        ),
        decision_hash_checks_passed=decision_valid,
        safety_checks_passed=True, all_checks_passed=decision_valid,
        gate_decision_completed=decision_valid,
        paper_execution_authorized=False, automatic_execution_authorized=False,
        execution_blocked=True, credentials_used=False,
        market_data_api_called=False, network_accessed=False,
        account_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_order_created=False, live_execution_authorized=False,
        gate_policy=policy, decision=decision,
        reasons=[
            f"V14.7 Risk {assessment.risk_status}/{assessment.risk_action}을 확인했습니다.",
            f"V14.8 Gate Action은 {gate_action}입니다.",
        ],
        warnings=[
            "Sandbox 진행 허용은 실제 Paper 주문 허용을 의미하지 않습니다.",
            "Broker API, Network, 계좌 및 Live Execution은 계속 차단됩니다.",
        ] + decision_errors,
        next_actions=[
            "Gate Action과 수동 검토 필요 여부를 확인합니다.",
            "PROCEED인 경우에만 다음 In-Memory Sandbox 단계로 진행합니다.",
        ],
    )


def save_gate_result(
    result: SandboxRiskDecisionGateResult,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report = output_directory / f"sandbox_risk_decision_gate_{stamp}.json"
    latest = output_directory / "latest_sandbox_risk_decision_gate.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_gate_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

