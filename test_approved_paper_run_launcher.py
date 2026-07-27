import importlib.util
import json
import sys
import tempfile
import types
from dataclasses import (
    FrozenInstanceError,
    dataclass,
    replace,
)
from pathlib import Path
from unittest.mock import patch


# 다운로드 작업공간에 V10.0 이전 의존 파일이 없을 때만
# V11.1이 직접 사용하지 않는 Ledger 모듈을 격리합니다.
if (
    importlib.util.find_spec(
        "backtest.paper_portfolio_valuation"
    )
    is None
):
    ledger_stub = types.ModuleType(
        "backtest.paper_trading_run_ledger"
    )

    @dataclass
    class PaperTradingRunLedgerEntry:
        run_status: str = "COMPLETED"

    @dataclass
    class PaperTradingRunLedgerState:
        entries: tuple = ()

    def load_latest_ledger_state():
        return PaperTradingRunLedgerState()

    def validate_ledger_state(_state):
        return (True, [])

    ledger_stub.PaperTradingRunLedgerEntry = (
        PaperTradingRunLedgerEntry
    )
    ledger_stub.PaperTradingRunLedgerState = (
        PaperTradingRunLedgerState
    )
    ledger_stub.load_latest_ledger_state = (
        load_latest_ledger_state
    )
    ledger_stub.validate_ledger_state = (
        validate_ledger_state
    )
    sys.modules[
        "backtest.paper_trading_run_ledger"
    ] = ledger_stub


import backtest.approved_paper_run_launcher as launcher_module
from backtest.approved_paper_run_launcher import (
    ApprovedPaperRunLauncherPolicy,
    empty_launcher_state,
    launcher_state_from_dict,
    load_latest_approved_paper_run_launcher,
    run_approved_paper_run_launcher,
    save_approved_paper_run_launcher,
    validate_launcher_policy,
    validate_launcher_state,
)
from backtest.paper_trading_schedule_planner import (
    PaperTradingSchedulePlan,
)
from backtest.scheduled_paper_run_approval import (
    ScheduledPaperRunApprovalRecord,
)


LINE_LENGTH = 140
SCHEDULED_AT = "2026-07-27T10:00:00"
LAUNCHED_AT = "2026-07-27T09:55:00"
LAUNCH_TEXT = "LAUNCH PAPER RUN"


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V11.1 "
        "APPROVED PAPER RUN LAUNCHER TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<84}: {value}")


def create_valid_plan(
    *,
    plan_id: str = "plan-v11-1-test-001",
) -> PaperTradingSchedulePlan:
    return PaperTradingSchedulePlan(
        plan_id=plan_id,
        created_at="2026-07-27T08:30:00",
        schedule_key=(
            f"{SCHEDULED_AT}|AAPL,MSFT,NVDA"
        ),
        scheduled_at=SCHEDULED_AT,
        scheduled_date="2026-07-27",
        scheduled_time="10:00:00",
        timezone_name="America/Los_Angeles",
        weekday=0,
        weekday_label="MONDAY",
        requested_symbols=(
            "AAPL",
            "MSFT",
            "NVDA",
        ),
        normalized_symbols=(
            "AAPL",
            "MSFT",
            "NVDA",
        ),
        duplicate_symbols=(),
        requested_symbol_count=3,
        unique_symbol_count=3,
        plan_status="PLANNED",
        plan_status_label="Paper Trading 실행 계획 완료",
        plan_action="QUEUE",
        plan_action_label="수동 실행 대기열 등록",
        source_summary_id="summary-ready-001",
        source_session_status="READY",
        source_session_action="CONTINUE",
        weekday_allowed=True,
        time_allowed=True,
        symbol_checks_passed=True,
        session_checks_passed=True,
        duplicate_checks_passed=True,
        all_checks_passed=True,
        manual_launch_required=True,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reasons=(
            "테스트용 승인 대상 Plan입니다.",
        ),
        warnings=(
            "자동 실행은 허용되지 않습니다.",
        ),
    )


