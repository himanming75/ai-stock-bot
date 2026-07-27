import json
import tempfile
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import backtest.paper_trading_run_ledger as ledger_module
from backtest.paper_trading_risk_gated_batch import (
    PaperTradingRiskGatedBatchResult,
)
from backtest.paper_trading_risk_gated_pipeline import (
    PaperTradingRiskGateDecision,
    PaperTradingRiskGatedPipelineResult,
)
from backtest.paper_trading_run_ledger import (
    VALID_LEDGER_STATUSES,
    PaperTradingRunLedgerPolicy,
    build_ledger_state,
    empty_ledger_state,
    ledger_state_from_dict,
    load_latest_paper_trading_run_ledger,
    run_paper_trading_run_ledger,
    save_paper_trading_run_ledger,
    validate_ledger_policy,
    validate_ledger_state,
    validate_source_safety,
)


LINE_LENGTH = 140
SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
]


def print_header() -> None:
    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.7 "
        "PAPER TRADING RUN LEDGER TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(name: str, value: bool) -> None:
    print(f"{name:<82}: {value}")


def create_empty_dataclass_instance(
    dataclass_type,
):
    """
    기존 Result Dataclass의 필드를 테스트용으로 초기화합니다.
    """

    instance = object.__new__(dataclass_type)

    for item in fields(dataclass_type):
        setattr(instance, item.name, None)

    return instance


def create_gate_decision(
    *,
    risk_status: str = "SAFE",
    risk_action: str = "ALLOW",
    gate_status: str = "PASSED",
    gate_passed: bool = True,
) -> PaperTradingRiskGateDecision:
    return PaperTradingRiskGateDecision(
        gate_status=gate_status,
        gate_status_label=gate_status,
        risk_status=risk_status,
        risk_action=risk_action,
        gate_passed=gate_passed,
        pipeline_execution_allowed=gate_passed,
        checks_passed=True,
        reasons=[
            "테스트 Risk Gate Decision입니다."
        ],
        warnings=[],
    )


def create_fake_daily_source(
    *,
    run_id: str,
    status: str = "COMPLETED",
    all_checks_passed: bool = True,
    initial_equity: float = 10_000.0,
    final_equity: float = 10_100.0,
    unsafe: bool = False,
) -> PaperTradingRiskGatedPipelineResult:
    """
    실제 Daily Pipeline 실행 없이 V10.5 결과를 만듭니다.
    """

    result = create_empty_dataclass_instance(
        PaperTradingRiskGatedPipelineResult
    )

    result.version = "V10.5"
    result.created_at = "2026-07-27T13:00:00"
    result.gated_pipeline_id = run_id
    result.symbol = "AAPL"
    result.gated_pipeline_status = status
    result.gated_pipeline_status_label = status

    result.risk_monitor_id = (
        f"risk-{run_id}"
    )
    result.daily_pipeline_id = (
        f"daily-{run_id}"
        if status == "COMPLETED"
        else None
    )

    result.risk_monitor_executed = True
    result.risk_gate_evaluated = True
    result.daily_pipeline_requested = (
        status == "COMPLETED"
    )
    result.daily_pipeline_executed = (
        status == "COMPLETED"
    )
    result.daily_pipeline_skipped = (
        status != "COMPLETED"
    )

    result.risk_checks_passed = (
        status != "FAILED"
    )
    result.gate_checks_passed = True
    result.daily_pipeline_checks_passed = (
        status
        in {
            "COMPLETED",
            "BLOCKED",
        }
    )
    result.all_checks_passed = (
        all_checks_passed
    )

    result.paper_trading_allowed = (
        status == "COMPLETED"
    )
    result.risk_gate_blocked = (
        status != "COMPLETED"
    )

    result.execution_blocked = True
    result.broker_api_called = unsafe
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    if status == "COMPLETED":
        result.risk_gate_decision = (
            create_gate_decision()
        )
        result.daily_pipeline_result = (
            SimpleNamespace(
                initial_cash=initial_equity,
                final_equity=final_equity,
            )
        )
    elif status == "BLOCKED":
        result.risk_gate_decision = (
            create_gate_decision(
                risk_status="BLOCKED",
                risk_action="BLOCK",
                gate_status="BLOCKED",
                gate_passed=False,
            )
        )
        result.daily_pipeline_result = None
    else:
        result.risk_gate_decision = (
            create_gate_decision(
                risk_status="FAILED",
                risk_action="BLOCK",
                gate_status="FAILED",
                gate_passed=False,
            )
        )
        result.daily_pipeline_result = None

    result.risk_monitor_result = None
    result.reasons = [
        f"테스트 V10.5 Run {run_id}입니다."
    ]
    result.warnings = [
        "실제 주문을 생성하지 않습니다."
    ]
    result.next_actions = [
        "Ledger 기록을 확인합니다."
    ]
    result.report_path = None
    result.latest_path = None

    return result


