import json
import tempfile
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import patch

import backtest.paper_trading_risk_gated_batch as gated_batch_module
from backtest.paper_trading_batch_pipeline import (
    PaperTradingBatchPipelinePolicy,
    PaperTradingBatchPipelineResult,
)
from backtest.paper_trading_risk_gated_batch import (
    VALID_GATED_BATCH_STATUSES,
    PaperTradingRiskGatedBatchPolicy,
    load_latest_paper_trading_risk_gated_batch,
    normalize_requested_symbols,
    run_paper_trading_risk_gated_batch,
    save_paper_trading_risk_gated_batch,
    validate_batch_result_safety,
    validate_gated_batch_policy,
)
from backtest.paper_trading_risk_monitor import (
    PaperTradingRiskMonitorPolicy,
    PaperTradingRiskMonitorResult,
)


LINE_LENGTH = 140
SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
]
ACCOUNT_CASH = 10_000.0


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.6 "
        "RISK-GATED MULTI-SYMBOL BATCH TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<80}: {value}")


def create_empty_dataclass_instance(
    dataclass_type,
):
    """
    기존 Result Dataclass의 모든 필드를 None으로 초기화합니다.
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
    실제 V10.1 파일 없이 V10.4 결과를 흉내 냅니다.
    """

    result = create_empty_dataclass_instance(
        PaperTradingRiskMonitorResult
    )

    result.version = "V10.4"
    result.created_at = "2026-07-27T12:30:00"
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

    result.current_equity = ACCOUNT_CASH
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


def create_fake_batch_result(
    *,
    batch_status: str = "COMPLETED",
    completed_count: int = 3,
    blocked_count: int = 0,
    failed_count: int = 0,
    skipped_count: int = 0,
    all_checks_passed: bool = True,
) -> PaperTradingBatchPipelineResult:
    """
    실제 종목 Pipeline 없이 V10.3 Batch 결과를 흉내 냅니다.
    """

    result = create_empty_dataclass_instance(
        PaperTradingBatchPipelineResult
    )

    result.version = "V10.3"
    result.created_at = "2026-07-27T12:31:00"
    result.batch_id = (
        f"batch-{batch_status.lower()}"
    )
    result.batch_status = batch_status
    result.batch_status_label = batch_status

    result.requested_symbols = list(SYMBOLS)
    result.normalized_symbols = list(SYMBOLS)
    result.duplicate_symbols = []
    result.requested_symbol_count = len(
        SYMBOLS
    )
    result.unique_symbol_count = len(
        SYMBOLS
    )

    result.completed_symbol_count = (
        completed_count
    )
    result.blocked_symbol_count = (
        blocked_count
    )
    result.failed_symbol_count = (
        failed_count
    )
    result.skipped_symbol_count = (
        skipped_count
    )

    result.success_rate_percent = round(
        completed_count
        / len(SYMBOLS)
        * 100.0,
        4,
    )

    result.initial_cash = ACCOUNT_CASH
    result.final_cash_balance = 8_000.0
    result.final_market_value = 2_100.0
    result.final_equity = 10_100.0
    result.batch_equity_change = 100.0
    result.batch_equity_change_percent = 1.0

    result.policy_checks_passed = True
    result.symbol_checks_passed = True
    result.result_checks_passed = True
    result.all_required_symbols_passed = (
        completed_count == len(SYMBOLS)
    )
    result.all_checks_passed = (
        all_checks_passed
    )

    result.execution_blocked = True
    result.broker_api_called = False
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    result.batch_policy = (
        PaperTradingBatchPipelinePolicy(
            save_daily_pipeline_outputs=False,
            save_batch_output=False,
        )
    )
    result.symbol_results = {}
    result.reasons = [
        f"테스트 Batch Status는 {batch_status}입니다."
    ]
    result.warnings = [
        "실제 주문을 생성하지 않습니다."
    ]
    result.next_actions = [
        "Batch 결과를 확인합니다."
    ]
    result.report_path = None
    result.latest_path = None

    return result


