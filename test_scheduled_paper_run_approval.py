import json
import importlib.util
import sys
import tempfile
import types
from dataclasses import dataclass
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from unittest.mock import patch

# 이 다운로드 묶음에는 V10.7보다 오래된 전체 의존 파일이
# 포함되지 않을 수 있습니다. V11.0이 직접 사용하지 않는
# Ledger 의존성만 테스트 전용 스텁으로 격리합니다.
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

import backtest.scheduled_paper_run_approval as approval_module
from backtest.paper_trading_schedule_planner import (
    PaperTradingSchedulePlan,
)
from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryResult,
)
from backtest.scheduled_paper_run_approval import (
    ScheduledPaperRunApprovalPolicy,
    approval_state_from_dict,
    empty_approval_state,
    load_latest_scheduled_paper_run_approval,
    normalize_decision,
    parse_datetime,
    run_scheduled_paper_run_approval,
    save_scheduled_paper_run_approval,
    validate_approval_policy,
    validate_approval_state,
)


LINE_LENGTH = 140
SCHEDULED_AT = "2026-07-27T10:00:00"
REVIEWED_AT = "2026-07-27T09:50:00"
APPROVAL_TEXT = "APPROVE PAPER RUN"


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V11.0 "
        "SCHEDULED PAPER RUN APPROVAL TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<84}: {value}")


def create_empty_dataclass_instance(dataclass_type):
    """
    이전 버전의 큰 Result 객체를 테스트용으로 안전하게 만듭니다.

    V11.0에서 실제로 사용하는 필드만 아래에서 채웁니다.
    """

    instance = object.__new__(dataclass_type)

    for item in fields(dataclass_type):
        setattr(instance, item.name, None)

    return instance


def create_ready_session(
    *,
    summary_id: str = "summary-ready-001",
    session_status: str = "READY",
    session_action: str = "CONTINUE",
    all_checks_passed: bool = True,
    unsafe: bool = False,
) -> PaperTradingSessionSummaryResult:
    result = create_empty_dataclass_instance(
        PaperTradingSessionSummaryResult
    )

    result.version = "V10.8"
    result.created_at = "2026-07-27T08:00:00"
    result.session_summary_id = summary_id
    result.source_ledger_id = "ledger-test-001"
    result.session_status = session_status
    result.session_status_label = session_status
    result.session_action = session_action
    result.session_action_label = session_action
    result.all_checks_passed = all_checks_passed
    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    return result


def create_valid_plan(
    *,
    plan_id: str = "plan-v11-test-001",
    scheduled_at: str = SCHEDULED_AT,
) -> PaperTradingSchedulePlan:
    return PaperTradingSchedulePlan(
        plan_id=plan_id,
        created_at="2026-07-27T08:30:00",
        schedule_key=f"{scheduled_at}|AAPL,MSFT,NVDA",
        scheduled_at=scheduled_at,
        scheduled_date=scheduled_at[:10],
        scheduled_time=scheduled_at[11:19],
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
            "테스트용 V10.9 Plan입니다.",
        ),
        warnings=(
            "자동 실행은 허용되지 않습니다.",
        ),
    )


def run_approval(
    *,
    plan=None,
    session=None,
    decision: str = "APPROVE",
    actor: str = "James Park",
    note: str = "Paper Run 내용을 직접 검토했습니다.",
    approval_text: str = APPROVAL_TEXT,
    reviewed_at: str = REVIEWED_AT,
    state=None,
    policy=None,
):
    """
    각 검사에서 같은 기본 입력을 반복하지 않기 위한 도우미입니다.
    """

    with patch.object(
        approval_module,
        "print_scheduled_paper_run_approval",
    ):
        return run_scheduled_paper_run_approval(
            schedule_plan=(
                plan
                if plan is not None
                else create_valid_plan()
            ),
            current_session_summary=(
                session
                if session is not None
                else create_ready_session()
            ),
            approval_decision=decision,
            approval_actor=actor,
            approval_note=note,
            approval_text=approval_text,
            reviewed_at=reviewed_at,
            approval_state=(
                state
                if state is not None
                else empty_approval_state()
            ),
            approval_policy=policy,
        )


