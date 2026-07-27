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


# 이 다운로드 작업공간에 오래된 V10.x 의존 파일이 없을 때만
# V10.7 모듈의 하위 의존성을 테스트용으로 격리합니다.
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


import backtest.approved_paper_run_ledger_integration as integration_module
from backtest.approved_paper_run_launcher import (
    ApprovedPaperRunLauncherResult,
)
from backtest.approved_paper_run_ledger_integration import (
    ApprovedRunLedgerIntegrationPolicy,
    empty_integration_state,
    integration_state_from_dict,
    load_latest_approved_run_ledger_integration,
    run_approved_paper_run_ledger_integration,
    save_approved_run_ledger_integration,
    validate_integration_policy,
    validate_integration_state,
)
from backtest.paper_trading_run_ledger import (
    PaperTradingRunLedgerEntry,
    PaperTradingRunLedgerResult,
)


LINE_LENGTH = 140
RUN_ID = "paper-run-v11-2-001"
LAUNCH_CREATED_AT = "2026-07-27T10:00:00"
LEDGER_CREATED_AT = "2026-07-27T10:02:00"


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V11.2 "
        "APPROVED PAPER RUN LEDGER INTEGRATION TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<84}: {value}")


def create_empty_dataclass_instance(dataclass_type):
    instance = object.__new__(dataclass_type)

    for item in fields(dataclass_type):
        setattr(instance, item.name, None)

    return instance


def create_launch_result(
    *,
    launch_id: str = "launch-v11-2-001",
    run_id: str = RUN_ID,
    created_at: str = LAUNCH_CREATED_AT,
    status: str = "COMPLETED",
    unsafe: bool = False,
) -> ApprovedPaperRunLauncherResult:
    result = create_empty_dataclass_instance(
        ApprovedPaperRunLauncherResult
    )

    result.version = "V11.1"
    result.created_at = created_at
    result.launcher_result_id = (
        f"launcher-result-{launch_id}"
    )
    result.launcher_state_id = (
        "launcher-state-test-001"
    )
    result.launch_id = launch_id
    result.approval_id = (
        f"approval-{launch_id}"
    )
    result.plan_id = f"plan-{launch_id}"
    result.launch_status = status
    result.launch_status_label = status
    result.executor_called = (
        status == "COMPLETED"
    )
    result.executor_result = {
        "run_id": run_id,
        "status": "COMPLETED",
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
    }
    result.paper_run_completed = (
        status == "COMPLETED"
    )
    result.executor_checks_passed = (
        status == "COMPLETED"
    )
    result.all_checks_passed = (
        status == "COMPLETED"
    )
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    return result


def create_ledger_entry(
    *,
    run_id: str = RUN_ID,
    entry_id: str = "ledger-entry-v11-2-001",
    unsafe: bool = False,
) -> PaperTradingRunLedgerEntry:
    return PaperTradingRunLedgerEntry(
        ledger_entry_id=entry_id,
        recorded_at=LEDGER_CREATED_AT,
        run_type="BATCH_GATED",
        run_id=run_id,
        source_version="V10.6",
        source_created_at=(
            "2026-07-27T10:00:30"
        ),
        run_status="COMPLETED",
        run_status_label="COMPLETED",
        risk_monitor_id="risk-monitor-test-001",
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
        source_broker_api_called=unsafe,
        source_broker_order_created=False,
        source_live_order_created=False,
        source_live_execution_authorized=False,
        entry_checks_passed=True,
        reasons=(
            "테스트용 V10.7 Ledger Entry입니다.",
        ),
        warnings=(
            "실거래는 실행하지 않습니다.",
        ),
    )


def create_ledger_result(
    *,
    run_id: str = RUN_ID,
    created_at: str = LEDGER_CREATED_AT,
    entry_id: str = "ledger-entry-v11-2-001",
    status: str = "UPDATED",
    unsafe: bool = False,
) -> PaperTradingRunLedgerResult:
    result = create_empty_dataclass_instance(
        PaperTradingRunLedgerResult
    )

    result.version = "V10.7"
    result.created_at = created_at
    result.ledger_update_id = (
        f"ledger-update-{entry_id}"
    )
    result.ledger_id = "ledger-test-001"
    result.ledger_status = status
    result.ledger_status_label = status
    result.source_run_type = "BATCH_GATED"
    result.source_run_id = run_id
    result.source_run_status = "COMPLETED"
    result.entry_added = status == "UPDATED"
    result.duplicate_detected = False
    result.all_checks_passed = (
        status == "UPDATED"
    )
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False
    result.ledger_entry = create_ledger_entry(
        run_id=run_id,
        entry_id=entry_id,
        unsafe=unsafe,
    )

    return result


