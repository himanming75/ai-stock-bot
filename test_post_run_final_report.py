import importlib.util
import json
import sys
import tempfile
import types
from dataclasses import (
    FrozenInstanceError,
    dataclass,
    fields,
    replace,
)
from pathlib import Path
from unittest.mock import patch


# 다운로드 작업공간에 오래된 의존 파일이 없을 때만
# import에 필요한 과거 형식을 테스트용으로 격리합니다.
if (
    importlib.util.find_spec(
        "backtest.paper_portfolio_valuation"
    )
    is None
):
    valuation_stub = types.ModuleType(
        "backtest.paper_portfolio_valuation"
    )

    @dataclass
    class PaperPortfolioValuationResult:
        version: str = "V10.0"

    valuation_stub.PAPER_VALUATION_OUTPUT_DIRECTORY = (
        Path("output")
    )
    valuation_stub.PaperPortfolioValuationResult = (
        PaperPortfolioValuationResult
    )
    valuation_stub.load_latest_valuation_result = (
        lambda: {}
    )
    valuation_stub.run_paper_portfolio_valuation = (
        lambda *args, **kwargs: None
    )
    valuation_stub.save_paper_portfolio_valuation = (
        lambda *args, **kwargs: None
    )
    sys.modules[
        "backtest.paper_portfolio_valuation"
    ] = valuation_stub

    ledger_stub = types.ModuleType(
        "backtest.paper_trading_run_ledger"
    )

    @dataclass
    class PaperTradingRunLedgerEntry:
        run_status: str = "COMPLETED"

    @dataclass
    class PaperTradingRunLedgerState:
        ledger_id: str = "ledger-test"
        entry_count: int = 1
        entries: tuple = ()

    @dataclass
    class PaperTradingRunLedgerResult:
        version: str = "V10.7"

    ledger_stub.PaperTradingRunLedgerEntry = (
        PaperTradingRunLedgerEntry
    )
    ledger_stub.PaperTradingRunLedgerState = (
        PaperTradingRunLedgerState
    )
    ledger_stub.PaperTradingRunLedgerResult = (
        PaperTradingRunLedgerResult
    )
    ledger_stub.load_latest_ledger_state = (
        lambda: PaperTradingRunLedgerState()
    )
    ledger_stub.validate_ledger_state = (
        lambda _state: (True, [])
    )
    sys.modules[
        "backtest.paper_trading_run_ledger"
    ] = ledger_stub


import backtest.post_run_final_report as report_module
from backtest.approved_paper_run_launcher import (
    ApprovedPaperRunLauncherResult,
)
from backtest.approved_paper_run_ledger_integration import (
    ApprovedRunLedgerIntegrationResult,
)
from backtest.paper_portfolio_performance_tracker import (
    PaperPortfolioPerformanceResult,
)
from backtest.paper_trading_risk_monitor import (
    PaperTradingRiskMonitorResult,
)
from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryResult,
)
from backtest.post_run_final_report import (
    PostRunFinalReportPolicy,
    load_latest_post_run_final_report,
    run_post_run_final_report,
    save_post_run_final_report,
    validate_report_policy,
)
from backtest.post_run_performance_risk_refresh import (
    PostRunPerformanceRiskResult,
)
from backtest.post_run_session_refresh import (
    PostRunSessionRefreshResult,
)
from backtest.scheduled_paper_run_approval import (
    ScheduledPaperRunApprovalResult,
)


LINE_LENGTH = 140
PLAN_ID = "plan-v11-5-001"
APPROVAL_ID = "approval-v11-5-001"
LAUNCH_ID = "launch-v11-5-001"
INTEGRATION_ID = "integration-v11-5-001"
LEDGER_ID = "ledger-v11-5-001"
SESSION_REFRESH_ID = "session-refresh-v11-5-001"
SUMMARY_ID = "summary-v11-5-001"
PERFORMANCE_REFRESH_ID = "performance-refresh-v11-5-001"
PERFORMANCE_ID = "performance-v11-5-001"


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V11.5 "
        "POST-RUN FINAL REPORT TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<84}: {value}")


