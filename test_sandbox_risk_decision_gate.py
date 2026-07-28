import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_risk_decision_gate import (
    SandboxRiskDecisionGatePolicy,
    apply_sandbox_risk_decision_gate,
    load_gate_result,
    map_risk_to_gate,
    save_gate_result,
    verify_gate_decision,
)
from test_sandbox_risk_reassessment import create_source as create_performance_source
from test_sandbox_risk_reassessment import reassess


NOW = datetime(2026, 7, 28, 13, 30, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return reassess(create_performance_source())


def apply_gate(
    source: Any,
    operator: str | None = None,
    text: str = "APPLY IN MEMORY SANDBOX RISK DECISION GATE",
    policy: Any = None,
) -> Any:
    default_operator = (
        source.assessment.operator
        if getattr(source, "assessment", None) is not None else "operator-001"
    )
    return silent(
        apply_sandbox_risk_decision_gate,
        source, operator or default_operator, text, policy, NOW,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(all((
        not result.paper_execution_authorized,
        not result.automatic_execution_authorized,
        result.execution_blocked,
        not result.credentials_used,
        not result.market_data_api_called,
        not result.network_accessed,
        not result.account_accessed,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )), "V14.8 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    result = apply_gate(source)
    require(result.result_status == "DECIDED_IN_MEMORY", "Gate 결정이 실패했습니다.")
    require(result.gate_action == "PROCEED", "SAFE Source가 PROCEED가 아닙니다.")
    require(result.sandbox_progress_allowed, "Sandbox 진행이 허용되지 않았습니다.")
    require(not result.manual_review_required, "SAFE 상태에 불필요한 검토가 설정됐습니다.")
    require(result.decision is not None, "Gate Decision이 없습니다.")
    decision_valid, decision_errors = verify_gate_decision(result.decision)
    require(decision_valid and not decision_errors, "Gate Decision 검사가 실패했습니다.")
    require_safe(result)

    mappings = {
        "SAFE": map_risk_to_gate("SAFE", "ALLOW"),
        "WARNING": map_risk_to_gate("WARNING", "WARN"),
        "PAUSED": map_risk_to_gate("PAUSED", "PAUSE"),
        "BLOCKED": map_risk_to_gate("BLOCKED", "BLOCK"),
        "INVALID": map_risk_to_gate("UNKNOWN", "ALLOW"),
    }
    require(mappings["SAFE"] == ("PROCEED", False, True), "SAFE 매핑이 다릅니다.")
    require(mappings["WARNING"] == ("REVIEW", True, False), "WARNING 매핑이 다릅니다.")
    require(mappings["PAUSED"] == ("PAUSE", True, False), "PAUSED 매핑이 다릅니다.")
    require(mappings["BLOCKED"] == ("BLOCK", True, False), "BLOCKED 매핑이 다릅니다.")
    require(mappings["INVALID"] == ("BLOCK", True, False), "알 수 없는 상태가 차단되지 않았습니다.")

    wrong_operator = apply_gate(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = apply_gate(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    unsafe_policy = SandboxRiskDecisionGatePolicy(broker_api_disabled=False)
    unsafe = apply_gate(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(tampered_source.assessment, "risk_status", "BLOCKED")
    tampered = apply_gate(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Source가 실패 처리되지 않았습니다.")
    changed_decision = replace(result.decision, gate_action="BLOCK")
    changed_valid, changed_errors = verify_gate_decision(changed_decision)
    require(not changed_valid and changed_errors, "Gate Decision 변조가 탐지되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_gate_result(result, Path(directory))
        require(report.exists() and latest.exists(), "V14.8 결과가 저장되지 않았습니다.")
        payload = load_gate_result(latest)
        require(payload["version"] == "V14.8", "저장 Version이 다릅니다.")

    for checked in (result, wrong_operator, wrong_text, unsafe, tampered):
        require_safe(checked)

    checks = {
        "Version is V14.8": result.version == "V14.8",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": SandboxRiskDecisionGatePolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.7 risk source passed": result.source_checks_passed,
        "SAFE mapped to PROCEED": mappings["SAFE"] == ("PROCEED", False, True),
        "WARNING mapped to REVIEW": mappings["WARNING"] == ("REVIEW", True, False),
        "PAUSED mapped to PAUSE": mappings["PAUSED"] == ("PAUSE", True, False),
        "BLOCKED mapped to BLOCK": mappings["BLOCKED"] == ("BLOCK", True, False),
        "Unknown risk was blocked": mappings["INVALID"] == ("BLOCK", True, False),
        "Sandbox progress was allowed": result.sandbox_progress_allowed,
        "Gate decision hash passed": decision_valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Tampered source failed": tampered.result_status == "FAILED",
        "Gate decision tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V14.8",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.8 SANDBOX RISK DECISION GATE TEST")
    print("=" * 92)
    print("V14.8 VALIDATION CHECKS")
    print("-" * 92)
    for name, checked in checks.items():
        print(f"{name:<58}: {checked}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.8 Validation Check가 실패했습니다.")
    print()
    print("V14.8 sandbox risk decision gate test completed successfully.")
    print("SAFE/WARNING/PAUSED/BLOCKED의 Gate 결정과 SHA-256 변조 탐지가 검증되었습니다.")
    print("Sandbox 진행 결정만 생성하며 Broker API 및 실제 주문은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
