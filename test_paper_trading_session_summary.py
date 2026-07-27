import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import backtest.paper_trading_session_summary as summary_module
from backtest.paper_trading_run_ledger import (
    PaperTradingRunLedgerEntry,
    build_ledger_state,
)
from backtest.paper_trading_session_summary import (
    VALID_SESSION_ACTIONS,
    VALID_SESSION_STATUSES,
    PaperTradingSessionSummaryPolicy,
    calculate_consecutive_status_count,
    load_latest_paper_trading_session_summary,
    run_paper_trading_session_summary,
    safe_rate,
    save_paper_trading_session_summary,
    validate_session_summary_policy,
)


LINE_LENGTH = 140


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.8 "
        "PAPER TRADING SESSION SUMMARY TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<82}: {value}")


def create_ledger_entry(
    *,
    run_id: str,
    sequence: int,
    run_type: str = "DAILY_GATED",
    run_status: str = "COMPLETED",
    requested_symbol_count: int = 1,
    completed_symbol_count: int = 1,
    blocked_symbol_count: int = 0,
    failed_symbol_count: int = 0,
    skipped_symbol_count: int = 0,
    equity_change: float = 100.0,
) -> PaperTradingRunLedgerEntry:
    """
    실제 Pipeline을 실행하지 않고 V10.7 Ledger Entry를 만듭니다.
    """

    initial_equity = 10_000.0
    final_equity = (
        initial_equity + equity_change
    )

    if run_status == "COMPLETED":
        risk_status = "SAFE"
        risk_action = "ALLOW"
        gate_status = "PASSED"
        gate_passed = True
    elif run_status == "PARTIAL":
        risk_status = "WARNING"
        risk_action = "WARNING"
        gate_status = "WARNING"
        gate_passed = True
    elif run_status == "BLOCKED":
        risk_status = "BLOCKED"
        risk_action = "BLOCK"
        gate_status = "BLOCKED"
        gate_passed = False
    else:
        risk_status = "FAILED"
        risk_action = "BLOCK"
        gate_status = "FAILED"
        gate_passed = False

    return PaperTradingRunLedgerEntry(
        ledger_entry_id=(
            f"entry-{run_id}"
        ),
        recorded_at=(
            f"2026-07-{sequence:02d}T12:00:00"
        ),
        run_type=run_type,
        run_id=run_id,
        source_version=(
            "V10.5"
            if run_type == "DAILY_GATED"
            else "V10.6"
        ),
        source_created_at=(
            f"2026-07-{sequence:02d}T11:59:00"
        ),
        run_status=run_status,
        run_status_label=run_status,
        risk_monitor_id=f"risk-{run_id}",
        risk_status=risk_status,
        risk_action=risk_action,
        gate_status=gate_status,
        gate_passed=gate_passed,
        requested_symbols=[
            f"TEST{sequence}"
            for _ in range(
                requested_symbol_count
            )
        ],
        requested_symbol_count=(
            requested_symbol_count
        ),
        completed_symbol_count=(
            completed_symbol_count
        ),
        blocked_symbol_count=(
            blocked_symbol_count
        ),
        failed_symbol_count=(
            failed_symbol_count
        ),
        skipped_symbol_count=(
            skipped_symbol_count
        ),
        initial_equity=initial_equity,
        final_equity=final_equity,
        equity_change=equity_change,
        equity_change_percent=round(
            equity_change
            / initial_equity
            * 100.0,
            4,
        ),
        source_checks_passed=(
            run_status != "FAILED"
        ),
        source_execution_blocked=True,
        source_broker_api_called=False,
        source_broker_order_created=False,
        source_live_order_created=False,
        source_live_execution_authorized=False,
        entry_checks_passed=True,
        reasons=(
            f"테스트 {run_status} Entry입니다.",
        ),
        warnings=(
            "실제 주문을 생성하지 않습니다.",
        ),
    )


