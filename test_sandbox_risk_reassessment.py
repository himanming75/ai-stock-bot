import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_risk_reassessment import (
    SandboxRiskReassessmentPolicy,
    classify_risk,
    load_risk_result,
    reassess_sandbox_risk,
    save_risk_result,
    verify_risk_assessment,
    verify_risk_rule,
)
from test_sandbox_performance_snapshot import create_source as create_valuation_source
from test_sandbox_performance_snapshot import record


NOW = datetime(2026, 7, 28, 13, 10, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return record(create_valuation_source())


def reassess(
    source: Any,
    operator: str | None = None,
    text: str = "REASSESS IN MEMORY SANDBOX RISK",
    policy: Any = None,
) -> Any:
    default_operator = (
        source.history.operator
        if getattr(source, "history", None) is not None else "operator-001"
    )
    return silent(
        reassess_sandbox_risk, source, operator or default_operator,
        text, policy, NOW,
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
    )), "V14.7 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    result = reassess(source)
    require(result.result_status == "ASSESSED_IN_MEMORY", "위험 재평가가 실패했습니다.")
    require(result.risk_status == "SAFE", "기본 Risk Status가 SAFE가 아닙니다.")
    require(result.risk_action == "ALLOW", "기본 권고 Action이 ALLOW가 아닙니다.")
    require(result.current_equity == 10087.5, "Current Equity가 다릅니다.")
    require(result.current_drawdown_percent == 1.102941, "Current Drawdown이 다릅니다.")
    require(result.assessment is not None, "Risk Assessment가 없습니다.")
    require(len(result.assessment.rules) == 4, "네 가지 Risk Rule이 생성되지 않았습니다.")
    assessment_valid, assessment_errors = verify_risk_assessment(result.assessment)
    require(assessment_valid and not assessment_errors, "Risk Assessment 검사가 실패했습니다.")
    require_safe(result)

    status_cases = {
        "SAFE": classify_risk(0.0, 10000.0),
        "WARNING": classify_risk(3.0, 10000.0),
        "PAUSED": classify_risk(5.0, 10000.0),
        "BLOCKED": classify_risk(10.0, 10000.0),
        "LOW_EQUITY": classify_risk(0.0, 999.0),
    }
    require(status_cases["SAFE"] == ("SAFE", "ALLOW"), "SAFE 경계가 다릅니다.")
    require(status_cases["WARNING"] == ("WARNING", "WARN"), "WARNING 경계가 다릅니다.")
    require(status_cases["PAUSED"] == ("PAUSED", "PAUSE"), "PAUSED 경계가 다릅니다.")
    require(status_cases["BLOCKED"] == ("BLOCKED", "BLOCK"), "BLOCK 경계가 다릅니다.")
    require(status_cases["LOW_EQUITY"] == ("BLOCKED", "BLOCK"), "최소 Equity 차단이 실패했습니다.")

    wrong_operator = reassess(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = reassess(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    unsafe_policy = SandboxRiskReassessmentPolicy(broker_api_disabled=False)
    unsafe = reassess(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(tampered_source.history, "current_equity", 1.0)
    tampered = reassess(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Source가 실패 처리되지 않았습니다.")

    changed_rule = replace(result.assessment.rules[0], metric_value=999999.0)
    rule_valid, rule_errors = verify_risk_rule(changed_rule)
    require(not rule_valid and rule_errors, "Risk Rule 변조가 탐지되지 않았습니다.")
    changed_assessment = replace(result.assessment, current_equity=1.0)
    changed_valid, changed_errors = verify_risk_assessment(changed_assessment)
    require(not changed_valid and changed_errors, "Risk Assessment 변조가 탐지되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_risk_result(result, Path(directory))
        require(report.exists() and latest.exists(), "V14.7 결과가 저장되지 않았습니다.")
        payload = load_risk_result(latest)
        require(payload["version"] == "V14.7", "저장 Version이 다릅니다.")

    for checked in (result, wrong_operator, wrong_text, unsafe, tampered):
        require_safe(checked)

    checks = {
        "Version is V14.7": result.version == "V14.7",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": SandboxRiskReassessmentPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.6 performance source passed": result.source_checks_passed,
        "SAFE risk status was calculated": result.risk_status == "SAFE",
        "ALLOW recommendation was calculated": result.risk_action == "ALLOW",
        "Four risk rules were created": len(result.assessment.rules) == 4,
        "WARNING boundary passed": status_cases["WARNING"] == ("WARNING", "WARN"),
        "PAUSED boundary passed": status_cases["PAUSED"] == ("PAUSED", "PAUSE"),
        "BLOCKED boundary passed": status_cases["BLOCKED"] == ("BLOCKED", "BLOCK"),
        "Low equity was blocked": status_cases["LOW_EQUITY"] == ("BLOCKED", "BLOCK"),
        "Assessment hash passed": assessment_valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Tampered source failed": tampered.result_status == "FAILED",
        "Risk rule tampering detected": not rule_valid,
        "Risk assessment tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V14.7",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.7 SANDBOX RISK REASSESSMENT TEST")
    print("=" * 92)
    print("V14.7 VALIDATION CHECKS")
    print("-" * 92)
    for name, checked in checks.items():
        print(f"{name:<58}: {checked}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.7 Validation Check가 실패했습니다.")
    print()
    print("V14.7 sandbox risk reassessment test completed successfully.")
    print("Equity와 Drawdown 기반 SAFE/WARNING/PAUSED/BLOCKED 경계가 검증되었습니다.")
    print("Risk Action은 권고만 생성하며 Broker API 및 실제 주문은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
