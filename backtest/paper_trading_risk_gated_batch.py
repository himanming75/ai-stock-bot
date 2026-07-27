import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backtest.paper_portfolio_performance_tracker import (
    PaperPortfolioPerformanceResult,
)
from backtest.paper_trading_batch_pipeline import (
    PaperTradingBatchPipelinePolicy,
    PaperTradingBatchPipelineResult,
    run_paper_trading_batch_pipeline,
)
from backtest.paper_trading_risk_gated_pipeline import (
    PaperTradingRiskGateDecision,
    PaperTradingRiskGatedPipelinePolicy,
    evaluate_risk_gate,
    validate_gated_policy,
)
from backtest.paper_trading_risk_monitor import (
    PaperTradingRiskMonitorPolicy,
    PaperTradingRiskMonitorResult,
    run_paper_trading_risk_monitor,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_RISK_GATED_BATCH_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_risk_gated_batch"
)


VALID_GATED_BATCH_STATUSES = {
    "COMPLETED",
    "PARTIAL",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperTradingRiskGatedBatchPolicy:
    """
    V10.6 Risk-Gated Multi-Symbol Batch 정책입니다.

    Batch 전체를 실행하기 전에 V10.4 Risk Gate를 한 번 적용합니다.
    """

    require_risk_checks: bool = True
    allow_safe: bool = True
    allow_warning: bool = True
    block_paused: bool = True
    block_blocked: bool = True
    block_failed: bool = True

    require_batch_checks: bool = True
    allow_partial_batch: bool = True
    save_output: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_gate_policy(
        self,
    ) -> PaperTradingRiskGatedPipelinePolicy:
        """
        공통 V10.5 Risk Gate Policy로 변환합니다.
        """

        return PaperTradingRiskGatedPipelinePolicy(
            require_risk_checks=(
                self.require_risk_checks
            ),
            allow_safe=self.allow_safe,
            allow_warning=self.allow_warning,
            block_paused=self.block_paused,
            block_blocked=self.block_blocked,
            block_failed=self.block_failed,
            require_daily_pipeline_checks=True,
            save_output=False,
            paper_only=self.paper_only,
            live_execution_disabled=(
                self.live_execution_disabled
            ),
        )


@dataclass
class PaperTradingRiskGatedBatchResult:
    """
    V10.6 Risk-Gated Multi-Symbol Batch 전체 결과입니다.
    """

    version: str
    created_at: str

    gated_batch_id: str
    gated_batch_status: str
    gated_batch_status_label: str

    requested_symbols: list[str]
    requested_symbol_count: int

    risk_monitor_id: str | None
    batch_id: str | None

    risk_monitor_executed: bool
    risk_gate_evaluated: bool
    batch_requested: bool
    batch_executed: bool
    batch_skipped: bool

    completed_symbol_count: int
    blocked_symbol_count: int
    failed_symbol_count: int
    skipped_symbol_count: int

    risk_checks_passed: bool
    gate_checks_passed: bool
    batch_checks_passed: bool
    all_checks_passed: bool

    paper_batch_allowed: bool
    risk_gate_blocked: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    gated_batch_policy: (
        PaperTradingRiskGatedBatchPolicy
    )
    risk_gate_decision: (
        PaperTradingRiskGateDecision
    )

    risk_monitor_result: (
        PaperTradingRiskMonitorResult
        | None
    )
    batch_result: (
        PaperTradingBatchPipelineResult
        | None
    )

    reasons: list[str] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )
    next_actions: list[str] = field(
        default_factory=list
    )

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["gated_batch_policy"] = (
            self.gated_batch_policy.to_dict()
        )
        payload["risk_gate_decision"] = (
            self.risk_gate_decision.to_dict()
        )
        payload["risk_monitor_result"] = (
            self.risk_monitor_result.to_dict()
            if self.risk_monitor_result is not None
            else None
        )
        payload["batch_result"] = (
            self.batch_result.to_dict()
            if self.batch_result is not None
            else None
        )

        return payload


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    임시 파일을 사용해 JSON을 안전하게 저장합니다.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    with temporary_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    temporary_path.replace(file_path)


