import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import backtest.paper_trading_risk_monitor as risk_monitor_module
from backtest.paper_trading_risk_monitor import (
    VALID_RISK_ACTIONS,
    VALID_RISK_STATUSES,
    PaperTradingRiskMonitorPolicy,
    calculate_consecutive_loss_count,
    create_lower_limit_rule,
    create_upper_limit_rule,
    determine_upper_limit_action,
    load_latest_paper_trading_risk_monitor,
    run_paper_trading_risk_monitor,
    save_paper_trading_risk_monitor,
    select_strongest_action,
    validate_performance_payload,
    validate_risk_monitor_policy,
)


LINE_LENGTH = 140


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.4 "
        "PAPER TRADING RISK MONITOR TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<74}: {value}")


def create_performance_payload(
    *,
    current_equity: float = 10_000.0,
    cash_balance: float = 8_000.0,
    period_profit_loss: float = 100.0,
    period_return_percent: float = 1.0,
    cumulative_profit_loss: float = 100.0,
    cumulative_return_percent: float = 1.0,
    current_drawdown_percent: float = 0.0,
    maximum_drawdown_percent: float = 2.0,
    total_commission: float = 10.0,
    history_profit_losses: list[float] | None = None,
    performance_status: str = "TRACKED",
    all_checks_passed: bool = True,
) -> dict:
    """
    실제 시장이나 Broker 없이 V10.1 Performance 결과를 만듭니다.
    """

    if history_profit_losses is None:
        history_profit_losses = [
            100.0,
            50.0,
            25.0,
        ]

    history = []

    for index, profit_loss in enumerate(
        history_profit_losses,
        start=1,
    ):
        history.append(
            {
                "snapshot_id": f"snapshot-{index}",
                "created_at": (
                    f"2026-07-{20 + index:02d}T12:00:00"
                ),
                "cash_balance": cash_balance,
                "total_market_value": (
                    current_equity - cash_balance
                ),
                "total_equity": current_equity,
                "period_profit_loss": profit_loss,
            }
        )

    latest_snapshot = dict(history[-1])
    latest_snapshot["cash_balance"] = cash_balance
    latest_snapshot["total_market_value"] = (
        current_equity - cash_balance
    )
    latest_snapshot["total_equity"] = current_equity

    return {
        "version": "V10.1",
        "created_at": "2026-07-27T12:00:00",
        "performance_id": "performance-test-001",
        "portfolio_id": "portfolio-test-001",
        "source_valuation_id": "valuation-test-001",
        "performance_status": performance_status,
        "current_equity": current_equity,
        "period_profit_loss": period_profit_loss,
        "period_return_percent": period_return_percent,
        "cumulative_profit_loss": cumulative_profit_loss,
        "cumulative_return_percent": (
            cumulative_return_percent
        ),
        "current_drawdown_amount": (
            current_equity
            * current_drawdown_percent
            / 100.0
        ),
        "current_drawdown_percent": (
            current_drawdown_percent
        ),
        "maximum_drawdown_percent": (
            maximum_drawdown_percent
        ),
        "performance_period_count": len(history),
        "total_commission": total_commission,
        "latest_snapshot": latest_snapshot,
        "performance_history": history,
        "all_checks_passed": all_checks_passed,
    }