def empty_instance(dataclass_type):
    instance = object.__new__(dataclass_type)
    for item in fields(dataclass_type):
        setattr(instance, item.name, None)
    return instance


def apply_safety(
    result,
    *,
    unsafe: bool = False,
):
    result.all_checks_passed = True
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    return result


def create_approval(
    *,
    created_at: str = "2026-07-27T10:00:00",
    status: str = "APPROVED",
    unsafe: bool = False,
):
    result = empty_instance(
        ScheduledPaperRunApprovalResult
    )
    result.version = "V11.0"
    result.created_at = created_at
    result.approval_status = status
    result.approval_id = APPROVAL_ID
    result.plan_id = PLAN_ID
    return apply_safety(result, unsafe=unsafe)


def create_launch(
    *,
    created_at: str = "2026-07-27T10:01:00",
    status: str = "COMPLETED",
    approval_id: str = APPROVAL_ID,
    plan_id: str = PLAN_ID,
    unsafe: bool = False,
):
    result = empty_instance(
        ApprovedPaperRunLauncherResult
    )
    result.version = "V11.1"
    result.created_at = created_at
    result.launch_status = status
    result.launch_id = LAUNCH_ID
    result.approval_id = approval_id
    result.plan_id = plan_id
    return apply_safety(result, unsafe=unsafe)


def create_integration(
    *,
    created_at: str = "2026-07-27T10:02:00",
    status: str = "LINKED",
    launch_id: str = LAUNCH_ID,
    approval_id: str = APPROVAL_ID,
    plan_id: str = PLAN_ID,
    unsafe: bool = False,
):
    result = empty_instance(
        ApprovedRunLedgerIntegrationResult
    )
    result.version = "V11.2"
    result.created_at = created_at
    result.integration_status = status
    result.integration_id = INTEGRATION_ID
    result.launch_id = launch_id
    result.approval_id = approval_id
    result.plan_id = plan_id
    result.ledger_update_id = (
        "ledger-update-v11-5-001"
    )
    result.ledger_id = LEDGER_ID
    result.source_run_id = "run-v11-5-001"
    return apply_safety(result, unsafe=unsafe)


def create_summary():
    result = empty_instance(
        PaperTradingSessionSummaryResult
    )
    result.version = "V10.8"
    result.session_summary_id = SUMMARY_ID
    result.session_status = "READY"
    result.session_action = "CONTINUE"
    return result


def create_session(
    *,
    created_at: str = "2026-07-27T10:03:00",
    status: str = "REFRESHED",
    integration_id: str = INTEGRATION_ID,
    ledger_id: str = LEDGER_ID,
    unsafe: bool = False,
):
    result = empty_instance(
        PostRunSessionRefreshResult
    )
    result.version = "V11.3"
    result.created_at = created_at
    result.refresh_status = status
    result.refresh_id = SESSION_REFRESH_ID
    result.integration_id = integration_id
    result.ledger_id = ledger_id
    result.session_summary_id = SUMMARY_ID
    result.session_summary = create_summary()
    return apply_safety(result, unsafe=unsafe)


def create_performance():
    result = empty_instance(
        PaperPortfolioPerformanceResult
    )
    result.version = "V10.1"
    result.performance_id = PERFORMANCE_ID
    result.portfolio_id = "portfolio-v11-5-001"
    result.performance_status = "TRACKED"
    result.current_equity = 10_100.0
    result.cumulative_return_percent = 1.0
    result.maximum_drawdown_percent = 2.0
    return result


def create_risk(
    performance,
    *,
    source_id: str | None = None,
):
    result = empty_instance(
        PaperTradingRiskMonitorResult
    )
    result.version = "V10.4"
    result.monitor_id = "risk-monitor-v11-5-001"
    result.source_performance_id = (
        source_id
        if source_id is not None
        else performance.performance_id
    )
    result.risk_status = "SAFE"
    result.risk_action = "ALLOW"
    return result


