import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backtest.paper_trading_daily_pipeline import (
    PIPELINE_STAGE_NAMES,
    VALID_PIPELINE_STATUSES,
    VALID_STAGE_STATUSES,
    PaperTradingDailyPipelinePolicy,
    PaperTradingDailyPipelineResult,
    PaperTradingPipelineStageResult,
    can_continue_after_stage,
    create_pending_stages,
    load_latest_paper_trading_daily_pipeline,
    normalize_symbol,
    run_paper_trading_daily_pipeline,
    save_paper_trading_daily_pipeline,
    validate_pipeline_policy,
)


LINE_LENGTH = 140
SYMBOL = "AAPL"
INITIAL_CASH = 10_000.0


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.2 "
        "PAPER TRADING DAILY PIPELINE TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<72}: {value}")


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


def fake_to_dict(
    name: str,
    identifier: str,
) -> dict[str, str]:
    return {
        "fake_type": name,
        "fake_id": identifier,
    }


def create_fake_request(
    all_checks_passed: bool = True,
) -> SimpleNamespace:
    request_id = "request-v10-2-test"

    return SimpleNamespace(
        symbol=SYMBOL,
        request_id=request_id,
        request_status=(
            "READY_FOR_PAPER"
            if all_checks_passed
            else "BLOCKED"
        ),
        all_checks_passed=all_checks_passed,
        paper_execution_authorized=(
            all_checks_passed
        ),
        live_execution_authorized=False,
        broker_order_created=False,
        live_order_created=False,
        reasons=[
            "테스트용 Paper Execution Request입니다."
        ],
        warnings=[
            "실제 주문을 생성하지 않습니다."
        ],
        to_dict=lambda: fake_to_dict(
            "PaperExecutionRequestResult",
            request_id,
        ),
    )


def create_fake_fill(
    all_checks_passed: bool = True,
) -> SimpleNamespace:
    fill_id = "fill-v10-2-test"

    return SimpleNamespace(
        symbol=SYMBOL,
        request_id="request-v10-2-test",
        fill_id=fill_id,
        fill_price=100.0,
        fill_status=(
            "FILLED"
            if all_checks_passed
            else "BLOCKED"
        ),
        all_checks_passed=all_checks_passed,
        paper_fill_created=all_checks_passed,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reasons=[
            "테스트용 Paper Fill입니다."
        ],
        warnings=[
            "실제 Broker API를 호출하지 않습니다."
        ],
        to_dict=lambda: fake_to_dict(
            "PaperBrokerFillResult",
            fill_id,
        ),
    )


def create_fake_portfolio_state() -> SimpleNamespace:
    return SimpleNamespace(
        portfolio_id="portfolio-v10-2-test",
        cash_balance=9_000.0,
        total_market_value=1_000.0,
        total_equity=10_000.0,
        to_dict=lambda: {
            "portfolio_id": "portfolio-v10-2-test",
            "cash_balance": 9_000.0,
            "total_market_value": 1_000.0,
            "total_equity": 10_000.0,
        },
    )


def create_fake_portfolio_result(
    portfolio_state: SimpleNamespace,
    all_checks_passed: bool = True,
) -> SimpleNamespace:
    update_id = "portfolio-update-v10-2-test"

    return SimpleNamespace(
        source_fill_id="fill-v10-2-test",
        update_id=update_id,
        portfolio_status=(
            "UPDATED"
            if all_checks_passed
            else "BLOCKED"
        ),
        all_checks_passed=all_checks_passed,
        portfolio_updated=all_checks_passed,
        broker_api_called=False,
        live_order_created=False,
        live_execution_authorized=False,
        portfolio_state=portfolio_state,
        updated_cash_balance=9_000.0,
        total_market_value=1_000.0,
        total_equity=10_000.0,
        reasons=[
            "테스트용 Portfolio Update입니다."
        ],
        warnings=[
            "실제 계좌를 변경하지 않습니다."
        ],
        to_dict=lambda: fake_to_dict(
            "PaperPortfolioResult",
            update_id,
        ),
    )