def validate_policy() -> PaperTradingRiskMonitorPolicy:
    policy = PaperTradingRiskMonitorPolicy()

    valid, errors = validate_risk_monitor_policy(policy)

    if not valid or errors:
        raise RuntimeError(
            f"기본 Risk Monitor Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "drawdown_warning_percent",
        "drawdown_pause_percent",
        "drawdown_block_percent",
        "period_loss_warning_percent",
        "period_loss_pause_percent",
        "period_loss_block_percent",
        "cumulative_loss_warning_percent",
        "cumulative_loss_pause_percent",
        "cumulative_loss_block_percent",
        "consecutive_loss_warning_count",
        "consecutive_loss_pause_count",
        "consecutive_loss_block_count",
        "minimum_cash_balance",
        "minimum_total_equity",
        "maximum_commission_to_equity_percent",
        "minimum_performance_periods",
        "allow_warning_trades",
        "require_valid_performance",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "Risk Monitor Policy Dictionary 구조가 다릅니다."
        )

    immutable = False

    try:
        policy.drawdown_warning_percent = 99.0
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "Risk Monitor Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingRiskMonitorPolicy(
            drawdown_warning_percent=10.0,
            drawdown_pause_percent=5.0,
        ),
        PaperTradingRiskMonitorPolicy(
            period_loss_warning_percent=-1.0,
        ),
        PaperTradingRiskMonitorPolicy(
            consecutive_loss_warning_count=3,
            consecutive_loss_pause_count=2,
        ),
        PaperTradingRiskMonitorPolicy(
            minimum_cash_balance=-1.0,
        ),
        PaperTradingRiskMonitorPolicy(
            minimum_performance_periods=-1,
        ),
        PaperTradingRiskMonitorPolicy(
            allow_warning_trades="yes",
        ),
        PaperTradingRiskMonitorPolicy(
            paper_only=False,
        ),
        PaperTradingRiskMonitorPolicy(
            live_execution_disabled=False,
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_risk_monitor_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_helpers(
    policy: PaperTradingRiskMonitorPolicy,
) -> None:
    expected_actions = {
        0.0: "ALLOW",
        5.0: "WARNING",
        10.0: "PAUSE",
        20.0: "BLOCK",
    }

    for observed_value, expected_action in (
        expected_actions.items()
    ):
        actual_action = determine_upper_limit_action(
            observed_value=observed_value,
            warning_threshold=5.0,
            pause_threshold=10.0,
            block_threshold=20.0,
        )

        if actual_action != expected_action:
            raise RuntimeError(
                "Upper Limit Action 계산이 다릅니다. "
                f"Value={observed_value}, "
                f"Actual={actual_action}, "
                f"Expected={expected_action}"
            )

    warning_rule = create_upper_limit_rule(
        rule_name="TEST_WARNING",
        rule_label="테스트 경고",
        observed_value=6.0,
        observed_unit="%",
        warning_threshold=5.0,
        pause_threshold=10.0,
        block_threshold=20.0,
    )

    block_rule = create_lower_limit_rule(
        rule_name="TEST_MINIMUM",
        rule_label="테스트 최소값",
        observed_value=50.0,
        observed_unit="$",
        block_threshold=100.0,
    )

    if warning_rule.risk_action != "WARNING":
        raise RuntimeError(
            "Upper Limit Warning Rule 생성이 실패했습니다."
        )

    if block_rule.risk_action != "BLOCK":
        raise RuntimeError(
            "Lower Limit Block Rule 생성이 실패했습니다."
        )

    strongest = select_strongest_action(
        {
            "WARNING": warning_rule,
            "BLOCK": block_rule,
        }
    )

    if strongest != "BLOCK":
        raise RuntimeError(
            "가장 강한 Risk Action 선택이 실패했습니다."
        )

    loss_count, loss_errors = (
        calculate_consecutive_loss_count(
            [
                {"period_profit_loss": 100.0},
                {"period_profit_loss": -10.0},
                {"period_profit_loss": -20.0},
                {"period_profit_loss": -30.0},
            ]
        )
    )

    if loss_count != 3 or loss_errors:
        raise RuntimeError(
            "연속 손실 기간 계산이 실패했습니다."
        )

    payload_valid, payload_errors = (
        validate_performance_payload(
            create_performance_payload(),
            policy,
        )
    )

    if not payload_valid or payload_errors:
        raise RuntimeError(
            "정상 Performance Payload가 거부되었습니다."
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
        "live_order_created": result.live_order_created,
        "live_execution_authorized": (
            result.live_execution_authorized
        ),
    }

    if any(unsafe_values.values()):
        raise RuntimeError(
            f"실거래 안전 검사가 실패했습니다: {unsafe_values}"
        )


def validate_safe_result(
    policy: PaperTradingRiskMonitorPolicy,
):
    result = run_paper_trading_risk_monitor(
        performance_result=(
            create_performance_payload()
        ),
        monitor_policy=policy,
    )

    if result.version != "V10.4":
        raise RuntimeError(
            "Risk Monitor 버전이 V10.4가 아닙니다."
        )

    if result.risk_status != "SAFE":
        raise RuntimeError(
            f"정상 상태가 SAFE가 아닙니다: {result.risk_status}"
        )

    if result.risk_action != "ALLOW":
        raise RuntimeError(
            "정상 상태의 Risk Action이 ALLOW가 아닙니다."
        )

    if not result.paper_trading_allowed:
        raise RuntimeError(
            "정상 상태에서 Paper Trading이 허용되지 않았습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 상태의 All Checks가 실패했습니다."
        )

    if set(result.rule_results) != {
        "CURRENT_DRAWDOWN",
        "PERIOD_LOSS",
        "CUMULATIVE_LOSS",
        "CONSECUTIVE_LOSSES",
        "MINIMUM_CASH",
        "MINIMUM_EQUITY",
        "COMMISSION_RATIO",
    }:
        raise RuntimeError(
            "Risk Rule 목록이 예상과 다릅니다."
        )

    assert_execution_safety(result)

    return result


def validate_warning_result(
    policy: PaperTradingRiskMonitorPolicy,
):
    result = run_paper_trading_risk_monitor(
        performance_result=(
            create_performance_payload(
                current_drawdown_percent=6.0,
            )
        ),
        monitor_policy=policy,
    )

    if result.risk_status != "WARNING":
        raise RuntimeError(
            "Drawdown Warning 상태가 생성되지 않았습니다."
        )

    if result.risk_action != "WARNING":
        raise RuntimeError(
            "Warning의 Risk Action이 다릅니다."
        )

    if not result.paper_trading_allowed:
        raise RuntimeError(
            "기본 Policy의 Warning 거래가 허용되지 않았습니다."
        )

    if not result.paper_trading_warning:
        raise RuntimeError(
            "Paper Trading Warning 표시가 False입니다."
        )

    if (
        result.rule_results[
            "CURRENT_DRAWDOWN"
        ].risk_action
        != "WARNING"
    ):
        raise RuntimeError(
            "Drawdown Rule이 WARNING이 아닙니다."
        )

    assert_execution_safety(result)

    strict_policy = PaperTradingRiskMonitorPolicy(
        allow_warning_trades=False,
    )

    strict_result = run_paper_trading_risk_monitor(
        performance_result=(
            create_performance_payload(
                current_drawdown_percent=6.0,
            )
        ),
        monitor_policy=strict_policy,
    )

    if strict_result.risk_action != "PAUSE":
        raise RuntimeError(
            "Warning 거래 금지 Policy가 PAUSE로 변경되지 않았습니다."
        )

    if strict_result.paper_trading_allowed:
        raise RuntimeError(
            "Warning 거래 금지 Policy에서 거래가 허용되었습니다."
        )

    assert_execution_safety(strict_result)

    return result


def validate_pause_result(
    policy: PaperTradingRiskMonitorPolicy,
):
    result = run_paper_trading_risk_monitor(
        performance_result=(
            create_performance_payload(
                current_drawdown_percent=12.0,
            )
        ),
        monitor_policy=policy,
    )

    if result.risk_status != "PAUSED":
        raise RuntimeError(
            "Drawdown Pause 상태가 생성되지 않았습니다."
        )

    if result.risk_action != "PAUSE":
        raise RuntimeError(
            "Pause의 Risk Action이 다릅니다."
        )

    if result.paper_trading_allowed:
        raise RuntimeError(
            "Pause 상태에서 Paper Trading이 허용되었습니다."
        )

    if not result.paper_trading_paused:
        raise RuntimeError(
            "Paper Trading Paused 표시가 False입니다."
        )

    assert_execution_safety(result)

    return result


def validate_block_result(
    policy: PaperTradingRiskMonitorPolicy,
):
    result = run_paper_trading_risk_monitor(
        performance_result=(
            create_performance_payload(
                current_drawdown_percent=22.0,
            )
        ),
        monitor_policy=policy,
    )

    if result.risk_status != "BLOCKED":
        raise RuntimeError(
            "Drawdown Block 상태가 생성되지 않았습니다."
        )

    if result.risk_action != "BLOCK":
        raise RuntimeError(
            "Block의 Risk Action이 다릅니다."
        )

    if result.paper_trading_allowed:
        raise RuntimeError(
            "Block 상태에서 Paper Trading이 허용되었습니다."
        )

    if not result.paper_trading_blocked:
        raise RuntimeError(
            "Paper Trading Blocked 표시가 False입니다."
        )

    if result.block_rule_count < 1:
        raise RuntimeError(
            "Block Rule Count가 기록되지 않았습니다."
        )

    assert_execution_safety(result)

    low_cash_result = run_paper_trading_risk_monitor(
        performance_result=(
            create_performance_payload(
                cash_balance=50.0,
            )
        ),
        monitor_policy=policy,
    )

    if (
        low_cash_result.rule_results[
            "MINIMUM_CASH"
        ].risk_action
        != "BLOCK"
    ):
        raise RuntimeError(
            "최소 현금 Rule이 거래를 차단하지 않았습니다."
        )

    assert_execution_safety(low_cash_result)

    return result


def validate_failed_result(
    policy: PaperTradingRiskMonitorPolicy,
):
    invalid_payload = create_performance_payload()
    invalid_payload["version"] = "V10.0"
    invalid_payload["all_checks_passed"] = False

    result = run_paper_trading_risk_monitor(
        performance_result=invalid_payload,
        monitor_policy=policy,
    )

    if result.risk_status != "FAILED":
        raise RuntimeError(
            "Invalid Performance가 FAILED로 처리되지 않았습니다."
        )

    if result.risk_action != "BLOCK":
        raise RuntimeError(
            "Invalid Performance가 차단되지 않았습니다."
        )

    if result.source_valid:
        raise RuntimeError(
            "Invalid Performance의 Source Valid가 True입니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "Invalid Performance의 All Checks가 True입니다."
        )

    if result.paper_trading_allowed:
        raise RuntimeError(
            "Invalid Performance에서 거래가 허용되었습니다."
        )

    assert_execution_safety(result)

    return result


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output_directory = (
            Path(temporary)
            / "paper_risk_monitor"
        )

        with patch.object(
            risk_monitor_module,
            "PAPER_RISK_MONITOR_OUTPUT_DIRECTORY",
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_risk_monitor(
                    result
                )
            )

            if not report_path.exists():
                raise RuntimeError(
                    "Risk Monitor Report가 저장되지 않았습니다."
                )

            if not latest_path.exists():
                raise RuntimeError(
                    "Risk Monitor Latest가 저장되지 않았습니다."
                )

            loaded = (
                load_latest_paper_trading_risk_monitor()
            )

            if loaded.get("version") != "V10.4":
                raise RuntimeError(
                    "저장된 Risk Monitor 버전이 다릅니다."
                )

            if (
                loaded.get("monitor_id")
                != result.monitor_id
            ):
                raise RuntimeError(
                    "저장된 Monitor ID가 다릅니다."
                )

            if loaded.get("risk_status") != "SAFE":
                raise RuntimeError(
                    "저장된 Risk Status가 다릅니다."
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

            if not result.report_path:
                raise RuntimeError(
                    "Result에 Report Path가 기록되지 않았습니다."
                )

            if not result.latest_path:
                raise RuntimeError(
                    "Result에 Latest Path가 기록되지 않았습니다."
                )


def validate_result_contract(results: list) -> None:
    for result in results:
        if result.risk_status not in VALID_RISK_STATUSES:
            raise RuntimeError(
                f"허용되지 않은 Risk Status입니다: {result.risk_status}"
            )

        if result.risk_action not in VALID_RISK_ACTIONS:
            raise RuntimeError(
                f"허용되지 않은 Risk Action입니다: {result.risk_action}"
            )

        if not result.monitor_id:
            raise RuntimeError(
                "Monitor ID가 비어 있습니다."
            )

        if not result.portfolio_id:
            raise RuntimeError(
                "Portfolio ID가 비어 있습니다."
            )

        if not result.source_performance_id:
            raise RuntimeError(
                "Source Performance ID가 비어 있습니다."
            )

        if not result.reasons:
            raise RuntimeError(
                "Risk Monitor Reasons가 비어 있습니다."
            )

        if not result.warnings:
            raise RuntimeError(
                "Risk Monitor Warnings가 비어 있습니다."
            )

        if not result.next_actions:
            raise RuntimeError(
                "Risk Monitor Next Actions가 비어 있습니다."
            )

        assert_execution_safety(result)


def main() -> None:
    print_header()

    policy = validate_policy()
    validate_helpers(policy)

    safe_result = validate_safe_result(policy)
    warning_result = validate_warning_result(policy)
    pause_result = validate_pause_result(policy)
    block_result = validate_block_result(policy)
    failed_result = validate_failed_result(policy)

    results = [
        safe_result,
        warning_result,
        pause_result,
        block_result,
        failed_result,
    ]

    validate_result_contract(results)
    validate_save_and_load(safe_result)

    checks = {
        "Version is V10.4": (
            safe_result.version == "V10.4"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Safe status is SAFE": (
            safe_result.risk_status == "SAFE"
        ),
        "Safe action is ALLOW": (
            safe_result.risk_action == "ALLOW"
        ),
        "Warning status is WARNING": (
            warning_result.risk_status == "WARNING"
        ),
        "Pause status is PAUSED": (
            pause_result.risk_status == "PAUSED"
        ),
        "Block status is BLOCKED": (
            block_result.risk_status == "BLOCKED"
        ),
        "Invalid source status is FAILED": (
            failed_result.risk_status == "FAILED"
        ),
        "Risk rules were evaluated": (
            len(safe_result.rule_results) == 7
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
    print("V10.4 VALIDATION CHECKS")
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
            "V10.4 Risk Monitor Test가 실패했습니다."
        )

    print()
    print(
        "V10.4 paper trading risk monitor test "
        "completed successfully."
    )
    print(
        "정상, 경고, 일시정지, 차단 및 입력 오류 처리가 "
        "정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