def validate_policy_and_helpers() -> None:
    policy = ScheduledPaperRunApprovalPolicy()
    valid, errors = validate_approval_policy(policy)

    assert valid is True
    assert errors == []
    assert normalize_decision(" approve ") == "APPROVE"
    assert normalize_decision("reject") == "REJECT"
    assert parse_datetime(
        REVIEWED_AT,
        "Reviewed At",
    ).isoformat() == REVIEWED_AT

    try:
        normalize_decision("AUTO")
        raise AssertionError(
            "잘못된 Decision이 허용되었습니다."
        )
    except ValueError:
        pass

    try:
        policy.paper_only = False
        raise AssertionError(
            "Policy가 변경 가능 상태입니다."
        )
    except FrozenInstanceError:
        pass

    invalid_policy = replace(
        policy,
        automatic_approval_disabled=False,
    )
    invalid_valid, invalid_errors = (
        validate_approval_policy(
            invalid_policy
        )
    )
    assert invalid_valid is False
    assert invalid_errors


def validate_approved_result():
    result = run_approval()

    assert result.version == "V11.0"
    assert result.approval_status == "APPROVED"
    assert result.approval_record_added is True
    assert result.duplicate_detected is False
    assert result.current_record_count == 1
    assert result.all_checks_passed is True
    assert result.paper_run_authorized is True
    assert result.paper_execution_prepared is True
    assert result.approval_record is not None
    assert (
        result.approval_record.approval_actor
        == "James Park"
    )
    assert (
        result.approval_record.approval_expires_at
        == "2026-07-27T10:05:00"
    )

    return result


def validate_rejected_result() -> None:
    result = run_approval(
        decision="REJECT",
        approval_text="",
        note="오늘 Paper Run을 실행하지 않습니다.",
    )

    assert result.approval_status == "REJECTED"
    assert result.approval_record_added is True
    assert result.current_record_count == 1
    assert result.paper_run_authorized is False
    assert result.paper_execution_prepared is False
    assert result.all_checks_passed is True


def validate_wrong_text_is_blocked() -> None:
    result = run_approval(
        approval_text="APPROVE",
    )

    assert result.approval_status == "BLOCKED"
    assert result.approval_record_added is True
    assert result.approval_text_checks_passed is False
    assert result.paper_run_authorized is False
    assert result.paper_execution_prepared is False


def validate_timing_blocks() -> None:
    too_early = run_approval(
        reviewed_at="2026-07-27T09:00:00",
    )
    too_late = run_approval(
        reviewed_at="2026-07-27T09:40:00",
    )
    grace_expired = run_approval(
        reviewed_at="2026-07-27T10:06:00",
    )

    assert too_early.approval_status == "BLOCKED"
    assert too_early.timing_checks_passed is False

    # 20분 전 승인은 15분 유효기간 때문에 실행 전에 만료됩니다.
    assert too_late.approval_status == "BLOCKED"
    assert too_late.timing_checks_passed is False

    assert grace_expired.approval_status == "BLOCKED"
    assert grace_expired.timing_checks_passed is False


def validate_unsafe_sources_are_blocked() -> None:
    unsafe_session = create_ready_session(
        unsafe=True,
    )
    unsafe_result = run_approval(
        session=unsafe_session,
    )

    invalid_plan = replace(
        create_valid_plan(
            plan_id="plan-invalid-001"
        ),
        broker_api_called=True,
    )
    invalid_plan_result = run_approval(
        plan=invalid_plan,
    )

    assert unsafe_result.approval_status == "BLOCKED"
    assert unsafe_result.session_checks_passed is False
    assert invalid_plan_result.approval_status == "BLOCKED"
    assert invalid_plan_result.plan_checks_passed is False


def validate_duplicate_is_blocked(approved_result) -> None:
    duplicate = run_approval(
        state=approved_result.approval_state,
    )

    assert duplicate.approval_status == "BLOCKED"
    assert duplicate.duplicate_detected is True
    assert duplicate.duplicate_checks_passed is False
    assert duplicate.approval_record_added is False
    assert duplicate.previous_record_count == 1
    assert duplicate.current_record_count == 1
    assert duplicate.paper_run_authorized is False


def validate_warning_policy() -> None:
    warning_session = create_ready_session(
        summary_id="summary-warning-001",
        session_status="WARNING",
        session_action="REVIEW",
    )

    default_result = run_approval(
        plan=create_valid_plan(
            plan_id="plan-warning-default"
        ),
        session=warning_session,
    )
    allowed_policy = replace(
        ScheduledPaperRunApprovalPolicy(),
        require_ready_session=False,
        allow_warning_session=True,
    )
    allowed_result = run_approval(
        plan=create_valid_plan(
            plan_id="plan-warning-allowed"
        ),
        session=warning_session,
        policy=allowed_policy,
    )

    assert default_result.approval_status == "BLOCKED"
    assert allowed_result.approval_status == "APPROVED"
    assert allowed_result.session_checks_passed is True


