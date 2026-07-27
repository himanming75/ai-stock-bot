import json
import tempfile
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import patch

import backtest.paper_trading_risk_gated_pipeline as gated_module
from backtest.paper_trading_daily_pipeline import (
    PaperTradingDailyPipelinePolicy,
    PaperTradingDailyPipelineResult,
)
from backtest.paper_trading_risk_gated_pipeline import (
    VALID_GATE_STATUSES,
    VALID_GATED_PIPELINE_STATUSES,
    PaperTradingRiskGatedPipelinePolicy,
    evaluate_risk_gate,
    load_latest_paper_trading_risk_gated_pipeline,
    normalize_symbol,
    run_paper_trading_risk_gated_pipeline,
    save_paper_trading_risk_gated_pipeline,
    validate_daily_pipeline_safety,
    validate_gated_policy,
    validate_risk_result_safety,
)
from backtest.paper_trading_risk_monitor import (
    PaperTradingRiskMonitorPolicy,
    PaperTradingRiskMonitorResult,
)


LINE_LENGTH = 140
SYMBOL = "AAPL"
ACCOUNT_CASH = 10_000.0


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.5 "
        "PAPER TRADING RISK-GATED PIPELINE TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<78}: {value}")


def create_empty_dataclass_instance(
    dataclass_type,
):
    """
    외부 API 없이 기존 Result Dataclass의 테스트 객체를 만듭니다.
    """

    instance = object.__new__(dataclass_type)

    for item in fields(dataclass_type):
        setattr(instance, item.name, None)

    return instance


def create_fake_risk_result(
    *,
    risk_status: str = "SAFE",
    risk_action: str = "ALLOW",
    paper_trading_allowed: bool = True,
    all_checks_passed: bool = True,
) -> PaperTradingRiskMonitorResult:
    """
    V10.4 Risk Monitor 결과를 안전하게 흉내 냅니다.
    """

    result = create_empty_dataclass_instance(
        PaperTradingRiskMonitorResult
    )

    result.version = "V10.4"
    result.created_at = "2026-07-27T12:00:00"
    result.monitor_id = (
        f"risk-{risk_status.lower()}"
    )
    result.portfolio_id = "portfolio-test-001"
    result.source_performance_id = (
        "performance-test-001"
    )
    result.source_performance_file = None

    result.risk_status = risk_status
    result.risk_status_label = risk_status
    result.risk_action = risk_action
    result.risk_action_label = risk_action

    result.current_equity = 10_000.0
    result.cash_balance = 8_000.0
    result.total_market_value = 2_000.0

    result.period_profit_loss = 100.0
    result.period_return_percent = 1.0
    result.cumulative_profit_loss = 100.0
    result.cumulative_return_percent = 1.0

    result.current_drawdown_amount = 0.0
    result.current_drawdown_percent = 0.0
    result.maximum_drawdown_percent = 2.0

    result.consecutive_loss_count = 0
    result.performance_period_count = 3

    result.total_commission = 10.0
    result.commission_to_equity_percent = 0.1

    result.triggered_rule_count = (
        0 if risk_action == "ALLOW" else 1
    )
    result.warning_rule_count = (
        1 if risk_action == "WARNING" else 0
    )
    result.pause_rule_count = (
        1 if risk_action == "PAUSE" else 0
    )
    result.block_rule_count = (
        1 if risk_action == "BLOCK" else 0
    )

    result.source_loaded = True
    result.source_valid = (
        risk_status != "FAILED"
    )
    result.policy_checks_passed = True
    result.history_checks_passed = True
    result.rule_checks_passed = True
    result.all_checks_passed = (
        all_checks_passed
    )

    result.paper_trading_allowed = (
        paper_trading_allowed
    )
    result.paper_trading_warning = (
        risk_status == "WARNING"
    )
    result.paper_trading_paused = (
        risk_status == "PAUSED"
    )
    result.paper_trading_blocked = (
        risk_status
        in {
            "BLOCKED",
            "FAILED",
        }
    )

    result.execution_blocked = True
    result.broker_api_called = False
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    result.monitor_policy = (
        PaperTradingRiskMonitorPolicy()
    )
    result.rule_results = {}
    result.reasons = [
        f"테스트 Risk Status는 {risk_status}입니다."
    ]
    result.warnings = [
        "실제 Broker API를 호출하지 않습니다."
    ]
    result.next_actions = [
        "Risk Gate 결과를 확인합니다."
    ]
    result.report_path = None
    result.latest_path = None

    return result


