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


# 일부 다운로드 작업공간에 V10.0 의존 파일이 없을 때만
# V10.7 하위 실행 모듈을 테스트용으로 격리합니다.
if (
    importlib.util.find_spec(
        "backtest.paper_portfolio_valuation"
    )
    is None
):
    performance_stub = types.ModuleType(
        "backtest.paper_portfolio_performance_tracker"
    )

    @dataclass
    class PaperPortfolioPerformanceResult:
        version: str = "V10.1"

    performance_stub.PaperPortfolioPerformanceResult = (
        PaperPortfolioPerformanceResult
    )
    sys.modules[
        "backtest.paper_portfolio_performance_tracker"
    ] = performance_stub

    batch_stub = types.ModuleType(
        "backtest.paper_trading_risk_gated_batch"
    )

    @dataclass
    class PaperTradingRiskGatedBatchResult:
        version: str = "V10.6"

    batch_stub.PaperTradingRiskGatedBatchResult = (
        PaperTradingRiskGatedBatchResult
    )
    sys.modules[
        "backtest.paper_trading_risk_gated_batch"
    ] = batch_stub

    pipeline_stub = types.ModuleType(
        "backtest.paper_trading_risk_gated_pipeline"
    )

    @dataclass
    class PaperTradingRiskGatedPipelineResult:
        version: str = "V10.5"

    pipeline_stub.PaperTradingRiskGatedPipelineResult = (
        PaperTradingRiskGatedPipelineResult
    )
    sys.modules[
        "backtest.paper_trading_risk_gated_pipeline"
    ] = pipeline_stub


import backtest.post_run_session_refresh as refresh_module
from backtest.approved_paper_run_ledger_integration import (
    ApprovedRunLedgerIntegrationRecord,
    ApprovedRunLedgerIntegrationResult,
)
from backtest.paper_trading_run_ledger import (
    PaperTradingRunLedgerEntry,
    PaperTradingRunLedgerResult,
    PaperTradingRunLedgerState,
)
from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryPolicy,
    PaperTradingSessionSummaryResult,
)
from backtest.post_run_session_refresh import (
    PostRunSessionRefreshPolicy,
    empty_refresh_state,
    load_latest_post_run_session_refresh,
    refresh_state_from_dict,
    run_post_run_session_refresh,
    save_post_run_session_refresh,
    validate_refresh_policy,
    validate_refresh_state,
)


LINE_LENGTH = 140
INTEGRATION_CREATED_AT = "2026-07-27T10:02:00"
REFRESHED_AT = "2026-07-27T10:05:00"
RUN_ID = "paper-run-v11-3-001"
LEDGER_ID = "ledger-v11-3-001"


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V11.3 "
        "POST-RUN SESSION REFRESH TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<84}: {value}")


def create_empty_dataclass_instance(dataclass_type):
    instance = object.__new__(dataclass_type)
    for item in fields(dataclass_type):
        setattr(instance, item.name, None)
    return instance


def create_ledger_entry(
    *,
    entry_id: str = "ledger-entry-v11-3-001",
    run_id: str = RUN_ID,
) -> PaperTradingRunLedgerEntry:
    return PaperTradingRunLedgerEntry(
        ledger_entry_id=entry_id,
        recorded_at="2026-07-27T10:01:00",
        run_type="BATCH_GATED",
        run_id=run_id,
        source_version="V10.6",
        source_created_at="2026-07-27T10:00:00",
        run_status="COMPLETED",
        run_status_label="COMPLETED",
        risk_monitor_id="risk-test-001",
        risk_status="SAFE",
        risk_action="ALLOW",
        gate_status="PASSED",
        gate_passed=True,
        requested_symbols=[
            "AAPL",
            "MSFT",
            "NVDA",
        ],
        requested_symbol_count=3,
        completed_symbol_count=3,
        blocked_symbol_count=0,
        failed_symbol_count=0,
        skipped_symbol_count=0,
        initial_equity=10_000.0,
        final_equity=10_100.0,
        equity_change=100.0,
        equity_change_percent=1.0,
        source_checks_passed=True,
        source_execution_blocked=True,
        source_broker_api_called=False,
        source_broker_order_created=False,
        source_live_order_created=False,
        source_live_execution_authorized=False,
        entry_checks_passed=True,
        reasons=("테스트 Ledger Entry입니다.",),
        warnings=("실거래는 없습니다.",),
    )