def create_fake_batch_source(
    *,
    run_id: str,
    status: str = "PARTIAL",
    all_checks_passed: bool = True,
    completed_count: int = 2,
    failed_count: int = 1,
    skipped_count: int = 0,
    initial_equity: float = 10_000.0,
    final_equity: float = 10_050.0,
) -> PaperTradingRiskGatedBatchResult:
    """
    실제 종목 실행 없이 V10.6 결과를 만듭니다.
    """

    result = create_empty_dataclass_instance(
        PaperTradingRiskGatedBatchResult
    )

    result.version = "V10.6"
    result.created_at = "2026-07-27T13:01:00"
    result.gated_batch_id = run_id
    result.gated_batch_status = status
    result.gated_batch_status_label = status

    result.requested_symbols = list(
        SYMBOLS
    )
    result.requested_symbol_count = len(
        SYMBOLS
    )

    result.risk_monitor_id = (
        f"risk-{run_id}"
    )
    result.batch_id = f"batch-{run_id}"

    result.risk_monitor_executed = True
    result.risk_gate_evaluated = True
    result.batch_requested = True
    result.batch_executed = True
    result.batch_skipped = False

    result.completed_symbol_count = (
        completed_count
    )
    result.blocked_symbol_count = 0
    result.failed_symbol_count = (
        failed_count
    )
    result.skipped_symbol_count = (
        skipped_count
    )

    result.risk_checks_passed = True
    result.gate_checks_passed = True
    result.batch_checks_passed = (
        all_checks_passed
    )
    result.all_checks_passed = (
        all_checks_passed
    )

    result.paper_batch_allowed = True
    result.risk_gate_blocked = False

    result.execution_blocked = True
    result.broker_api_called = False
    result.broker_order_created = False
    result.live_order_created = False
    result.live_execution_authorized = False

    result.risk_gate_decision = (
        create_gate_decision()
    )
    result.risk_monitor_result = None
    result.batch_result = SimpleNamespace(
        initial_cash=initial_equity,
        final_equity=final_equity,
    )

    result.reasons = [
        f"테스트 V10.6 Run {run_id}입니다."
    ]
    result.warnings = [
        "실제 주문을 생성하지 않습니다."
    ]
    result.next_actions = [
        "Ledger 기록을 확인합니다."
    ]
    result.report_path = None
    result.latest_path = None

    return result


def validate_policy() -> (
    PaperTradingRunLedgerPolicy
):
    policy = PaperTradingRunLedgerPolicy()

    valid, errors = validate_ledger_policy(
        policy
    )

    if not valid or errors:
        raise RuntimeError(
            f"기본 V10.7 Policy가 유효하지 않습니다: {errors}"
        )

    expected_keys = {
        "reject_duplicate_run_id",
        "retain_blocked_runs",
        "retain_failed_runs",
        "maximum_entry_count",
        "trim_oldest_entries",
        "require_source_checks",
        "require_execution_safety",
        "save_output",
        "paper_only",
        "live_execution_disabled",
    }

    if set(policy.to_dict()) != expected_keys:
        raise RuntimeError(
            "V10.7 Policy Dictionary 구조가 다릅니다."
        )

    immutable = False

    try:
        policy.maximum_entry_count = 1
    except (FrozenInstanceError, AttributeError):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "V10.7 Policy가 Frozen Dataclass가 아닙니다."
        )

    invalid_policies = [
        PaperTradingRunLedgerPolicy(
            reject_duplicate_run_id=False,
        ),
        PaperTradingRunLedgerPolicy(
            retain_blocked_runs=False,
        ),
        PaperTradingRunLedgerPolicy(
            retain_failed_runs=False,
        ),
        PaperTradingRunLedgerPolicy(
            maximum_entry_count=0,
        ),
        PaperTradingRunLedgerPolicy(
            trim_oldest_entries="yes",
        ),
        PaperTradingRunLedgerPolicy(
            require_execution_safety=False,
        ),
        PaperTradingRunLedgerPolicy(
            paper_only=False,
        ),
        PaperTradingRunLedgerPolicy(
            live_execution_disabled=False,
        ),
    ]

    for index, invalid_policy in enumerate(
        invalid_policies,
        start=1,
    ):
        invalid_valid, invalid_errors = (
            validate_ledger_policy(
                invalid_policy
            )
        )

        if invalid_valid or not invalid_errors:
            raise RuntimeError(
                f"Invalid Policy #{index}가 거부되지 않았습니다."
            )

    return policy


