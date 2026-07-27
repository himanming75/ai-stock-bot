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


# 다운로드 작업공간에 V10.0 파일이 없을 때만
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


import backtest.post_run_performance_risk_refresh as refresh_module
from backtest.paper_portfolio_performance_tracker import (
    PaperPerformanceSnapshot,
    PaperPortfolioPerformancePolicy,
    PaperPortfolioPerformanceResult,
)
from backtest.paper_trading_risk_monitor import (
    PaperTradingRiskMonitorPolicy,
    PaperTradingRiskMonitorResult,
)
from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryPolicy,
    PaperTradingSessionSummaryResult,
)
from backtest.post_run_performance_risk_refresh import (
    PostRunPerformanceRiskPolicy,
    empty_refresh_state,
    load_latest_post_run_performance_risk,
    run_post_run_performance_risk_refresh,
    save_post_run_performance_risk_refresh,
    state_from_dict,
    validate_refresh_policy,
    validate_refresh_state,
)
from backtest.post_run_session_refresh import (
    PostRunSessionRefreshResult,
)


LINE_LENGTH = 140
SESSION_CREATED_AT = "2026-07-27T10:05:00"
REFRESHED_AT = "2026-07-27T10:10:00"
PORTFOLIO_ID = "portfolio-v11-4-001"
PERFORMANCE_ID = "performance-v11-4-001"


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V11.4 "
        "POST-RUN PERFORMANCE & RISK REFRESH TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<84}: {value}")


def empty_instance(dataclass_type):
    instance = object.__new__(dataclass_type)
    for item in fields(dataclass_type):
        setattr(instance, item.name, None)
    return instance


def create_session_summary():
    result = empty_instance(
        PaperTradingSessionSummaryResult
    )
    result.version = "V10.8"
    result.created_at = SESSION_CREATED_AT
    result.session_summary_id = "summary-v11-4-001"
    result.source_ledger_id = "ledger-v11-4-001"
    result.session_status = "READY"
    result.session_status_label = "READY"
    result.session_action = "CONTINUE"
    result.session_action_label = "CONTINUE"
    result.total_run_count = 1
    result.all_checks_passed = True
    result.execution_blocked = True
    result.broker_api_called = False
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    result.summary_policy = (
        PaperTradingSessionSummaryPolicy()
    )
    result.rule_results = {}
    result.reasons = []
    result.warnings = []
    result.next_actions = []
    result.report_path = None
    result.latest_path = None
    return result


def create_session_refresh(
    *,
    refresh_id: str = "session-refresh-v11-4-001",
    created_at: str = SESSION_CREATED_AT,
    status: str = "REFRESHED",
    unsafe: bool = False,
):
    result = empty_instance(
        PostRunSessionRefreshResult
    )
    result.version = "V11.3"
    result.created_at = created_at
    result.refresh_id = refresh_id
    result.refresh_status = status
    result.session_refreshed = (
        status == "REFRESHED"
    )
    result.summary_checks_passed = (
        status == "REFRESHED"
    )
    result.all_checks_passed = (
        status == "REFRESHED"
    )
    result.integration_id = (
        "integration-v11-4-001"
    )
    result.ledger_id = "ledger-v11-4-001"
    result.session_summary_id = (
        "summary-v11-4-001"
    )
    result.session_summary = create_session_summary()
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    return result


def create_snapshot():
    snapshot = empty_instance(
        PaperPerformanceSnapshot
    )
    for item in fields(PaperPerformanceSnapshot):
        value = getattr(snapshot, item.name)
        if value is None:
            setattr(snapshot, item.name, 0)
    return snapshot


def create_performance(
    *,
    performance_id: str = PERFORMANCE_ID,
    portfolio_id: str = PORTFOLIO_ID,
    status: str = "TRACKED",
    unsafe: bool = False,
):
    result = empty_instance(
        PaperPortfolioPerformanceResult
    )
    result.version = "V10.1"
    result.created_at = REFRESHED_AT
    result.performance_id = performance_id
    result.portfolio_id = portfolio_id
    result.source_valuation_id = "valuation-test-001"
    result.source_valuation_file = None
    result.performance_status = status
    result.performance_status_label = status
    result.current_equity = 10_100.0
    result.cumulative_return_percent = 1.0
    result.maximum_drawdown_percent = 2.0
    result.all_checks_passed = (
        status in {
            "TRACKED",
            "FIRST_SNAPSHOT",
            "NO_CHANGE",
        }
    )
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    result.performance_policy = (
        PaperPortfolioPerformancePolicy()
    )
    result.latest_snapshot = create_snapshot()
    result.performance_history = [
        result.latest_snapshot
    ]
    result.reasons = []
    result.warnings = []
    result.next_actions = []
    result.report_path = None
    result.latest_path = None
    result.history_path = None
    return result


