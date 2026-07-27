import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backtest.paper_trading_batch_pipeline import (
    VALID_BATCH_STATUSES,
    VALID_SYMBOL_STATUSES,
    PaperTradingBatchPipelinePolicy,
    PaperTradingBatchPipelineResult,
    PaperTradingBatchSymbolResult,
    load_latest_paper_trading_batch_pipeline,
    normalize_latest_prices,
    normalize_symbol,
    normalize_symbols,
    run_paper_trading_batch_pipeline,
    save_paper_trading_batch_pipeline,
    validate_batch_policy,
    validate_symbol_batch,
    validate_symbol_result_safety,
)


LINE_LENGTH = 140
SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
]
INITIAL_CASH = 10_000.0


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.3 "
        "MULTI-SYMBOL PAPER TRADING BATCH TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<74}: {value}")


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


def create_fake_daily_pipeline_result(
    symbol: str,
    status: str = "COMPLETED",
    final_equity: float = 10_100.0,
) -> SimpleNamespace:
    """
    실제 시장 데이터 없이 V10.2 결과를 흉내 냅니다.
    """

    normalized_symbol = normalize_symbol(symbol)
    pipeline_id = (
        f"pipeline-{normalized_symbol.lower()}"
    )

    completed = status == "COMPLETED"

    return SimpleNamespace(
        version="V10.2",
        created_at="2026-07-27T12:00:00",
        pipeline_id=pipeline_id,
        symbol=normalized_symbol,
        pipeline_status=status,
        completed_stage_count=(
            5 if completed else 2
        ),
        blocked_stage_count=(
            0 if completed else 1
        ),
        failed_stage_count=0,
        skipped_stage_count=(
            0 if completed else 2
        ),
        initial_cash=INITIAL_CASH,
        final_cash_balance=8_000.0,
        final_market_value=round(
            final_equity - 8_000.0,
            2,
        ),
        final_equity=final_equity,
        all_checks_passed=completed,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reasons=[
            (
                f"{normalized_symbol} 테스트용 "
                "V10.2 Pipeline입니다."
            )
        ],
        warnings=[
            "실제 주문을 생성하지 않습니다."
        ],
        to_dict=lambda: {
            "version": "V10.2",
            "pipeline_id": pipeline_id,
            "symbol": normalized_symbol,
            "pipeline_status": status,
            "final_equity": final_equity,
        },
    )