def create_approved_record(
    *,
    approval_id: str = "approval-v11-1-test-001",
    plan_id: str = "plan-v11-1-test-001",
    approval_status: str = "APPROVED",
    expires_at: str = "2026-07-27T10:05:00",
) -> ScheduledPaperRunApprovalRecord:
    return ScheduledPaperRunApprovalRecord(
        approval_id=approval_id,
        created_at="2026-07-27T09:50:00",
        plan_id=plan_id,
        schedule_key=(
            f"{SCHEDULED_AT}|AAPL,MSFT,NVDA"
        ),
        scheduled_at=SCHEDULED_AT,
        approval_status=approval_status,
        approval_status_label=approval_status,
        approval_decision=(
            "APPROVE"
            if approval_status == "APPROVED"
            else "REJECT"
        ),
        approval_actor="James Park",
        approval_note="실행 계획을 직접 확인했습니다.",
        approval_text="APPROVE PAPER RUN",
        reviewed_at="2026-07-27T09:50:00",
        approval_expires_at=expires_at,
        source_summary_id="summary-ready-001",
        source_session_status="READY",
        source_session_action="CONTINUE",
        normalized_symbols=(
            "AAPL",
            "MSFT",
            "NVDA",
        ),
        symbol_count=3,
        plan_checks_passed=True,
        timing_checks_passed=True,
        session_checks_passed=True,
        approval_text_checks_passed=True,
        duplicate_checks_passed=True,
        all_checks_passed=True,
        paper_run_authorized=(
            approval_status == "APPROVED"
        ),
        paper_execution_prepared=(
            approval_status == "APPROVED"
        ),
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reasons=(
            "테스트용 V11.0 승인입니다.",
        ),
        warnings=(
            "실거래는 허용되지 않습니다.",
        ),
    )


def safe_paper_executor(
    plan: PaperTradingSchedulePlan,
) -> dict:
    """
    실제 주문 없이 테스트 결과만 돌려주는 Paper Executor입니다.
    """

    return {
        "version": "TEST-PAPER-EXECUTOR",
        "plan_id": plan.plan_id,
        "status": "COMPLETED",
        "symbol_count": len(
            plan.normalized_symbols
        ),
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
        "automatic_execution_authorized": False,
    }


def unsafe_executor(
    plan: PaperTradingSchedulePlan,
) -> dict:
    return {
        "plan_id": plan.plan_id,
        "status": "UNSAFE",
        "execution_blocked": False,
        "broker_api_called": True,
        "broker_order_created": True,
        "live_order_created": False,
        "live_execution_authorized": False,
        "automatic_execution_authorized": False,
    }


def failing_executor(
    _plan: PaperTradingSchedulePlan,
) -> dict:
    raise RuntimeError(
        "테스트용 Paper Executor 오류"
    )


def run_launcher(
    *,
    plan=None,
    approval=None,
    actor: str = "James Park",
    note: str = "승인된 Paper Run을 직접 실행합니다.",
    launch_text: str = LAUNCH_TEXT,
    launched_at: str = LAUNCHED_AT,
    executor=safe_paper_executor,
    state=None,
    policy=None,
):
    with patch.object(
        launcher_module,
        "print_approved_paper_run_launcher",
    ):
        return run_approved_paper_run_launcher(
            schedule_plan=(
                plan
                if plan is not None
                else create_valid_plan()
            ),
            approval_record=(
                approval
                if approval is not None
                else create_approved_record()
            ),
            launch_actor=actor,
            launch_note=note,
            launch_text=launch_text,
            launched_at=launched_at,
            paper_run_executor=executor,
            launcher_state=(
                state
                if state is not None
                else empty_launcher_state()
            ),
            launcher_policy=policy,
        )


def validate_policy() -> None:
    policy = ApprovedPaperRunLauncherPolicy()
    valid, errors = validate_launcher_policy(policy)

    assert valid is True
    assert errors == []

    try:
        policy.paper_only = False
        raise AssertionError(
            "Launcher Policy가 변경 가능 상태입니다."
        )
    except FrozenInstanceError:
        pass

    invalid_policy = replace(
        policy,
        live_execution_disabled=False,
    )
    invalid_valid, invalid_errors = (
        validate_launcher_policy(
            invalid_policy
        )
    )
    assert invalid_valid is False
    assert invalid_errors