def create_performance_risk(
    *,
    created_at: str = "2026-07-27T10:04:00",
    status: str = "REFRESHED",
    session_refresh_id: str = SESSION_REFRESH_ID,
    wrong_performance_source: bool = False,
    unsafe: bool = False,
):
    performance = create_performance()
    risk = create_risk(
        performance,
        source_id=(
            "different-performance"
            if wrong_performance_source
            else None
        ),
    )
    result = empty_instance(
        PostRunPerformanceRiskResult
    )
    result.version = "V11.4"
    result.created_at = created_at
    result.refresh_status = status
    result.refresh_id = PERFORMANCE_REFRESH_ID
    result.session_refresh_id = (
        session_refresh_id
    )
    result.performance_result = performance
    result.risk_result = risk
    return apply_safety(result, unsafe=unsafe)


def run_report(
    *,
    approval=None,
    launch=None,
    integration=None,
    session=None,
    performance_risk=None,
    policy=None,
):
    with patch.object(
        report_module,
        "print_post_run_final_report",
    ):
        return run_post_run_final_report(
            approval_result=(
                approval
                if approval is not None
                else create_approval()
            ),
            launch_result=(
                launch
                if launch is not None
                else create_launch()
            ),
            integration_result=(
                integration
                if integration is not None
                else create_integration()
            ),
            session_refresh_result=(
                session
                if session is not None
                else create_session()
            ),
            performance_risk_result=(
                performance_risk
                if performance_risk is not None
                else create_performance_risk()
            ),
            report_policy=policy,
        )


def validate_policy() -> None:
    policy = PostRunFinalReportPolicy()
    valid, errors = validate_report_policy(
        policy
    )
    assert valid is True
    assert errors == []

    try:
        policy.paper_only = False
        raise AssertionError(
            "Final Report Policy가 변경 가능 상태입니다."
        )
    except FrozenInstanceError:
        pass

    invalid = replace(
        policy,
        require_execution_safety=False,
    )
    invalid_valid, invalid_errors = (
        validate_report_policy(invalid)
    )
    assert invalid_valid is False
    assert invalid_errors


def validate_completed_report():
    result = run_report()

    assert result.version == "V11.5"
    assert result.report_status == "COMPLETED"
    assert result.all_checks_passed is True
    assert result.lineage_checks_passed is True
    assert result.chronology_checks_passed is True
    assert result.safety_checks_passed is True
    assert len(result.stage_summaries) == 5
    assert result.session_status == "READY"
    assert result.session_action == "CONTINUE"
    assert result.performance_status == "TRACKED"
    assert result.current_equity == 10_100.0
    assert result.risk_status == "SAFE"
    assert result.risk_action == "ALLOW"

    return result


def validate_stage_failures() -> None:
    cases = (
        run_report(
            approval=create_approval(
                status="BLOCKED"
            )
        ),
        run_report(
            launch=create_launch(
                status="FAILED"
            )
        ),
        run_report(
            integration=create_integration(
                status="BLOCKED"
            )
        ),
        run_report(
            session=create_session(
                status="FAILED"
            )
        ),
        run_report(
            performance_risk=(
                create_performance_risk(
                    status="FAILED"
                )
            )
        ),
    )

    for result in cases:
        assert result.report_status == "BLOCKED"
        assert result.all_checks_passed is False


def validate_lineage_failures() -> None:
    wrong_approval = run_report(
        launch=create_launch(
            approval_id="different-approval"
        )
    )
    wrong_plan = run_report(
        launch=create_launch(
            plan_id="different-plan"
        )
    )
    wrong_launch = run_report(
        integration=create_integration(
            launch_id="different-launch"
        )
    )
    wrong_integration = run_report(
        session=create_session(
            integration_id="different-integration"
        )
    )
    wrong_ledger = run_report(
        session=create_session(
            ledger_id="different-ledger"
        )
    )
    wrong_session = run_report(
        performance_risk=create_performance_risk(
            session_refresh_id="different-session"
        )
    )
    wrong_performance = run_report(
        performance_risk=create_performance_risk(
            wrong_performance_source=True
        )
    )

    for result in (
        wrong_approval,
        wrong_plan,
        wrong_launch,
        wrong_integration,
        wrong_ledger,
        wrong_session,
        wrong_performance,
    ):
        assert result.report_status == "BLOCKED"
        assert result.lineage_checks_passed is False


