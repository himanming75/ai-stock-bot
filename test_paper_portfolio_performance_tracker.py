import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any
from unittest.mock import patch

from backtest.paper_portfolio_performance_tracker import (
    VALID_PERFORMANCE_STATUSES,
    PaperPerformanceSnapshot,
    PaperPortfolioPerformancePolicy,
    PaperPortfolioPerformanceResult,
    calculate_performance_metrics,
    create_performance_snapshot,
    load_latest_performance_result,
    load_performance_history,
    prepare_performance_history,
    recalculate_snapshot_metrics,
    round_money,
    round_percent,
    round_ratio,
    run_paper_portfolio_performance_tracker,
    save_paper_portfolio_performance,
    snapshot_from_dict,
    validate_performance_policy,
    validate_performance_snapshot,
    validate_valuation_payload,
)


LINE_LENGTH = 140
PORTFOLIO_ID = "test-paper-portfolio"
INITIAL_EQUITY = 10_000.0


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.1 "
        "PORTFOLIO PERFORMANCE TRACKER TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<70}: {value}")


def assert_close(
    actual: float,
    expected: float,
    tolerance: float = 0.01,
    message: str = "숫자 값이 일치하지 않습니다.",
) -> None:
    difference = abs(float(actual) - float(expected))

    if difference > tolerance:
        raise RuntimeError(
            f"{message} "
            f"Actual={actual}, "
            f"Expected={expected}, "
            f"Difference={difference}"
        )


def create_valuation_payload(
    valuation_id: str,
    created_at: str,
    total_equity: float,
    portfolio_id: str = PORTFOLIO_ID,
    initial_cash: float = INITIAL_EQUITY,
    valuation_status: str = "VALUED",
    all_checks_passed: bool = True,
) -> dict[str, Any]:
    """
    외부 Market Data 없이 테스트할 V10.0 Valuation Payload입니다.
    """

    cash_balance = 4_000.0
    total_market_value = round_money(
        total_equity - cash_balance
    )
    total_profit_loss = round_money(
        total_equity - initial_cash
    )

    if initial_cash > 0:
        total_return_percent = round_percent(
            total_profit_loss / initial_cash * 100.0
        )
    else:
        total_return_percent = 0.0

    if total_equity > 0:
        cash_weight_percent = round_percent(
            cash_balance / total_equity * 100.0
        )
        invested_weight_percent = round_percent(
            total_market_value / total_equity * 100.0
        )
    else:
        cash_weight_percent = 0.0
        invested_weight_percent = 0.0

    return {
        "version": "V10.0",
        "created_at": created_at,
        "valuation_id": valuation_id,
        "portfolio_id": portfolio_id,
        "valuation_status": valuation_status,
        "initial_cash": initial_cash,
        "cash_balance": cash_balance,
        "updated_total_market_value": total_market_value,
        "updated_total_equity": total_equity,
        "updated_total_unrealized_pnl": total_profit_loss,
        "total_realized_pnl": 0.0,
        "total_commission": 0.0,
        "total_profit_loss": total_profit_loss,
        "total_return_percent": total_return_percent,
        "cash_weight_percent": cash_weight_percent,
        "invested_weight_percent": invested_weight_percent,
        "position_count": 1,
        "long_position_count": 1,
        "all_checks_passed": all_checks_passed,
    }