def create_fake_daily_result(
    *,
    pipeline_status: str = "COMPLETED",
    all_checks_passed: bool = True,
) -> PaperTradingDailyPipelineResult:
    """
    실제 주문 없이 V10.2 Daily Pipeline 결과를 흉내 냅니다.
    """

    result = create_empty_dataclass_instance(
        PaperTradingDailyPipelineResult
    )

    result.version = "V10.2"
    result.created_at = "2026-07-27T12:01:00"
    result.pipeline_id = "daily-pipeline-test-001"
    result.symbol = SYMBOL

    result.pipeline_status = pipeline_status
    result.pipeline_status_label = (
        pipeline_status
    )

    result.initial_cash = ACCOUNT_CASH
    result.final_cash_balance = 8_000.0
    result.final_market_value = 2_100.0
    result.final_equity = 10_100.0

    result.request_id = "request-test-001"
    result.fill_id = "fill-test-001"
    result.portfolio_update_id = (
        "portfolio-update-test-001"
    )
    result.valuation_id = "valuation-test-001"
    result.performance_id = (
        "performance-test-002"
    )

    result.completed_stage_count = (
        5 if all_checks_passed else 3
    )
    result.blocked_stage_count = 0
    result.failed_stage_count = (
        0 if all_checks_passed else 1
    )
    result.skipped_stage_count = (
        0 if all_checks_passed else 1
    )

    result.request_stage_passed = True
    result.broker_stage_passed = True
    result.portfolio_stage_passed = True
    result.valuation_stage_passed = (
        all_checks_passed
    )
    result.performance_stage_passed = (
        all_checks_passed
    )

    result.all_required_stages_passed = (
        all_checks_passed
    )
    result.all_checks_passed = (
        all_checks_passed
    )

    result.execution_blocked = True
    result.broker_api_called = False
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    result.pipeline_policy = (
        PaperTradingDailyPipelinePolicy(
            save_stage_outputs=False,
        )
    )
    result.stages = {}

    result.execution_request = None
    result.paper_fill = None
    result.portfolio_result = None
    result.valuation_result = None
    result.performance_result = None

    result.reasons = [
        "테스트용 V10.2 Daily Pipeline입니다."
    ]
    result.warnings = [
        "실제 주문을 생성하지 않습니다."
    ]
    result.next_actions = [
        "테스트 결과를 확인합니다."
    ]
    result.report_path = None
    result.latest_path = None

    return result


class DailyRunnerRecorder:
    """
    Daily Pipeline 호출 횟수와 인자를 기록합니다.
    """

    def __init__(
        self,
        result: PaperTradingDailyPipelineResult,
    ) -> None:
        self.result = result
        self.call_count = 0
        self.last_arguments = {}

    def __call__(self, **kwargs):
        self.call_count += 1
        self.last_arguments = dict(kwargs)
        return self.result