def create_ready_state():
    """
    5회 모두 성공한 정상 Ledger State를 만듭니다.
    """

    entries = tuple(
        create_ledger_entry(
            run_id=f"ready-run-{index}",
            sequence=index,
            run_type=(
                "DAILY_GATED"
                if index <= 3
                else "BATCH_GATED"
            ),
            requested_symbol_count=(
                1 if index <= 3 else 3
            ),
            completed_symbol_count=(
                1 if index <= 3 else 3
            ),
            equity_change=100.0,
        )
        for index in range(1, 6)
    )

    return build_ledger_state(
        entries=entries,
        ledger_id="ledger-ready",
        created_at="2026-07-01T00:00:00",
    )


def create_warning_state():
    """
    성공했지만 최소 5회 이력이 부족한 State를 만듭니다.
    """

    entries = tuple(
        create_ledger_entry(
            run_id=f"warning-run-{index}",
            sequence=index,
            equity_change=50.0,
        )
        for index in range(1, 3)
    )

    return build_ledger_state(
        entries=entries,
        ledger_id="ledger-warning",
        created_at="2026-07-01T00:00:00",
    )


def create_pause_state():
    """
    최근 2회 연속 실패한 State를 만듭니다.
    """

    entries = []

    for index in range(1, 4):
        entries.append(
            create_ledger_entry(
                run_id=f"pause-good-{index}",
                sequence=index,
                equity_change=50.0,
            )
        )

    for index in range(4, 6):
        entries.append(
            create_ledger_entry(
                run_id=f"pause-failed-{index}",
                sequence=index,
                run_status="FAILED",
                completed_symbol_count=0,
                failed_symbol_count=1,
                equity_change=-50.0,
            )
        )

    return build_ledger_state(
        entries=tuple(entries),
        ledger_id="ledger-pause",
        created_at="2026-07-01T00:00:00",
    )


def create_block_state():
    """
    최근 3회 연속 실패한 State를 만듭니다.
    """

    entries = []

    for index in range(1, 3):
        entries.append(
            create_ledger_entry(
                run_id=f"block-good-{index}",
                sequence=index,
                equity_change=50.0,
            )
        )

    for index in range(3, 6):
        entries.append(
            create_ledger_entry(
                run_id=f"block-failed-{index}",
                sequence=index,
                run_status="FAILED",
                completed_symbol_count=0,
                failed_symbol_count=1,
                equity_change=-100.0,
            )
        )

    return build_ledger_state(
        entries=tuple(entries),
        ledger_id="ledger-block",
        created_at="2026-07-01T00:00:00",
    )


def create_equity_loss_state():
    """
    실행은 완료됐지만 누적 Equity 손실이 큰 State를 만듭니다.
    """

    entries = tuple(
        create_ledger_entry(
            run_id=f"loss-run-{index}",
            sequence=index,
            equity_change=-250.0,
        )
        for index in range(1, 6)
    )

    return build_ledger_state(
        entries=entries,
        ledger_id="ledger-equity-loss",
        created_at="2026-07-01T00:00:00",
    )