def validate_policy() -> (
    PaperPortfolioPerformancePolicy
):
    policy = PaperPortfolioPerformancePolicy()

    valid, errors = validate_performance_policy(policy)

    if not valid:
        raise RuntimeError(
            f"기본 Policy가 유효하지 않습니다: {errors}"
        )

    if errors:
        raise RuntimeError(
            "정상 Policy에서 오류가 생성되었습니다."
        )

    expected_keys = {
        "annual_trading_periods",
        "risk_free_rate_percent",
        "minimum_valid_equity",
        "maximum_valid_equity",
        "drawdown_warning_percent",
        "maximum_history_records",
        "reject_duplicate_valuation_ids",
        "require_same_portfolio_id",
        "require_successful_valuation",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "Policy Dictionary 구조가 일치하지 않습니다."
        )

    immutable = False

    try:
        policy.annual_trading_periods = 365
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperPortfolioPerformancePolicy(
            annual_trading_periods=0
        ),
        PaperPortfolioPerformancePolicy(
            minimum_valid_equity=0.0
        ),
        PaperPortfolioPerformancePolicy(
            minimum_valid_equity=100.0,
            maximum_valid_equity=50.0,
        ),
        PaperPortfolioPerformancePolicy(
            drawdown_warning_percent=-1.0
        ),
        PaperPortfolioPerformancePolicy(
            drawdown_warning_percent=101.0
        ),
        PaperPortfolioPerformancePolicy(
            maximum_history_records=0
        ),
        PaperPortfolioPerformancePolicy(
            paper_only=False
        ),
        PaperPortfolioPerformancePolicy(
            live_execution_disabled=False
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_performance_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_helpers(
    policy: PaperPortfolioPerformancePolicy,
) -> None:
    assert_close(
        round_money(10.126),
        10.13,
        tolerance=0.000001,
    )
    assert_close(
        round_percent(12.345678),
        12.3457,
        tolerance=0.000001,
    )
    assert_close(
        round_ratio(1.23456789),
        1.234568,
        tolerance=0.000001,
    )

    payload = create_valuation_payload(
        valuation_id="helper-valuation",
        created_at="2026-07-27T09:30:00",
        total_equity=10_500.0,
    )

    valid, errors = validate_valuation_payload(
        payload,
        policy,
    )

    if not valid or errors:
        raise RuntimeError(
            f"정상 Valuation Payload가 거부되었습니다: {errors}"
        )

    snapshot = create_performance_snapshot(payload)

    if not isinstance(
        snapshot,
        PaperPerformanceSnapshot,
    ):
        raise RuntimeError(
            "Snapshot 형식이 올바르지 않습니다."
        )

    snapshot_valid, snapshot_errors = (
        validate_performance_snapshot(
            snapshot,
            policy,
        )
    )

    if not snapshot_valid or snapshot_errors:
        raise RuntimeError(
            f"정상 Snapshot이 거부되었습니다: {snapshot_errors}"
        )

    restored = snapshot_from_dict(
        snapshot.to_dict()
    )

    if restored.to_dict() != snapshot.to_dict():
        raise RuntimeError(
            "Snapshot Dictionary 복원이 실패했습니다."
        )


def validate_invalid_valuation_payloads(
    policy: PaperPortfolioPerformancePolicy,
) -> None:
    invalid_version = create_valuation_payload(
        valuation_id="invalid-version",
        created_at="2026-07-27T09:30:00",
        total_equity=10_000.0,
    )
    invalid_version["version"] = "V9.9"

    failed_valuation = create_valuation_payload(
        valuation_id="failed-valuation",
        created_at="2026-07-27T09:31:00",
        total_equity=10_000.0,
        valuation_status="BLOCKED",
        all_checks_passed=False,
    )

    inconsistent_equity = create_valuation_payload(
        valuation_id="bad-equity",
        created_at="2026-07-27T09:32:00",
        total_equity=10_000.0,
    )
    inconsistent_equity[
        "updated_total_market_value"
    ] = 100.0

    for index, payload in enumerate(
        [
            invalid_version,
            failed_valuation,
            inconsistent_equity,
        ],
        start=1,
    ):
        valid, errors = validate_valuation_payload(
            payload,
            policy,
        )

        if valid or not errors:
            raise RuntimeError(
                f"Invalid Valuation #{index}가 거부되지 않았습니다."
            )


def validate_first_snapshot(
    policy: PaperPortfolioPerformancePolicy,
) -> PaperPortfolioPerformanceResult:
    payload = create_valuation_payload(
        valuation_id="valuation-001",
        created_at="2026-07-27T09:30:00",
        total_equity=10_000.0,
    )

    result = run_paper_portfolio_performance_tracker(
        valuation_result=payload,
        existing_history=[],
        performance_policy=policy,
    )

    if result.version != "V10.1":
        raise RuntimeError(
            "Version이 V10.1이 아닙니다."
        )

    if (
        result.performance_status
        != "FIRST_SNAPSHOT"
    ):
        raise RuntimeError(
            "첫 실행 Status가 FIRST_SNAPSHOT이 아닙니다."
        )

    if not result.snapshot_added:
        raise RuntimeError(
            "첫 Snapshot이 추가되지 않았습니다."
        )

    if result.duplicate_snapshot:
        raise RuntimeError(
            "첫 Snapshot이 중복으로 판정되었습니다."
        )

    if result.history_record_count != 1:
        raise RuntimeError(
            "첫 History Record Count가 1이 아닙니다."
        )

    if result.performance_period_count != 0:
        raise RuntimeError(
            "첫 Performance Period Count가 0이 아닙니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "첫 Snapshot All Checks가 실패했습니다."
        )

    assert_close(result.current_equity, 10_000.0)
    assert_close(result.period_profit_loss, 0.0)
    assert_close(result.period_return_percent, 0.0)
    assert_close(result.current_drawdown_percent, 0.0)

    return result


def run_next_period(
    history: list[PaperPerformanceSnapshot],
    policy: PaperPortfolioPerformancePolicy,
    valuation_id: str,
    created_at: str,
    total_equity: float,
) -> PaperPortfolioPerformanceResult:
    payload = create_valuation_payload(
        valuation_id=valuation_id,
        created_at=created_at,
        total_equity=total_equity,
    )

    result = run_paper_portfolio_performance_tracker(
        valuation_result=payload,
        existing_history=history,
        performance_policy=policy,
    )

    if result.performance_status != "TRACKED":
        raise RuntimeError(
            f"{valuation_id} Status가 TRACKED가 아닙니다."
        )

    if not result.snapshot_added:
        raise RuntimeError(
            f"{valuation_id} Snapshot이 추가되지 않았습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            f"{valuation_id} All Checks가 실패했습니다."
        )

    return result


def validate_profit_loss_drawdown_sequence(
    first_result: PaperPortfolioPerformanceResult,
    policy: PaperPortfolioPerformancePolicy,
) -> PaperPortfolioPerformanceResult:
    profit_result = run_next_period(
        history=first_result.performance_history,
        policy=policy,
        valuation_id="valuation-002",
        created_at="2026-07-28T09:30:00",
        total_equity=11_000.0,
    )

    assert_close(
        profit_result.period_profit_loss,
        1_000.0,
    )
    assert_close(
        profit_result.period_return_percent,
        10.0,
        tolerance=0.0001,
    )
    assert_close(
        profit_result.equity_high_water_mark,
        11_000.0,
    )

    loss_result = run_next_period(
        history=profit_result.performance_history,
        policy=policy,
        valuation_id="valuation-003",
        created_at="2026-07-29T09:30:00",
        total_equity=9_900.0,
    )

    assert_close(
        loss_result.period_profit_loss,
        -1_100.0,
    )
    assert_close(
        loss_result.period_return_percent,
        -10.0,
        tolerance=0.0001,
    )
    assert_close(
        loss_result.current_drawdown_amount,
        1_100.0,
    )
    assert_close(
        loss_result.current_drawdown_percent,
        10.0,
        tolerance=0.0001,
    )
    assert_close(
        loss_result.maximum_drawdown_percent,
        10.0,
        tolerance=0.0001,
    )

    recovery_result = run_next_period(
        history=loss_result.performance_history,
        policy=policy,
        valuation_id="valuation-004",
        created_at="2026-07-30T09:30:00",
        total_equity=11_880.0,
    )

    assert_close(
        recovery_result.period_profit_loss,
        1_980.0,
    )
    assert_close(
        recovery_result.period_return_percent,
        20.0,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.cumulative_profit_loss,
        1_880.0,
    )
    assert_close(
        recovery_result.cumulative_return_percent,
        18.8,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.current_drawdown_percent,
        0.0,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.maximum_drawdown_percent,
        10.0,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.average_period_return_percent,
        6.6667,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.best_period_return_percent,
        20.0,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.worst_period_return_percent,
        -10.0,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.return_volatility_percent,
        15.2753,
        tolerance=0.0002,
    )
    assert_close(
        recovery_result.win_rate_percent,
        66.6667,
        tolerance=0.0001,
    )
    assert_close(
        recovery_result.gross_profit,
        2_980.0,
    )
    assert_close(
        recovery_result.gross_loss,
        1_100.0,
    )
    assert_close(
        recovery_result.profit_factor,
        2.709091,
        tolerance=0.000001,
    )

    if recovery_result.profitable_period_count != 2:
        raise RuntimeError(
            "Profitable Period Count가 2가 아닙니다."
        )

    if recovery_result.loss_period_count != 1:
        raise RuntimeError(
            "Loss Period Count가 1이 아닙니다."
        )

    if recovery_result.performance_period_count != 3:
        raise RuntimeError(
            "Performance Period Count가 3이 아닙니다."
        )

    return recovery_result


def validate_duplicate_snapshot(
    result: PaperPortfolioPerformanceResult,
    policy: PaperPortfolioPerformancePolicy,
) -> PaperPortfolioPerformanceResult:
    duplicate_payload = create_valuation_payload(
        valuation_id="valuation-004",
        created_at="2026-07-30T09:30:00",
        total_equity=11_880.0,
    )

    duplicate_result = (
        run_paper_portfolio_performance_tracker(
            valuation_result=duplicate_payload,
            existing_history=result.performance_history,
            performance_policy=policy,
        )
    )

    if duplicate_result.performance_status != "NO_CHANGE":
        raise RuntimeError(
            "중복 Snapshot Status가 NO_CHANGE가 아닙니다."
        )

    if duplicate_result.snapshot_added:
        raise RuntimeError(
            "중복 Snapshot이 History에 추가되었습니다."
        )

    if not duplicate_result.duplicate_snapshot:
        raise RuntimeError(
            "중복 Snapshot이 Duplicate로 판정되지 않았습니다."
        )

    if (
        duplicate_result.history_record_count
        != result.history_record_count
    ):
        raise RuntimeError(
            "중복 처리 후 History Count가 변경되었습니다."
        )

    if not duplicate_result.all_checks_passed:
        raise RuntimeError(
            "중복 처리 All Checks가 실패했습니다."
        )

    return duplicate_result


def validate_out_of_order_history(
    policy: PaperPortfolioPerformancePolicy,
) -> None:
    late = create_performance_snapshot(
        create_valuation_payload(
            valuation_id="late",
            created_at="2026-08-02T09:30:00",
            total_equity=10_500.0,
        )
    )
    early = create_performance_snapshot(
        create_valuation_payload(
            valuation_id="early",
            created_at="2026-08-01T09:30:00",
            total_equity=10_000.0,
        )
    )

    history, added, duplicate, errors = (
        prepare_performance_history(
            existing_history=[late],
            new_snapshot=early,
            policy=policy,
        )
    )

    if errors:
        raise RuntimeError(
            f"Out-of-order History 검사 실패: {errors}"
        )

    if not added or duplicate:
        raise RuntimeError(
            "Out-of-order Snapshot 추가 결과가 올바르지 않습니다."
        )

    if history[0].valuation_id != "early":
        raise RuntimeError(
            "History가 created_at 순서로 정렬되지 않았습니다."
        )

    recalculate_snapshot_metrics(history)

    assert_close(
        history[1].period_return_percent,
        5.0,
        tolerance=0.0001,
    )

    metrics = calculate_performance_metrics(
        history,
        policy,
    )

    assert_close(
        float(metrics["cumulative_return_percent"]),
        5.0,
        tolerance=0.0001,
    )


def validate_blocked_source(
    policy: PaperPortfolioPerformancePolicy,
) -> PaperPortfolioPerformanceResult:
    payload = create_valuation_payload(
        valuation_id="blocked-source",
        created_at="2026-08-03T09:30:00",
        total_equity=10_000.0,
        valuation_status="BLOCKED",
        all_checks_passed=False,
    )

    result = run_paper_portfolio_performance_tracker(
        valuation_result=payload,
        existing_history=[],
        performance_policy=policy,
    )

    if result.performance_status != "BLOCKED":
        raise RuntimeError(
            "실패 Valuation이 BLOCKED 처리되지 않았습니다."
        )

    if result.source_valid:
        raise RuntimeError(
            "실패 Valuation Source Valid가 True입니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "실패 Valuation All Checks가 True입니다."
        )

    return result


def validate_save_and_load(
    result: PaperPortfolioPerformanceResult,
) -> tuple[Path, Path, Path]:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)
        latest_file = (
            output_directory
            / "paper_portfolio_performance_latest.json"
        )
        history_file = (
            output_directory
            / "paper_portfolio_performance_history.json"
        )

        with (
            patch(
                "backtest.paper_portfolio_performance_tracker."
                "PAPER_PERFORMANCE_OUTPUT_DIRECTORY",
                output_directory,
            ),
            patch(
                "backtest.paper_portfolio_performance_tracker."
                "PERFORMANCE_LATEST_FILE",
                latest_file,
            ),
            patch(
                "backtest.paper_portfolio_performance_tracker."
                "PERFORMANCE_HISTORY_FILE",
                history_file,
            ),
        ):
            (
                report_path,
                latest_path,
                history_path,
            ) = save_paper_portfolio_performance(
                result
            )

            for file_path in (
                report_path,
                latest_path,
                history_path,
            ):
                if not file_path.exists():
                    raise RuntimeError(
                        f"저장 파일이 없습니다: {file_path}"
                    )

                if file_path.stat().st_size <= 0:
                    raise RuntimeError(
                        f"저장 파일이 비어 있습니다: {file_path}"
                    )

            with report_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                report_payload = json.load(file)

            with latest_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                latest_payload = json.load(file)

            if report_payload != latest_payload:
                raise RuntimeError(
                    "Report와 Latest 내용이 다릅니다."
                )

            loaded_latest = (
                load_latest_performance_result()
            )

            if loaded_latest != latest_payload:
                raise RuntimeError(
                    "Latest Performance 재로딩이 실패했습니다."
                )

            loaded_history = load_performance_history()

            if [
                snapshot.to_dict()
                for snapshot in loaded_history
            ] != [
                snapshot.to_dict()
                for snapshot in result.performance_history
            ]:
                raise RuntimeError(
                    "Performance History 재로딩이 실패했습니다."
                )

            copied_report = (
                Path(directory)
                / report_path.name
            )
            copied_latest = (
                Path(directory)
                / latest_path.name
            )
            copied_history = (
                Path(directory)
                / history_path.name
            )

            return (
                copied_report,
                copied_latest,
                copied_history,
            )