def create_risk(
    performance,
    *,
    portfolio_id: str | None = None,
    source_id: str | None = None,
    equity: float | None = None,
    status: str = "SAFE",
    unsafe: bool = False,
):
    result = empty_instance(
        PaperTradingRiskMonitorResult
    )
    result.version = "V10.4"
    result.created_at = REFRESHED_AT
    result.monitor_id = "risk-monitor-v11-4-001"
    result.portfolio_id = (
        portfolio_id
        if portfolio_id is not None
        else performance.portfolio_id
    )
    result.source_performance_id = (
        source_id
        if source_id is not None
        else performance.performance_id
    )
    result.source_performance_file = None
    result.risk_status = status
    result.risk_status_label = status
    result.risk_action = (
        "ALLOW"
        if status == "SAFE"
        else "BLOCK"
    )
    result.risk_action_label = result.risk_action
    result.current_equity = (
        equity
        if equity is not None
        else performance.current_equity
    )
    result.all_checks_passed = True
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    result.monitor_policy = (
        PaperTradingRiskMonitorPolicy()
    )
    result.rule_results = {}
    result.reasons = []
    result.warnings = []
    result.next_actions = []
    result.report_path = None
    result.latest_path = None
    return result


def safe_performance_builder(_summary):
    return create_performance()


def unsafe_performance_builder(_summary):
    return create_performance(unsafe=True)


def failing_performance_builder(_summary):
    raise RuntimeError("테스트 Performance 오류")


def safe_risk_builder(performance):
    return create_risk(performance)


def unsafe_risk_builder(performance):
    return create_risk(
        performance,
        unsafe=True,
    )


def mismatch_risk_builder(performance):
    return create_risk(
        performance,
        portfolio_id="different-portfolio",
        source_id="different-performance",
        equity=9_999.0,
    )


def failing_risk_builder(_performance):
    raise RuntimeError("테스트 Risk 오류")


def run_refresh(
    *,
    session=None,
    refreshed_at: str = REFRESHED_AT,
    performance_builder=safe_performance_builder,
    risk_builder=safe_risk_builder,
    state=None,
    policy=None,
):
    with patch.object(
        refresh_module,
        "print_post_run_performance_risk_refresh",
    ):
        return (
            run_post_run_performance_risk_refresh(
                session_refresh_result=(
                    session
                    if session is not None
                    else create_session_refresh()
                ),
                refreshed_at=refreshed_at,
                performance_builder=(
                    performance_builder
                ),
                risk_builder=risk_builder,
                refresh_state=(
                    state
                    if state is not None
                    else empty_refresh_state()
                ),
                refresh_policy=policy,
            )
        )


def validate_policy() -> None:
    policy = PostRunPerformanceRiskPolicy()
    valid, errors = validate_refresh_policy(
        policy
    )
    assert valid is True
    assert errors == []

    try:
        policy.paper_only = False
        raise AssertionError(
            "Policy가 변경 가능 상태입니다."
        )
    except FrozenInstanceError:
        pass

    invalid = replace(
        policy,
        require_successful_risk=False,
    )
    invalid_valid, invalid_errors = (
        validate_refresh_policy(invalid)
    )
    assert invalid_valid is False
    assert invalid_errors


def validate_refreshed_result():
    result = run_refresh()
    assert result.version == "V11.4"
    assert result.refresh_status == "REFRESHED"
    assert result.performance_builder_called is True
    assert result.risk_builder_called is True
    assert result.performance_refreshed is True
    assert result.risk_refreshed is True
    assert result.record_added is True
    assert result.current_record_count == 1
    assert result.risk_status == "SAFE"
    assert result.risk_action == "ALLOW"
    assert result.all_checks_passed is True
    return result


def validate_preflight_blocks() -> None:
    invalid_session = run_refresh(
        session=create_session_refresh(
            status="BLOCKED"
        )
    )
    unsafe_session = run_refresh(
        session=create_session_refresh(
            unsafe=True
        )
    )
    late = run_refresh(
        refreshed_at="2026-07-27T10:26:00"
    )
    early = run_refresh(
        refreshed_at="2026-07-27T10:04:00"
    )

    assert invalid_session.refresh_status == "BLOCKED"
    assert unsafe_session.refresh_status == "BLOCKED"
    assert late.refresh_status == "BLOCKED"
    assert early.refresh_status == "BLOCKED"
    assert late.performance_builder_called is False


