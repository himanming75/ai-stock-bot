import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_performance_snapshot import (
    SandboxPerformanceSnapshotPolicy,
    load_performance_result,
    record_sandbox_performance_snapshot,
    save_performance_result,
    verify_performance_history,
    verify_performance_record,
)
from test_sandbox_portfolio_valuation_refresh import (
    create_settlement_source,
    refresh,
)


NOW = datetime(2026, 7, 28, 12, 51, tzinfo=timezone.utc)
PRIOR = [
    {
        "recorded_at": "2026-07-28T12:30:00+00:00",
        "total_equity": 10000.0,
        "source_id": "prior-001",
    },
    {
        "recorded_at": "2026-07-28T12:40:00+00:00",
        "total_equity": 10200.0,
        "source_id": "prior-002",
    },
]


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return refresh(create_settlement_source())


def record(
    source: Any,
    operator: str | None = None,
    text: str = "RECORD IN MEMORY SANDBOX PERFORMANCE SNAPSHOT",
    prior: Any = None,
    policy: Any = None,
) -> Any:
    return silent(
        record_sandbox_performance_snapshot,
        source,
        operator or source.snapshot.operator,
        text,
        PRIOR if prior is None else prior,
        policy,
        NOW,
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
        not result.account_updated,
        not result.broker_api_called,
        not result.order_submitted,
        not result.live_execution_authorized,
    )), "Performance 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    result = record(source)
    require(result.result_status == "RECORDED_IN_MEMORY", "정상 Snapshot 기록이 실패했습니다.")
    require(result.record_count == 3, "세 기간이 기록되지 않았습니다.")
    require(result.starting_equity == 10000.0, "Starting Equity가 다릅니다.")
    require(result.current_equity == 10087.5, "Current Equity가 다릅니다.")
    require(result.peak_equity == 10200.0, "Peak Equity가 다릅니다.")
    require(result.cumulative_profit_loss == 87.5, "Cumulative P/L이 다릅니다.")
    require(result.cumulative_return_percent == 0.875, "Cumulative Return이 다릅니다.")
    require(result.current_drawdown_percent == 1.102941, "Current Drawdown이 다릅니다.")
    require(result.maximum_drawdown_percent == 1.102941, "Maximum Drawdown이 다릅니다.")
    require(result.history is not None, "Performance History가 없습니다.")
    valid, errors = verify_performance_history(result.history)
    require(valid and not errors, "Performance History 검사가 실패했습니다.")
    require_safe(result)

    wrong_operator = record(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = record(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    backward = record(source, prior=list(reversed(PRIOR)))
    require(backward.result_status == "BLOCKED", "역순 History가 차단되지 않았습니다.")
    duplicate = record(source, prior=[PRIOR[0], PRIOR[0]])
    require(duplicate.result_status == "BLOCKED", "중복 History가 차단되지 않았습니다.")
    invalid = record(source, prior=[{"recorded_at": "", "total_equity": -1, "source_id": ""}])
    require(invalid.result_status == "BLOCKED", "잘못된 History가 차단되지 않았습니다.")
    unsafe_policy = SandboxPerformanceSnapshotPolicy(account_access_disabled=False)
    unsafe = record(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(tampered_source.snapshot, "total_equity", 1.0)
    tampered = record(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Valuation Source가 실패 처리되지 않았습니다.")

    changed_record = replace(result.history.records[-1], total_equity=9999.0)
    record_valid, record_errors = verify_performance_record(changed_record)
    require(not record_valid and record_errors, "Performance Record 변조가 탐지되지 않았습니다.")
    changed_history = replace(result.history, peak_equity=9999.0)
    history_valid, history_errors = verify_performance_history(changed_history)
    require(not history_valid and history_errors, "Performance History 변조가 탐지되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_performance_result(result, Path(directory))
        require(report.exists() and latest.exists(), "Performance 결과가 저장되지 않았습니다.")
        payload = load_performance_result(latest)
        require(payload["version"] == "V14.6", "저장 Version이 다릅니다.")

    for checked in (
        result, wrong_operator, wrong_text, backward,
        duplicate, invalid, unsafe, tampered,
    ):
        require_safe(checked)

    checks = {
        "Version is V14.6": result.version == "V14.6",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": SandboxPerformanceSnapshotPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.5 valuation source passed": result.source_checks_passed,
        "Three performance periods exist": result.record_count == 3,
        "Current equity is 10087.50": result.current_equity == 10087.5,
        "Peak equity is 10200.00": result.peak_equity == 10200.0,
        "Cumulative return is 0.875 percent": result.cumulative_return_percent == 0.875,
        "Maximum drawdown is 1.102941 percent": result.maximum_drawdown_percent == 1.102941,
        "Performance history hash passed": valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Backward history was blocked": backward.result_status == "BLOCKED",
        "Duplicate history was blocked": duplicate.result_status == "BLOCKED",
        "Invalid history was blocked": invalid.result_status == "BLOCKED",
        "Tampered valuation source failed": tampered.result_status == "FAILED",
        "Performance record tampering detected": not record_valid,
        "Performance history tampering detected": not history_valid,
        "Result save and load passed": payload["version"] == "V14.6",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.6 SANDBOX PERFORMANCE SNAPSHOT TEST")
    print("=" * 92)
    print("V14.6 VALIDATION CHECKS")
    print("-" * 92)
    for name, checked in checks.items():
        print(f"{name:<58}: {checked}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.6 Validation Check가 실패했습니다.")
    print()
    print("V14.6 sandbox performance snapshot test completed successfully.")
    print("시간순 Equity, 누적 수익률, Peak 및 Drawdown Hash Chain이 검증되었습니다.")
    print("시세 API, 계좌, Network, Broker API 및 실제 주문은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