def create_ledger_state(
    *,
    ledger_id: str = LEDGER_ID,
    entry_id: str = "ledger-entry-v11-3-001",
    run_id: str = RUN_ID,
) -> PaperTradingRunLedgerState:
    entry = create_ledger_entry(
        entry_id=entry_id,
        run_id=run_id,
    )
    return PaperTradingRunLedgerState(
        ledger_id=ledger_id,
        created_at="2026-07-27T09:00:00",
        updated_at="2026-07-27T10:01:00",
        entry_count=1,
        daily_run_count=0,
        batch_run_count=1,
        completed_run_count=1,
        partial_run_count=0,
        blocked_run_count=0,
        failed_run_count=0,
        total_requested_symbol_count=3,
        total_completed_symbol_count=3,
        total_blocked_symbol_count=0,
        total_failed_symbol_count=0,
        total_skipped_symbol_count=0,
        cumulative_equity_change=100.0,
        entries=(entry,),
    )


def create_ledger_result(
    *,
    ledger_id: str = LEDGER_ID,
    update_id: str = "ledger-update-v11-3-001",
    entry_id: str = "ledger-entry-v11-3-001",
    run_id: str = RUN_ID,
    status: str = "UPDATED",
    unsafe: bool = False,
) -> PaperTradingRunLedgerResult:
    result = create_empty_dataclass_instance(
        PaperTradingRunLedgerResult
    )
    result.version = "V10.7"
    result.created_at = "2026-07-27T10:01:30"
    result.ledger_update_id = update_id
    result.ledger_id = ledger_id
    result.ledger_status = status
    result.ledger_status_label = status
    result.source_run_type = "BATCH_GATED"
    result.source_run_id = run_id
    result.source_run_status = "COMPLETED"
    result.entry_added = status == "UPDATED"
    result.duplicate_detected = False
    result.previous_entry_count = 0
    result.current_entry_count = 1
    result.all_checks_passed = status == "UPDATED"
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    result.ledger_entry = create_ledger_entry(
        entry_id=entry_id,
        run_id=run_id,
    )
    result.ledger_state = create_ledger_state(
        ledger_id=ledger_id,
        entry_id=entry_id,
        run_id=run_id,
    )
    return result


def create_integration_result(
    *,
    integration_id: str = "integration-v11-3-001",
    ledger_id: str = LEDGER_ID,
    update_id: str = "ledger-update-v11-3-001",
    entry_id: str = "ledger-entry-v11-3-001",
    run_id: str = RUN_ID,
    created_at: str = INTEGRATION_CREATED_AT,
    status: str = "LINKED",
    unsafe: bool = False,
) -> ApprovedRunLedgerIntegrationResult:
    result = create_empty_dataclass_instance(
        ApprovedRunLedgerIntegrationResult
    )
    record = ApprovedRunLedgerIntegrationRecord(
        integration_id=integration_id,
        created_at=created_at,
        launch_id=f"launch-{integration_id}",
        approval_id=f"approval-{integration_id}",
        plan_id=f"plan-{integration_id}",
        launcher_result_id=(
            f"launcher-result-{integration_id}"
        ),
        launcher_created_at="2026-07-27T10:00:00",
        launch_status="COMPLETED",
        ledger_update_id=update_id,
        ledger_id=ledger_id,
        ledger_created_at="2026-07-27T10:01:30",
        ledger_status="UPDATED",
        ledger_entry_id=entry_id,
        source_run_id=run_id,
        source_run_type="BATCH_GATED",
        source_run_status="COMPLETED",
        link_delay_minutes=1.5,
        launch_checks_passed=True,
        ledger_checks_passed=True,
        source_match_checks_passed=True,
        timing_checks_passed=True,
        duplicate_checks_passed=True,
        all_checks_passed=True,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reasons=("테스트 Integration입니다.",),
        warnings=("실거래는 없습니다.",),
    )
    result.version = "V11.2"
    result.created_at = created_at
    result.integration_result_id = (
        f"integration-result-{integration_id}"
    )
    result.integration_id = integration_id
    result.integration_status = status
    result.integration_status_label = status
    result.launch_id = record.launch_id
    result.approval_id = record.approval_id
    result.plan_id = record.plan_id
    result.ledger_update_id = update_id
    result.ledger_id = ledger_id
    result.ledger_entry_id = entry_id
    result.source_run_id = run_id
    result.record_added = status == "LINKED"
    result.all_checks_passed = status == "LINKED"
    result.integration_record = record
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    return result


