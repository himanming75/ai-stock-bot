import json
import tempfile
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import patch

import backtest.paper_trading_schedule_planner as planner_module
from backtest.paper_trading_schedule_planner import (
    VALID_PLAN_ACTIONS,
    VALID_PLAN_STATUSES,
    PaperTradingSchedulePlannerPolicy,
    empty_schedule_state,
    load_latest_paper_trading_schedule_planner,
    normalize_symbols,
    parse_clock_time,
    parse_scheduled_at,
    run_paper_trading_schedule_planner,
    save_paper_trading_schedule_planner,
    schedule_state_from_dict,
    validate_schedule_planner_policy,
    validate_schedule_state,
)
from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryResult,
)


LINE_LENGTH = 140
SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
]
VALID_MONDAY = "2026-07-27T10:00:00"
VALID_TUESDAY = "2026-07-28T10:00:00"
VALID_WEDNESDAY = "2026-07-29T10:00:00"
WEEKEND_SATURDAY = "2026-08-01T10:00:00"
EARLY_MONDAY = "2026-07-27T09:00:00"


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.9 "
        "PAPER TRADING SCHEDULE PLANNER TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<84}: {value}")


def create_empty_dataclass_instance(
    dataclass_type,
):
    instance = object.__new__(dataclass_type)

    for item in fields(dataclass_type):
        setattr(instance, item.name, None)

    return instance


def create_fake_session_summary(
    *,
    summary_id: str = "summary-ready-001",
    session_status: str = "READY",
    session_action: str = "CONTINUE",
    all_checks_passed: bool = True,
    unsafe: bool = False,
) -> PaperTradingSessionSummaryResult:
    """
    실제 Ledger 분석 없이 V10.8 Summary 결과를 만듭니다.
    """

    result = create_empty_dataclass_instance(
        PaperTradingSessionSummaryResult
    )

    result.version = "V10.8"
    result.created_at = "2026-07-27T08:00:00"
    result.session_summary_id = summary_id
    result.source_ledger_id = "ledger-test-001"

    result.session_status = session_status
    result.session_status_label = (
        session_status
    )
    result.session_action = session_action
    result.session_action_label = (
        session_action
    )

    result.first_run_at = (
        "2026-07-20T10:00:00"
    )
    result.latest_run_at = (
        "2026-07-26T10:00:00"
    )

    result.total_run_count = 10
    result.daily_run_count = 7
    result.batch_run_count = 3
    result.completed_run_count = 10
    result.partial_run_count = 0
    result.blocked_run_count = 0
    result.failed_run_count = 0
    result.completed_run_rate_percent = 100.0
    result.partial_run_rate_percent = 0.0
    result.blocked_run_rate_percent = 0.0
    result.failed_run_rate_percent = 0.0

    result.requested_symbol_count = 16
    result.completed_symbol_count = 16
    result.blocked_symbol_count = 0
    result.failed_symbol_count = 0
    result.skipped_symbol_count = 0
    result.completed_symbol_rate_percent = 100.0

    result.consecutive_failed_run_count = 0
    result.consecutive_blocked_run_count = 0
    result.cumulative_equity_change = 500.0
    result.profitable_run_count = 8
    result.losing_run_count = 2
    result.unchanged_run_count = 0

    result.triggered_rule_count = (
        1 if session_status == "WARNING" else 0
    )
    result.review_rule_count = (
        1 if session_status == "WARNING" else 0
    )
    result.pause_rule_count = (
        1 if session_action == "PAUSE" else 0
    )
    result.block_rule_count = (
        1 if session_action == "BLOCK" else 0
    )

    result.minimum_history_met = True
    result.source_checks_passed = True
    result.policy_checks_passed = True
    result.rule_checks_passed = True
    result.all_checks_passed = (
        all_checks_passed
    )

    result.paper_trading_continue_allowed = (
        session_action == "CONTINUE"
    )
    result.manual_review_required = (
        session_action == "REVIEW"
    )
    result.paper_trading_paused = (
        session_action == "PAUSE"
    )
    result.paper_trading_blocked = (
        session_action == "BLOCK"
    )

    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    result.rule_results = {}
    result.reasons = [
        "테스트 V10.8 Session Summary입니다."
    ]
    result.warnings = [
        "실제 주문을 생성하지 않습니다."
    ]
    result.next_actions = [
        "Schedule Plan을 확인합니다."
    ]
    result.report_path = None
    result.latest_path = None

    return result