def validate_policy() -> (
    PaperTradingSessionSummaryPolicy
):
    policy = (
        PaperTradingSessionSummaryPolicy()
    )

    valid, errors = (
        validate_session_summary_policy(
            policy
        )
    )

    if not valid or errors:
        raise RuntimeError(
            f"기본 V10.8 Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "minimum_run_count",
        "minimum_completed_run_rate_percent",
        "minimum_completed_symbol_rate_percent",
        "warning_failed_run_rate_percent",
        "pause_failed_run_rate_percent",
        "block_failed_run_rate_percent",
        "warning_blocked_run_rate_percent",
        "pause_blocked_run_rate_percent",
        "block_blocked_run_rate_percent",
        "warning_consecutive_failed_runs",
        "pause_consecutive_failed_runs",
        "block_consecutive_failed_runs",
        "warning_cumulative_equity_loss",
        "pause_cumulative_equity_loss",
        "block_cumulative_equity_loss",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "V10.8 Policy Dictionary 구조가 다릅니다."
        )

    immutable = False

    try:
        policy.minimum_run_count = 1
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "V10.8 Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingSessionSummaryPolicy(
            minimum_run_count=0,
        ),
        PaperTradingSessionSummaryPolicy(
            minimum_completed_run_rate_percent=101.0,
        ),
        PaperTradingSessionSummaryPolicy(
            warning_failed_run_rate_percent=30.0,
            pause_failed_run_rate_percent=20.0,
        ),
        PaperTradingSessionSummaryPolicy(
            warning_consecutive_failed_runs=2,
            pause_consecutive_failed_runs=1,
        ),
        PaperTradingSessionSummaryPolicy(
            warning_cumulative_equity_loss=-1.0,
        ),
        PaperTradingSessionSummaryPolicy(
            paper_only=False,
        ),
        PaperTradingSessionSummaryPolicy(
            live_execution_disabled=False,
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_session_summary_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_helpers() -> None:
    if safe_rate(3, 4) != 75.0:
        raise RuntimeError(
            "Safe Rate 계산이 실패했습니다."
        )

    if safe_rate(1, 0) != 0.0:
        raise RuntimeError(
            "0 Denominator 처리가 실패했습니다."
        )

    state = create_block_state()

    failed_streak = (
        calculate_consecutive_status_count(
            state.entries,
            "FAILED",
        )
    )

    if failed_streak != 3:
        raise RuntimeError(
            "연속 실패 Run 계산이 실패했습니다."
        )

    blocked_streak = (
        calculate_consecutive_status_count(
            state.entries,
            "BLOCKED",
        )
    )

    if blocked_streak != 0:
        raise RuntimeError(
            "연속 Blocked Run 계산이 다릅니다."
        )


def assert_execution_safety(result) -> None:
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


def validate_ready_result(
    policy: PaperTradingSessionSummaryPolicy,
):
    result = run_paper_trading_session_summary(
        ledger_state=create_ready_state(),
        summary_policy=policy,
    )

    if result.version != "V10.8":
        raise RuntimeError(
            "Summary 버전이 V10.8이 아닙니다."
        )

    if result.session_status != "READY":
        raise RuntimeError(
            f"정상 State가 READY가 아닙니다: {result.session_status}"
        )

    if result.session_action != "CONTINUE":
        raise RuntimeError(
            "정상 State의 Action이 CONTINUE가 아닙니다."
        )

    if not result.minimum_history_met:
        raise RuntimeError(
            "최소 실행 이력이 충족되지 않았습니다."
        )

    if result.total_run_count != 5:
        raise RuntimeError(
            "전체 Run Count가 다릅니다."
        )

    if result.daily_run_count != 3:
        raise RuntimeError(
            "Daily Run Count가 다릅니다."
        )

    if result.batch_run_count != 2:
        raise RuntimeError(
            "Batch Run Count가 다릅니다."
        )

    if (
        result.completed_run_rate_percent
        != 100.0
    ):
        raise RuntimeError(
            "Completed Run Rate가 다릅니다."
        )

    if (
        result.completed_symbol_rate_percent
        != 100.0
    ):
        raise RuntimeError(
            "Completed Symbol Rate가 다릅니다."
        )

    if result.cumulative_equity_change != 500.0:
        raise RuntimeError(
            "누적 Equity Change가 다릅니다."
        )

    if not result.paper_trading_continue_allowed:
        raise RuntimeError(
            "READY 상태에서 Paper Trading이 허용되지 않았습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "READY 결과의 All Checks가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_warning_result(
    policy: PaperTradingSessionSummaryPolicy,
):
    result = run_paper_trading_session_summary(
        ledger_state=create_warning_state(),
        summary_policy=policy,
    )

    if result.session_status != "WARNING":
        raise RuntimeError(
            "이력 부족 State가 WARNING이 아닙니다."
        )

    if result.session_action != "REVIEW":
        raise RuntimeError(
            "이력 부족 State의 Action이 REVIEW가 아닙니다."
        )

    if result.minimum_history_met:
        raise RuntimeError(
            "이력 부족인데 Minimum History가 True입니다."
        )

    if not result.manual_review_required:
        raise RuntimeError(
            "WARNING 상태에서 Manual Review가 False입니다."
        )

    if (
        result.rule_results[
            "MINIMUM_HISTORY"
        ].session_action
        != "REVIEW"
    ):
        raise RuntimeError(
            "Minimum History Rule이 REVIEW가 아닙니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "WARNING 결과의 구조 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_pause_result(
    policy: PaperTradingSessionSummaryPolicy,
):
    result = run_paper_trading_session_summary(
        ledger_state=create_pause_state(),
        summary_policy=policy,
    )

    if result.session_status != "NOT_READY":
        raise RuntimeError(
            "Pause State가 NOT_READY가 아닙니다."
        )

    if result.session_action != "PAUSE":
        raise RuntimeError(
            f"Pause State Action이 PAUSE가 아닙니다: {result.session_action}"
        )

    if not result.paper_trading_paused:
        raise RuntimeError(
            "Paper Trading Paused가 False입니다."
        )

    if result.consecutive_failed_run_count != 2:
        raise RuntimeError(
            "연속 실패 횟수가 2가 아닙니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "PAUSE 결과의 구조 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_block_result(
    policy: PaperTradingSessionSummaryPolicy,
):
    result = run_paper_trading_session_summary(
        ledger_state=create_block_state(),
        summary_policy=policy,
    )

    if result.session_status != "NOT_READY":
        raise RuntimeError(
            "Block State가 NOT_READY가 아닙니다."
        )

    if result.session_action != "BLOCK":
        raise RuntimeError(
            "Block State Action이 BLOCK이 아닙니다."
        )

    if not result.paper_trading_blocked:
        raise RuntimeError(
            "Paper Trading Blocked가 False입니다."
        )

    if result.consecutive_failed_run_count != 3:
        raise RuntimeError(
            "연속 실패 횟수가 3이 아닙니다."
        )

    if result.block_rule_count < 1:
        raise RuntimeError(
            "Block Rule Count가 기록되지 않았습니다."
        )

    assert_execution_safety(result)

    return result


def validate_equity_loss_block(
    policy: PaperTradingSessionSummaryPolicy,
):
    result = run_paper_trading_session_summary(
        ledger_state=create_equity_loss_state(),
        summary_policy=policy,
    )

    if result.session_action != "BLOCK":
        raise RuntimeError(
            "누적 Equity 손실이 BLOCK을 생성하지 않았습니다."
        )

    equity_rule = result.rule_results[
        "CUMULATIVE_EQUITY_LOSS"
    ]

    if equity_rule.session_action != "BLOCK":
        raise RuntimeError(
            "Cumulative Equity Loss Rule이 BLOCK이 아닙니다."
        )

    if result.cumulative_equity_change != -1250.0:
        raise RuntimeError(
            "누적 Equity 손실 계산이 다릅니다."
        )

    assert_execution_safety(result)

    return result


def validate_invalid_state(
    policy: PaperTradingSessionSummaryPolicy,
):
    entry = create_ledger_entry(
        run_id="duplicate-run",
        sequence=1,
    )

    invalid_state = build_ledger_state(
        entries=(
            entry,
            entry,
        ),
        ledger_id="ledger-invalid",
        created_at="2026-07-01T00:00:00",
    )

    result = run_paper_trading_session_summary(
        ledger_state=invalid_state,
        summary_policy=policy,
    )

    if result.session_status != "FAILED":
        raise RuntimeError(
            "Invalid Ledger가 FAILED가 아닙니다."
        )

    if result.session_action != "BLOCK":
        raise RuntimeError(
            "Invalid Ledger Action이 BLOCK이 아닙니다."
        )

    if result.source_checks_passed:
        raise RuntimeError(
            "Invalid Ledger Source Checks가 True입니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "Invalid Ledger의 All Checks가 True입니다."
        )

    assert_execution_safety(result)

    return result


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output_directory = (
            Path(temporary)
            / "session_summary"
        )

        with patch.object(
            summary_module,
            (
                "PAPER_TRADING_SESSION_SUMMARY_"
                "OUTPUT_DIRECTORY"
            ),
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_session_summary(
                    result
                )
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V10.8 Report가 저장되지 않았습니다."
                )

            if not latest_path.exists():
                raise RuntimeError(
                    "V10.8 Latest가 저장되지 않았습니다."
                )

            loaded = (
                load_latest_paper_trading_session_summary()
            )

            if loaded.get("version") != "V10.8":
                raise RuntimeError(
                    "저장된 버전이 V10.8이 아닙니다."
                )

            if (
                loaded.get("session_summary_id")
                != result.session_summary_id
            ):
                raise RuntimeError(
                    "저장된 Session Summary ID가 다릅니다."
                )

            if loaded.get("session_status") != "READY":
                raise RuntimeError(
                    "저장된 Session Status가 다릅니다."
                )

            with latest_path.open(
                mode="r",
                encoding="utf-8",
            ) as file:
                raw_payload = json.load(file)

            if not isinstance(
                raw_payload.get("rule_results"),
                dict,
            ):
                raise RuntimeError(
                    "저장된 Rule Results 형식이 다릅니다."
                )


def validate_result_contract(results: list) -> None:
    for result in results:
        if (
            result.session_status
            not in VALID_SESSION_STATUSES
        ):
            raise RuntimeError(
                "허용되지 않은 Session Status입니다."
            )

        if (
            result.session_action
            not in VALID_SESSION_ACTIONS
        ):
            raise RuntimeError(
                "허용되지 않은 Session Action입니다."
            )

        if not result.session_summary_id:
            raise RuntimeError(
                "Session Summary ID가 비어 있습니다."
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

    ready_result = validate_ready_result(
        policy
    )
    warning_result = validate_warning_result(
        policy
    )
    pause_result = validate_pause_result(
        policy
    )
    block_result = validate_block_result(
        policy
    )
    equity_block_result = (
        validate_equity_loss_block(
            policy
        )
    )
    invalid_result = validate_invalid_state(
        policy
    )

    results = [
        ready_result,
        warning_result,
        pause_result,
        block_result,
        equity_block_result,
        invalid_result,
    ]

    validate_result_contract(results)
    validate_save_and_load(ready_result)

    checks = {
        "Version is V10.8": (
            ready_result.version == "V10.8"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Ready history status is READY": (
            ready_result.session_status
            == "READY"
        ),
        "Ready action is CONTINUE": (
            ready_result.session_action
            == "CONTINUE"
        ),
        "Insufficient history is WARNING": (
            warning_result.session_status
            == "WARNING"
        ),
        "Two consecutive failures pause": (
            pause_result.session_action
            == "PAUSE"
        ),
        "Three consecutive failures block": (
            block_result.session_action
            == "BLOCK"
        ),
        "Large cumulative loss blocks": (
            equity_block_result
            .session_action
            == "BLOCK"
        ),
        "Invalid ledger is FAILED": (
            invalid_result.session_status
            == "FAILED"
        ),
        "Run and symbol rates calculated": (
            ready_result
            .completed_run_rate_percent
            == 100.0
            and ready_result
            .completed_symbol_rate_percent
            == 100.0
        ),
        "Result save and load passed": True,
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
    print("V10.8 VALIDATION CHECKS")
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
            "V10.8 Session Summary Test가 실패했습니다."
        )

    print()
    print(
        "V10.8 paper trading session summary test "
        "completed successfully."
    )
    print(
        "READY, WARNING, PAUSE, BLOCK 및 FAILED "
        "Session 판정이 정상적으로 검증되었습니다."
    )
    print(
        "Run 비율, 종목 처리율, 연속 실패 및 누적 Equity "
        "손실 계산이 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