def create_summary(
    ledger_state: PaperTradingRunLedgerState,
    *,
    unsafe: bool = False,
    wrong_ledger: bool = False,
) -> PaperTradingSessionSummaryResult:
    result = create_empty_dataclass_instance(
        PaperTradingSessionSummaryResult
    )
    result.version = "V10.8"
    result.created_at = REFRESHED_AT
    result.session_summary_id = str(
        f"summary-{ledger_state.ledger_id}"
    )
    result.source_ledger_id = (
        "wrong-ledger"
        if wrong_ledger
        else ledger_state.ledger_id
    )
    result.session_status = "READY"
    result.session_status_label = "READY"
    result.session_action = "CONTINUE"
    result.session_action_label = "CONTINUE"
    result.total_run_count = (
        ledger_state.entry_count
    )
    result.daily_run_count = (
        ledger_state.daily_run_count
    )
    result.batch_run_count = (
        ledger_state.batch_run_count
    )
    result.completed_run_count = (
        ledger_state.completed_run_count
    )
    result.partial_run_count = (
        ledger_state.partial_run_count
    )
    result.blocked_run_count = (
        ledger_state.blocked_run_count
    )
    result.failed_run_count = (
        ledger_state.failed_run_count
    )
    result.all_checks_passed = True
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    result.summary_policy = (
        PaperTradingSessionSummaryPolicy()
    )
    result.rule_results = {}
    result.reasons = [
        "테스트 Session Summary입니다."
    ]
    result.warnings = [
        "실거래는 없습니다."
    ]
    result.next_actions = []
    result.report_path = None
    result.latest_path = None
    return result


def safe_summary_builder(
    ledger_state: PaperTradingRunLedgerState,
) -> PaperTradingSessionSummaryResult:
    return create_summary(ledger_state)


def unsafe_summary_builder(
    ledger_state: PaperTradingRunLedgerState,
) -> PaperTradingSessionSummaryResult:
    return create_summary(
        ledger_state,
        unsafe=True,
    )


def wrong_summary_builder(
    ledger_state: PaperTradingRunLedgerState,
) -> PaperTradingSessionSummaryResult:
    return create_summary(
        ledger_state,
        wrong_ledger=True,
    )


def failing_summary_builder(
    _ledger_state: PaperTradingRunLedgerState,
):
    raise RuntimeError("테스트 Summary Builder 오류")


def run_refresh(
    *,
    integration=None,
    ledger=None,
    refreshed_at: str = REFRESHED_AT,
    builder=safe_summary_builder,
    state=None,
    policy=None,
):
    with patch.object(
        refresh_module,
        "print_post_run_session_refresh",
    ):
        return run_post_run_session_refresh(
            integration_result=(
                integration
                if integration is not None
                else create_integration_result()
            ),
            ledger_result=(
                ledger
                if ledger is not None
                else create_ledger_result()
            ),
            refreshed_at=refreshed_at,
            summary_builder=builder,
            refresh_state=(
                state
                if state is not None
                else empty_refresh_state()
            ),
            refresh_policy=policy,
        )