def validate_empty_state() -> None:
    state = empty_ledger_state()

    valid, errors = validate_ledger_state(
        state
    )

    if not valid or errors:
        raise RuntimeError(
            f"빈 Ledger State가 유효하지 않습니다: {errors}"
        )

    if state.entry_count != 0:
        raise RuntimeError(
            "빈 Ledger의 Entry Count가 0이 아닙니다."
        )

    restored = ledger_state_from_dict(
        state.to_dict()
    )

    if restored.to_dict() != state.to_dict():
        restored_payload = restored.to_dict()
        original_payload = state.to_dict()

        restored_payload["updated_at"] = (
            original_payload["updated_at"]
        )

        if restored_payload != original_payload:
            raise RuntimeError(
                "Ledger State Dictionary 복원이 실패했습니다."
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


def validate_daily_initialization(
    policy: PaperTradingRunLedgerPolicy,
):
    source = create_fake_daily_source(
        run_id="daily-run-001",
    )

    source_valid, source_errors = (
        validate_source_safety(
            source
        )
    )

    if not source_valid or source_errors:
        raise RuntimeError(
            f"정상 Daily Source가 거부되었습니다: {source_errors}"
        )

    result = run_paper_trading_run_ledger(
        source_result=source,
        ledger_state=empty_ledger_state(),
        ledger_policy=policy,
    )

    if result.version != "V10.7":
        raise RuntimeError(
            "Ledger 버전이 V10.7이 아닙니다."
        )

    if result.ledger_status != "INITIALIZED":
        raise RuntimeError(
            "첫 기록이 INITIALIZED가 아닙니다."
        )

    if not result.entry_added:
        raise RuntimeError(
            "첫 Daily Entry가 추가되지 않았습니다."
        )

    if result.current_entry_count != 1:
        raise RuntimeError(
            "첫 기록 후 Entry Count가 1이 아닙니다."
        )

    state = result.ledger_state

    if state.daily_run_count != 1:
        raise RuntimeError(
            "Daily Run Count가 1이 아닙니다."
        )

    if state.completed_run_count != 1:
        raise RuntimeError(
            "Completed Run Count가 1이 아닙니다."
        )

    if state.cumulative_equity_change != 100.0:
        raise RuntimeError(
            "Daily Equity Change가 다릅니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "Daily Initialization 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_batch_update(
    previous_result,
    policy: PaperTradingRunLedgerPolicy,
):
    source = create_fake_batch_source(
        run_id="batch-run-001",
    )

    result = run_paper_trading_run_ledger(
        source_result=source,
        ledger_state=(
            previous_result.ledger_state
        ),
        ledger_policy=policy,
    )

    if result.ledger_status != "UPDATED":
        raise RuntimeError(
            "Batch 누적 결과가 UPDATED가 아닙니다."
        )

    if result.current_entry_count != 2:
        raise RuntimeError(
            "Batch 추가 후 Entry Count가 2가 아닙니다."
        )

    state = result.ledger_state

    if state.daily_run_count != 1:
        raise RuntimeError(
            "누적 Daily Run Count가 다릅니다."
        )

    if state.batch_run_count != 1:
        raise RuntimeError(
            "누적 Batch Run Count가 다릅니다."
        )

    if state.partial_run_count != 1:
        raise RuntimeError(
            "Partial Run Count가 다릅니다."
        )

    if state.total_requested_symbol_count != 4:
        raise RuntimeError(
            "누적 요청 종목 수가 다릅니다."
        )

    if state.total_completed_symbol_count != 3:
        raise RuntimeError(
            "누적 완료 종목 수가 다릅니다."
        )

    if state.total_failed_symbol_count != 1:
        raise RuntimeError(
            "누적 실패 종목 수가 다릅니다."
        )

    if state.cumulative_equity_change != 150.0:
        raise RuntimeError(
            "누적 Equity Change가 다릅니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "Batch Update 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_duplicate_block(
    previous_result,
    policy: PaperTradingRunLedgerPolicy,
):
    duplicate_source = (
        create_fake_daily_source(
            run_id="daily-run-001",
        )
    )

    result = run_paper_trading_run_ledger(
        source_result=duplicate_source,
        ledger_state=(
            previous_result.ledger_state
        ),
        ledger_policy=policy,
    )

    if result.ledger_status != "NO_CHANGE":
        raise RuntimeError(
            "Duplicate Run이 NO_CHANGE가 아닙니다."
        )

    if not result.duplicate_detected:
        raise RuntimeError(
            "Duplicate Run이 감지되지 않았습니다."
        )

    if result.entry_added:
        raise RuntimeError(
            "Duplicate Run이 Ledger에 추가되었습니다."
        )

    if (
        result.current_entry_count
        != previous_result.current_entry_count
    ):
        raise RuntimeError(
            "Duplicate 처리 후 Entry Count가 변경되었습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "안전한 중복 차단 검사가 실패했습니다."
        )

    assert_execution_safety(result)

    return result


def validate_blocked_and_failed_retention(
    previous_result,
    policy: PaperTradingRunLedgerPolicy,
):
    blocked_source = (
        create_fake_daily_source(
            run_id="daily-run-blocked",
            status="BLOCKED",
            all_checks_passed=True,
            initial_equity=0.0,
            final_equity=0.0,
        )
    )

    blocked_result = (
        run_paper_trading_run_ledger(
            source_result=blocked_source,
            ledger_state=(
                previous_result.ledger_state
            ),
            ledger_policy=policy,
        )
    )

    if not blocked_result.entry_added:
        raise RuntimeError(
            "차단된 Run이 Ledger에 보존되지 않았습니다."
        )

    if (
        blocked_result
        .ledger_state
        .blocked_run_count
        != 1
    ):
        raise RuntimeError(
            "Blocked Run Count가 다릅니다."
        )

    failed_source = create_fake_daily_source(
        run_id="daily-run-failed",
        status="FAILED",
        all_checks_passed=False,
        initial_equity=0.0,
        final_equity=0.0,
    )

    failed_result = (
        run_paper_trading_run_ledger(
            source_result=failed_source,
            ledger_state=(
                blocked_result.ledger_state
            ),
            ledger_policy=policy,
        )
    )

    if not failed_result.entry_added:
        raise RuntimeError(
            "실패한 Run이 Ledger에 보존되지 않았습니다."
        )

    if (
        failed_result
        .ledger_state
        .failed_run_count
        != 1
    ):
        raise RuntimeError(
            "Failed Run Count가 다릅니다."
        )

    if not failed_result.all_checks_passed:
        raise RuntimeError(
            "실패 Run 보존 검사가 실패했습니다."
        )

    assert_execution_safety(
        blocked_result
    )
    assert_execution_safety(
        failed_result
    )

    return blocked_result, failed_result


def validate_trim_policy() -> None:
    policy = PaperTradingRunLedgerPolicy(
        maximum_entry_count=2,
        trim_oldest_entries=True,
    )

    first = run_paper_trading_run_ledger(
        source_result=create_fake_daily_source(
            run_id="trim-run-001",
        ),
        ledger_state=empty_ledger_state(),
        ledger_policy=policy,
    )
    second = run_paper_trading_run_ledger(
        source_result=create_fake_daily_source(
            run_id="trim-run-002",
        ),
        ledger_state=first.ledger_state,
        ledger_policy=policy,
    )
    third = run_paper_trading_run_ledger(
        source_result=create_fake_daily_source(
            run_id="trim-run-003",
        ),
        ledger_state=second.ledger_state,
        ledger_policy=policy,
    )

    if not third.ledger_trimmed:
        raise RuntimeError(
            "Maximum Entry Count 초과 시 Trim되지 않았습니다."
        )

    if third.trimmed_entry_count != 1:
        raise RuntimeError(
            "Trimmed Entry Count가 다릅니다."
        )

    if third.current_entry_count != 2:
        raise RuntimeError(
            "Trim 후 Entry Count가 2가 아닙니다."
        )

    remaining_run_ids = [
        entry.run_id
        for entry in third.ledger_state.entries
    ]

    if remaining_run_ids != [
        "trim-run-002",
        "trim-run-003",
    ]:
        raise RuntimeError(
            "가장 오래된 Entry가 제거되지 않았습니다."
        )


def validate_unsafe_source(
    policy: PaperTradingRunLedgerPolicy,
):
    unsafe_source = create_fake_daily_source(
        run_id="unsafe-run-001",
        unsafe=True,
    )

    result = run_paper_trading_run_ledger(
        source_result=unsafe_source,
        ledger_state=empty_ledger_state(),
        ledger_policy=policy,
    )

    if result.ledger_status != "FAILED":
        raise RuntimeError(
            "Unsafe Source가 FAILED로 처리되지 않았습니다."
        )

    if result.entry_added:
        raise RuntimeError(
            "Unsafe Source가 Ledger에 추가되었습니다."
        )

    if result.source_checks_passed:
        raise RuntimeError(
            "Unsafe Source Checks가 True입니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "Unsafe Source의 All Checks가 True입니다."
        )

    assert_execution_safety(result)

    return result


def validate_save_and_load(result) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output_directory = (
            Path(temporary)
            / "run_ledger"
        )

        with patch.object(
            ledger_module,
            (
                "PAPER_TRADING_RUN_LEDGER_"
                "OUTPUT_DIRECTORY"
            ),
            output_directory,
        ):
            report_path, latest_path = (
                save_paper_trading_run_ledger(
                    result
                )
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V10.7 Report가 저장되지 않았습니다."
                )

            if not latest_path.exists():
                raise RuntimeError(
                    "V10.7 Latest가 저장되지 않았습니다."
                )

            loaded = (
                load_latest_paper_trading_run_ledger()
            )

            if loaded.get("version") != "V10.7":
                raise RuntimeError(
                    "저장된 버전이 V10.7이 아닙니다."
                )

            if (
                loaded.get("ledger_id")
                != result.ledger_id
            ):
                raise RuntimeError(
                    "저장된 Ledger ID가 다릅니다."
                )

            with latest_path.open(
                mode="r",
                encoding="utf-8",
            ) as file:
                raw_payload = json.load(file)

            state_payload = raw_payload.get(
                "ledger_state"
            )

            if not isinstance(
                state_payload,
                dict,
            ):
                raise RuntimeError(
                    "저장된 Ledger State 형식이 다릅니다."
                )

            restored_state = (
                ledger_state_from_dict(
                    state_payload
                )
            )
            valid, errors = (
                validate_ledger_state(
                    restored_state
                )
            )

            if not valid or errors:
                raise RuntimeError(
                    f"복원된 Ledger State가 유효하지 않습니다: {errors}"
                )


def validate_result_contract(results: list) -> None:
    for result in results:
        if (
            result.ledger_status
            not in VALID_LEDGER_STATUSES
        ):
            raise RuntimeError(
                "허용되지 않은 Ledger Status입니다."
            )

        if not result.ledger_update_id:
            raise RuntimeError(
                "Ledger Update ID가 비어 있습니다."
            )

        if not result.ledger_id:
            raise RuntimeError(
                "Ledger ID가 비어 있습니다."
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
    validate_empty_state()

    daily_result = (
        validate_daily_initialization(
            policy
        )
    )
    batch_result = validate_batch_update(
        daily_result,
        policy,
    )
    duplicate_result = (
        validate_duplicate_block(
            batch_result,
            policy,
        )
    )
    (
        blocked_result,
        failed_result,
    ) = validate_blocked_and_failed_retention(
        batch_result,
        policy,
    )

    validate_trim_policy()
    unsafe_result = validate_unsafe_source(
        policy
    )
    validate_save_and_load(failed_result)

    results = [
        daily_result,
        batch_result,
        duplicate_result,
        blocked_result,
        failed_result,
        unsafe_result,
    ]

    validate_result_contract(results)

    checks = {
        "Version is V10.7": (
            daily_result.version == "V10.7"
        ),
        "Default policy is valid": True,
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Daily run initialized ledger": (
            daily_result.ledger_status
            == "INITIALIZED"
        ),
        "Batch run updated ledger": (
            batch_result.ledger_status
            == "UPDATED"
        ),
        "Daily and batch counts correct": (
            batch_result
            .ledger_state
            .daily_run_count
            == 1
            and batch_result
            .ledger_state
            .batch_run_count
            == 1
        ),
        "Duplicate run was blocked": (
            duplicate_result
            .ledger_status
            == "NO_CHANGE"
        ),
        "Blocked run was retained": (
            blocked_result.entry_added
        ),
        "Failed run was retained": (
            failed_result.entry_added
        ),
        "Oldest entries were trimmed": True,
        "Unsafe source was rejected": (
            unsafe_result.ledger_status
            == "FAILED"
        ),
        "Ledger aggregates are valid": (
            failed_result
            .ledger_checks_passed
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
    print("V10.7 VALIDATION CHECKS")
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
            "V10.7 Run Ledger Test가 실패했습니다."
        )

    print()
    print(
        "V10.7 paper trading run ledger test "
        "completed successfully."
    )
    print(
        "Daily, Batch, Blocked 및 Failed 실행 이력 누적과 "
        "중복 방지가 정상적으로 검증되었습니다."
    )
    print(
        "Ledger 집계, 최대 보관 건수, JSON 저장 및 복원이 "
        "정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