def validate_policy() -> (
    PaperTradingRiskGatedPipelinePolicy
):
    policy = PaperTradingRiskGatedPipelinePolicy()

    valid, errors = validate_gated_policy(policy)

    if not valid or errors:
        raise RuntimeError(
            f"기본 V10.5 Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "require_risk_checks",
        "allow_safe",
        "allow_warning",
        "block_paused",
        "block_blocked",
        "block_failed",
        "require_daily_pipeline_checks",
        "save_output",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "V10.5 Policy Dictionary 구조가 다릅니다."
        )

    immutable = False

    try:
        policy.allow_warning = False
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "V10.5 Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingRiskGatedPipelinePolicy(
            require_risk_checks=False,
        ),
        PaperTradingRiskGatedPipelinePolicy(
            allow_safe=False,
        ),
        PaperTradingRiskGatedPipelinePolicy(
            block_paused=False,
        ),
        PaperTradingRiskGatedPipelinePolicy(
            block_blocked=False,
        ),
        PaperTradingRiskGatedPipelinePolicy(
            block_failed=False,
        ),
        PaperTradingRiskGatedPipelinePolicy(
            allow_warning="yes",
        ),
        PaperTradingRiskGatedPipelinePolicy(
            paper_only=False,
        ),
        PaperTradingRiskGatedPipelinePolicy(
            live_execution_disabled=False,
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_gated_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_helpers(
    policy: PaperTradingRiskGatedPipelinePolicy,
) -> None:
    if normalize_symbol(" aapl ") != SYMBOL:
        raise RuntimeError(
            "Symbol 정규화가 실패했습니다."
        )

    invalid_symbols = [
        "",
        "   ",
        "AA PL",
        "AAPL!",
    ]

    for invalid_symbol in invalid_symbols:
        rejected = False

        try:
            normalize_symbol(invalid_symbol)
        except (TypeError, ValueError):
            rejected = True

        if not rejected:
            raise RuntimeError(
                f"Invalid Symbol이 거부되지 않았습니다: {invalid_symbol!r}"
            )

    safe_risk = create_fake_risk_result()

    risk_valid, risk_errors = (
        validate_risk_result_safety(
            safe_risk
        )
    )

    if not risk_valid or risk_errors:
        raise RuntimeError(
            f"정상 Risk Result가 거부되었습니다: {risk_errors}"
        )

    daily_result = create_fake_daily_result()

    daily_valid, daily_errors = (
        validate_daily_pipeline_safety(
            daily_result
        )
    )

    if not daily_valid or daily_errors:
        raise RuntimeError(
            f"정상 Daily Result가 거부되었습니다: {daily_errors}"
        )

    decision = evaluate_risk_gate(
        safe_risk,
        policy,
    )

    if (
        decision.gate_status != "PASSED"
        or not decision.gate_passed
    ):
        raise RuntimeError(
            "SAFE Risk Gate Decision이 실패했습니다."
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


def validate_safe_execution(
    policy: PaperTradingRiskGatedPipelinePolicy,
):
    runner = DailyRunnerRecorder(
        create_fake_daily_result()
    )

    result = (
        run_paper_trading_risk_gated_pipeline(
            symbol=" aapl ",
            account_cash=ACCOUNT_CASH,
            gated_policy=policy,
            risk_monitor_result=(
                create_fake_risk_result()
            ),
            daily_pipeline_runner=runner,
        )
    )

    if result.version != "V10.5":
        raise RuntimeError(
            "결과 버전이 V10.5가 아닙니다."
        )

    if (
        result.gated_pipeline_status
        != "COMPLETED"
    ):
        raise RuntimeError(
            "SAFE 결과가 COMPLETED가 아닙니다."
        )

    if runner.call_count != 1:
        raise RuntimeError(
            "SAFE 상태에서 Daily Pipeline이 정확히 한 번 호출되지 않았습니다."
        )

    if not result.daily_pipeline_executed:
        raise RuntimeError(
            "SAFE 상태에서 Daily Pipeline이 실행되지 않았습니다."
        )

    if result.daily_pipeline_skipped:
        raise RuntimeError(
            "SAFE 상태에서 Daily Pipeline이 Skipped 처리되었습니다."
        )

    if not result.paper_trading_allowed:
        raise RuntimeError(
            "SAFE 상태에서 Paper Trading이 허용되지 않았습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "SAFE 결과의 All Checks가 실패했습니다."
        )

    if (
        runner.last_arguments.get("symbol")
        != SYMBOL
    ):
        raise RuntimeError(
            "정규화된 Symbol이 Daily Pipeline에 전달되지 않았습니다."
        )

    assert_execution_safety(result)

    return result


def validate_warning_execution(
    policy: PaperTradingRiskGatedPipelinePolicy,
):
    runner = DailyRunnerRecorder(
        create_fake_daily_result()
    )

    risk_result = create_fake_risk_result(
        risk_status="WARNING",
        risk_action="WARNING",
        paper_trading_allowed=True,
    )

    result = (
        run_paper_trading_risk_gated_pipeline(
            symbol=SYMBOL,
            account_cash=ACCOUNT_CASH,
            gated_policy=policy,
            risk_monitor_result=risk_result,
            daily_pipeline_runner=runner,
        )
    )

    if (
        result.risk_gate_decision.gate_status
        != "WARNING"
    ):
        raise RuntimeError(
            "WARNING Gate Status가 생성되지 않았습니다."
        )

    if runner.call_count != 1:
        raise RuntimeError(
            "허용된 WARNING에서 Daily Pipeline이 실행되지 않았습니다."
        )

    if (
        result.gated_pipeline_status
        != "COMPLETED"
    ):
        raise RuntimeError(
            "허용된 WARNING 결과가 COMPLETED가 아닙니다."
        )

    strict_policy = (
        PaperTradingRiskGatedPipelinePolicy(
            allow_warning=False,
        )
    )
    strict_runner = DailyRunnerRecorder(
        create_fake_daily_result()
    )

    strict_result = (
        run_paper_trading_risk_gated_pipeline(
            symbol=SYMBOL,
            account_cash=ACCOUNT_CASH,
            gated_policy=strict_policy,
            risk_monitor_result=risk_result,
            daily_pipeline_runner=(
                strict_runner
            ),
        )
    )

    if (
        strict_result.gated_pipeline_status
        != "BLOCKED"
    ):
        raise RuntimeError(
            "금지된 WARNING이 BLOCKED가 아닙니다."
        )

    if strict_runner.call_count != 0:
        raise RuntimeError(
            "금지된 WARNING에서 Daily Pipeline이 호출되었습니다."
        )

    assert_execution_safety(result)
    assert_execution_safety(strict_result)

    return result


def validate_blocked_execution(
    policy: PaperTradingRiskGatedPipelinePolicy,
    risk_status: str,
    risk_action: str,
):
    runner = DailyRunnerRecorder(
        create_fake_daily_result()
    )

    result = (
        run_paper_trading_risk_gated_pipeline(
            symbol=SYMBOL,
            account_cash=ACCOUNT_CASH,
            gated_policy=policy,
            risk_monitor_result=(
                create_fake_risk_result(
                    risk_status=risk_status,
                    risk_action=risk_action,
                    paper_trading_allowed=False,
                )
            ),
            daily_pipeline_runner=runner,
        )
    )

    if (
        result.gated_pipeline_status
        != "BLOCKED"
    ):
        raise RuntimeError(
            f"{risk_status} 결과가 BLOCKED가 아닙니다."
        )

    if runner.call_count != 0:
        raise RuntimeError(
            f"{risk_status} 상태에서 Daily Pipeline이 호출되었습니다."
        )

    if result.daily_pipeline_executed:
        raise RuntimeError(
            f"{risk_status} 상태에서 Daily Pipeline Executed가 True입니다."
        )

    if not result.daily_pipeline_skipped:
        raise RuntimeError(
            f"{risk_status} 상태에서 Daily Pipeline이 Skipped가 아닙니다."
        )

    if result.paper_trading_allowed:
        raise RuntimeError(
            f"{risk_status} 상태에서 Paper Trading이 허용되었습니다."
        )

    if not result.risk_gate_blocked:
        raise RuntimeError(
            f"{risk_status} 상태에서 Risk Gate Blocked가 False입니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            f"{risk_status}의 안전한 차단 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_failed_risk(
    policy: PaperTradingRiskGatedPipelinePolicy,
):
    runner = DailyRunnerRecorder(
        create_fake_daily_result()
    )

    result = (
        run_paper_trading_risk_gated_pipeline(
            symbol=SYMBOL,
            account_cash=ACCOUNT_CASH,
            gated_policy=policy,
            risk_monitor_result=(
                create_fake_risk_result(
                    risk_status="FAILED",
                    risk_action="BLOCK",
                    paper_trading_allowed=False,
                    all_checks_passed=False,
                )
            ),
            daily_pipeline_runner=runner,
        )
    )

    if (
        result.gated_pipeline_status
        != "FAILED"
    ):
        raise RuntimeError(
            "FAILED Risk가 Gated Pipeline FAILED로 처리되지 않았습니다."
        )

    if runner.call_count != 0:
        raise RuntimeError(
            "FAILED Risk에서 Daily Pipeline이 호출되었습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "FAILED Risk 결과의 All Checks가 True입니다."
        )

    assert_execution_safety(result)

    return result


def validate_daily_failure(
    policy: PaperTradingRiskGatedPipelinePolicy,
):
    runner = DailyRunnerRecorder(
        create_fake_daily_result(
            pipeline_status="FAILED",
            all_checks_passed=False,
        )
    )

    result = (
        run_paper_trading_risk_gated_pipeline(
            symbol=SYMBOL,
            account_cash=ACCOUNT_CASH,
            gated_policy=policy,
            risk_monitor_result=(
                create_fake_risk_result()
            ),
            daily_pipeline_runner=runner,
        )
    )

    if (
        result.gated_pipeline_status
        != "FAILED"
    ):
        raise RuntimeError(
            "Daily Pipeline 실패가 V10.5 FAILED로 전파되지 않았습니다."
        )

    if runner.call_count != 1:
        raise RuntimeError(
            "Daily Failure 테스트에서 호출 횟수가 다릅니다."
        )

    if result.daily_pipeline_checks_passed:
        raise RuntimeError(
            "실패한 Daily Pipeline Checks가 True입니다."
        )

    assert_execution_safety(result)

    return result


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output_directory = (
            Path(temporary)
            / "risk_gated_pipeline"
        )

        with patch.object(
            gated_module,
            (
                "PAPER_RISK_GATED_PIPELINE_"
                "OUTPUT_DIRECTORY"
            ),
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_risk_gated_pipeline(
                    result
                )
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V10.5 Report가 저장되지 않았습니다."
                )

            if not latest_path.exists():
                raise RuntimeError(
                    "V10.5 Latest가 저장되지 않았습니다."
                )

            loaded = (
                load_latest_paper_trading_risk_gated_pipeline()
            )

            if loaded.get("version") != "V10.5":
                raise RuntimeError(
                    "저장된 버전이 V10.5가 아닙니다."
                )

            if (
                loaded.get("gated_pipeline_id")
                != result.gated_pipeline_id
            ):
                raise RuntimeError(
                    "저장된 Gated Pipeline ID가 다릅니다."
                )

            if (
                loaded.get(
                    "gated_pipeline_status"
                )
                != "COMPLETED"
            ):
                raise RuntimeError(
                    "저장된 Pipeline Status가 다릅니다."
                )

            with latest_path.open(
                mode="r",
                encoding="utf-8",
            ) as file:
                raw_payload = json.load(file)

            if not isinstance(
                raw_payload.get(
                    "risk_gate_decision"
                ),
                dict,
            ):
                raise RuntimeError(
                    "저장된 Risk Gate Decision 형식이 다릅니다."
                )

            if not isinstance(
                raw_payload.get(
                    "daily_pipeline_result"
                ),
                dict,
            ):
                raise RuntimeError(
                    "저장된 Daily Pipeline Result 형식이 다릅니다."
                )


def validate_result_contract(results: list) -> None:
    for result in results:
        if (
            result.gated_pipeline_status
            not in VALID_GATED_PIPELINE_STATUSES
        ):
            raise RuntimeError(
                "허용되지 않은 Gated Pipeline Status입니다."
            )

        if (
            result.risk_gate_decision.gate_status
            not in VALID_GATE_STATUSES
        ):
            raise RuntimeError(
                "허용되지 않은 Risk Gate Status입니다."
            )

        if not result.gated_pipeline_id:
            raise RuntimeError(
                "Gated Pipeline ID가 비어 있습니다."
            )

        if result.symbol != SYMBOL:
            raise RuntimeError(
                "Result Symbol이 다릅니다."
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
    validate_helpers(policy)

    safe_result = validate_safe_execution(
        policy
    )
    warning_result = validate_warning_execution(
        policy
    )
    paused_result = validate_blocked_execution(
        policy=policy,
        risk_status="PAUSED",
        risk_action="PAUSE",
    )
    blocked_result = validate_blocked_execution(
        policy=policy,
        risk_status="BLOCKED",
        risk_action="BLOCK",
    )
    failed_risk_result = validate_failed_risk(
        policy
    )
    failed_daily_result = validate_daily_failure(
        policy
    )

    results = [
        safe_result,
        warning_result,
        paused_result,
        blocked_result,
        failed_risk_result,
        failed_daily_result,
    ]

    validate_result_contract(results)
    validate_save_and_load(safe_result)

    checks = {
        "Version is V10.5": (
            safe_result.version == "V10.5"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "SAFE gate passed": (
            safe_result
            .risk_gate_decision
            .gate_status
            == "PASSED"
        ),
        "SAFE executed daily pipeline": (
            safe_result.daily_pipeline_executed
        ),
        "Allowed WARNING executed pipeline": (
            warning_result.daily_pipeline_executed
        ),
        "PAUSED skipped daily pipeline": (
            paused_result.daily_pipeline_skipped
        ),
        "BLOCKED skipped daily pipeline": (
            blocked_result.daily_pipeline_skipped
        ),
        "FAILED risk skipped daily pipeline": (
            failed_risk_result
            .daily_pipeline_skipped
        ),
        "Daily failure propagated": (
            failed_daily_result
            .gated_pipeline_status
            == "FAILED"
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
    print("V10.5 VALIDATION CHECKS")
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
            "V10.5 Risk-Gated Pipeline Test가 실패했습니다."
        )

    print()
    print(
        "V10.5 paper trading risk-gated pipeline test "
        "completed successfully."
    )
    print(
        "SAFE, WARNING, PAUSED, BLOCKED 및 FAILED "
        "Risk Gate 처리가 정상적으로 검증되었습니다."
    )
    print(
        "차단 상태에서는 V10.2 Daily Pipeline이 "
        "호출되지 않았습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