def run_integration(
    *,
    launch=None,
    ledger=None,
    state=None,
    policy=None,
):
    with patch.object(
        integration_module,
        "print_approved_run_ledger_integration",
    ):
        return (
            run_approved_paper_run_ledger_integration(
                launch_result=(
                    launch
                    if launch is not None
                    else create_launch_result()
                ),
                ledger_result=(
                    ledger
                    if ledger is not None
                    else create_ledger_result()
                ),
                integration_state=(
                    state
                    if state is not None
                    else empty_integration_state()
                ),
                integration_policy=policy,
            )
        )


def validate_policy() -> None:
    policy = ApprovedRunLedgerIntegrationPolicy()
    valid, errors = validate_integration_policy(
        policy
    )

    assert valid is True
    assert errors == []

    try:
        policy.paper_only = False
        raise AssertionError(
            "Integration Policy가 변경 가능 상태입니다."
        )
    except FrozenInstanceError:
        pass

    invalid_policy = replace(
        policy,
        require_execution_safety=False,
    )
    invalid_valid, invalid_errors = (
        validate_integration_policy(
            invalid_policy
        )
    )
    assert invalid_valid is False
    assert invalid_errors


def validate_linked_result():
    result = run_integration()

    assert result.version == "V11.2"
    assert result.integration_status == "LINKED"
    assert result.record_added is True
    assert result.duplicate_detected is False
    assert result.current_record_count == 1
    assert result.all_checks_passed is True
    assert result.integration_record is not None
    assert (
        result.integration_record.source_run_id
        == RUN_ID
    )
    assert (
        result.integration_record.link_delay_minutes
        == 2.0
    )

    return result


def validate_run_id_mismatch_is_blocked() -> None:
    result = run_integration(
        ledger=create_ledger_result(
            run_id="different-run-id"
        )
    )

    assert result.integration_status == "BLOCKED"
    assert (
        result.source_match_checks_passed
        is False
    )
    assert result.record_added is False


def validate_incomplete_launch_is_blocked() -> None:
    result = run_integration(
        launch=create_launch_result(
            status="BLOCKED"
        )
    )

    assert result.integration_status == "BLOCKED"
    assert result.launch_checks_passed is False
    assert result.record_added is False


def validate_failed_ledger_is_blocked() -> None:
    result = run_integration(
        ledger=create_ledger_result(
            status="FAILED"
        )
    )

    assert result.integration_status == "BLOCKED"
    assert result.ledger_checks_passed is False
    assert result.record_added is False


def validate_unsafe_sources_are_blocked() -> None:
    unsafe_launch = run_integration(
        launch=create_launch_result(
            unsafe=True
        )
    )
    unsafe_ledger = run_integration(
        ledger=create_ledger_result(
            unsafe=True
        )
    )

    assert unsafe_launch.integration_status == "BLOCKED"
    assert unsafe_launch.launch_checks_passed is False
    assert unsafe_ledger.integration_status == "BLOCKED"
    assert unsafe_ledger.ledger_checks_passed is False


def validate_timing_is_blocked() -> None:
    too_late = run_integration(
        ledger=create_ledger_result(
            created_at="2026-07-27T10:11:00"
        )
    )
    before_launch = run_integration(
        ledger=create_ledger_result(
            created_at="2026-07-27T09:59:00"
        )
    )

    assert too_late.integration_status == "BLOCKED"
    assert too_late.timing_checks_passed is False
    assert before_launch.integration_status == "BLOCKED"
    assert before_launch.timing_checks_passed is False


def validate_duplicate_is_blocked(
    linked_result,
) -> None:
    duplicate = run_integration(
        state=linked_result.integration_state
    )

    assert duplicate.integration_status == "BLOCKED"
    assert duplicate.duplicate_detected is True
    assert (
        duplicate.duplicate_checks_passed
        is False
    )
    assert duplicate.record_added is False
    assert duplicate.current_record_count == 1