def validate_chronology_and_safety() -> None:
    wrong_time = run_report(
        session=create_session(
            created_at="2026-07-27T10:01:30"
        )
    )
    unsafe_results = (
        run_report(
            approval=create_approval(unsafe=True)
        ),
        run_report(
            launch=create_launch(unsafe=True)
        ),
        run_report(
            integration=create_integration(
                unsafe=True
            )
        ),
        run_report(
            session=create_session(unsafe=True)
        ),
        run_report(
            performance_risk=(
                create_performance_risk(
                    unsafe=True
                )
            )
        ),
    )

    assert wrong_time.report_status == "BLOCKED"
    assert (
        wrong_time.chronology_checks_passed
        is False
    )

    for result in unsafe_results:
        assert result.report_status == "BLOCKED"
        assert result.safety_checks_passed is False
        assert result.broker_api_called is False


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch.object(
            report_module,
            "POST_RUN_FINAL_REPORT_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_post_run_final_report(
                    result
                )
            )
            loaded = (
                load_latest_post_run_final_report()
            )

        assert report_path.exists()
        assert latest_path.exists()
        assert loaded["version"] == "V11.5"
        assert (
            loaded["report_status"]
            == "COMPLETED"
        )
        assert len(loaded["stage_summaries"]) == 5

        with report_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        assert payload["plan_id"] == PLAN_ID
        assert payload["risk_status"] == "SAFE"


def main() -> None:
    print_header()

    validate_policy()
    completed = validate_completed_report()
    validate_stage_failures()
    validate_lineage_failures()
    validate_chronology_and_safety()
    validate_save_and_load(completed)

    checks = {
        "Version is V11.5": (
            completed.version == "V11.5"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Five successful stages completed": True,
        "Stage summaries were created": True,
        "Approval failure was blocked": True,
        "Launch failure was blocked": True,
        "Integration failure was blocked": True,
        "Session failure was blocked": True,
        "Performance risk failure was blocked": True,
        "Approval ID mismatch was blocked": True,
        "Plan ID mismatch was blocked": True,
        "Launch ID mismatch was blocked": True,
        "Integration ID mismatch was blocked": True,
        "Ledger ID mismatch was blocked": True,
        "Session refresh mismatch was blocked": True,
        "Performance source mismatch was blocked": True,
        "Chronology error was blocked": True,
        "Unsafe stage results were blocked": True,
        "Result save and load passed": True,
        "Execution remains blocked": (
            completed.execution_blocked is True
        ),
        "Broker API was not called": (
            completed.broker_api_called is False
        ),
        "Broker order was not created": (
            completed.broker_order_created
            is False
        ),
        "Live order was not created": (
            completed.live_order_created is False
        ),
        "Live execution not authorized": (
            completed.live_execution_authorized
            is False
        ),
    }
    checks["All checks passed"] = all(
        checks.values()
    )

    print()
    print("V11.5 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)
    for name, value in checks.items():
        print_check(name, value)

    if not checks["All checks passed"]:
        raise RuntimeError(
            "V11.5 Validation Check가 실패했습니다."
        )

    print("=" * LINE_LENGTH)
    print()
    print(
        "V11.5 post-run final report "
        "test completed successfully."
    )
    print(
        "V11.0부터 V11.4까지 Stage 상태와 ID 연결이 "
        "정상적으로 검증되었습니다."
    )
    print(
        "시간 순서 오류와 위험한 Stage 결과가 안전하게 차단되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