def validate_policy() -> (
    PaperTradingSchedulePlannerPolicy
):
    policy = (
        PaperTradingSchedulePlannerPolicy()
    )

    valid, errors = (
        validate_schedule_planner_policy(
            policy
        )
    )

    if not valid or errors:
        raise RuntimeError(
            f"기본 V10.9 Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "timezone_name",
        "earliest_run_time",
        "latest_run_time",
        "allowed_weekdays",
        "minimum_symbol_count",
        "maximum_symbol_count",
        "reject_duplicate_symbols",
        "require_ready_session",
        "allow_warning_session",
        "reject_duplicate_schedule",
        "maximum_plan_count",
        "trim_oldest_plans",
        "require_manual_launch",
        "automatic_execution_disabled",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "V10.9 Policy Dictionary 구조가 다릅니다."
        )

    immutable = False

    try:
        policy.maximum_plan_count = 1
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "V10.9 Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingSchedulePlannerPolicy(
            earliest_run_time="16:00",
            latest_run_time="10:00",
        ),
        PaperTradingSchedulePlannerPolicy(
            allowed_weekdays=(0, 7),
        ),
        PaperTradingSchedulePlannerPolicy(
            minimum_symbol_count=0,
        ),
        PaperTradingSchedulePlannerPolicy(
            minimum_symbol_count=10,
            maximum_symbol_count=5,
        ),
        PaperTradingSchedulePlannerPolicy(
            reject_duplicate_schedule=False,
        ),
        PaperTradingSchedulePlannerPolicy(
            maximum_plan_count=0,
        ),
        PaperTradingSchedulePlannerPolicy(
            require_manual_launch=False,
        ),
        PaperTradingSchedulePlannerPolicy(
            automatic_execution_disabled=False,
        ),
        PaperTradingSchedulePlannerPolicy(
            paper_only=False,
        ),
        PaperTradingSchedulePlannerPolicy(
            live_execution_disabled=False,
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_schedule_planner_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_helpers() -> None:
    if (
        parse_clock_time("09:35")
        .strftime("%H:%M")
        != "09:35"
    ):
        raise RuntimeError(
            "Clock Time Parsing이 실패했습니다."
        )

    parsed = parse_scheduled_at(
        VALID_MONDAY
    )

    if parsed.weekday() != 0:
        raise RuntimeError(
            "2026-07-27이 Monday로 계산되지 않았습니다."
        )

    (
        requested,
        normalized,
        duplicates,
    ) = normalize_symbols(
        [
            " aapl ",
            "msft",
            "AAPL",
            "nvda",
        ]
    )

    if requested != (
        "AAPL",
        "MSFT",
        "AAPL",
        "NVDA",
    ):
        raise RuntimeError(
            "Requested Symbol 정규화가 실패했습니다."
        )

    if normalized != tuple(SYMBOLS):
        raise RuntimeError(
            "Unique Symbol 정규화가 실패했습니다."
        )

    if duplicates != ("AAPL",):
        raise RuntimeError(
            "Duplicate Symbol 계산이 실패했습니다."
        )

    state = empty_schedule_state()
    valid, errors = validate_schedule_state(
        state
    )

    if not valid or errors:
        raise RuntimeError(
            f"빈 Schedule State가 유효하지 않습니다: {errors}"
        )


def assert_execution_safety(result) -> None:
    if not result.manual_launch_required:
        raise RuntimeError(
            "Manual Launch Required가 False입니다."
        )

    if result.automatic_execution_authorized:
        raise RuntimeError(
            "Automatic Execution이 허용되었습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "Execution이 차단되지 않았습니다."
        )

    unsafe_values = {
        "broker_api_called": result.broker_api_called,
        "broker_order_created": (
            result.broker_order_created
        ),
        "live_order_created": (
            result.live_order_created
        ),
        "live_execution_authorized": (
            result.live_execution_authorized
        ),
    }

    if any(unsafe_values.values()):
        raise RuntimeError(
            f"실거래 안전 검사가 실패했습니다: {unsafe_values}"
        )


def validate_planned_result(
    policy: PaperTradingSchedulePlannerPolicy,
):
    result = run_paper_trading_schedule_planner(
        scheduled_at=VALID_MONDAY,
        symbols=[
            " aapl ",
            "msft",
            "nvda",
        ],
        session_summary=(
            create_fake_session_summary()
        ),
        schedule_state=(
            empty_schedule_state()
        ),
        planner_policy=policy,
    )

    if result.version != "V10.9":
        raise RuntimeError(
            "Planner 버전이 V10.9가 아닙니다."
        )

    if result.planner_status != "PLANNED":
        raise RuntimeError(
            "정상 계획이 PLANNED가 아닙니다."
        )

    if not result.plan_added:
        raise RuntimeError(
            "정상 Plan이 State에 추가되지 않았습니다."
        )

    if result.current_plan_count != 1:
        raise RuntimeError(
            "Plan Count가 1이 아닙니다."
        )

    if result.schedule_plan is None:
        raise RuntimeError(
            "Schedule Plan이 생성되지 않았습니다."
        )

    plan = result.schedule_plan

    if plan.plan_action != "QUEUE":
        raise RuntimeError(
            "정상 Plan Action이 QUEUE가 아닙니다."
        )

    if plan.weekday_label != "Monday":
        raise RuntimeError(
            "Weekday Label이 Monday가 아닙니다."
        )

    if (
        plan.normalized_symbols
        != tuple(SYMBOLS)
    ):
        raise RuntimeError(
            "Plan Symbol 목록이 다릅니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "PLANNED 결과의 All Checks가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_duplicate_result(
    previous_result,
    policy: PaperTradingSchedulePlannerPolicy,
):
    result = run_paper_trading_schedule_planner(
        scheduled_at=VALID_MONDAY,
        symbols=SYMBOLS,
        session_summary=(
            create_fake_session_summary()
        ),
        schedule_state=(
            previous_result.schedule_state
        ),
        planner_policy=policy,
    )

    if result.planner_status != "BLOCKED":
        raise RuntimeError(
            "Duplicate Schedule이 BLOCKED가 아닙니다."
        )

    if not result.duplicate_detected:
        raise RuntimeError(
            "Duplicate Schedule이 감지되지 않았습니다."
        )

    if result.plan_added:
        raise RuntimeError(
            "Duplicate Plan이 State에 추가되었습니다."
        )

    if (
        result.current_plan_count
        != previous_result.current_plan_count
    ):
        raise RuntimeError(
            "Duplicate 처리 후 Plan Count가 변경되었습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "안전한 Duplicate 차단 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_warning_review() -> object:
    policy = PaperTradingSchedulePlannerPolicy(
        allow_warning_session=True,
    )

    result = run_paper_trading_schedule_planner(
        scheduled_at=VALID_TUESDAY,
        symbols=SYMBOLS,
        session_summary=(
            create_fake_session_summary(
                summary_id=(
                    "summary-warning-001"
                ),
                session_status="WARNING",
                session_action="REVIEW",
            )
        ),
        schedule_state=(
            empty_schedule_state()
        ),
        planner_policy=policy,
    )

    if (
        result.planner_status
        != "REVIEW_REQUIRED"
    ):
        raise RuntimeError(
            "허용된 WARNING이 REVIEW_REQUIRED가 아닙니다."
        )

    if result.schedule_plan is None:
        raise RuntimeError(
            "WARNING Review Plan이 생성되지 않았습니다."
        )

    if (
        result.schedule_plan.plan_action
        != "REVIEW"
    ):
        raise RuntimeError(
            "WARNING Plan Action이 REVIEW가 아닙니다."
        )

    if not result.plan_added:
        raise RuntimeError(
            "WARNING Review Plan이 State에 추가되지 않았습니다."
        )

    assert_execution_safety(result)

    return result


def validate_blocked_condition(
    *,
    scheduled_at: str,
    session_summary,
    policy: PaperTradingSchedulePlannerPolicy,
    label: str,
):
    result = run_paper_trading_schedule_planner(
        scheduled_at=scheduled_at,
        symbols=SYMBOLS,
        session_summary=session_summary,
        schedule_state=(
            empty_schedule_state()
        ),
        planner_policy=policy,
    )

    if result.planner_status != "BLOCKED":
        raise RuntimeError(
            f"{label} 조건이 BLOCKED가 아닙니다."
        )

    if result.plan_added:
        raise RuntimeError(
            f"{label} 조건에서 Plan이 추가되었습니다."
        )

    if result.schedule_plan is not None:
        raise RuntimeError(
            f"{label} 조건에서 Schedule Plan이 생성되었습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            f"{label} 안전 차단 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_failed_input(
    policy: PaperTradingSchedulePlannerPolicy,
):
    result = run_paper_trading_schedule_planner(
        scheduled_at="not-a-date",
        symbols=[],
        session_summary=(
            create_fake_session_summary()
        ),
        schedule_state=(
            empty_schedule_state()
        ),
        planner_policy=policy,
    )

    if result.planner_status != "FAILED":
        raise RuntimeError(
            "Invalid Input이 FAILED가 아닙니다."
        )

    if result.input_checks_passed:
        raise RuntimeError(
            "Invalid Input Checks가 True입니다."
        )

    if result.plan_added:
        raise RuntimeError(
            "Invalid Input에서 Plan이 추가되었습니다."
        )

    assert_execution_safety(result)

    return result


def validate_trim_policy() -> None:
    policy = PaperTradingSchedulePlannerPolicy(
        maximum_plan_count=2,
        trim_oldest_plans=True,
    )
    summary = create_fake_session_summary()
    state = empty_schedule_state()

    first = run_paper_trading_schedule_planner(
        scheduled_at=VALID_MONDAY,
        symbols=SYMBOLS,
        session_summary=summary,
        schedule_state=state,
        planner_policy=policy,
    )
    second = run_paper_trading_schedule_planner(
        scheduled_at=VALID_TUESDAY,
        symbols=SYMBOLS,
        session_summary=summary,
        schedule_state=first.schedule_state,
        planner_policy=policy,
    )
    third = run_paper_trading_schedule_planner(
        scheduled_at=VALID_WEDNESDAY,
        symbols=SYMBOLS,
        session_summary=summary,
        schedule_state=second.schedule_state,
        planner_policy=policy,
    )

    if not third.state_trimmed:
        raise RuntimeError(
            "Maximum Plan Count 초과 시 Trim되지 않았습니다."
        )

    if third.trimmed_plan_count != 1:
        raise RuntimeError(
            "Trimmed Plan Count가 다릅니다."
        )

    if third.current_plan_count != 2:
        raise RuntimeError(
            "Trim 후 Plan Count가 2가 아닙니다."
        )

    remaining_dates = [
        plan.scheduled_date
        for plan in third.schedule_state.plans
    ]

    if remaining_dates != [
        "2026-07-28",
        "2026-07-29",
    ]:
        raise RuntimeError(
            "가장 오래된 Plan이 제거되지 않았습니다."
        )


def validate_state_round_trip(result) -> None:
    payload = result.schedule_state.to_dict()
    restored = schedule_state_from_dict(
        payload
    )

    valid, errors = validate_schedule_state(
        restored
    )

    if not valid or errors:
        raise RuntimeError(
            f"복원된 Schedule State가 유효하지 않습니다: {errors}"
        )

    if (
        restored.plan_count
        != result.schedule_state.plan_count
    ):
        raise RuntimeError(
            "Schedule State 복원 후 Plan Count가 다릅니다."
        )


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output_directory = (
            Path(temporary)
            / "schedule_planner"
        )

        with patch.object(
            planner_module,
            (
                "PAPER_TRADING_SCHEDULE_PLANNER_"
                "OUTPUT_DIRECTORY"
            ),
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_schedule_planner(
                    result
                )
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V10.9 Report가 저장되지 않았습니다."
                )

            if not latest_path.exists():
                raise RuntimeError(
                    "V10.9 Latest가 저장되지 않았습니다."
                )

            loaded = (
                load_latest_paper_trading_schedule_planner()
            )

            if loaded.get("version") != "V10.9":
                raise RuntimeError(
                    "저장된 버전이 V10.9가 아닙니다."
                )

            if (
                loaded.get("planner_result_id")
                != result.planner_result_id
            ):
                raise RuntimeError(
                    "저장된 Planner Result ID가 다릅니다."
                )

            with latest_path.open(
                mode="r",
                encoding="utf-8",
            ) as file:
                raw_payload = json.load(file)

            state_payload = raw_payload.get(
                "schedule_state"
            )

            if not isinstance(
                state_payload,
                dict,
            ):
                raise RuntimeError(
                    "저장된 Schedule State 형식이 다릅니다."
                )

            restored = schedule_state_from_dict(
                state_payload
            )
            valid, errors = (
                validate_schedule_state(
                    restored
                )
            )

            if not valid or errors:
                raise RuntimeError(
                    f"저장된 State 복원이 실패했습니다: {errors}"
                )


def validate_result_contract(results: list) -> None:
    for result in results:
        if (
            result.planner_status
            not in VALID_PLAN_STATUSES
        ):
            raise RuntimeError(
                "허용되지 않은 Planner Status입니다."
            )

        if not result.planner_result_id:
            raise RuntimeError(
                "Planner Result ID가 비어 있습니다."
            )

        if not result.schedule_state_id:
            raise RuntimeError(
                "Schedule State ID가 비어 있습니다."
            )

        if result.schedule_plan is not None:
            if (
                result.schedule_plan.plan_action
                not in VALID_PLAN_ACTIONS
            ):
                raise RuntimeError(
                    "허용되지 않은 Plan Action입니다."
                )

        if not result.reasons:
            raise RuntimeError(
                "Reasons가 비어 있습니다."
            )

        if not result.warnings:
            raise RuntimeError(
                "Warnings가 비어 있습니다."
            )

        if not result.next_actions:
            raise RuntimeError(
                "Next Actions가 비어 있습니다."
            )

        assert_execution_safety(result)


def main() -> None:
    print_header()

    policy = validate_policy()
    validate_helpers()

    planned_result = (
        validate_planned_result(
            policy
        )
    )
    duplicate_result = (
        validate_duplicate_result(
            planned_result,
            policy,
        )
    )
    review_result = (
        validate_warning_review()
    )

    weekend_result = (
        validate_blocked_condition(
            scheduled_at=(
                WEEKEND_SATURDAY
            ),
            session_summary=(
                create_fake_session_summary()
            ),
            policy=policy,
            label="Weekend",
        )
    )
    early_result = (
        validate_blocked_condition(
            scheduled_at=EARLY_MONDAY,
            session_summary=(
                create_fake_session_summary()
            ),
            policy=policy,
            label="Outside Time",
        )
    )
    not_ready_result = (
        validate_blocked_condition(
            scheduled_at=VALID_TUESDAY,
            session_summary=(
                create_fake_session_summary(
                    summary_id=(
                        "summary-not-ready"
                    ),
                    session_status=(
                        "NOT_READY"
                    ),
                    session_action="BLOCK",
                )
            ),
            policy=policy,
            label="Not Ready Session",
        )
    )
    invalid_result = validate_failed_input(
        policy
    )

    validate_trim_policy()
    validate_state_round_trip(
        planned_result
    )
    validate_save_and_load(
        planned_result
    )

    results = [
        planned_result,
        duplicate_result,
        review_result,
        weekend_result,
        early_result,
        not_ready_result,
        invalid_result,
    ]

    validate_result_contract(results)

    checks = {
        "Version is V10.9": (
            planned_result.version == "V10.9"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Weekday plan was created": (
            planned_result.planner_status
            == "PLANNED"
        ),
        "Manual launch is required": (
            planned_result
            .manual_launch_required
        ),
        "Duplicate schedule was blocked": (
            duplicate_result
            .duplicate_detected
        ),
        "Warning session requires review": (
            review_result.planner_status
            == "REVIEW_REQUIRED"
        ),
        "Weekend was blocked": (
            weekend_result.planner_status
            == "BLOCKED"
        ),
        "Outside time was blocked": (
            early_result.planner_status
            == "BLOCKED"
        ),
        "Not-ready session was blocked": (
            not_ready_result
            .planner_status
            == "BLOCKED"
        ),
        "Invalid input was failed": (
            invalid_result.planner_status
            == "FAILED"
        ),
        "Oldest plans were trimmed": True,
        "State round-trip passed": True,
        "Result save and load passed": True,
        "Automatic execution disabled": all(
            not result
            .automatic_execution_authorized
            for result in results
        ),
        "Execution remains blocked": all(
            result.execution_blocked
            for result in results
        ),
        "Broker API was not called": all(
            not result.broker_api_called
            for result in results
        ),
        "Broker order was not created": all(
            not result.broker_order_created
            for result in results
        ),
        "Live order was not created": all(
            not result.live_order_created
            for result in results
        ),
        "Live execution not authorized": all(
            not result.live_execution_authorized
            for result in results
        ),
    }

    print()
    print("=" * LINE_LENGTH)
    print("V10.9 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)

    for name, value in checks.items():
        print_check(name, value)

    all_checks_passed = all(checks.values())

    print_check(
        "All checks passed",
        all_checks_passed,
    )
    print("=" * LINE_LENGTH)

    if not all_checks_passed:
        raise RuntimeError(
            "V10.9 Schedule Planner Test가 실패했습니다."
        )

    print()
    print(
        "V10.9 paper trading schedule planner test "
        "completed successfully."
    )
    print(
        "평일 계획, WARNING 검토, 주말, 시간 외, "
        "NOT_READY 및 중복 차단이 정상적으로 검증되었습니다."
    )
    print(
        "Plan 보관 한도, State 저장 및 복원이 "
        "정상적으로 검증되었습니다."
    )
    print(
        "자동 실행, 실제 Broker API, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