def validate_policy() -> (
    PaperTradingBatchPipelinePolicy
):
    policy = PaperTradingBatchPipelinePolicy()

    valid, errors = validate_batch_policy(policy)

    if not valid or errors:
        raise RuntimeError(
            f"기본 Batch Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "minimum_symbol_count",
        "maximum_symbol_count",
        "reject_duplicate_symbols",
        "continue_on_symbol_failure",
        "require_all_symbols_success",
        "save_daily_pipeline_outputs",
        "save_batch_output",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "Batch Policy Dictionary 구조가 다릅니다."
        )

    immutable = False

    try:
        policy.maximum_symbol_count = 100
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "Batch Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingBatchPipelinePolicy(
            minimum_symbol_count=0
        ),
        PaperTradingBatchPipelinePolicy(
            maximum_symbol_count=0
        ),
        PaperTradingBatchPipelinePolicy(
            minimum_symbol_count=10,
            maximum_symbol_count=5,
        ),
        PaperTradingBatchPipelinePolicy(
            continue_on_symbol_failure="yes"
        ),
        PaperTradingBatchPipelinePolicy(
            paper_only=False
        ),
        PaperTradingBatchPipelinePolicy(
            live_execution_disabled=False
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_batch_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_symbol_helpers(
    policy: PaperTradingBatchPipelinePolicy,
) -> None:
    if normalize_symbol(" aapl ") != "AAPL":
        raise RuntimeError(
            "Symbol 정규화가 실패했습니다."
        )

    normalized, duplicates = normalize_symbols(
        [
            " aapl ",
            "msft",
            "AAPL",
            "nvda",
            "MSFT",
        ]
    )

    if normalized != [
        "AAPL",
        "MSFT",
        "NVDA",
    ]:
        raise RuntimeError(
            "Symbol 목록 정규화 결과가 다릅니다."
        )

    if duplicates != [
        "AAPL",
        "MSFT",
    ]:
        raise RuntimeError(
            "중복 Symbol 목록이 다릅니다."
        )

    symbol_valid, symbol_errors = (
        validate_symbol_batch(
            requested_symbols=SYMBOLS,
            normalized_symbols=SYMBOLS,
            duplicate_symbols=[],
            policy=policy,
        )
    )

    if not symbol_valid or symbol_errors:
        raise RuntimeError(
            f"정상 Symbol Batch가 거부되었습니다: {symbol_errors}"
        )

    normalized_prices = normalize_latest_prices(
        {
            " aapl ": 100.123456,
            "msft": 200.56789,
        }
    )

    if set(normalized_prices) != {
        "AAPL",
        "MSFT",
    }:
        raise RuntimeError(
            "Latest Price Symbol 정규화가 실패했습니다."
        )

    assert_close(
        normalized_prices["AAPL"],
        100.1235,
        tolerance=0.0001,
    )
    assert_close(
        normalized_prices["MSFT"],
        200.5679,
        tolerance=0.0001,
    )

    for invalid_prices in (
        {"AAPL": 0.0},
        {"AAPL": -1.0},
        {"AAPL": "invalid"},
    ):
        try:
            normalize_latest_prices(
                invalid_prices
            )
        except (ValueError, TypeError):
            pass
        else:
            raise RuntimeError(
                "잘못된 Latest Price가 거부되지 않았습니다."
            )


def validate_all_symbols_success(
    policy: PaperTradingBatchPipelinePolicy,
) -> PaperTradingBatchPipelineResult:
    equity_map = {
        "AAPL": 10_100.0,
        "MSFT": 10_200.0,
        "NVDA": 10_300.0,
    }

    calls: list[str] = []

    def runner(
        symbol: str,
        account_cash: float,
        latest_prices: dict[str, float],
    ) -> SimpleNamespace:
        calls.append(symbol)

        if account_cash != INITIAL_CASH:
            raise RuntimeError(
                "Runner Account Cash가 다릅니다."
            )

        if set(latest_prices) != set(SYMBOLS):
            raise RuntimeError(
                "Runner Latest Prices가 다릅니다."
            )

        return create_fake_daily_pipeline_result(
            symbol=symbol,
            status="COMPLETED",
            final_equity=equity_map[symbol],
        )

    with patch(
        "backtest.paper_trading_batch_pipeline."
        "save_paper_trading_daily_pipeline",
        side_effect=lambda result: (
            Path(
                f"{result.symbol}_report.json"
            ),
            Path(
                f"{result.symbol}_latest.json"
            ),
        ),
    ) as save_mock:
        result = run_paper_trading_batch_pipeline(
            symbols=SYMBOLS,
            account_cash=INITIAL_CASH,
            latest_prices={
                "AAPL": 100.0,
                "MSFT": 200.0,
                "NVDA": 300.0,
            },
            batch_policy=policy,
            daily_pipeline_runner=runner,
        )

    if not isinstance(
        result,
        PaperTradingBatchPipelineResult,
    ):
        raise RuntimeError(
            "Batch Result 형식이 올바르지 않습니다."
        )

    if result.version != "V10.3":
        raise RuntimeError(
            "Version이 V10.3이 아닙니다."
        )

    if result.batch_status != "COMPLETED":
        raise RuntimeError(
            "정상 Batch Status가 COMPLETED가 아닙니다."
        )

    if calls != SYMBOLS:
        raise RuntimeError(
            "종목 실행 순서가 요청 순서와 다릅니다."
        )

    if result.completed_symbol_count != 3:
        raise RuntimeError(
            "Completed Symbol Count가 3이 아닙니다."
        )

    if (
        result.blocked_symbol_count != 0
        or result.failed_symbol_count != 0
        or result.skipped_symbol_count != 0
    ):
        raise RuntimeError(
            "정상 Batch에 미완료 Symbol이 있습니다."
        )

    if result.success_rate_percent != 100.0:
        raise RuntimeError(
            "정상 Batch Success Rate가 100%가 아닙니다."
        )

    if not result.all_required_symbols_passed:
        raise RuntimeError(
            "All Required Symbols가 실패했습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Batch All Checks가 실패했습니다."
        )

    if save_mock.call_count != 3:
        raise RuntimeError(
            "종목별 Pipeline 저장이 3회 실행되지 않았습니다."
        )

    for sequence, symbol in enumerate(
        SYMBOLS,
        start=1,
    ):
        symbol_result = result.symbol_results[
            symbol
        ]

        if not isinstance(
            symbol_result,
            PaperTradingBatchSymbolResult,
        ):
            raise RuntimeError(
                f"{symbol} Result 형식이 올바르지 않습니다."
            )

        if symbol_result.sequence != sequence:
            raise RuntimeError(
                f"{symbol} Sequence가 다릅니다."
            )

        if symbol_result.symbol_status != "COMPLETED":
            raise RuntimeError(
                f"{symbol} Status가 COMPLETED가 아닙니다."
            )

        if not symbol_result.output_saved:
            raise RuntimeError(
                f"{symbol} Output Saved가 False입니다."
            )

    assert_close(
        result.final_equity,
        10_300.0,
    )
    assert_close(
        result.batch_equity_change,
        300.0,
    )
    assert_close(
        result.batch_equity_change_percent,
        3.0,
        tolerance=0.0001,
    )

    return result


def validate_partial_batch(
    policy: PaperTradingBatchPipelinePolicy,
) -> PaperTradingBatchPipelineResult:
    calls: list[str] = []

    def runner(
        symbol: str,
        account_cash: float,
        latest_prices: dict[str, float],
    ) -> SimpleNamespace:
        calls.append(symbol)

        if symbol == "MSFT":
            raise RuntimeError(
                "테스트용 MSFT Pipeline 예외"
            )

        return create_fake_daily_pipeline_result(
            symbol=symbol,
            status="COMPLETED",
            final_equity=(
                10_100.0
                if symbol == "AAPL"
                else 10_300.0
            ),
        )

    no_save_policy = (
        PaperTradingBatchPipelinePolicy(
            continue_on_symbol_failure=True,
            require_all_symbols_success=False,
            save_daily_pipeline_outputs=False,
        )
    )

    result = run_paper_trading_batch_pipeline(
        symbols=SYMBOLS,
        batch_policy=no_save_policy,
        daily_pipeline_runner=runner,
    )

    if result.batch_status != "PARTIAL":
        raise RuntimeError(
            "일부 실패 Batch Status가 PARTIAL이 아닙니다."
        )

    if calls != SYMBOLS:
        raise RuntimeError(
            "실패 격리 후 다음 종목이 계속 실행되지 않았습니다."
        )

    if result.completed_symbol_count != 2:
        raise RuntimeError(
            "Partial Completed Count가 2가 아닙니다."
        )

    if result.failed_symbol_count != 1:
        raise RuntimeError(
            "Partial Failed Count가 1이 아닙니다."
        )

    if (
        result.symbol_results["MSFT"]
        .symbol_status
        != "FAILED"
    ):
        raise RuntimeError(
            "MSFT Status가 FAILED가 아닙니다."
        )

    if not (
        result.symbol_results["MSFT"]
        .error_message
    ):
        raise RuntimeError(
            "MSFT Error Message가 없습니다."
        )

    assert_close(
        result.success_rate_percent,
        66.6667,
        tolerance=0.0001,
    )

    if not result.all_checks_passed:
        raise RuntimeError(
            "Partial 허용 정책의 All Checks가 실패했습니다."
        )

    return result


def validate_stop_after_failure() -> (
    PaperTradingBatchPipelineResult
):
    calls: list[str] = []

    def runner(
        symbol: str,
        account_cash: float,
        latest_prices: dict[str, float],
    ) -> SimpleNamespace:
        calls.append(symbol)

        if symbol == "MSFT":
            raise RuntimeError(
                "테스트용 중단 예외"
            )

        return create_fake_daily_pipeline_result(
            symbol=symbol,
            status="COMPLETED",
            final_equity=10_100.0,
        )

    stop_policy = PaperTradingBatchPipelinePolicy(
        continue_on_symbol_failure=False,
        require_all_symbols_success=False,
        save_daily_pipeline_outputs=False,
    )

    result = run_paper_trading_batch_pipeline(
        symbols=SYMBOLS,
        batch_policy=stop_policy,
        daily_pipeline_runner=runner,
    )

    if calls != [
        "AAPL",
        "MSFT",
    ]:
        raise RuntimeError(
            "실패 후 Batch가 올바른 위치에서 중단되지 않았습니다."
        )

    if result.completed_symbol_count != 1:
        raise RuntimeError(
            "중단 Batch Completed Count가 1이 아닙니다."
        )

    if result.failed_symbol_count != 1:
        raise RuntimeError(
            "중단 Batch Failed Count가 1이 아닙니다."
        )

    if result.skipped_symbol_count != 1:
        raise RuntimeError(
            "중단 Batch Skipped Count가 1이 아닙니다."
        )

    if (
        result.symbol_results["NVDA"]
        .symbol_status
        != "SKIPPED"
    ):
        raise RuntimeError(
            "NVDA Status가 SKIPPED가 아닙니다."
        )

    return result


def validate_require_all_policy() -> (
    PaperTradingBatchPipelineResult
):
    def runner(
        symbol: str,
        account_cash: float,
        latest_prices: dict[str, float],
    ) -> SimpleNamespace:
        if symbol == "MSFT":
            raise RuntimeError(
                "테스트용 필수 성공 실패"
            )

        return create_fake_daily_pipeline_result(
            symbol=symbol,
            status="COMPLETED",
        )

    strict_policy = PaperTradingBatchPipelinePolicy(
        continue_on_symbol_failure=True,
        require_all_symbols_success=True,
        save_daily_pipeline_outputs=False,
    )

    result = run_paper_trading_batch_pipeline(
        symbols=SYMBOLS,
        batch_policy=strict_policy,
        daily_pipeline_runner=runner,
    )

    if result.batch_status != "BLOCKED":
        raise RuntimeError(
            "전체 성공 필수 Batch가 BLOCKED가 아닙니다."
        )

    if result.all_required_symbols_passed:
        raise RuntimeError(
            "실패 종목이 있는데 All Required가 True입니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "전체 성공 필수 Batch All Checks가 True입니다."
        )

    return result


def validate_duplicate_policies() -> None:
    calls: list[str] = []

    def runner(
        symbol: str,
        account_cash: float,
        latest_prices: dict[str, float],
    ) -> SimpleNamespace:
        calls.append(symbol)

        return create_fake_daily_pipeline_result(
            symbol=symbol,
            status="COMPLETED",
        )

    allow_policy = PaperTradingBatchPipelinePolicy(
        reject_duplicate_symbols=False,
        save_daily_pipeline_outputs=False,
    )

    allow_result = run_paper_trading_batch_pipeline(
        symbols=[
            "AAPL",
            "aapl",
            "MSFT",
        ],
        batch_policy=allow_policy,
        daily_pipeline_runner=runner,
    )

    if allow_result.normalized_symbols != [
        "AAPL",
        "MSFT",
    ]:
        raise RuntimeError(
            "허용 정책에서 중복 제거가 실패했습니다."
        )

    if allow_result.duplicate_symbols != [
        "AAPL"
    ]:
        raise RuntimeError(
            "Duplicate Symbol 기록이 다릅니다."
        )

    if calls != [
        "AAPL",
        "MSFT",
    ]:
        raise RuntimeError(
            "중복 Symbol이 두 번 실행되었습니다."
        )

    reject_policy = PaperTradingBatchPipelinePolicy(
        reject_duplicate_symbols=True,
        save_daily_pipeline_outputs=False,
    )

    reject_calls: list[str] = []

    def reject_runner(
        symbol: str,
        account_cash: float,
        latest_prices: dict[str, float],
    ) -> SimpleNamespace:
        reject_calls.append(symbol)
        return create_fake_daily_pipeline_result(
            symbol=symbol
        )

    reject_result = run_paper_trading_batch_pipeline(
        symbols=[
            "AAPL",
            "aapl",
        ],
        batch_policy=reject_policy,
        daily_pipeline_runner=reject_runner,
    )

    if reject_result.batch_status != "FAILED":
        raise RuntimeError(
            "중복 거부 Batch가 FAILED가 아닙니다."
        )

    if reject_calls:
        raise RuntimeError(
            "중복 거부 후 Runner가 호출되었습니다."
        )


def validate_empty_and_oversized_batches() -> None:
    empty_result = run_paper_trading_batch_pipeline(
        symbols=[],
        batch_policy=(
            PaperTradingBatchPipelinePolicy(
                save_daily_pipeline_outputs=False
            )
        ),
    )

    if empty_result.batch_status != "FAILED":
        raise RuntimeError(
            "빈 Batch가 FAILED가 아닙니다."
        )

    oversized_result = run_paper_trading_batch_pipeline(
        symbols=[
            "AAPL",
            "MSFT",
        ],
        batch_policy=(
            PaperTradingBatchPipelinePolicy(
                maximum_symbol_count=1,
                save_daily_pipeline_outputs=False,
            )
        ),
    )

    if oversized_result.batch_status != "FAILED":
        raise RuntimeError(
            "Maximum Count 초과 Batch가 FAILED가 아닙니다."
        )


def validate_execution_safety(
    result: PaperTradingBatchPipelineResult,
) -> None:
    if result.batch_status not in VALID_BATCH_STATUSES:
        raise RuntimeError(
            "Batch Status가 유효하지 않습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "Batch Execution이 차단되지 않았습니다."
        )

    if result.broker_api_called:
        raise RuntimeError(
            "실제 Broker API가 호출되었습니다."
        )

    if result.broker_order_created:
        raise RuntimeError(
            "실제 Broker Order가 생성되었습니다."
        )

    if result.live_order_created:
        raise RuntimeError(
            "Live Order가 생성되었습니다."
        )

    if result.live_execution_authorized:
        raise RuntimeError(
            "Live Execution이 허용되었습니다."
        )

    for symbol, symbol_result in (
        result.symbol_results.items()
    ):
        if (
            symbol_result.symbol_status
            not in VALID_SYMBOL_STATUSES
        ):
            raise RuntimeError(
                f"{symbol} Status가 유효하지 않습니다."
            )

        safe, errors = validate_symbol_result_safety(
            symbol_result
        )

        if not safe:
            raise RuntimeError(
                f"{symbol} Safety 검사 실패: {errors}"
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


def validate_save_and_load(
    result: PaperTradingBatchPipelineResult,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch(
            "backtest.paper_trading_batch_pipeline."
            "PAPER_BATCH_PIPELINE_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_batch_pipeline(
                    result
                )
            )

            for file_path in (
                report_path,
                latest_path,
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
                    "Batch Report와 Latest가 다릅니다."
                )

            loaded_payload = (
                load_latest_paper_trading_batch_pipeline()
            )

            if loaded_payload != latest_payload:
                raise RuntimeError(
                    "Latest Batch 재로딩이 실패했습니다."
                )

            if (
                loaded_payload.get("version")
                != "V10.3"
            ):
                raise RuntimeError(
                    "저장된 Version이 V10.3이 아닙니다."
                )


def print_validation_checks(
    completed_result: PaperTradingBatchPipelineResult,
    partial_result: PaperTradingBatchPipelineResult,
    stopped_result: PaperTradingBatchPipelineResult,
    strict_result: PaperTradingBatchPipelineResult,
) -> None:
    checks = {
        "Version is V10.3": (
            completed_result.version == "V10.3"
        ),
        "All-success status is COMPLETED": (
            completed_result.batch_status
            == "COMPLETED"
        ),
        "Three symbols completed": (
            completed_result.completed_symbol_count
            == 3
        ),
        "All-success rate is 100 percent": (
            completed_result.success_rate_percent
            == 100.0
        ),
        "All-success checks passed": (
            completed_result.all_checks_passed
        ),
        "Partial status is PARTIAL": (
            partial_result.batch_status
            == "PARTIAL"
        ),
        "Partial batch completed two symbols": (
            partial_result.completed_symbol_count
            == 2
        ),
        "Partial batch isolated one failure": (
            partial_result.failed_symbol_count
            == 1
        ),
        "Partial success rate is 66.6667 percent": (
            abs(
                partial_result.success_rate_percent
                - 66.6667
            )
            <= 0.0001
        ),
        "Stop policy skipped remaining symbol": (
            stopped_result.skipped_symbol_count
            == 1
        ),
        "Strict policy blocks partial batch": (
            strict_result.batch_status
            == "BLOCKED"
        ),
        "Execution remains blocked": (
            completed_result.execution_blocked
        ),
        "Broker API was not called": (
            not completed_result.broker_api_called
        ),
        "Broker order was not created": (
            not completed_result.broker_order_created
        ),
        "Live order was not created": (
            not completed_result.live_order_created
        ),
        "Live execution not authorized": (
            not completed_result
            .live_execution_authorized
        ),
    }

    print()
    print("=" * LINE_LENGTH)
    print("V10.3 VALIDATION CHECKS")
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
            "다음 V10.3 검증 항목이 실패했습니다: "
            f"{failed_checks}"
        )


def main() -> None:
    """
    V10.3 Multi-Symbol Batch Pipeline 통합 테스트입니다.

    검증 항목:

    1. Batch Policy 구조와 불변성
    2. Symbol 정규화 및 중복 제거
    3. Latest Price 정규화
    4. 세 종목 전체 성공
    5. 일부 종목 실패 격리
    6. 실패 후 남은 종목 중단
    7. 전체 성공 필수 정책
    8. 중복 Symbol 허용 및 거부 정책
    9. 빈 목록과 Maximum Count 초과 차단
    10. JSON 저장 및 재로딩
    11. 실제 Broker와 Live Execution 차단
    """

    print_header()

    policy = validate_policy()
    validate_symbol_helpers(policy)

    completed_result = (
        validate_all_symbols_success(policy)
    )

    partial_result = validate_partial_batch(
        policy
    )

    stopped_result = (
        validate_stop_after_failure()
    )

    strict_result = validate_require_all_policy()

    validate_duplicate_policies()
    validate_empty_and_oversized_batches()

    for result in (
        completed_result,
        partial_result,
        stopped_result,
        strict_result,
    ):
        validate_execution_safety(result)

    validate_save_and_load(completed_result)

    print_validation_checks(
        completed_result=completed_result,
        partial_result=partial_result,
        stopped_result=stopped_result,
        strict_result=strict_result,
    )

    print()
    print(
        "V10.3 multi-symbol paper trading batch "
        "test completed successfully."
    )
    print(
        "다중 종목 순서, 중복 제거, 실패 격리 및 "
        "중단 정책이 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