def validate_completed_result():
    result = run_launcher()

    assert result.version == "V11.1"
    assert result.launch_status == "COMPLETED"
    assert result.executor_called is True
    assert result.executor_checks_passed is True
    assert result.paper_run_completed is True
    assert result.record_added is True
    assert result.launch_record is not None
    assert result.launcher_state.record_count == 1
    assert result.launcher_state.completed_count == 1
    assert result.all_checks_passed is True
    assert (
        result.executor_result["plan_id"]
        == "plan-v11-1-test-001"
    )

    return result


def validate_wrong_text_is_blocked() -> None:
    result = run_launcher(
        launch_text="RUN",
    )

    assert result.launch_status == "BLOCKED"
    assert result.input_checks_passed is False
    assert result.executor_called is False
    assert result.paper_run_completed is False


def validate_expired_approval_is_blocked() -> None:
    approval = create_approved_record(
        expires_at="2026-07-27T09:54:00",
    )
    result = run_launcher(
        approval=approval,
    )

    assert result.launch_status == "BLOCKED"
    assert result.timing_checks_passed is False
    assert result.executor_called is False


def validate_late_launch_is_blocked() -> None:
    approval = create_approved_record(
        expires_at="2026-07-27T10:20:00",
    )
    result = run_launcher(
        approval=approval,
        launched_at="2026-07-27T10:06:00",
    )

    assert result.launch_status == "BLOCKED"
    assert result.timing_checks_passed is False
    assert result.executor_called is False


def validate_rejected_approval_is_blocked() -> None:
    approval = create_approved_record(
        approval_status="REJECTED",
    )
    result = run_launcher(
        approval=approval,
    )

    assert result.launch_status == "BLOCKED"
    assert result.approval_checks_passed is False
    assert result.executor_called is False


def validate_plan_mismatch_is_blocked() -> None:
    plan = create_valid_plan(
        plan_id="different-plan-id"
    )
    result = run_launcher(plan=plan)

    assert result.launch_status == "BLOCKED"
    assert result.plan_checks_passed is False
    assert result.executor_called is False


def validate_duplicate_is_blocked(
    completed_result,
) -> None:
    result = run_launcher(
        state=completed_result.launcher_state,
    )

    assert result.launch_status == "BLOCKED"
    assert result.duplicate_detected is True
    assert result.duplicate_checks_passed is False
    assert result.executor_called is False
    assert result.record_added is False
    assert result.launcher_state.record_count == 1


def validate_unsafe_executor_fails() -> None:
    result = run_launcher(
        executor=unsafe_executor,
    )

    assert result.launch_status == "FAILED"
    assert result.executor_called is True
    assert result.executor_checks_passed is False
    assert result.paper_run_completed is False
    assert result.broker_api_called is False
    assert result.live_execution_authorized is False


def validate_executor_exception_fails() -> None:
    result = run_launcher(
        executor=failing_executor,
    )

    assert result.launch_status == "FAILED"
    assert result.executor_called is True
    assert result.executor_checks_passed is False
    assert result.paper_run_completed is False
    assert any(
        "Paper Executor 실행 실패"
        in warning
        for warning in result.warnings
    )


def validate_missing_executor_fails() -> None:
    result = run_launcher(executor=None)

    assert result.launch_status == "FAILED"
    assert result.executor_called is False
    assert result.paper_run_completed is False