def validate_trim_and_round_trip() -> None:
    policy = replace(
        ApprovedRunLedgerIntegrationPolicy(),
        maximum_record_count=2,
    )

    first = run_integration(
        launch=create_launch_result(
            launch_id="launch-trim-001",
            run_id="run-trim-001",
        ),
        ledger=create_ledger_result(
            run_id="run-trim-001",
            entry_id="entry-trim-001",
        ),
        policy=policy,
    )
    second = run_integration(
        launch=create_launch_result(
            launch_id="launch-trim-002",
            run_id="run-trim-002",
        ),
        ledger=create_ledger_result(
            run_id="run-trim-002",
            entry_id="entry-trim-002",
        ),
        state=first.integration_state,
        policy=policy,
    )
    third = run_integration(
        launch=create_launch_result(
            launch_id="launch-trim-003",
            run_id="run-trim-003",
        ),
        ledger=create_ledger_result(
            run_id="run-trim-003",
            entry_id="entry-trim-003",
        ),
        state=second.integration_state,
        policy=policy,
    )

    assert third.state_trimmed is True
    assert third.trimmed_record_count == 1
    assert third.current_record_count == 2
    assert [
        record.launch_id
        for record in third.integration_state.records
    ] == [
        "launch-trim-002",
        "launch-trim-003",
    ]

    restored = integration_state_from_dict(
        third.integration_state.to_dict()
    )
    valid, errors = validate_integration_state(
        restored
    )
    assert valid is True
    assert errors == []
    assert (
        restored.integration_state_id
        == third.integration_state.integration_state_id
    )
    assert (
        restored.records
        == third.integration_state.records
    )


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch.object(
            integration_module,
            "APPROVED_RUN_LEDGER_INTEGRATION_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_approved_run_ledger_integration(
                    result
                )
            )
            loaded = (
                load_latest_approved_run_ledger_integration()
            )

        assert report_path.exists()
        assert latest_path.exists()
        assert loaded["version"] == "V11.2"
        assert (
            loaded["integration_status"]
            == "LINKED"
        )
        assert (
            loaded["integration_state"]["record_count"]
            == 1
        )

        with report_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        assert (
            payload["integration_record"][
                "source_run_id"
            ]
            == RUN_ID
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
    linked_result = validate_linked_result()
    validate_run_id_mismatch_is_blocked()
    validate_incomplete_launch_is_blocked()
    validate_failed_ledger_is_blocked()
    validate_unsafe_sources_are_blocked()
    validate_timing_is_blocked()
    validate_duplicate_is_blocked(
        linked_result
    )
    validate_trim_and_round_trip()
    validate_save_and_load(linked_result)

    safety_results = [
        linked_result,
        run_integration(
            ledger=create_ledger_result(
                run_id="different"
            )
        ),
        run_integration(
            launch=create_launch_result(
                unsafe=True
            )
        ),
        run_integration(
            ledger=create_ledger_result(
                unsafe=True
            )
        ),
    ]
    validate_execution_safety(safety_results)

    checks = {
        "Version is V11.2": (
            linked_result.version == "V11.2"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Completed launch linked to ledger": True,
        "Link delay was calculated": True,
        "Run ID mismatch was blocked": True,
        "Incomplete launch was blocked": True,
        "Failed ledger update was blocked": True,
        "Unsafe launcher result was blocked": True,
        "Unsafe ledger result was blocked": True,
        "Late ledger link was blocked": True,
        "Ledger-before-launch was blocked": True,
        "Duplicate launch link was blocked": True,
        "Oldest integration records were trimmed": True,
        "Integration state round-trip passed": True,
        "Result save and load passed": True,
        "Execution remains blocked": (
            linked_result.execution_blocked
            is True
        ),
        "Broker API was not called": (
            linked_result.broker_api_called
            is False
        ),
        "Broker order was not created": (
            linked_result.broker_order_created
            is False
        ),
        "Live order was not created": (
            linked_result.live_order_created
            is False
        ),
        "Live execution not authorized": (
            linked_result
            .live_execution_authorized
            is False
        ),
    }
    checks["All checks passed"] = all(
        checks.values()
    )

    print()
    print("V11.2 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)
    for name, value in checks.items():
        print_check(name, value)

    if not checks["All checks passed"]:
        raise RuntimeError(
            "V11.2 Validation Check가 실패했습니다."
        )

    print("=" * LINE_LENGTH)
    print()
    print(
        "V11.2 approved paper run ledger integration "
        "test completed successfully."
    )
    print(
        "승인 실행과 Ledger Entry 연결, Run ID 및 시간 검사가 "
        "정상적으로 검증되었습니다."
    )
    print(
        "중복, 불일치 및 위험한 Source 결과가 안전하게 차단되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