class BatchRunnerRecorder:
    """
    V10.3 Batch 호출 횟수와 전달 인자를 기록합니다.
    """

    def __init__(
        self,
        result: PaperTradingBatchPipelineResult,
    ) -> None:
        self.result = result
        self.call_count = 0
        self.last_arguments = {}

    def __call__(self, **kwargs):
        self.call_count += 1
        self.last_arguments = dict(kwargs)
        return self.result


def validate_policy() -> (
    PaperTradingRiskGatedBatchPolicy
):
    policy = PaperTradingRiskGatedBatchPolicy()

    valid, errors = (
        validate_gated_batch_policy(
            policy
        )
    )

    if not valid or errors:
        raise RuntimeError(
            f"기본 V10.6 Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "require_risk_checks",
        "allow_safe",
        "allow_warning",
        "block_paused",
        "block_blocked",
        "block_failed",
        "require_batch_checks",
        "allow_partial_batch",
        "save_output",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "V10.6 Policy Dictionary 구조가 다릅니다."
        )

    gate_policy = policy.to_gate_policy()

    if (
        gate_policy.allow_warning
        != policy.allow_warning
    ):
        raise RuntimeError(
            "공통 Risk Gate Policy 변환이 실패했습니다."
        )

    immutable = False

    try:
        policy.allow_partial_batch = False
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "V10.6 Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingRiskGatedBatchPolicy(
            require_risk_checks=False,
        ),
        PaperTradingRiskGatedBatchPolicy(
            allow_safe=False,
        ),
        PaperTradingRiskGatedBatchPolicy(
            block_paused=False,
        ),
        PaperTradingRiskGatedBatchPolicy(
            block_blocked=False,
        ),
        PaperTradingRiskGatedBatchPolicy(
            block_failed=False,
        ),
        PaperTradingRiskGatedBatchPolicy(
            require_batch_checks=False,
        ),
        PaperTradingRiskGatedBatchPolicy(
            allow_partial_batch="yes",
        ),
        PaperTradingRiskGatedBatchPolicy(
            paper_only=False,
        ),
        PaperTradingRiskGatedBatchPolicy(
            live_execution_disabled=False,
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_gated_batch_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_helpers() -> None:
    normalized = normalize_requested_symbols(
        [
            " aapl ",
            "msft",
            "NVDA",
        ]
    )

    if normalized != SYMBOLS:
        raise RuntimeError(
            "요청 Symbol 정규화가 실패했습니다."
        )

    invalid_inputs = [
        [],
        (),
        ["AAPL", ""],
        "AAPL",
    ]

    for invalid_input in invalid_inputs:
        rejected = False

        try:
            normalize_requested_symbols(
                invalid_input
            )
        except (TypeError, ValueError):
            rejected = True

        if not rejected:
            raise RuntimeError(
                f"Invalid Symbols가 거부되지 않았습니다: {invalid_input!r}"
            )

    batch_result = create_fake_batch_result()

    safe, safety_errors = (
        validate_batch_result_safety(
            batch_result
        )
    )

    if not safe or safety_errors:
        raise RuntimeError(
            f"정상 Batch Result가 거부되었습니다: {safety_errors}"
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
    policy: PaperTradingRiskGatedBatchPolicy,
):
    runner = BatchRunnerRecorder(
        create_fake_batch_result()
    )

    result = run_paper_trading_risk_gated_batch(
        symbols=[
            " aapl ",
            "msft",
            "nvda",
        ],
        account_cash=ACCOUNT_CASH,
        gated_batch_policy=policy,
        risk_monitor_result=(
            create_fake_risk_result()
        ),
        batch_runner=runner,
    )

    if result.version != "V10.6":
        raise RuntimeError(
            "결과 버전이 V10.6이 아닙니다."
        )

    if (
        result.gated_batch_status
        != "COMPLETED"
    ):
        raise RuntimeError(
            "SAFE 결과가 COMPLETED가 아닙니다."
        )

    if runner.call_count != 1:
        raise RuntimeError(
            "SAFE 상태에서 V10.3 Batch가 정확히 한 번 호출되지 않았습니다."
        )

    if (
        runner.last_arguments.get("symbols")
        != SYMBOLS
    ):
        raise RuntimeError(
            "정규화된 Symbol 목록이 Batch에 전달되지 않았습니다."
        )

    if not result.batch_executed:
        raise RuntimeError(
            "SAFE 상태에서 Batch가 실행되지 않았습니다."
        )

    if result.batch_skipped:
        raise RuntimeError(
            "SAFE 상태에서 Batch가 Skipped 처리되었습니다."
        )

    if not result.paper_batch_allowed:
        raise RuntimeError(
            "SAFE 상태에서 Paper Batch가 허용되지 않았습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "SAFE 결과의 All Checks가 실패했습니다."
        )

    if result.completed_symbol_count != 3:
        raise RuntimeError(
            "완료 종목 수가 다릅니다."
        )

    assert_execution_safety(result)

    return result


def validate_warning_execution(
    policy: PaperTradingRiskGatedBatchPolicy,
):
    runner = BatchRunnerRecorder(
        create_fake_batch_result()
    )

    risk_result = create_fake_risk_result(
        risk_status="WARNING",
        risk_action="WARNING",
        paper_trading_allowed=True,
    )

    result = run_paper_trading_risk_gated_batch(
        symbols=SYMBOLS,
        account_cash=ACCOUNT_CASH,
        gated_batch_policy=policy,
        risk_monitor_result=risk_result,
        batch_runner=runner,
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
            "허용된 WARNING에서 Batch가 실행되지 않았습니다."
        )

    strict_policy = (
        PaperTradingRiskGatedBatchPolicy(
            allow_warning=False,
        )
    )
    strict_runner = BatchRunnerRecorder(
        create_fake_batch_result()
    )

    strict_result = (
        run_paper_trading_risk_gated_batch(
            symbols=SYMBOLS,
            account_cash=ACCOUNT_CASH,
            gated_batch_policy=strict_policy,
            risk_monitor_result=risk_result,
            batch_runner=strict_runner,
        )
    )

    if (
        strict_result.gated_batch_status
        != "BLOCKED"
    ):
        raise RuntimeError(
            "금지된 WARNING이 BLOCKED가 아닙니다."
        )

    if strict_runner.call_count != 0:
        raise RuntimeError(
            "금지된 WARNING에서 Batch가 호출되었습니다."
        )

    if strict_result.skipped_symbol_count != 3:
        raise RuntimeError(
            "금지된 WARNING에서 모든 종목이 Skipped 처리되지 않았습니다."
        )

    assert_execution_safety(result)
    assert_execution_safety(strict_result)

    return result


def validate_risk_block(
    policy: PaperTradingRiskGatedBatchPolicy,
    risk_status: str,
    risk_action: str,
):
    runner = BatchRunnerRecorder(
        create_fake_batch_result()
    )

    result = run_paper_trading_risk_gated_batch(
        symbols=SYMBOLS,
        account_cash=ACCOUNT_CASH,
        gated_batch_policy=policy,
        risk_monitor_result=(
            create_fake_risk_result(
                risk_status=risk_status,
                risk_action=risk_action,
                paper_trading_allowed=False,
            )
        ),
        batch_runner=runner,
    )

    if (
        result.gated_batch_status
        != "BLOCKED"
    ):
        raise RuntimeError(
            f"{risk_status} 결과가 BLOCKED가 아닙니다."
        )

    if runner.call_count != 0:
        raise RuntimeError(
            f"{risk_status} 상태에서 V10.3 Batch가 호출되었습니다."
        )

    if result.batch_executed:
        raise RuntimeError(
            f"{risk_status} 상태에서 Batch Executed가 True입니다."
        )

    if not result.batch_skipped:
        raise RuntimeError(
            f"{risk_status} 상태에서 Batch가 Skipped가 아닙니다."
        )

    if result.skipped_symbol_count != len(
        SYMBOLS
    ):
        raise RuntimeError(
            f"{risk_status} 상태에서 모든 종목이 Skipped 처리되지 않았습니다."
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
    policy: PaperTradingRiskGatedBatchPolicy,
):
    runner = BatchRunnerRecorder(
        create_fake_batch_result()
    )

    result = run_paper_trading_risk_gated_batch(
        symbols=SYMBOLS,
        account_cash=ACCOUNT_CASH,
        gated_batch_policy=policy,
        risk_monitor_result=(
            create_fake_risk_result(
                risk_status="FAILED",
                risk_action="BLOCK",
                paper_trading_allowed=False,
                all_checks_passed=False,
            )
        ),
        batch_runner=runner,
    )

    if (
        result.gated_batch_status
        != "FAILED"
    ):
        raise RuntimeError(
            "FAILED Risk가 V10.6 FAILED로 처리되지 않았습니다."
        )

    if runner.call_count != 0:
        raise RuntimeError(
            "FAILED Risk에서 Batch가 호출되었습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "FAILED Risk 결과의 All Checks가 True입니다."
        )

    assert_execution_safety(result)

    return result


def validate_partial_batch(
    policy: PaperTradingRiskGatedBatchPolicy,
):
    partial_batch = create_fake_batch_result(
        batch_status="PARTIAL",
        completed_count=2,
        failed_count=1,
        all_checks_passed=True,
    )
    runner = BatchRunnerRecorder(
        partial_batch
    )

    result = run_paper_trading_risk_gated_batch(
        symbols=SYMBOLS,
        account_cash=ACCOUNT_CASH,
        gated_batch_policy=policy,
        risk_monitor_result=(
            create_fake_risk_result()
        ),
        batch_runner=runner,
    )

    if result.gated_batch_status != "PARTIAL":
        raise RuntimeError(
            "허용된 Partial Batch가 PARTIAL로 처리되지 않았습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "허용된 Partial Batch의 All Checks가 실패했습니다."
        )

    strict_policy = (
        PaperTradingRiskGatedBatchPolicy(
            allow_partial_batch=False,
        )
    )
    strict_runner = BatchRunnerRecorder(
        partial_batch
    )

    strict_result = (
        run_paper_trading_risk_gated_batch(
            symbols=SYMBOLS,
            account_cash=ACCOUNT_CASH,
            gated_batch_policy=strict_policy,
            risk_monitor_result=(
                create_fake_risk_result()
            ),
            batch_runner=strict_runner,
        )
    )

    if (
        strict_result.gated_batch_status
        != "FAILED"
    ):
        raise RuntimeError(
            "금지된 Partial Batch가 FAILED가 아닙니다."
        )

    assert_execution_safety(result)
    assert_execution_safety(strict_result)

    return result


def validate_batch_failure(
    policy: PaperTradingRiskGatedBatchPolicy,
):
    runner = BatchRunnerRecorder(
        create_fake_batch_result(
            batch_status="FAILED",
            completed_count=0,
            failed_count=3,
            all_checks_passed=False,
        )
    )

    result = run_paper_trading_risk_gated_batch(
        symbols=SYMBOLS,
        account_cash=ACCOUNT_CASH,
        gated_batch_policy=policy,
        risk_monitor_result=(
            create_fake_risk_result()
        ),
        batch_runner=runner,
    )

    if (
        result.gated_batch_status
        != "FAILED"
    ):
        raise RuntimeError(
            "V10.3 Batch 실패가 V10.6 FAILED로 전파되지 않았습니다."
        )

    if runner.call_count != 1:
        raise RuntimeError(
            "Batch Failure 테스트 호출 횟수가 다릅니다."
        )

    if result.batch_checks_passed:
        raise RuntimeError(
            "실패한 Batch Checks가 True입니다."
        )

    assert_execution_safety(result)

    return result


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output_directory = (
            Path(temporary)
            / "risk_gated_batch"
        )

        with patch.object(
            gated_batch_module,
            (
                "PAPER_RISK_GATED_BATCH_"
                "OUTPUT_DIRECTORY"
            ),
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_risk_gated_batch(
                    result
                )
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V10.6 Report가 저장되지 않았습니다."
                )

            if not latest_path.exists():
                raise RuntimeError(
                    "V10.6 Latest가 저장되지 않았습니다."
                )

            loaded = (
                load_latest_paper_trading_risk_gated_batch()
            )

            if loaded.get("version") != "V10.6":
                raise RuntimeError(
                    "저장된 버전이 V10.6이 아닙니다."
                )

            if (
                loaded.get("gated_batch_id")
                != result.gated_batch_id
            ):
                raise RuntimeError(
                    "저장된 Gated Batch ID가 다릅니다."
                )

            if (
                loaded.get(
                    "gated_batch_status"
                )
                != "COMPLETED"
            ):
                raise RuntimeError(
                    "저장된 Gated Batch Status가 다릅니다."
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
                raw_payload.get("batch_result"),
                dict,
            ):
                raise RuntimeError(
                    "저장된 Batch Result 형식이 다릅니다."
                )


def validate_result_contract(results: list) -> None:
    for result in results:
        if (
            result.gated_batch_status
            not in VALID_GATED_BATCH_STATUSES
        ):
            raise RuntimeError(
                "허용되지 않은 Gated Batch Status입니다."
            )

        if not result.gated_batch_id:
            raise RuntimeError(
                "Gated Batch ID가 비어 있습니다."
            )

        if (
            result.requested_symbols
            != SYMBOLS
        ):
            raise RuntimeError(
                "Result Symbol 목록이 다릅니다."
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

    safe_result = validate_safe_execution(
        policy
    )
    warning_result = (
        validate_warning_execution(
            policy
        )
    )
    paused_result = validate_risk_block(
        policy=policy,
        risk_status="PAUSED",
        risk_action="PAUSE",
    )
    blocked_result = validate_risk_block(
        policy=policy,
        risk_status="BLOCKED",
        risk_action="BLOCK",
    )
    failed_risk_result = validate_failed_risk(
        policy
    )
    partial_result = validate_partial_batch(
        policy
    )
    failed_batch_result = (
        validate_batch_failure(
            policy
        )
    )

    results = [
        safe_result,
        warning_result,
        paused_result,
        blocked_result,
        failed_risk_result,
        partial_result,
        failed_batch_result,
    ]

    validate_result_contract(results)
    validate_save_and_load(safe_result)

    checks = {
        "Version is V10.6": (
            safe_result.version == "V10.6"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "SAFE gate executed batch": (
            safe_result.batch_executed
        ),
        "Allowed WARNING executed batch": (
            warning_result.batch_executed
        ),
        "PAUSED skipped entire batch": (
            paused_result.batch_skipped
        ),
        "BLOCKED skipped entire batch": (
            blocked_result.batch_skipped
        ),
        "PAUSED skipped all symbols": (
            paused_result.skipped_symbol_count
            == len(SYMBOLS)
        ),
        "BLOCKED skipped all symbols": (
            blocked_result.skipped_symbol_count
            == len(SYMBOLS)
        ),
        "FAILED risk skipped batch": (
            failed_risk_result.batch_skipped
        ),
        "Allowed partial batch passed": (
            partial_result.gated_batch_status
            == "PARTIAL"
        ),
        "Batch failure propagated": (
            failed_batch_result
            .gated_batch_status
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
    print("V10.6 VALIDATION CHECKS")
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
            "V10.6 Risk-Gated Batch Test가 실패했습니다."
        )

    print()
    print(
        "V10.6 paper trading risk-gated batch test "
        "completed successfully."
    )
    print(
        "SAFE, WARNING, PAUSED, BLOCKED 및 FAILED "
        "Risk Gate 처리가 정상적으로 검증되었습니다."
    )
    print(
        "차단 상태에서는 V10.3 Batch와 모든 종목 Pipeline이 "
        "호출되지 않았습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