def create_fake_valuation(
    all_checks_passed: bool = True,
) -> SimpleNamespace:
    valuation_id = "valuation-v10-2-test"

    return SimpleNamespace(
        portfolio_id="portfolio-v10-2-test",
        valuation_id=valuation_id,
        valuation_status=(
            "VALUED"
            if all_checks_passed
            else "BLOCKED"
        ),
        all_checks_passed=all_checks_passed,
        portfolio_updated=all_checks_passed,
        cash_balance=9_000.0,
        updated_total_market_value=1_100.0,
        updated_total_equity=10_100.0,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reasons=[
            "테스트용 Portfolio Valuation입니다."
        ],
        warnings=[
            "실제 Broker Position을 조회하지 않습니다."
        ],
        to_dict=lambda: fake_to_dict(
            "PaperPortfolioValuationResult",
            valuation_id,
        ),
    )


def create_fake_performance(
    all_checks_passed: bool = True,
) -> SimpleNamespace:
    performance_id = "performance-v10-2-test"

    return SimpleNamespace(
        source_valuation_id="valuation-v10-2-test",
        performance_id=performance_id,
        performance_status=(
            "TRACKED"
            if all_checks_passed
            else "BLOCKED"
        ),
        all_checks_passed=all_checks_passed,
        current_equity=10_100.0,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reasons=[
            "테스트용 Performance Result입니다."
        ],
        warnings=[
            "성과는 미래 수익을 보장하지 않습니다."
        ],
        to_dict=lambda: fake_to_dict(
            "PaperPortfolioPerformanceResult",
            performance_id,
        ),
    )