def validate_result_safety(
    result: PaperPortfolioPerformanceResult,
) -> None:
    if not isinstance(
        result,
        PaperPortfolioPerformanceResult,
    ):
        raise RuntimeError(
            "Result 형식이 올바르지 않습니다."
        )

    if (
        result.performance_status
        not in VALID_PERFORMANCE_STATUSES
    ):
        raise RuntimeError(
            "Performance Status가 유효하지 않습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "Execution이 차단되지 않았습니다."
        )

    if result.broker_api_called:
        raise RuntimeError(
            "Broker API가 호출되었습니다."
        )

    if result.broker_order_created:
        raise RuntimeError(
            "Broker Order가 생성되었습니다."
        )

    if result.live_order_created:
        raise RuntimeError(
            "Live Order가 생성되었습니다."
        )

    if result.live_execution_authorized:
        raise RuntimeError(
            "Live Execution이 허용되었습니다."
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


def print_validation_checks(
    first_result: PaperPortfolioPerformanceResult,
    final_result: PaperPortfolioPerformanceResult,
    duplicate_result: PaperPortfolioPerformanceResult,
    blocked_result: PaperPortfolioPerformanceResult,
) -> None:
    checks = {
        "Version is V10.1": (
            final_result.version == "V10.1"
        ),
        "First status is FIRST_SNAPSHOT": (
            first_result.performance_status
            == "FIRST_SNAPSHOT"
        ),
        "Final status is TRACKED": (
            final_result.performance_status
            == "TRACKED"
        ),
        "Four history records exist": (
            final_result.history_record_count == 4
        ),
        "Three performance periods exist": (
            final_result.performance_period_count == 3
        ),
        "Cumulative return is 18.8 percent": (
            abs(
                final_result.cumulative_return_percent
                - 18.8
            )
            <= 0.0001
        ),
        "Maximum drawdown is 10 percent": (
            abs(
                final_result.maximum_drawdown_percent
                - 10.0
            )
            <= 0.0001
        ),
        "Win rate is 66.6667 percent": (
            abs(
                final_result.win_rate_percent
                - 66.6667
            )
            <= 0.0001
        ),
        "Duplicate status is NO_CHANGE": (
            duplicate_result.performance_status
            == "NO_CHANGE"
        ),
        "Duplicate snapshot was not added": (
            not duplicate_result.snapshot_added
        ),
        "Invalid source is BLOCKED": (
            blocked_result.performance_status
            == "BLOCKED"
        ),
        "Execution remains blocked": (
            final_result.execution_blocked
        ),
        "Broker API was not called": (
            not final_result.broker_api_called
        ),
        "Live order was not created": (
            not final_result.live_order_created
        ),
        "Live execution not authorized": (
            not final_result.live_execution_authorized
        ),
        "All checks passed": (
            final_result.all_checks_passed
        ),
    }

    print()
    print("=" * LINE_LENGTH)
    print("V10.1 VALIDATION CHECKS")
    print("=" * LINE_LENGTH)

    for name, value in checks.items():
        print_check(name, value)

    print("=" * LINE_LENGTH)

    failed_checks = [
        name
        for name, value in checks.items()
        if not value
    ]

    if failed_checks:
        raise RuntimeError(
            "다음 V10.1 검증 항목이 실패했습니다: "
            f"{failed_checks}"
        )


def main() -> None:
    """
    V10.1 Portfolio Performance Tracker 통합 테스트입니다.

    검증 항목:

    1. Policy 구조, 불변성 및 잘못된 정책 차단
    2. V10.0 Valuation Payload 검증
    3. 첫 Snapshot 생성
    4. 수익 기간 계산
    5. 손실 기간 및 Drawdown 계산
    6. 회복 기간 및 Maximum Drawdown 보존
    7. 누적 수익률, 변동성, 승률, Profit Factor
    8. 중복 Valuation 차단
    9. 날짜순 History 정렬
    10. 실패한 V10.0 Valuation 차단
    11. JSON 저장 및 다시 불러오기
    12. 실제 Broker 및 Live Execution 차단
    """

    print_header()

    policy = validate_policy()
    validate_helpers(policy)
    validate_invalid_valuation_payloads(policy)

    first_result = validate_first_snapshot(policy)

    final_result = (
        validate_profit_loss_drawdown_sequence(
            first_result,
            policy,
        )
    )

    duplicate_result = validate_duplicate_snapshot(
        final_result,
        policy,
    )

    validate_out_of_order_history(policy)

    blocked_result = validate_blocked_source(policy)

    validate_result_safety(first_result)
    validate_result_safety(final_result)
    validate_result_safety(duplicate_result)
    validate_result_safety(blocked_result)

    validate_save_and_load(final_result)

    print_validation_checks(
        first_result=first_result,
        final_result=final_result,
        duplicate_result=duplicate_result,
        blocked_result=blocked_result,
    )

    print()
    print(
        "V10.1 portfolio performance tracker "
        "test completed successfully."
    )
    print(
        "수익률, Drawdown, 변동성, 승률 및 "
        "중복 방지 계산이 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