def read_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽고 Dictionary인지 확인합니다.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    if file_path.stat().st_size <= 0:
        raise RuntimeError(
            f"JSON 파일이 비어 있습니다: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise RuntimeError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def normalize_requested_symbols(
    symbols: list[str] | tuple[str, ...],
) -> list[str]:
    """
    요청 Symbol을 문자열 목록으로 정규화합니다.
    실제 중복 검사는 V10.3 Batch가 담당합니다.
    """

    if not isinstance(
        symbols,
        (list, tuple),
    ):
        raise TypeError(
            "Symbols는 List 또는 Tuple이어야 합니다."
        )

    normalized = [
        str(symbol).strip().upper()
        for symbol in symbols
    ]

    if not normalized:
        raise ValueError(
            "요청 Symbol 목록이 비어 있습니다."
        )

    if any(
        not symbol
        for symbol in normalized
    ):
        raise ValueError(
            "비어 있는 Symbol이 포함되어 있습니다."
        )

    return normalized


def validate_gated_batch_policy(
    policy: PaperTradingRiskGatedBatchPolicy,
) -> tuple[bool, list[str]]:
    """
    V10.6 Gated Batch Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingRiskGatedBatchPolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingRiskGatedBatchPolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    boolean_fields = {
        "require_risk_checks": (
            policy.require_risk_checks
        ),
        "allow_safe": policy.allow_safe,
        "allow_warning": policy.allow_warning,
        "block_paused": policy.block_paused,
        "block_blocked": policy.block_blocked,
        "block_failed": policy.block_failed,
        "require_batch_checks": (
            policy.require_batch_checks
        ),
        "allow_partial_batch": (
            policy.allow_partial_batch
        ),
        "save_output": policy.save_output,
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(value, bool):
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    gate_policy = policy.to_gate_policy()
    gate_valid, gate_errors = (
        validate_gated_policy(
            gate_policy
        )
    )

    if not gate_valid:
        errors.extend(gate_errors)

    if not policy.require_batch_checks:
        errors.append(
            "V10.6에서는 Batch Checks가 필수입니다."
        )

    if not policy.paper_only:
        errors.append(
            "V10.6에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.6에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def validate_batch_result_safety(
    result: PaperTradingBatchPipelineResult,
) -> tuple[bool, list[str]]:
    """
    V10.3 Batch 결과의 안전 상태를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        result,
        PaperTradingBatchPipelineResult,
    ):
        return (
            False,
            [
                (
                    "Batch Result가 "
                    "PaperTradingBatchPipelineResult "
                    "형식이 아닙니다."
                )
            ],
        )

    if result.version != "V10.3":
        errors.append(
            "Batch Result 버전이 V10.3이 아닙니다."
        )

    if result.execution_blocked is not True:
        errors.append(
            "Batch Result의 Execution이 차단되지 않았습니다."
        )

    unsafe_flags = {
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

    for field_name, value in unsafe_flags.items():
        if value is not False:
            errors.append(
                f"Batch Result의 {field_name}가 False가 아닙니다."
            )

    return (not errors, errors)


def run_paper_trading_risk_gated_batch(
    symbols: list[str] | tuple[str, ...] = (
        "AAPL",
        "MSFT",
        "NVDA",
    ),
    account_cash: float = 10_000.0,
    latest_prices: dict[str, float] | None = None,
    performance_result: (
        PaperPortfolioPerformanceResult
        | dict[str, Any]
        | None
    ) = None,
    gated_batch_policy: (
        PaperTradingRiskGatedBatchPolicy
        | None
    ) = None,
    risk_monitor_policy: (
        PaperTradingRiskMonitorPolicy
        | None
    ) = None,
    batch_policy: (
        PaperTradingBatchPipelinePolicy
        | None
    ) = None,
    risk_monitor_result: (
        PaperTradingRiskMonitorResult
        | None
    ) = None,
    batch_runner: (
        Callable[..., PaperTradingBatchPipelineResult]
        | None
    ) = None,
) -> PaperTradingRiskGatedBatchResult:
    """
    V10.4 Risk Gate를 먼저 적용한 뒤,
    허용된 경우에만 V10.3 Multi-Symbol Batch를 실행합니다.

    차단된 경우에는 어떤 종목의 Pipeline도 실행하지 않습니다.
    """

    requested_symbols = (
        normalize_requested_symbols(
            symbols
        )
    )

    if (
        isinstance(account_cash, bool)
        or not isinstance(
            account_cash,
            (int, float),
        )
        or float(account_cash) <= 0
    ):
        raise ValueError(
            "Account Cash는 0보다 큰 숫자여야 합니다."
        )

    policy = (
        gated_batch_policy
        if gated_batch_policy is not None
        else PaperTradingRiskGatedBatchPolicy()
    )

    policy_valid, policy_errors = (
        validate_gated_batch_policy(
            policy
        )
    )

    risk_result: (
        PaperTradingRiskMonitorResult
        | None
    ) = None
    batch_result: (
        PaperTradingBatchPipelineResult
        | None
    ) = None

    risk_monitor_executed = False
    risk_gate_evaluated = False
    batch_requested = False
    batch_executed = False
    batch_skipped = True

    reasons: list[str] = []
    warnings: list[str] = list(policy_errors)

    if policy_valid:
        try:
            risk_result = (
                risk_monitor_result
                if risk_monitor_result is not None
                else run_paper_trading_risk_monitor(
                    performance_result=(
                        performance_result
                    ),
                    monitor_policy=(
                        risk_monitor_policy
                    ),
                )
            )
            risk_monitor_executed = True
        except Exception as error:
            warnings.append(
                f"Risk Monitor 실행 실패: {error}"
            )

    if risk_result is not None:
        gate_decision = evaluate_risk_gate(
            risk_result=risk_result,
            policy=policy.to_gate_policy(),
        )
        risk_gate_evaluated = True
    else:
        gate_decision = PaperTradingRiskGateDecision(
            gate_status="FAILED",
            gate_status_label=(
                "Risk Monitor 결과 없음"
            ),
            risk_status="FAILED",
            risk_action="BLOCK",
            gate_passed=False,
            pipeline_execution_allowed=False,
            checks_passed=False,
            reasons=[
                (
                    "Risk Monitor 결과가 없어 "
                    "Multi-Symbol Batch를 차단합니다."
                )
            ],
            warnings=list(warnings),
        )

    reasons.extend(gate_decision.reasons)
    warnings.extend(gate_decision.warnings)

    if (
        policy_valid
        and gate_decision.pipeline_execution_allowed
    ):
        batch_requested = True

        try:
            runner = (
                batch_runner
                if batch_runner is not None
                else run_paper_trading_batch_pipeline
            )

            batch_result = runner(
                symbols=requested_symbols,
                account_cash=float(
                    account_cash
                ),
                latest_prices=latest_prices,
                batch_policy=batch_policy,
            )

            batch_executed = True
            batch_skipped = False
        except Exception as error:
            warnings.append(
                f"Multi-Symbol Batch 실행 실패: {error}"
            )
    else:
        reasons.append(
            "Risk Gate가 Batch 실행 전에 모든 종목을 차단했습니다."
        )

    risk_checks_passed = bool(
        risk_result is not None
        and risk_result.all_checks_passed
        and risk_result.execution_blocked
        and not risk_result.broker_api_called
        and not risk_result.broker_order_created
        and not risk_result.live_order_created
        and not risk_result.live_execution_authorized
    )

    gate_checks_passed = bool(
        risk_gate_evaluated
        and gate_decision.checks_passed
    )

    batch_safety_valid = False

    if batch_result is not None:
        (
            batch_safety_valid,
            batch_safety_errors,
        ) = validate_batch_result_safety(
            batch_result
        )
        warnings.extend(batch_safety_errors)

        acceptable_status = (
            batch_result.batch_status
            == "COMPLETED"
            or (
                policy.allow_partial_batch
                and batch_result.batch_status
                == "PARTIAL"
            )
        )

        batch_checks_passed = bool(
            batch_safety_valid
            and acceptable_status
            and (
                batch_result.all_checks_passed
                if policy.require_batch_checks
                else True
            )
        )
    else:
        batch_checks_passed = bool(
            not gate_decision.gate_passed
            and batch_skipped
        )

    if not policy_valid:
        gated_batch_status = "FAILED"
        gated_batch_status_label = (
            "Gated Batch Policy 검사 실패"
        )
    elif not risk_checks_passed:
        gated_batch_status = "FAILED"
        gated_batch_status_label = (
            "Risk Monitor 검사 실패"
        )
    elif gate_decision.gate_passed:
        if not batch_executed:
            gated_batch_status = "FAILED"
            gated_batch_status_label = (
                "Multi-Symbol Batch 실행 실패"
            )
        elif (
            batch_result is not None
            and batch_result.batch_status
            == "COMPLETED"
            and batch_checks_passed
        ):
            gated_batch_status = "COMPLETED"
            gated_batch_status_label = (
                "Risk 통과 후 모든 종목 Batch 완료"
            )
        elif (
            batch_result is not None
            and batch_result.batch_status
            == "PARTIAL"
            and batch_checks_passed
        ):
            gated_batch_status = "PARTIAL"
            gated_batch_status_label = (
                "Risk 통과 후 일부 종목 Batch 완료"
            )
        else:
            gated_batch_status = "FAILED"
            gated_batch_status_label = (
                "Multi-Symbol Batch 검사 실패"
            )
    else:
        gated_batch_status = "BLOCKED"
        gated_batch_status_label = (
            "Risk Gate에서 전체 Batch 차단"
        )

    completed_symbol_count = (
        batch_result.completed_symbol_count
        if batch_result is not None
        else 0
    )
    blocked_symbol_count = (
        batch_result.blocked_symbol_count
        if batch_result is not None
        else 0
    )
    failed_symbol_count = (
        batch_result.failed_symbol_count
        if batch_result is not None
        else 0
    )
    skipped_symbol_count = (
        batch_result.skipped_symbol_count
        if batch_result is not None
        else len(requested_symbols)
    )

    paper_batch_allowed = bool(
        gate_decision.gate_passed
        and batch_executed
    )
    risk_gate_blocked = (
        not gate_decision.gate_passed
    )

    all_checks_passed = bool(
        policy_valid
        and risk_checks_passed
        and gate_checks_passed
        and batch_checks_passed
        and gated_batch_status
        in {
            "COMPLETED",
            "PARTIAL",
            "BLOCKED",
        }
    )

    if gated_batch_status in {
        "COMPLETED",
        "PARTIAL",
    }:
        reasons.append(
            "Risk Gate 통과 후 V10.3 Multi-Symbol Batch를 실행했습니다."
        )
        next_actions = [
            "종목별 Batch Status와 실패 원인을 확인합니다.",
            "다음 Batch 전에 V10.4 Risk Monitor를 다시 실행합니다.",
        ]
    elif gated_batch_status == "BLOCKED":
        reasons.append(
            "Risk Gate가 모든 종목의 Batch 실행을 사전에 차단했습니다."
        )
        next_actions = [
            "Risk Monitor의 Triggered Rule을 확인합니다.",
            "Risk가 회복될 때까지 Multi-Symbol Batch를 중단합니다.",
        ]
    else:
        next_actions = [
            "Warnings와 실패 원인을 확인합니다.",
            "입력 또는 Policy를 수정한 후 V10.6을 다시 실행합니다.",
        ]

    warnings.extend(
        [
            (
                "V10.6은 연구용 Risk-Gated "
                "Multi-Symbol Paper Trading Batch입니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    result = PaperTradingRiskGatedBatchResult(
        version="V10.6",
        created_at=datetime.now().isoformat(),
        gated_batch_id=str(uuid.uuid4()),
        gated_batch_status=(
            gated_batch_status
        ),
        gated_batch_status_label=(
            gated_batch_status_label
        ),
        requested_symbols=requested_symbols,
        requested_symbol_count=len(
            requested_symbols
        ),
        risk_monitor_id=(
            risk_result.monitor_id
            if risk_result is not None
            else None
        ),
        batch_id=(
            batch_result.batch_id
            if batch_result is not None
            else None
        ),
        risk_monitor_executed=(
            risk_monitor_executed
        ),
        risk_gate_evaluated=(
            risk_gate_evaluated
        ),
        batch_requested=batch_requested,
        batch_executed=batch_executed,
        batch_skipped=batch_skipped,
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
        risk_checks_passed=(
            risk_checks_passed
        ),
        gate_checks_passed=(
            gate_checks_passed
        ),
        batch_checks_passed=(
            batch_checks_passed
        ),
        all_checks_passed=(
            all_checks_passed
        ),
        paper_batch_allowed=(
            paper_batch_allowed
        ),
        risk_gate_blocked=(
            risk_gate_blocked
        ),
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        gated_batch_policy=policy,
        risk_gate_decision=gate_decision,
        risk_monitor_result=risk_result,
        batch_result=batch_result,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_risk_gated_batch(
        result
    )

    return result


def save_paper_trading_risk_gated_batch(
    result: PaperTradingRiskGatedBatchResult,
) -> tuple[Path, Path]:
    """
    V10.6 Report와 Latest JSON을 저장합니다.
    """

    PAPER_RISK_GATED_BATCH_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_RISK_GATED_BATCH_OUTPUT_DIRECTORY
        / (
            "paper_trading_risk_gated_batch_"
            f"{timestamp}.json"
        )
    )
    latest_path = (
        PAPER_RISK_GATED_BATCH_OUTPUT_DIRECTORY
        / (
            "paper_trading_risk_gated_batch_"
            "latest.json"
        )
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_risk_gated_batch() -> (
    dict[str, Any]
):
    """
    저장된 최신 V10.6 결과를 읽습니다.
    """

    latest_path = (
        PAPER_RISK_GATED_BATCH_OUTPUT_DIRECTORY
        / (
            "paper_trading_risk_gated_batch_"
            "latest.json"
        )
    )

    return read_json_file(latest_path)


def print_paper_trading_risk_gated_batch(
    result: PaperTradingRiskGatedBatchResult,
) -> None:
    """
    V10.6 결과를 터미널에 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.6 PAPER TRADING RISK-GATED "
        "MULTI-SYMBOL BATCH"
    )
    print("=" * line_length)

    print(
        f"Gated batch status             : "
        f"{result.gated_batch_status}"
    )
    print(
        f"Gated batch status label       : "
        f"{result.gated_batch_status_label}"
    )
    print(
        f"Gated batch ID                 : "
        f"{result.gated_batch_id}"
    )
    print(
        f"Requested symbols              : "
        f"{', '.join(result.requested_symbols)}"
    )

    print()
    print("RISK GATE")
    print("-" * line_length)

    print(
        f"Risk monitor ID                : "
        f"{result.risk_monitor_id}"
    )
    print(
        f"Risk status                    : "
        f"{result.risk_gate_decision.risk_status}"
    )
    print(
        f"Risk action                    : "
        f"{result.risk_gate_decision.risk_action}"
    )
    print(
        f"Gate status                    : "
        f"{result.risk_gate_decision.gate_status}"
    )
    print(
        f"Gate passed                    : "
        f"{result.risk_gate_decision.gate_passed}"
    )

    print()
    print("BATCH EXECUTION")
    print("-" * line_length)

    print(
        f"Batch ID                       : "
        f"{result.batch_id}"
    )
    print(
        f"Batch requested                : "
        f"{result.batch_requested}"
    )
    print(
        f"Batch executed                 : "
        f"{result.batch_executed}"
    )
    print(
        f"Batch skipped                  : "
        f"{result.batch_skipped}"
    )
    print(
        f"Completed symbols              : "
        f"{result.completed_symbol_count}"
    )
    print(
        f"Blocked symbols                : "
        f"{result.blocked_symbol_count}"
    )
    print(
        f"Failed symbols                 : "
        f"{result.failed_symbol_count}"
    )
    print(
        f"Skipped symbols                : "
        f"{result.skipped_symbol_count}"
    )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Risk checks passed             : "
        f"{result.risk_checks_passed}"
    )
    print(
        f"Gate checks passed             : "
        f"{result.gate_checks_passed}"
    )
    print(
        f"Batch checks passed            : "
        f"{result.batch_checks_passed}"
    )
    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )
    print(
        f"Broker API called              : "
        f"{result.broker_api_called}"
    )
    print(
        f"Broker order created           : "
        f"{result.broker_order_created}"
    )
    print(
        f"Live order created             : "
        f"{result.live_order_created}"
    )
    print(
        f"Live execution authorized      : "
        f"{result.live_execution_authorized}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * line_length)

        for reason in result.reasons:
            print(f"- {reason}")

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * line_length)

        for warning in result.warnings:
            print(f"- {warning}")

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * line_length)

        for action in result.next_actions:
            print(f"- {action}")

    print()
    print("FILES")
    print("-" * line_length)

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )
    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * line_length)
    print(
        "주의: V10.6은 연구용 Paper Trading Batch이며 "
        "실제 Broker 주문을 수행하지 않습니다."
    )


if __name__ == "__main__":
    gated_batch_result = (
        run_paper_trading_risk_gated_batch()
    )

    if (
        gated_batch_result
        .gated_batch_policy
        .save_output
    ):
        save_paper_trading_risk_gated_batch(
            gated_batch_result
        )