def validate_policy() -> PaperTradingDailyPipelinePolicy:
    policy = PaperTradingDailyPipelinePolicy()

    valid, errors = validate_pipeline_policy(policy)

    if not valid or errors:
        raise RuntimeError(
            f"기본 Pipeline Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "stop_on_stage_failure",
        "require_request_checks",
        "require_fill_checks",
        "require_portfolio_checks",
        "require_valuation_checks",
        "require_performance_checks",
        "save_stage_outputs",
        "use_fill_price_for_valuation",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "Pipeline Policy Dictionary 구조가 다릅니다."
        )

    immutable = False

    try:
        policy.stop_on_stage_failure = False
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "Pipeline Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingDailyPipelinePolicy(
            paper_only=False
        ),
        PaperTradingDailyPipelinePolicy(
            live_execution_disabled=False
        ),
        PaperTradingDailyPipelinePolicy(
            stop_on_stage_failure="yes"
        ),
        PaperTradingDailyPipelinePolicy(
            save_stage_outputs=1
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_pipeline_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_stage_helpers(
    policy: PaperTradingDailyPipelinePolicy,
) -> None:
    if normalize_symbol(" aapl ") != "AAPL":
        raise RuntimeError(
            "Symbol 정규화가 실패했습니다."
        )

    try:
        normalize_symbol("   ")
    except ValueError:
        pass
    else:
        raise RuntimeError(
            "빈 Symbol이 거부되지 않았습니다."
        )

    stages = create_pending_stages(policy)

    if tuple(stages.keys()) != PIPELINE_STAGE_NAMES:
        raise RuntimeError(
            "Pipeline Stage 순서가 올바르지 않습니다."
        )

    for order, stage_name in enumerate(
        PIPELINE_STAGE_NAMES,
        start=1,
    ):
        stage = stages[stage_name]

        if not isinstance(
            stage,
            PaperTradingPipelineStageResult,
        ):
            raise RuntimeError(
                f"{stage_name} Stage 형식이 올바르지 않습니다."
            )

        if stage.stage_order != order:
            raise RuntimeError(
                f"{stage_name} Stage 순서가 다릅니다."
            )

        if stage.stage_status != "SKIPPED":
            raise RuntimeError(
                f"{stage_name} 초기 상태가 SKIPPED가 아닙니다."
            )

    completed_stage = PaperTradingPipelineStageResult(
        stage_name="TEST",
        stage_order=1,
        stage_status="COMPLETED",
        stage_status_label="완료",
        started_at=None,
        completed_at=None,
        source_id=None,
        result_id=None,
        checks_required=True,
        checks_passed=True,
        output_saved=False,
    )

    blocked_stage = PaperTradingPipelineStageResult(
        stage_name="TEST",
        stage_order=1,
        stage_status="BLOCKED",
        stage_status_label="차단",
        started_at=None,
        completed_at=None,
        source_id=None,
        result_id=None,
        checks_required=True,
        checks_passed=False,
        output_saved=False,
    )

    if not can_continue_after_stage(
        completed_stage,
        policy,
    ):
        raise RuntimeError(
            "완료 Stage 이후 진행이 차단되었습니다."
        )

    if can_continue_after_stage(
        blocked_stage,
        policy,
    ):
        raise RuntimeError(
            "차단 Stage 이후 Pipeline이 계속 진행됩니다."
        )


def validate_completed_pipeline(
    policy: PaperTradingDailyPipelinePolicy,
) -> PaperTradingDailyPipelineResult:
    request = create_fake_request()
    fill = create_fake_fill()
    portfolio_state = create_fake_portfolio_state()
    portfolio_result = create_fake_portfolio_result(
        portfolio_state
    )
    valuation_result = create_fake_valuation()
    performance_result = create_fake_performance()

    with (
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_manager",
            return_value=portfolio_result,
        ) as portfolio_mock,
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_valuation",
            return_value=valuation_result,
        ) as valuation_mock,
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_performance_tracker",
            return_value=performance_result,
        ) as performance_mock,
        patch(
            "backtest.paper_trading_daily_pipeline."
            "save_paper_portfolio_result",
            return_value=(
                Path("portfolio_report.json"),
                Path("portfolio_latest.json"),
                Path("portfolio_state.json"),
            ),
        ),
        patch(
            "backtest.paper_trading_daily_pipeline."
            "save_paper_portfolio_valuation",
            return_value=(
                Path("valuation_report.json"),
                Path("valuation_latest.json"),
                Path("valuation_snapshot.json"),
                Path("portfolio_state.json"),
            ),
        ),
        patch(
            "backtest.paper_trading_daily_pipeline."
            "save_paper_portfolio_performance",
            return_value=(
                Path("performance_report.json"),
                Path("performance_latest.json"),
                Path("performance_history.json"),
            ),
        ),
    ):
        result = run_paper_trading_daily_pipeline(
            symbol=SYMBOL,
            account_cash=INITIAL_CASH,
            latest_prices={
                SYMBOL: 110.0,
            },
            pipeline_policy=policy,
            execution_request=request,
            paper_fill=fill,
            portfolio_state=portfolio_state,
        )

    if not isinstance(
        result,
        PaperTradingDailyPipelineResult,
    ):
        raise RuntimeError(
            "Pipeline Result 형식이 올바르지 않습니다."
        )

    if result.version != "V10.2":
        raise RuntimeError(
            "Version이 V10.2가 아닙니다."
        )

    if result.pipeline_status != "COMPLETED":
        raise RuntimeError(
            "정상 Pipeline Status가 COMPLETED가 아닙니다."
        )

    if result.completed_stage_count != 5:
        raise RuntimeError(
            "Completed Stage Count가 5가 아닙니다."
        )

    if (
        result.blocked_stage_count != 0
        or result.failed_stage_count != 0
        or result.skipped_stage_count != 0
    ):
        raise RuntimeError(
            "정상 Pipeline에 미완료 Stage가 있습니다."
        )

    if not result.all_required_stages_passed:
        raise RuntimeError(
            "All Required Stages가 실패했습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Pipeline All Checks가 실패했습니다."
        )

    for stage_name in PIPELINE_STAGE_NAMES:
        stage = result.stages[stage_name]

        if stage.stage_status != "COMPLETED":
            raise RuntimeError(
                f"{stage_name} Status가 COMPLETED가 아닙니다."
            )

        if not stage.checks_passed:
            raise RuntimeError(
                f"{stage_name} Checks가 실패했습니다."
            )

    if portfolio_mock.call_count != 1:
        raise RuntimeError(
            "Portfolio Manager가 정확히 한 번 호출되지 않았습니다."
        )

    if valuation_mock.call_count != 1:
        raise RuntimeError(
            "Portfolio Valuation이 정확히 한 번 호출되지 않았습니다."
        )

    if performance_mock.call_count != 1:
        raise RuntimeError(
            "Performance Tracker가 정확히 한 번 호출되지 않았습니다."
        )

    assert_close(
        result.final_cash_balance,
        9_000.0,
    )
    assert_close(
        result.final_market_value,
        1_100.0,
    )
    assert_close(
        result.final_equity,
        10_100.0,
    )

    return result