def validate_policy() -> None:
    policy = PostRunSessionRefreshPolicy()
    valid, errors = validate_refresh_policy(
        policy
    )
    assert valid is True
    assert errors == []

    try:
        policy.paper_only = False
        raise AssertionError(
            "Refresh Policy가 변경 가능 상태입니다."
        )
    except FrozenInstanceError:
        pass

    invalid = replace(
        policy,
        require_safe_summary=False,
    )
    invalid_valid, invalid_errors = (
        validate_refresh_policy(invalid)
    )
    assert invalid_valid is False
    assert invalid_errors


def validate_refreshed_result():
    result = run_refresh()

    assert result.version == "V11.3"
    assert result.refresh_status == "REFRESHED"
    assert result.summary_builder_called is True
    assert result.session_refreshed is True
    assert result.record_added is True
    assert result.current_record_count == 1
    assert result.summary_checks_passed is True
    assert result.all_checks_passed is True
    assert result.refresh_record is not None
    assert (
        result.refresh_record.refresh_delay_minutes
        == 3.0
    )
    return result


def validate_source_mismatch_is_blocked() -> None:
    ledger = create_ledger_result(
        ledger_id="different-ledger"
    )
    result = run_refresh(ledger=ledger)

    assert result.refresh_status == "BLOCKED"
    assert (
        result.source_match_checks_passed
        is False
    )
    assert result.summary_builder_called is False


def validate_invalid_sources_are_blocked() -> None:
    invalid_integration = run_refresh(
        integration=create_integration_result(
            status="BLOCKED"
        )
    )
    invalid_ledger = run_refresh(
        ledger=create_ledger_result(
            status="FAILED"
        )
    )
    unsafe_integration = run_refresh(
        integration=create_integration_result(
            unsafe=True
        )
    )
    unsafe_ledger = run_refresh(
        ledger=create_ledger_result(
            unsafe=True
        )
    )

    assert (
        invalid_integration.refresh_status
        == "BLOCKED"
    )
    assert invalid_ledger.refresh_status == "BLOCKED"
    assert (
        unsafe_integration.refresh_status
        == "BLOCKED"
    )
    assert unsafe_ledger.refresh_status == "BLOCKED"


def validate_timing_is_blocked() -> None:
    too_late = run_refresh(
        refreshed_at="2026-07-27T10:18:00"
    )
    before = run_refresh(
        refreshed_at="2026-07-27T10:01:00"
    )

    assert too_late.refresh_status == "BLOCKED"
    assert too_late.timing_checks_passed is False
    assert before.refresh_status == "BLOCKED"
    assert before.timing_checks_passed is False


def validate_bad_summary_fails() -> None:
    unsafe = run_refresh(
        builder=unsafe_summary_builder
    )
    wrong = run_refresh(
        builder=wrong_summary_builder
    )
    failed = run_refresh(
        builder=failing_summary_builder
    )
    missing = run_refresh(builder=None)

    assert unsafe.refresh_status == "FAILED"
    assert unsafe.summary_checks_passed is False
    assert wrong.refresh_status == "FAILED"
    assert wrong.summary_checks_passed is False
    assert failed.refresh_status == "FAILED"
    assert failed.summary_builder_called is True
    assert missing.refresh_status == "FAILED"
    assert missing.summary_builder_called is False


def validate_duplicate_is_blocked(
    refreshed_result,
) -> None:
    duplicate = run_refresh(
        state=refreshed_result.refresh_state
    )

    assert duplicate.refresh_status == "BLOCKED"
    assert duplicate.duplicate_detected is True
    assert duplicate.summary_builder_called is False
    assert duplicate.record_added is False
    assert duplicate.current_record_count == 1


