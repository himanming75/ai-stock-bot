import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_performance_snapshot import (
    SandboxPerformanceHistory,
    SandboxPerformanceSnapshotResult,
    verify_performance_history,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "trading_engine" / "sandbox_risk_reassessment"
REQUIRED_REASSESSMENT_TEXT = "REASSESS IN MEMORY SANDBOX RISK"


@dataclass(frozen=True)
class SandboxRiskReassessmentPolicy:
    required_source_version: str = "V14.6"
    required_source_status: str = "RECORDED_IN_MEMORY"
    required_history_status: str = "RECORDED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_REASSESSMENT_TEXT
    warning_drawdown_percent: float = 3.0
    pause_drawdown_percent: float = 5.0
    block_drawdown_percent: float = 10.0
    minimum_equity: float = 1000.0
    require_same_operator: bool = True
    require_source_hash_validation: bool = True
    simulation_only: bool = True
    market_data_api_disabled: bool = True
    credentials_forbidden: bool = True
    account_access_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxRiskRuleResult:
    rule_name: str
    metric_value: float
    threshold: float
    triggered: bool
    risk_action: str
    rule_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("rule_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxRiskAssessment:
    assessment_id: str
    assessed_at: str
    assessment_status: str
    risk_status: str
    risk_action: str
    performance_result_id: str
    performance_history_id: str
    performance_history_hash: str
    session_id: str
    operator: str
    starting_equity: float
    current_equity: float
    peak_equity: float
    cumulative_return_percent: float
    current_drawdown_percent: float
    maximum_drawdown_percent: float
    rules: tuple[SandboxRiskRuleResult, ...]
    simulation_only: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    assessment_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rules"] = [rule.to_dict() for rule in self.rules]
        payload.pop("assessment_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["assessment_hash"] = self.assessment_hash
        return payload


@dataclass
class SandboxRiskReassessmentResult:
    version: str
    created_at: str
    risk_result_id: str
    result_status: str
    result_status_label: str
    risk_status: str
    risk_action: str
    assessment_id: str | None
    assessment_hash: str | None
    current_equity: float
    cumulative_return_percent: float
    current_drawdown_percent: float
    maximum_drawdown_percent: float
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    history_checks_passed: bool
    rule_checks_passed: bool
    assessment_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    risk_reassessment_completed: bool
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
    risk_policy: SandboxRiskReassessmentPolicy
    assessment: SandboxRiskAssessment | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["risk_policy"] = self.risk_policy.to_dict()
        payload["assessment"] = self.assessment.to_dict() if self.assessment else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: SandboxRiskReassessmentPolicy) -> list[str]:
    if not isinstance(policy, SandboxRiskReassessmentPolicy):
        return ["Risk Reassessment Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.6",
        "required_source_status": "RECORDED_IN_MEMORY",
        "required_history_status": "RECORDED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_REASSESSMENT_TEXT,
        "warning_drawdown_percent": 3.0,
        "pause_drawdown_percent": 5.0,
        "block_drawdown_percent": 10.0,
        "minimum_equity": 1000.0,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.7 기준과 다릅니다.")
    if not (
        0 < policy.warning_drawdown_percent
        < policy.pause_drawdown_percent
        < policy.block_drawdown_percent
    ):
        errors.append("Drawdown 위험 기준 순서가 올바르지 않습니다.")
    for name in (
        "require_same_operator", "require_source_hash_validation", "simulation_only",
        "market_data_api_disabled", "credentials_forbidden",
        "account_access_disabled", "network_access_disabled",
        "broker_api_disabled", "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.7에서 True여야 합니다.")
    return errors


def classify_risk(
    current_drawdown_percent: float,
    current_equity: float,
    policy: SandboxRiskReassessmentPolicy | None = None,
) -> tuple[str, str]:
    policy = policy or SandboxRiskReassessmentPolicy()
    if current_equity < policy.minimum_equity:
        return "BLOCKED", "BLOCK"
    if current_drawdown_percent >= policy.block_drawdown_percent:
        return "BLOCKED", "BLOCK"
    if current_drawdown_percent >= policy.pause_drawdown_percent:
        return "PAUSED", "PAUSE"
    if current_drawdown_percent >= policy.warning_drawdown_percent:
        return "WARNING", "WARN"
    return "SAFE", "ALLOW"


def validate_source(
    source: Any,
) -> tuple[SandboxPerformanceHistory | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, SandboxPerformanceSnapshotResult):
        return None, ["Source는 V14.6 Performance Result여야 합니다."]
    if not (
        source.version == "V14.6"
        and source.result_status == "RECORDED_IN_MEMORY"
        and source.all_checks_passed
        and source.performance_snapshot_completed
        and source.history is not None
    ):
        errors.append("정상 V14.6 Performance Source가 아닙니다.")
    if any((
        source.paper_execution_authorized,
        source.automatic_execution_authorized,
        not source.execution_blocked,
        source.credentials_used,
        source.market_data_api_called,
        source.network_accessed,
        source.account_accessed,
        source.account_updated,
        source.broker_api_called,
        source.order_submitted,
        source.live_execution_authorized,
    )):
        errors.append("V14.6 Source 실행 안전장치가 올바르지 않습니다.")
    history = source.history
    if history:
        valid, verify_errors = verify_performance_history(history)
        if not valid:
            errors.extend(verify_errors)
        if source.performance_history_id != history.performance_history_id:
            errors.append("Performance History ID 연결이 다릅니다.")
        if source.history_hash != history.history_hash:
            errors.append("Performance History Hash 연결이 다릅니다.")
    return history, errors


def make_rule(
    name: str, value: float, threshold: float, triggered: bool, action: str
) -> SandboxRiskRuleResult:
    payload = {
        "rule_name": name,
        "metric_value": round(float(value), 6),
        "threshold": round(float(threshold), 6),
        "triggered": triggered,
        "risk_action": action,
    }
    return SandboxRiskRuleResult(**payload, rule_hash=sha256_payload(payload))


def verify_risk_rule(rule: SandboxRiskRuleResult) -> tuple[bool, list[str]]:
    if not isinstance(rule, SandboxRiskRuleResult):
        return False, ["Risk Rule 형식이 올바르지 않습니다."]
    errors: list[str] = []
    if rule.rule_hash != sha256_payload(rule.payload_without_hash()):
        errors.append("Risk Rule Hash가 일치하지 않습니다.")
    if rule.risk_action not in {"ALLOW", "WARN", "PAUSE", "BLOCK"}:
        errors.append("Risk Rule Action이 올바르지 않습니다.")
    return not errors, errors


def verify_risk_assessment(
    assessment: SandboxRiskAssessment,
) -> tuple[bool, list[str]]:
    if not isinstance(assessment, SandboxRiskAssessment):
        return False, ["Risk Assessment 형식이 올바르지 않습니다."]
    errors: list[str] = []
    if assessment.assessment_status != "ASSESSED_IN_MEMORY":
        errors.append("Risk Assessment Status가 올바르지 않습니다.")
    expected_status, expected_action = classify_risk(
        assessment.current_drawdown_percent, assessment.current_equity
    )
    if (assessment.risk_status, assessment.risk_action) != (
        expected_status, expected_action
    ):
        errors.append("Risk Status 또는 Action 계산이 다릅니다.")
    for rule in assessment.rules:
        valid, rule_errors = verify_risk_rule(rule)
        if not valid:
            errors.extend(rule_errors)
    if assessment.assessment_hash != sha256_payload(
        assessment.payload_without_hash()
    ):
        errors.append("Risk Assessment Hash가 일치하지 않습니다.")
    if any((
        not assessment.simulation_only,
        assessment.credentials_used,
        assessment.market_data_api_called,
        assessment.network_accessed,
        assessment.account_accessed,
        assessment.broker_api_called,
        assessment.order_submitted,
        assessment.live_execution_authorized,
    )):
        errors.append("Risk Assessment 실행 안전장치가 올바르지 않습니다.")
    return not errors, errors


def _empty_result(
    policy: SandboxRiskReassessmentPolicy,
    now: datetime,
    status: str,
    reasons: list[str],
    policy_ok: bool,
    input_ok: bool,
) -> SandboxRiskReassessmentResult:
    return SandboxRiskReassessmentResult(
        version="V14.7", created_at=now.isoformat(),
        risk_result_id=str(uuid.uuid4()), result_status=status,
        result_status_label="위험 재평가 차단" if status == "BLOCKED" else "위험 재평가 실패",
        risk_status="FAILED", risk_action="BLOCK", assessment_id=None,
        assessment_hash=None, current_equity=0.0,
        cumulative_return_percent=0.0, current_drawdown_percent=0.0,
        maximum_drawdown_percent=0.0, policy_checks_passed=policy_ok,
        input_checks_passed=input_ok, source_checks_passed=False,
        history_checks_passed=False, rule_checks_passed=False,
        assessment_hash_checks_passed=False, safety_checks_passed=True,
        all_checks_passed=False, risk_reassessment_completed=False,
        paper_execution_authorized=False, automatic_execution_authorized=False,
        execution_blocked=True, credentials_used=False,
        market_data_api_called=False, network_accessed=False,
        account_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_order_created=False, live_execution_authorized=False,
        risk_policy=policy, assessment=None, reasons=reasons,
        warnings=["V14.7은 위험 판단만 하며 주문 권한을 부여하지 않습니다."],
        next_actions=["입력과 Source 무결성을 확인한 뒤 다시 실행합니다."],
    )


def reassess_sandbox_risk(
    source: Any,
    operator: str,
    confirmation_text: str,
    policy: SandboxRiskReassessmentPolicy | None = None,
    now: datetime | None = None,
) -> SandboxRiskReassessmentResult:
    policy = policy or SandboxRiskReassessmentPolicy()
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

    history, source_errors = validate_source(source)
    if source_errors or history is None:
        return _empty_result(
            policy, now, "FAILED", source_errors, True, True
        )
    if policy.require_same_operator and operator != history.operator:
        return _empty_result(
            policy, now, "BLOCKED",
            ["Operator가 V14.6 Performance Source와 다릅니다."], True, False,
        )

    risk_status, risk_action = classify_risk(
        history.current_drawdown_percent, history.current_equity, policy
    )
    rules = (
        make_rule("MINIMUM_EQUITY", history.current_equity, policy.minimum_equity,
                  history.current_equity < policy.minimum_equity, "BLOCK"),
        make_rule("WARNING_DRAWDOWN", history.current_drawdown_percent,
                  policy.warning_drawdown_percent,
                  history.current_drawdown_percent >= policy.warning_drawdown_percent,
                  "WARN"),
        make_rule("PAUSE_DRAWDOWN", history.current_drawdown_percent,
                  policy.pause_drawdown_percent,
                  history.current_drawdown_percent >= policy.pause_drawdown_percent,
                  "PAUSE"),
        make_rule("BLOCK_DRAWDOWN", history.current_drawdown_percent,
                  policy.block_drawdown_percent,
                  history.current_drawdown_percent >= policy.block_drawdown_percent,
                  "BLOCK"),
    )
    payload = {
        "assessment_id": str(uuid.uuid4()),
        "assessed_at": now.isoformat(),
        "assessment_status": "ASSESSED_IN_MEMORY",
        "risk_status": risk_status,
        "risk_action": risk_action,
        "performance_result_id": source.performance_result_id,
        "performance_history_id": history.performance_history_id,
        "performance_history_hash": history.history_hash,
        "session_id": history.session_id,
        "operator": operator,
        "starting_equity": history.starting_equity,
        "current_equity": history.current_equity,
        "peak_equity": history.peak_equity,
        "cumulative_return_percent": history.cumulative_return_percent,
        "current_drawdown_percent": history.current_drawdown_percent,
        "maximum_drawdown_percent": history.maximum_drawdown_percent,
        "rules": [rule.to_dict() for rule in rules],
        "simulation_only": True,
        "credentials_used": False,
        "market_data_api_called": False,
        "network_accessed": False,
        "account_accessed": False,
        "broker_api_called": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    assessment = SandboxRiskAssessment(
        **{**payload, "rules": rules},
        assessment_hash=sha256_payload(payload),
    )
    assessment_valid, assessment_errors = verify_risk_assessment(assessment)
    result = SandboxRiskReassessmentResult(
        version="V14.7", created_at=now.isoformat(),
        risk_result_id=str(uuid.uuid4()),
        result_status="ASSESSED_IN_MEMORY" if assessment_valid else "FAILED",
        result_status_label="Sandbox 위험 재평가 완료" if assessment_valid else "위험 재평가 실패",
        risk_status=risk_status if assessment_valid else "FAILED",
        risk_action=risk_action if assessment_valid else "BLOCK",
        assessment_id=assessment.assessment_id,
        assessment_hash=assessment.assessment_hash,
        current_equity=history.current_equity,
        cumulative_return_percent=history.cumulative_return_percent,
        current_drawdown_percent=history.current_drawdown_percent,
        maximum_drawdown_percent=history.maximum_drawdown_percent,
        policy_checks_passed=True, input_checks_passed=True,
        source_checks_passed=True, history_checks_passed=True,
        rule_checks_passed=all(verify_risk_rule(rule)[0] for rule in rules),
        assessment_hash_checks_passed=assessment_valid,
        safety_checks_passed=True, all_checks_passed=assessment_valid,
        risk_reassessment_completed=assessment_valid,
        paper_execution_authorized=False, automatic_execution_authorized=False,
        execution_blocked=True, credentials_used=False,
        market_data_api_called=False, network_accessed=False,
        account_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_order_created=False, live_execution_authorized=False,
        risk_policy=policy, assessment=assessment,
        reasons=[
            f"현재 Drawdown은 {history.current_drawdown_percent:.6f}%입니다.",
            f"최종 Risk Status는 {risk_status}, 권고 Action은 {risk_action}입니다.",
        ],
        warnings=[
            "Risk Action은 수동 검토용 권고이며 실제 주문 권한이 아닙니다.",
            "Broker API, 계좌, Network 및 Live Execution은 차단됩니다.",
        ] + assessment_errors,
        next_actions=[
            "위험 등급과 네 가지 Rule 결과를 수동으로 확인합니다.",
            "다음 Sandbox 단계로 진행하기 전에 Source Hash를 보존합니다.",
        ],
    )
    return result


def save_risk_result(
    result: SandboxRiskReassessmentResult,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "").replace("-", "").replace("+", "_")
    report = output_directory / f"sandbox_risk_reassessment_{stamp}.json"
    latest = output_directory / "latest_sandbox_risk_reassessment.json"
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    report.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_risk_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