def validate_request_block(
    policy: PaperTradingDailyPipelinePolicy,
) -> PaperTradingDailyPipelineResult:
    failed_request = create_fake_request(
        all_checks_passed=False
    )

    with (
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_broker_simulator"
        ) as broker_mock,
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_manager"
        ) as portfolio_mock,
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_valuation"
        ) as valuation_mock,
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_performance_tracker"
        ) as performance_mock,
    ):
        result = run_paper_trading_daily_pipeline(
            symbol=SYMBOL,
            pipeline_policy=policy,
            execution_request=failed_request,
        )

    if result.pipeline_status != "BLOCKED":
        raise RuntimeError(
            "Request 실패 Pipeline이 BLOCKED가 아닙니다."
        )

    if (
        result.stages["EXECUTION_REQUEST"]
        .stage_status
        != "BLOCKED"
    ):
        raise RuntimeError(
            "Execution Request Stage가 BLOCKED가 아닙니다."
        )

    for stage_name in PIPELINE_STAGE_NAMES[1:]:
        if (
            result.stages[stage_name].stage_status
            != "SKIPPED"
        ):
            raise RuntimeError(
                f"{stage_name} Stage가 SKIPPED가 아닙니다."
            )

    for name, mock in {
        "Broker": broker_mock,
        "Portfolio": portfolio_mock,
        "Valuation": valuation_mock,
        "Performance": performance_mock,
    }.items():
        if mock.called:
            raise RuntimeError(
                f"Request 차단 후 {name} Stage가 호출되었습니다."
            )

    if result.all_checks_passed:
        raise RuntimeError(
            "Request 차단 결과 All Checks가 True입니다."
        )

    return result


def validate_portfolio_exception(
    policy: PaperTradingDailyPipelinePolicy,
) -> PaperTradingDailyPipelineResult:
    request = create_fake_request()
    fill = create_fake_fill()
    portfolio_state = create_fake_portfolio_state()

    with (
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_manager",
            side_effect=RuntimeError(
                "테스트용 Portfolio 예외"
            ),
        ),
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_valuation"
        ) as valuation_mock,
        patch(
            "backtest.paper_trading_daily_pipeline."
            "run_paper_portfolio_performance_tracker"
        ) as performance_mock,
    ):
        result = run_paper_trading_daily_pipeline(
            symbol=SYMBOL,
            pipeline_policy=policy,
            execution_request=request,
            paper_fill=fill,
            portfolio_state=portfolio_state,
        )

    if result.pipeline_status != "FAILED":
        raise RuntimeError(
            "Portfolio 예외 Pipeline이 FAILED가 아닙니다."
        )

    portfolio_stage = result.stages[
        "PORTFOLIO_UPDATE"
    ]

    if portfolio_stage.stage_status != "FAILED":
        raise RuntimeError(
            "Portfolio Stage가 FAILED가 아닙니다."
        )

    if not portfolio_stage.error_message:
        raise RuntimeError(
            "Portfolio Stage Error Message가 없습니다."
        )

    if valuation_mock.called:
        raise RuntimeError(
            "Portfolio 예외 후 Valuation이 호출되었습니다."
        )

    if performance_mock.called:
        raise RuntimeError(
            "Portfolio 예외 후 Performance가 호출되었습니다."
        )

    return result


def validate_invalid_policy_pipeline() -> (
    PaperTradingDailyPipelineResult
):
    invalid_policy = (
        PaperTradingDailyPipelinePolicy(
            paper_only=False
        )
    )

    result = run_paper_trading_daily_pipeline(
        symbol=SYMBOL,
        pipeline_policy=invalid_policy,
    )

    if result.pipeline_status != "FAILED":
        raise RuntimeError(
            "Invalid Policy Pipeline이 FAILED가 아닙니다."
        )

    if result.policy_checks_passed if hasattr(
        result,
        "policy_checks_passed",
    ) else False:
        raise RuntimeError(
            "Invalid Policy가 통과했습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "Invalid Policy All Checks가 True입니다."
        )

    return result