def validate_builder_failures() -> None:
    unsafe_performance = run_refresh(
        performance_builder=(
            unsafe_performance_builder
        )
    )
    performance_exception = run_refresh(
        performance_builder=(
            failing_performance_builder
        )
    )
    unsafe_risk = run_refresh(
        risk_builder=unsafe_risk_builder
    )
    mismatch = run_refresh(
        risk_builder=mismatch_risk_builder
    )
    risk_exception = run_refresh(
        risk_builder=failing_risk_builder
    )
    missing = run_refresh(
        performance_builder=None
    )

    assert unsafe_performance.refresh_status == "FAILED"
    assert performance_exception.refresh_status == "FAILED"
    assert unsafe_risk.refresh_status == "FAILED"
    assert mismatch.refresh_status == "FAILED"
    assert (
        mismatch.source_match_checks_passed
        is False
    )
    assert risk_exception.refresh_status == "FAILED"
    assert missing.refresh_status == "FAILED"


def validate_duplicate_is_blocked(result) -> None:
    duplicate = run_refresh(
        state=result.refresh_state
    )
    assert duplicate.refresh_status == "BLOCKED"
    assert duplicate.duplicate_detected is True
    assert duplicate.record_added is False
    assert duplicate.performance_builder_called is False


def validate_trim_and_round_trip() -> None:
    policy = replace(
        PostRunPerformanceRiskPolicy(),
        maximum_record_count=2,
    )
    state = empty_refresh_state()
    results = []

    for number in (1, 2, 3):
        session = create_session_refresh(
            refresh_id=(
                f"session-refresh-trim-{number}"
            )
        )
        result = run_refresh(
            session=session,
            state=state,
            policy=policy,
        )
        results.append(result)
        state = result.refresh_state

    third = results[-1]
    assert third.state_trimmed is True
    assert third.trimmed_record_count == 1
    assert third.current_record_count == 2

    restored = state_from_dict(
        third.refresh_state.to_dict()
    )
    valid, errors = validate_refresh_state(
        restored
    )
    assert valid is True
    assert errors == []
    assert restored.records == third.refresh_state.records


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch.object(
            refresh_module,
            "POST_RUN_PERFORMANCE_RISK_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_post_run_performance_risk_refresh(
                    result
                )
            )
            loaded = (
                load_latest_post_run_performance_risk()
            )

        assert report_path.exists()
        assert latest_path.exists()
        assert loaded["version"] == "V11.4"
        assert loaded["refresh_status"] == "REFRESHED"

        with report_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        assert (
            payload["risk_result"][
                "source_performance_id"
            ]
            == PERFORMANCE_ID
        )


def validate_execution_safety(results) -> None:
    for result in results:
        assert result.execution_blocked is True
        assert result.broker_api_called is False
        assert result.broker_order_created is False
        assert result.live_order_created is False
        assert (
            result.live_execution_authorized
            is False
        )


def main() -> None:
    print_header()

    validate_policy()
    refreshed = validate_refreshed_result()
    validate_preflight_blocks()
    validate_builder_failures()
    validate_duplicate_is_blocked(refreshed)
    validate_trim_and_round_trip()
    validate_save_and_load(refreshed)

    validate_execution_safety(
        [
            refreshed,
            run_refresh(
                performance_builder=(
                    unsafe_performance_builder
                )
            ),
            run_refresh(
                risk_builder=unsafe_risk_builder
            ),
            run_refresh(
                risk_builder=mismatch_risk_builder
            ),
        ]
    )

    checks = {
        "Version is V11.4": (
            refreshed.version == "V11.4"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Performance and risk refreshed": True,
        "SAFE risk action is ALLOW": True,
        "Invalid session was blocked": True,
        "Unsafe session was blocked": True,
        "Late refresh was blocked": True,
        "Early refresh was blocked": True,
        "Unsafe performance failed": True,
        "Performance exception was contained": True,
        "Unsafe risk failed": True,
        "Portfolio mismatch failed": True,
        "Performance source mismatch failed": True,
        "Risk exception was contained": True,
        "Missing builder failed safely": True,
        "Duplicate refresh was blocked": True,
        "Oldest records were trimmed": True,
        "State round-trip passed": True,
        "Result save and load passed": True,
        "Execution remains blocked": (
            refreshed.execution_blocked is True
        ),
        "Broker API was not called": (
            refreshed.broker_api_called is False
        ),
        "Broker order was not created": (
            refreshed.broker_order_created is False
        ),
        "Live order was not created": (
            refreshed.live_order_created is False
        ),
        "Live execution not authorized": (
            refreshed.live_execution_authorized
            is False
        ),
    }
    checks["All checks passed"] = all(
        checks.values()
    )

    print()
    print("V11.4 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)
    for name, value in checks.items():
        print_check(name, value)

    if not checks["All checks passed"]:
        raise RuntimeError(
            "V11.4 Validation Check가 실패했습니다."
        )

    print("=" * LINE_LENGTH)
    print()
    print(
        "V11.4 post-run performance and risk refresh "
        "test completed successfully."
    )
    print(
        "성과 및 Risk 갱신, Source 일치와 중복 방지가 "
        "정상적으로 검증되었습니다."
    )
    print(
        "위험한 Builder 결과와 실행 예외가 안전하게 차단되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