def validate_trim_and_round_trip() -> None:
    policy = replace(
        ApprovedPaperRunLauncherPolicy(),
        maximum_launch_record_count=2,
    )

    first = run_launcher(
        plan=create_valid_plan(
            plan_id="plan-trim-001"
        ),
        approval=create_approved_record(
            approval_id="approval-trim-001",
            plan_id="plan-trim-001",
        ),
        policy=policy,
    )
    second = run_launcher(
        plan=create_valid_plan(
            plan_id="plan-trim-002"
        ),
        approval=create_approved_record(
            approval_id="approval-trim-002",
            plan_id="plan-trim-002",
        ),
        state=first.launcher_state,
        policy=policy,
    )
    third = run_launcher(
        plan=create_valid_plan(
            plan_id="plan-trim-003"
        ),
        approval=create_approved_record(
            approval_id="approval-trim-003",
            plan_id="plan-trim-003",
        ),
        state=second.launcher_state,
        policy=policy,
    )

    assert third.state_trimmed is True
    assert third.trimmed_record_count == 1
    assert third.launcher_state.record_count == 2
    assert [
        record.approval_id
        for record in third.launcher_state.records
    ] == [
        "approval-trim-002",
        "approval-trim-003",
    ]

    restored = launcher_state_from_dict(
        third.launcher_state.to_dict()
    )
    valid, errors = validate_launcher_state(restored)
    assert valid is True
    assert errors == []
    assert (
        restored.launcher_state_id
        == third.launcher_state.launcher_state_id
    )
    assert (
        restored.records
        == third.launcher_state.records
    )


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch.object(
            launcher_module,
            "APPROVED_PAPER_RUN_LAUNCHER_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_approved_paper_run_launcher(
                    result
                )
            )
            loaded = (
                load_latest_approved_paper_run_launcher()
            )

        assert report_path.exists()
        assert latest_path.exists()
        assert loaded["version"] == "V11.1"
        assert (
            loaded["launch_status"]
            == "COMPLETED"
        )
        assert (
            loaded["launcher_state"]["record_count"]
            == 1
        )

        with report_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        assert (
            payload["launch_record"]["approval_id"]
            == "approval-v11-1-test-001"
        )


def validate_output_safety(results: list) -> None:
    for result in results:
        assert result.execution_blocked is True
        assert result.broker_api_called is False
        assert result.broker_order_created is False
        assert result.live_order_created is False
        assert (
            result.live_execution_authorized
            is False
        )
        assert (
            result.automatic_execution_authorized
            is False
        )


def main() -> None:
    print_header()

    validate_policy()
    completed_result = (
        validate_completed_result()
    )
    validate_wrong_text_is_blocked()
    validate_expired_approval_is_blocked()
    validate_late_launch_is_blocked()
    validate_rejected_approval_is_blocked()
    validate_plan_mismatch_is_blocked()
    validate_duplicate_is_blocked(
        completed_result
    )
    validate_unsafe_executor_fails()
    validate_executor_exception_fails()
    validate_missing_executor_fails()
    validate_trim_and_round_trip()
    validate_save_and_load(
        completed_result
    )

    safety_results = [
        completed_result,
        run_launcher(
            launch_text="WRONG",
        ),
        run_launcher(
            executor=unsafe_executor,
        ),
        run_launcher(
            executor=failing_executor,
        ),
    ]
    validate_output_safety(safety_results)

    checks = {
        "Version is V11.1": (
            completed_result.version == "V11.1"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Valid approved run completed": True,
        "Safe paper executor was called": True,
        "Wrong launch text was blocked": True,
        "Expired approval was blocked": True,
        "Late launch was blocked": True,
        "Rejected approval was blocked": True,
        "Plan mismatch was blocked": True,
        "Duplicate approval launch was blocked": True,
        "Unsafe executor result failed": True,
        "Executor exception was contained": True,
        "Missing executor failed safely": True,
        "Oldest launch records were trimmed": True,
        "Launcher state round-trip passed": True,
        "Result save and load passed": True,
        "Automatic execution remains disabled": (
            completed_result
            .automatic_execution_authorized
            is False
        ),
        "Execution remains blocked": (
            completed_result.execution_blocked
            is True
        ),
        "Broker API was not called": (
            completed_result.broker_api_called
            is False
        ),
        "Broker order was not created": (
            completed_result.broker_order_created
            is False
        ),
        "Live order was not created": (
            completed_result.live_order_created
            is False
        ),
        "Live execution not authorized": (
            completed_result
            .live_execution_authorized
            is False
        ),
    }
    checks["All checks passed"] = all(
        checks.values()
    )

    print()
    print("V11.1 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)
    for name, value in checks.items():
        print_check(name, value)

    if not checks["All checks passed"]:
        raise RuntimeError(
            "V11.1 Validation Check가 실패했습니다."
        )

    print("=" * LINE_LENGTH)
    print()
    print(
        "V11.1 approved paper run launcher "
        "test completed successfully."
    )
    print(
        "승인 검증, 수동 실행, 만료 및 중복 차단이 "
        "정상적으로 검증되었습니다."
    )
    print(
        "위험한 Executor 결과와 실행 예외가 안전하게 차단되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