def validate_trim_and_state_round_trip() -> None:
    policy = replace(
        ScheduledPaperRunApprovalPolicy(),
        maximum_record_count=2,
    )

    first = run_approval(
        plan=create_valid_plan(
            plan_id="plan-trim-001"
        ),
        policy=policy,
    )
    second = run_approval(
        plan=create_valid_plan(
            plan_id="plan-trim-002"
        ),
        state=first.approval_state,
        policy=policy,
    )
    third = run_approval(
        plan=create_valid_plan(
            plan_id="plan-trim-003"
        ),
        state=second.approval_state,
        policy=policy,
    )

    assert third.state_trimmed is True
    assert third.trimmed_record_count == 1
    assert third.current_record_count == 2
    assert [
        record.plan_id
        for record in third.approval_state.records
    ] == [
        "plan-trim-002",
        "plan-trim-003",
    ]

    restored = approval_state_from_dict(
        third.approval_state.to_dict()
    )
    state_valid, state_errors = (
        validate_approval_state(restored)
    )
    assert state_valid is True
    assert state_errors == []
    assert (
        restored.approval_state_id
        == third.approval_state.approval_state_id
    )
    assert restored.records == third.approval_state.records
    assert (
        restored.record_count
        == third.approval_state.record_count
    )


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch.object(
            approval_module,
            "SCHEDULED_PAPER_RUN_APPROVAL_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_scheduled_paper_run_approval(
                    result
                )
            )
            loaded = (
                load_latest_scheduled_paper_run_approval()
            )

        assert report_path.exists()
        assert latest_path.exists()
        assert loaded["version"] == "V11.0"
        assert (
            loaded["approval_status"]
            == "APPROVED"
        )
        assert (
            loaded["approval_state"]["record_count"]
            == 1
        )

        with report_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        assert (
            payload["approval_record"]["plan_id"]
            == "plan-v11-test-001"
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
        assert (
            result.automatic_execution_authorized
            is False
        )


def main() -> None:
    print_header()

    validate_policy_and_helpers()
    approved_result = validate_approved_result()
    validate_rejected_result()
    validate_wrong_text_is_blocked()
    validate_timing_blocks()
    validate_unsafe_sources_are_blocked()
    validate_duplicate_is_blocked(
        approved_result
    )
    validate_warning_policy()
    validate_trim_and_state_round_trip()
    validate_save_and_load(
        approved_result
    )

    safety_results = [
        approved_result,
        run_approval(
            decision="REJECT",
            approval_text="",
        ),
        run_approval(
            approval_text="WRONG TEXT",
        ),
        run_approval(
            reviewed_at=(
                "2026-07-27T10:06:00"
            ),
        ),
    ]
    validate_execution_safety(
        safety_results
    )

    checks = {
        "Version is V11.0": (
            approved_result.version == "V11.0"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Valid manual approval passed": True,
        "Approval expiration calculated": True,
        "Manual rejection was retained": True,
        "Wrong approval text was blocked": True,
        "Too-early approval was blocked": True,
        "Expired approval window was blocked": True,
        "Unsafe session was blocked": True,
        "Unsafe plan was blocked": True,
        "Duplicate plan approval was blocked": True,
        "Allowed WARNING session passed": True,
        "Oldest approval records were trimmed": True,
        "Approval state round-trip passed": True,
        "Result save and load passed": True,
        "Paper execution was only prepared": (
            approved_result.paper_execution_prepared
            is True
        ),
        "Automatic execution remains disabled": (
            approved_result
            .automatic_execution_authorized
            is False
        ),
        "Execution remains blocked": (
            approved_result.execution_blocked
            is True
        ),
        "Broker API was not called": (
            approved_result.broker_api_called
            is False
        ),
        "Broker order was not created": (
            approved_result.broker_order_created
            is False
        ),
        "Live order was not created": (
            approved_result.live_order_created
            is False
        ),
        "Live execution not authorized": (
            approved_result
            .live_execution_authorized
            is False
        ),
    }
    checks["All checks passed"] = all(
        checks.values()
    )

    print()
    print("V11.0 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)

    for name, value in checks.items():
        print_check(name, value)

    if not checks["All checks passed"]:
        raise RuntimeError(
            "V11.0 Validation Check가 실패했습니다."
        )

    print("=" * LINE_LENGTH)
    print()
    print(
        "V11.0 scheduled paper run approval "
        "test completed successfully."
    )
    print(
        "수동 승인, 거부, 시간 제한, 중복 방지 및 "
        "기록 저장이 정상적으로 검증되었습니다."
    )
    print(
        "Paper 실행은 준비 상태일 뿐 자동 실행되지 않았습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