def validate_trim_and_round_trip() -> None:
    policy = replace(
        PostRunSessionRefreshPolicy(),
        maximum_record_count=2,
    )

    results = []
    state = empty_refresh_state()
    for number in (1, 2, 3):
        integration_id = (
            f"integration-trim-{number:03d}"
        )
        update_id = (
            f"ledger-update-trim-{number:03d}"
        )
        entry_id = (
            f"ledger-entry-trim-{number:03d}"
        )
        run_id = f"run-trim-{number:03d}"
        result = run_refresh(
            integration=create_integration_result(
                integration_id=integration_id,
                update_id=update_id,
                entry_id=entry_id,
                run_id=run_id,
            ),
            ledger=create_ledger_result(
                update_id=update_id,
                entry_id=entry_id,
                run_id=run_id,
            ),
            state=state,
            policy=policy,
        )
        results.append(result)
        state = result.refresh_state

    third = results[-1]
    assert third.state_trimmed is True
    assert third.trimmed_record_count == 1
    assert third.current_record_count == 2

    restored = refresh_state_from_dict(
        third.refresh_state.to_dict()
    )
    valid, errors = validate_refresh_state(
        restored
    )
    assert valid is True
    assert errors == []
    assert (
        restored.refresh_state_id
        == third.refresh_state.refresh_state_id
    )
    assert restored.records == third.refresh_state.records


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch.object(
            refresh_module,
            "POST_RUN_SESSION_REFRESH_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_post_run_session_refresh(
                    result
                )
            )
            loaded = (
                load_latest_post_run_session_refresh()
            )

        assert report_path.exists()
        assert latest_path.exists()
        assert loaded["version"] == "V11.3"
        assert (
            loaded["refresh_status"]
            == "REFRESHED"
        )
        assert (
            loaded["refresh_state"]["record_count"]
            == 1
        )

        with report_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        assert (
            payload["session_summary"][
                "source_ledger_id"
            ]
            == LEDGER_ID
        )


def validate_execution_safety(results: list) -> None:
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
    refreshed_result = validate_refreshed_result()
    validate_source_mismatch_is_blocked()
    validate_invalid_sources_are_blocked()
    validate_timing_is_blocked()
    validate_bad_summary_fails()
    validate_duplicate_is_blocked(
        refreshed_result
    )
    validate_trim_and_round_trip()
    validate_save_and_load(refreshed_result)

    safety_results = [
        refreshed_result,
        run_refresh(
            ledger=create_ledger_result(
                ledger_id="different"
            )
        ),
        run_refresh(
            builder=unsafe_summary_builder
        ),
        run_refresh(
            builder=failing_summary_builder
        ),
    ]
    validate_execution_safety(safety_results)

    checks = {
        "Version is V11.3": (
            refreshed_result.version == "V11.3"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Linked ledger refreshed session": True,
        "Summary builder was called": True,
        "Refresh delay was calculated": True,
        "Source mismatch was blocked": True,
        "Invalid integration was blocked": True,
        "Invalid ledger was blocked": True,
        "Unsafe integration was blocked": True,
        "Unsafe ledger was blocked": True,
        "Late refresh was blocked": True,
        "Refresh-before-integration was blocked": True,
        "Unsafe summary failed": True,
        "Wrong summary ledger failed": True,
        "Builder exception was contained": True,
        "Missing builder failed safely": True,
        "Duplicate refresh was blocked": True,
        "Oldest refresh records were trimmed": True,
        "Refresh state round-trip passed": True,
        "Result save and load passed": True,
        "Execution remains blocked": (
            refreshed_result.execution_blocked
            is True
        ),
        "Broker API was not called": (
            refreshed_result.broker_api_called
            is False
        ),
        "Broker order was not created": (
            refreshed_result.broker_order_created
            is False
        ),
        "Live order was not created": (
            refreshed_result.live_order_created
            is False
        ),
        "Live execution not authorized": (
            refreshed_result
            .live_execution_authorized
            is False
        ),
    }
    checks["All checks passed"] = all(
        checks.values()
    )

    print()
    print("V11.3 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)
    for name, value in checks.items():
        print_check(name, value)

    if not checks["All checks passed"]:
        raise RuntimeError(
            "V11.3 Validation Check가 실패했습니다."
        )

    print("=" * LINE_LENGTH)
    print()
    print(
        "V11.3 post-run session refresh "
        "test completed successfully."
    )
    print(
        "최신 Ledger 기반 Session Summary 갱신과 중복 방지가 "
        "정상적으로 검증되었습니다."
    )
    print(
        "불일치, 시간 초과 및 위험한 Summary가 안전하게 차단되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