def validate_execution_safety(
    result: PaperTradingDailyPipelineResult,
) -> None:
    if (
        result.pipeline_status
        not in VALID_PIPELINE_STATUSES
    ):
        raise RuntimeError(
            "Pipeline Status가 유효하지 않습니다."
        )

    for stage in result.stages.values():
        if stage.stage_status not in VALID_STAGE_STATUSES:
            raise RuntimeError(
                f"Stage Status가 유효하지 않습니다: "
                f"{stage.stage_status}"
            )

    if not result.execution_blocked:
        raise RuntimeError(
            "Execution이 차단되지 않았습니다."
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
    result: PaperTradingDailyPipelineResult,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        output_directory = Path(directory)

        with patch(
            "backtest.paper_trading_daily_pipeline."
            "PAPER_DAILY_PIPELINE_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_daily_pipeline(
                    result
                )
            )

            if not report_path.exists():
                raise RuntimeError(
                    "Pipeline Report 파일이 없습니다."
                )

            if not latest_path.exists():
                raise RuntimeError(
                    "Pipeline Latest 파일이 없습니다."
                )

            if (
                report_path.stat().st_size <= 0
                or latest_path.stat().st_size <= 0
            ):
                raise RuntimeError(
                    "저장된 Pipeline 파일이 비어 있습니다."
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
                    "Report와 Latest JSON이 다릅니다."
                )

            loaded_payload = (
                load_latest_paper_trading_daily_pipeline(
                    symbol=SYMBOL
                )
            )

            if loaded_payload != latest_payload:
                raise RuntimeError(
                    "Latest Pipeline 재로딩이 실패했습니다."
                )

            if (
                loaded_payload.get("version")
                != "V10.2"
            ):
                raise RuntimeError(
                    "저장된 Version이 V10.2가 아닙니다."
                )


def print_validation_checks(
    completed_result: PaperTradingDailyPipelineResult,
    blocked_result: PaperTradingDailyPipelineResult,
    failed_result: PaperTradingDailyPipelineResult,
    invalid_policy_result: (
        PaperTradingDailyPipelineResult
    ),
) -> None:
    checks = {
        "Version is V10.2": (
            completed_result.version == "V10.2"
        ),
        "Completed pipeline status is COMPLETED": (
            completed_result.pipeline_status
            == "COMPLETED"
        ),
        "All five stages completed": (
            completed_result.completed_stage_count
            == 5
        ),
        "Request stage passed": (
            completed_result.request_stage_passed
        ),
        "Broker stage passed": (
            completed_result.broker_stage_passed
        ),
        "Portfolio stage passed": (
            completed_result.portfolio_stage_passed
        ),
        "Valuation stage passed": (
            completed_result.valuation_stage_passed
        ),
        "Performance stage passed": (
            completed_result.performance_stage_passed
        ),
        "All required stages passed": (
            completed_result
            .all_required_stages_passed
        ),
        "Completed result all checks passed": (
            completed_result.all_checks_passed
        ),
        "Failed request blocks pipeline": (
            blocked_result.pipeline_status
            == "BLOCKED"
        ),
        "Request block skips later stages": (
            blocked_result.skipped_stage_count
            == 4
        ),
        "Stage exception fails pipeline": (
            failed_result.pipeline_status
            == "FAILED"
        ),
        "Invalid policy fails pipeline": (
            invalid_policy_result.pipeline_status
            == "FAILED"
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
    print("V10.2 VALIDATION CHECKS")
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
            "다음 V10.2 검증 항목이 실패했습니다: "
            f"{failed_checks}"
        )


def main() -> None:
    """
    V10.2 Paper Trading Daily Pipeline 통합 테스트입니다.

    검증 항목:

    1. Pipeline Policy 구조와 불변성
    2. 5개 Stage 순서
    3. 모든 Stage 성공
    4. Request 실패 시 즉시 차단
    5. 중간 Stage 예외 시 이후 Stage 중단
    6. Invalid Policy 차단
    7. Pipeline JSON 저장 및 재로딩
    8. 실제 Broker 및 Live Execution 차단
    """

    print_header()

    policy = validate_policy()
    validate_stage_helpers(policy)

    completed_result = (
        validate_completed_pipeline(policy)
    )

    blocked_result = validate_request_block(
        policy
    )

    failed_result = validate_portfolio_exception(
        policy
    )

    invalid_policy_result = (
        validate_invalid_policy_pipeline()
    )

    for result in (
        completed_result,
        blocked_result,
        failed_result,
        invalid_policy_result,
    ):
        validate_execution_safety(result)

    validate_save_and_load(completed_result)

    print_validation_checks(
        completed_result=completed_result,
        blocked_result=blocked_result,
        failed_result=failed_result,
        invalid_policy_result=(
            invalid_policy_result
        ),
    )

    print()
    print(
        "V10.2 paper trading daily pipeline "
        "test completed successfully."
    )
    print(
        "5개 Paper Trading Stage의 순서, 차단 및 "
        "예외 처리가 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
