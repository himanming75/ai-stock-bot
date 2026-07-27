import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_broker_simulator import (
    PaperBrokerFillResult,
    run_paper_broker_simulator,
    save_paper_broker_fill,
)
from backtest.paper_execution_request_builder import (
    PaperExecutionRequestResult,
    run_paper_execution_request_builder,
    save_paper_execution_request,
)
from backtest.paper_portfolio_manager import (
    PaperPortfolioResult,
    PaperPortfolioState,
    load_latest_portfolio_state,
    run_paper_portfolio_manager,
    save_paper_portfolio_result,
)
from backtest.paper_portfolio_performance_tracker import (
    PaperPortfolioPerformanceResult,
    run_paper_portfolio_performance_tracker,
    save_paper_portfolio_performance,
)
from backtest.paper_portfolio_valuation import (
    PaperPortfolioValuationResult,
    run_paper_portfolio_valuation,
    save_paper_portfolio_valuation,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_DAILY_PIPELINE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_daily_pipeline"
)


VALID_PIPELINE_STATUSES = {
    "COMPLETED",
    "PARTIAL",
    "BLOCKED",
    "FAILED",
}


VALID_STAGE_STATUSES = {
    "COMPLETED",
    "SKIPPED",
    "BLOCKED",
    "FAILED",
}


PIPELINE_STAGE_NAMES = (
    "EXECUTION_REQUEST",
    "PAPER_BROKER",
    "PORTFOLIO_UPDATE",
    "PORTFOLIO_VALUATION",
    "PERFORMANCE_TRACKING",
)


@dataclass(frozen=True)
class PaperTradingDailyPipelinePolicy:
    """
    V10.2 Paper Trading Daily Pipeline 정책입니다.

    각 단계가 성공해야 다음 단계로 진행합니다.
    실제 Broker 주문과 Live Execution은 항상 차단합니다.
    """

    stop_on_stage_failure: bool = True
    require_request_checks: bool = True
    require_fill_checks: bool = True
    require_portfolio_checks: bool = True
    require_valuation_checks: bool = True
    require_performance_checks: bool = True

    save_stage_outputs: bool = True
    use_fill_price_for_valuation: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingPipelineStageResult:
    """
    Pipeline 한 단계의 실행 상태입니다.
    """

    stage_name: str
    stage_order: int

    stage_status: str
    stage_status_label: str

    started_at: str | None
    completed_at: str | None

    source_id: str | None
    result_id: str | None

    checks_required: bool
    checks_passed: bool

    output_saved: bool
    output_paths: list[str] = field(
        default_factory=list
    )

    error_message: str | None = None

    reasons: list[str] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingDailyPipelineResult:
    """
    V10.2 Paper Trading Daily Pipeline 전체 결과입니다.
    """

    version: str
    created_at: str

    pipeline_id: str
    symbol: str

    pipeline_status: str
    pipeline_status_label: str

    initial_cash: float
    final_cash_balance: float
    final_market_value: float
    final_equity: float

    request_id: str | None
    fill_id: str | None
    portfolio_update_id: str | None
    valuation_id: str | None
    performance_id: str | None

    completed_stage_count: int
    blocked_stage_count: int
    failed_stage_count: int
    skipped_stage_count: int

    request_stage_passed: bool
    broker_stage_passed: bool
    portfolio_stage_passed: bool
    valuation_stage_passed: bool
    performance_stage_passed: bool

    all_required_stages_passed: bool
    all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    pipeline_policy: PaperTradingDailyPipelinePolicy
    stages: dict[str, PaperTradingPipelineStageResult]

    execution_request: PaperExecutionRequestResult | None
    paper_fill: PaperBrokerFillResult | None
    portfolio_result: PaperPortfolioResult | None
    valuation_result: PaperPortfolioValuationResult | None
    performance_result: PaperPortfolioPerformanceResult | None

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["pipeline_policy"] = (
            self.pipeline_policy.to_dict()
        )

        payload["stages"] = {
            name: stage.to_dict()
            for name, stage in self.stages.items()
        }

        payload["execution_request"] = (
            self.execution_request.to_dict()
            if self.execution_request is not None
            else None
        )

        payload["paper_fill"] = (
            self.paper_fill.to_dict()
            if self.paper_fill is not None
            else None
        )

        payload["portfolio_result"] = (
            self.portfolio_result.to_dict()
            if self.portfolio_result is not None
            else None
        )

        payload["valuation_result"] = (
            self.valuation_result.to_dict()
            if self.valuation_result is not None
            else None
        )

        payload["performance_result"] = (
            self.performance_result.to_dict()
            if self.performance_result is not None
            else None
        )

        return payload


def normalize_symbol(symbol: str) -> str:
    """
    Symbol을 대문자로 정규화합니다.
    """

    normalized = str(symbol).strip().upper()

    if not normalized:
        raise ValueError(
            "Symbol이 비어 있습니다."
        )

    return normalized


def round_money(value: float) -> float:
    """
    금액을 소수점 둘째 자리로 반올림합니다.
    """

    return round(float(value), 2)


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    임시 파일을 이용해 JSON을 안전하게 저장합니다.
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
    JSON 파일을 읽습니다.
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


def validate_pipeline_policy(
    policy: PaperTradingDailyPipelinePolicy,
) -> tuple[bool, list[str]]:
    """
    V10.2 Pipeline Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingDailyPipelinePolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingDailyPipelinePolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    boolean_fields = {
        "stop_on_stage_failure": (
            policy.stop_on_stage_failure
        ),
        "require_request_checks": (
            policy.require_request_checks
        ),
        "require_fill_checks": (
            policy.require_fill_checks
        ),
        "require_portfolio_checks": (
            policy.require_portfolio_checks
        ),
        "require_valuation_checks": (
            policy.require_valuation_checks
        ),
        "require_performance_checks": (
            policy.require_performance_checks
        ),
        "save_stage_outputs": (
            policy.save_stage_outputs
        ),
        "use_fill_price_for_valuation": (
            policy.use_fill_price_for_valuation
        ),
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

    if not policy.paper_only:
        errors.append(
            "V10.2에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.2에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def create_pending_stages(
    policy: PaperTradingDailyPipelinePolicy,
) -> dict[str, PaperTradingPipelineStageResult]:
    """
    실행 전 5개 Pipeline Stage를 SKIPPED 상태로 생성합니다.
    """

    required_checks = {
        "EXECUTION_REQUEST": (
            policy.require_request_checks
        ),
        "PAPER_BROKER": (
            policy.require_fill_checks
        ),
        "PORTFOLIO_UPDATE": (
            policy.require_portfolio_checks
        ),
        "PORTFOLIO_VALUATION": (
            policy.require_valuation_checks
        ),
        "PERFORMANCE_TRACKING": (
            policy.require_performance_checks
        ),
    }

    return {
        stage_name: PaperTradingPipelineStageResult(
            stage_name=stage_name,
            stage_order=index,
            stage_status="SKIPPED",
            stage_status_label="아직 실행되지 않음",
            started_at=None,
            completed_at=None,
            source_id=None,
            result_id=None,
            checks_required=required_checks[
                stage_name
            ],
            checks_passed=False,
            output_saved=False,
            output_paths=[],
            error_message=None,
            reasons=[],
            warnings=[],
        )
        for index, stage_name in enumerate(
            PIPELINE_STAGE_NAMES,
            start=1,
        )
    }


def start_stage(
    stage: PaperTradingPipelineStageResult,
) -> None:
    """
    Stage 시작 시간을 기록합니다.
    """

    stage.started_at = datetime.now().isoformat()
    stage.stage_status = "SKIPPED"
    stage.stage_status_label = "실행 중"


def complete_stage(
    stage: PaperTradingPipelineStageResult,
    source_id: str | None,
    result_id: str | None,
    checks_passed: bool,
    output_paths: tuple[Path, ...] | list[Path] | None,
    success_label: str,
    reasons: list[str] | None = None,
    warnings: list[str] | None = None,
) -> None:
    """
    Stage의 성공 또는 차단 상태를 기록합니다.
    """

    stage.completed_at = datetime.now().isoformat()
    stage.source_id = source_id
    stage.result_id = result_id
    stage.checks_passed = bool(checks_passed)

    if checks_passed or not stage.checks_required:
        stage.stage_status = "COMPLETED"
        stage.stage_status_label = success_label
    else:
        stage.stage_status = "BLOCKED"
        stage.stage_status_label = (
            "필수 검사 실패로 다음 단계 차단"
        )

    paths = list(output_paths or [])

    stage.output_paths = [
        str(path)
        for path in paths
    ]
    stage.output_saved = bool(paths)

    stage.reasons = list(reasons or [])
    stage.warnings = list(warnings or [])


def fail_stage(
    stage: PaperTradingPipelineStageResult,
    error: Exception,
) -> None:
    """
    예외가 발생한 Stage를 FAILED로 기록합니다.
    """

    stage.completed_at = datetime.now().isoformat()
    stage.stage_status = "FAILED"
    stage.stage_status_label = "Stage 실행 예외 발생"
    stage.checks_passed = False
    stage.error_message = (
        f"{type(error).__name__}: {error}"
    )
    stage.warnings.append(
        stage.error_message
    )


def can_continue_after_stage(
    stage: PaperTradingPipelineStageResult,
    policy: PaperTradingDailyPipelinePolicy,
) -> bool:
    """
    현재 Stage 이후 다음 Stage를 실행할지 결정합니다.
    """

    if stage.stage_status == "COMPLETED":
        return True

    return not policy.stop_on_stage_failure


def save_paths_if_enabled(
    enabled: bool,
    save_function: Any,
    result: Any,
) -> tuple[Path, ...]:
    """
    Policy가 허용할 때 Stage 결과를 저장합니다.
    """

    if not enabled:
        return ()

    saved_paths = save_function(result)

    if isinstance(saved_paths, Path):
        return (saved_paths,)

    return tuple(saved_paths)


def run_paper_trading_daily_pipeline(
    symbol: str = "AAPL",
    account_cash: float = 10_000.0,
    latest_prices: dict[str, float] | None = None,
    pipeline_policy: (
        PaperTradingDailyPipelinePolicy
        | None
    ) = None,
    execution_request: (
        PaperExecutionRequestResult
        | None
    ) = None,
    paper_fill: PaperBrokerFillResult | None = None,
    portfolio_state: PaperPortfolioState | None = None,
) -> PaperTradingDailyPipelineResult:
    """
    V9.7부터 V10.1까지의 Paper Trading 단계를 한 번에 실행합니다.

    실행 순서:

    1. V9.7 Paper Execution Request
    2. V9.8 Paper Broker Simulator
    3. V9.9 Paper Portfolio Manager
    4. V10.0 Paper Portfolio Valuation
    5. V10.1 Portfolio Performance Tracker

    실제 Broker API 또는 Live Execution은 수행하지 않습니다.
    """

    normalized_symbol = normalize_symbol(symbol)

    policy = (
        pipeline_policy
        if pipeline_policy is not None
        else PaperTradingDailyPipelinePolicy()
    )

    policy_valid, policy_errors = (
        validate_pipeline_policy(policy)
    )

    stages = create_pending_stages(policy)

    request_result: (
        PaperExecutionRequestResult
        | None
    ) = None
    fill_result: PaperBrokerFillResult | None = None
    portfolio_result: PaperPortfolioResult | None = None
    valuation_result: (
        PaperPortfolioValuationResult
        | None
    ) = None
    performance_result: (
        PaperPortfolioPerformanceResult
        | None
    ) = None

    reasons: list[str] = []
    warnings: list[str] = list(policy_errors)

    if not policy_valid:
        request_stage = stages[
            "EXECUTION_REQUEST"
        ]
        request_stage.stage_status = "FAILED"
        request_stage.stage_status_label = (
            "Pipeline Policy 검사 실패"
        )
        request_stage.completed_at = (
            datetime.now().isoformat()
        )
        request_stage.warnings.extend(
            policy_errors
        )

    else:
        request_stage = stages[
            "EXECUTION_REQUEST"
        ]
        start_stage(request_stage)

        try:
            request_result = (
                execution_request
                if execution_request is not None
                else run_paper_execution_request_builder(
                    symbol=normalized_symbol,
                    account_cash=account_cash,
                    approval_actor=(
                        "V10.2_PIPELINE_USER"
                    ),
                    approval_note=(
                        "V10.2 Paper Trading Daily "
                        "Pipeline paper approval"
                    ),
                )
            )

            if request_result.symbol != normalized_symbol:
                raise ValueError(
                    "Execution Request Symbol이 "
                    "Pipeline Symbol과 다릅니다."
                )

            request_checks_passed = (
                request_result.all_checks_passed
                and request_result.paper_execution_authorized
                and request_result.request_status
                == "READY_FOR_PAPER"
                and not request_result.live_execution_authorized
                and not request_result.broker_order_created
                and not request_result.live_order_created
            )

            request_paths = save_paths_if_enabled(
                enabled=(
                    policy.save_stage_outputs
                    and execution_request is None
                ),
                save_function=(
                    save_paper_execution_request
                ),
                result=request_result,
            )

            complete_stage(
                stage=request_stage,
                source_id=None,
                result_id=request_result.request_id,
                checks_passed=request_checks_passed,
                output_paths=request_paths,
                success_label=(
                    "V9.7 Paper Execution Request 완료"
                ),
                reasons=request_result.reasons,
                warnings=request_result.warnings,
            )

        except Exception as error:
            fail_stage(
                request_stage,
                error,
            )
            warnings.append(
                f"Execution Request Stage 실패: {error}"
            )

    broker_stage = stages["PAPER_BROKER"]

    if can_continue_after_stage(
        request_stage,
        policy,
    ):
        start_stage(broker_stage)

        try:
            if paper_fill is not None:
                fill_result = paper_fill
            elif request_result is not None:
                fill_result = run_paper_broker_simulator(
                    symbol=normalized_symbol,
                    request=request_result,
                    account_cash=account_cash,
                )
            else:
                raise RuntimeError(
                    "Paper Broker에 전달할 Request가 없습니다."
                )

            if fill_result.symbol != normalized_symbol:
                raise ValueError(
                    "Paper Fill Symbol이 "
                    "Pipeline Symbol과 다릅니다."
                )

            fill_checks_passed = (
                fill_result.all_checks_passed
                and fill_result.paper_fill_created
                and fill_result.fill_status == "FILLED"
                and not fill_result.broker_api_called
                and not fill_result.broker_order_created
                and not fill_result.live_order_created
                and not fill_result.live_execution_authorized
            )

            fill_paths = save_paths_if_enabled(
                enabled=(
                    policy.save_stage_outputs
                    and paper_fill is None
                ),
                save_function=save_paper_broker_fill,
                result=fill_result,
            )

            complete_stage(
                stage=broker_stage,
                source_id=fill_result.request_id,
                result_id=fill_result.fill_id,
                checks_passed=fill_checks_passed,
                output_paths=fill_paths,
                success_label=(
                    "V9.8 Paper Broker Fill 완료"
                ),
                reasons=fill_result.reasons,
                warnings=fill_result.warnings,
            )

        except Exception as error:
            fail_stage(
                broker_stage,
                error,
            )
            warnings.append(
                f"Paper Broker Stage 실패: {error}"
            )

    portfolio_stage = stages[
        "PORTFOLIO_UPDATE"
    ]

    if can_continue_after_stage(
        broker_stage,
        policy,
    ):
        start_stage(portfolio_stage)

        try:
            if fill_result is None:
                raise RuntimeError(
                    "Portfolio에 전달할 Fill이 없습니다."
                )

            working_portfolio = (
                portfolio_state
                if portfolio_state is not None
                else load_latest_portfolio_state(
                    initial_cash=account_cash
                )
            )

            portfolio_result = (
                run_paper_portfolio_manager(
                    symbol=normalized_symbol,
                    fill_result=fill_result,
                    portfolio_state=working_portfolio,
                    initial_cash=account_cash,
                )
            )

            portfolio_checks_passed = (
                portfolio_result.all_checks_passed
                and portfolio_result.portfolio_updated
                and portfolio_result.portfolio_status
                == "UPDATED"
                and not portfolio_result.broker_api_called
                and not portfolio_result.live_order_created
                and not (
                    portfolio_result
                    .live_execution_authorized
                )
            )

            portfolio_paths = save_paths_if_enabled(
                enabled=policy.save_stage_outputs,
                save_function=(
                    save_paper_portfolio_result
                ),
                result=portfolio_result,
            )

            complete_stage(
                stage=portfolio_stage,
                source_id=(
                    portfolio_result.source_fill_id
                ),
                result_id=portfolio_result.update_id,
                checks_passed=(
                    portfolio_checks_passed
                ),
                output_paths=portfolio_paths,
                success_label=(
                    "V9.9 Paper Portfolio Update 완료"
                ),
                reasons=portfolio_result.reasons,
                warnings=portfolio_result.warnings,
            )

        except Exception as error:
            fail_stage(
                portfolio_stage,
                error,
            )
            warnings.append(
                f"Portfolio Update Stage 실패: {error}"
            )

    valuation_stage = stages[
        "PORTFOLIO_VALUATION"
    ]

    if can_continue_after_stage(
        portfolio_stage,
        policy,
    ):
        start_stage(valuation_stage)

        try:
            if portfolio_result is None:
                raise RuntimeError(
                    "Valuation에 전달할 Portfolio가 없습니다."
                )

            valuation_prices = dict(
                latest_prices or {}
            )

            if (
                policy.use_fill_price_for_valuation
                and fill_result is not None
                and fill_result.fill_price > 0
                and normalized_symbol
                not in {
                    str(key).strip().upper()
                    for key in valuation_prices
                }
            ):
                valuation_prices[
                    normalized_symbol
                ] = fill_result.fill_price

            valuation_result = (
                run_paper_portfolio_valuation(
                    portfolio_state=(
                        portfolio_result
                        .portfolio_state
                    ),
                    latest_prices=valuation_prices,
                    initial_cash=account_cash,
                )
            )

            valuation_checks_passed = (
                valuation_result.all_checks_passed
                and valuation_result.portfolio_updated
                and valuation_result.valuation_status
                in {
                    "VALUED",
                    "PARTIAL",
                    "NO_POSITIONS",
                }
                and not valuation_result.broker_api_called
                and not valuation_result.broker_order_created
                and not valuation_result.live_order_created
                and not (
                    valuation_result
                    .live_execution_authorized
                )
            )

            valuation_paths = save_paths_if_enabled(
                enabled=policy.save_stage_outputs,
                save_function=(
                    save_paper_portfolio_valuation
                ),
                result=valuation_result,
            )

            complete_stage(
                stage=valuation_stage,
                source_id=(
                    valuation_result.portfolio_id
                ),
                result_id=(
                    valuation_result.valuation_id
                ),
                checks_passed=(
                    valuation_checks_passed
                ),
                output_paths=valuation_paths,
                success_label=(
                    "V10.0 Paper Portfolio Valuation 완료"
                ),
                reasons=valuation_result.reasons,
                warnings=valuation_result.warnings,
            )

        except Exception as error:
            fail_stage(
                valuation_stage,
                error,
            )
            warnings.append(
                f"Portfolio Valuation Stage 실패: {error}"
            )

    performance_stage = stages[
        "PERFORMANCE_TRACKING"
    ]

    if can_continue_after_stage(
        valuation_stage,
        policy,
    ):
        start_stage(performance_stage)

        try:
            if valuation_result is None:
                raise RuntimeError(
                    "Performance Tracker에 전달할 "
                    "Valuation이 없습니다."
                )

            performance_result = (
                run_paper_portfolio_performance_tracker(
                    valuation_result=valuation_result,
                    initial_cash=account_cash,
                )
            )

            performance_checks_passed = (
                performance_result.all_checks_passed
                and performance_result
                .performance_status
                in {
                    "TRACKED",
                    "FIRST_SNAPSHOT",
                    "NO_CHANGE",
                }
                and not performance_result.broker_api_called
                and not performance_result.broker_order_created
                and not performance_result.live_order_created
                and not (
                    performance_result
                    .live_execution_authorized
                )
            )

            performance_paths = save_paths_if_enabled(
                enabled=policy.save_stage_outputs,
                save_function=(
                    save_paper_portfolio_performance
                ),
                result=performance_result,
            )

            complete_stage(
                stage=performance_stage,
                source_id=(
                    performance_result
                    .source_valuation_id
                ),
                result_id=(
                    performance_result.performance_id
                ),
                checks_passed=(
                    performance_checks_passed
                ),
                output_paths=performance_paths,
                success_label=(
                    "V10.1 Portfolio Performance Tracking 완료"
                ),
                reasons=performance_result.reasons,
                warnings=performance_result.warnings,
            )

        except Exception as error:
            fail_stage(
                performance_stage,
                error,
            )
            warnings.append(
                f"Performance Tracking Stage 실패: {error}"
            )

    completed_stage_count = sum(
        stage.stage_status == "COMPLETED"
        for stage in stages.values()
    )
    blocked_stage_count = sum(
        stage.stage_status == "BLOCKED"
        for stage in stages.values()
    )
    failed_stage_count = sum(
        stage.stage_status == "FAILED"
        for stage in stages.values()
    )
    skipped_stage_count = sum(
        stage.stage_status == "SKIPPED"
        for stage in stages.values()
    )

    request_stage_passed = (
        stages["EXECUTION_REQUEST"].stage_status
        == "COMPLETED"
    )
    broker_stage_passed = (
        stages["PAPER_BROKER"].stage_status
        == "COMPLETED"
    )
    portfolio_stage_passed = (
        stages["PORTFOLIO_UPDATE"].stage_status
        == "COMPLETED"
    )
    valuation_stage_passed = (
        stages["PORTFOLIO_VALUATION"].stage_status
        == "COMPLETED"
    )
    performance_stage_passed = (
        stages["PERFORMANCE_TRACKING"].stage_status
        == "COMPLETED"
    )

    all_required_stages_passed = all(
        (
            request_stage_passed
            or not policy.require_request_checks,
            broker_stage_passed
            or not policy.require_fill_checks,
            portfolio_stage_passed
            or not policy.require_portfolio_checks,
            valuation_stage_passed
            or not policy.require_valuation_checks,
            performance_stage_passed
            or not policy.require_performance_checks,
        )
    )

    if (
        policy_valid
        and all_required_stages_passed
        and completed_stage_count == len(
            PIPELINE_STAGE_NAMES
        )
    ):
        pipeline_status = "COMPLETED"
        pipeline_status_label = (
            "모든 Paper Trading 단계 완료"
        )
    elif failed_stage_count > 0:
        pipeline_status = "FAILED"
        pipeline_status_label = (
            "Pipeline Stage 실행 실패"
        )
    elif blocked_stage_count > 0:
        pipeline_status = "BLOCKED"
        pipeline_status_label = (
            "필수 검사 실패로 Pipeline 차단"
        )
    else:
        pipeline_status = "PARTIAL"
        pipeline_status_label = (
            "일부 Pipeline Stage만 완료"
        )

    all_checks_passed = (
        policy_valid
        and all_required_stages_passed
        and pipeline_status == "COMPLETED"
    )

    if pipeline_status == "COMPLETED":
        reasons.append(
            "V9.7부터 V10.1까지 모든 Paper 단계가 완료되었습니다."
        )
        next_actions = [
            "V10.2 Pipeline 결과를 JSON으로 저장합니다.",
            "다음 실행 전 최신 Portfolio State를 확인합니다.",
            "V10.3에서 Daily Pipeline 통합 테스트를 추가합니다.",
        ]
    else:
        reasons.append(
            "실패 또는 차단된 Stage 때문에 Pipeline을 완료하지 못했습니다."
        )
        next_actions = [
            "Stage Summary에서 최초 실패 단계를 확인합니다.",
            "해당 단계의 Warnings와 Error Message를 확인합니다.",
            "문제를 수정한 후 V10.2 Pipeline을 다시 실행합니다.",
        ]

    warnings.extend(
        [
            (
                "V10.2는 연구용 Paper Trading "
                "통합 Pipeline입니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    final_cash_balance = (
        valuation_result.cash_balance
        if valuation_result is not None
        else (
            portfolio_result.updated_cash_balance
            if portfolio_result is not None
            else round_money(account_cash)
        )
    )

    final_market_value = (
        valuation_result.updated_total_market_value
        if valuation_result is not None
        else (
            portfolio_result.total_market_value
            if portfolio_result is not None
            else 0.0
        )
    )

    final_equity = (
        performance_result.current_equity
        if performance_result is not None
        else (
            valuation_result.updated_total_equity
            if valuation_result is not None
            else (
                portfolio_result.total_equity
                if portfolio_result is not None
                else round_money(account_cash)
            )
        )
    )

    result = PaperTradingDailyPipelineResult(
        version="V10.2",
        created_at=datetime.now().isoformat(),
        pipeline_id=str(uuid.uuid4()),
        symbol=normalized_symbol,
        pipeline_status=pipeline_status,
        pipeline_status_label=(
            pipeline_status_label
        ),
        initial_cash=round_money(account_cash),
        final_cash_balance=round_money(
            final_cash_balance
        ),
        final_market_value=round_money(
            final_market_value
        ),
        final_equity=round_money(final_equity),
        request_id=(
            request_result.request_id
            if request_result is not None
            else None
        ),
        fill_id=(
            fill_result.fill_id
            if fill_result is not None
            else None
        ),
        portfolio_update_id=(
            portfolio_result.update_id
            if portfolio_result is not None
            else None
        ),
        valuation_id=(
            valuation_result.valuation_id
            if valuation_result is not None
            else None
        ),
        performance_id=(
            performance_result.performance_id
            if performance_result is not None
            else None
        ),
        completed_stage_count=(
            completed_stage_count
        ),
        blocked_stage_count=blocked_stage_count,
        failed_stage_count=failed_stage_count,
        skipped_stage_count=skipped_stage_count,
        request_stage_passed=request_stage_passed,
        broker_stage_passed=broker_stage_passed,
        portfolio_stage_passed=(
            portfolio_stage_passed
        ),
        valuation_stage_passed=(
            valuation_stage_passed
        ),
        performance_stage_passed=(
            performance_stage_passed
        ),
        all_required_stages_passed=(
            all_required_stages_passed
        ),
        all_checks_passed=all_checks_passed,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        pipeline_policy=policy,
        stages=stages,
        execution_request=request_result,
        paper_fill=fill_result,
        portfolio_result=portfolio_result,
        valuation_result=valuation_result,
        performance_result=performance_result,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_daily_pipeline(result)

    return result


def save_paper_trading_daily_pipeline(
    result: PaperTradingDailyPipelineResult,
) -> tuple[Path, Path]:
    """
    V10.2 Pipeline Report와 Latest JSON을 저장합니다.
    """

    PAPER_DAILY_PIPELINE_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_DAILY_PIPELINE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_daily_pipeline_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_DAILY_PIPELINE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_daily_pipeline_latest.json"
        )
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_daily_pipeline(
    symbol: str = "AAPL",
) -> dict[str, Any]:
    """
    저장된 최신 V10.2 Pipeline 결과를 읽습니다.
    """

    normalized_symbol = normalize_symbol(symbol)

    latest_path = (
        PAPER_DAILY_PIPELINE_OUTPUT_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "paper_daily_pipeline_latest.json"
        )
    )

    return read_json_file(latest_path)


def print_paper_trading_daily_pipeline(
    result: PaperTradingDailyPipelineResult,
) -> None:
    """
    V10.2 Pipeline 결과를 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        f"{result.symbol} V10.2 "
        "PAPER TRADING DAILY PIPELINE"
    )
    print("=" * line_length)

    print(
        f"Pipeline status                : "
        f"{result.pipeline_status}"
    )
    print(
        f"Pipeline status label          : "
        f"{result.pipeline_status_label}"
    )
    print(
        f"Pipeline ID                    : "
        f"{result.pipeline_id}"
    )

    print()
    print("STAGE SUMMARY")
    print("-" * line_length)

    for stage_name in PIPELINE_STAGE_NAMES:
        stage = result.stages[stage_name]

        print(
            f"{stage.stage_order}. "
            f"{stage.stage_name:<26}: "
            f"{stage.stage_status} - "
            f"{stage.stage_status_label}"
        )

        if stage.error_message:
            print(
                f"   Error                        : "
                f"{stage.error_message}"
            )

    print()
    print("PIPELINE COUNTS")
    print("-" * line_length)

    print(
        f"Completed stages               : "
        f"{result.completed_stage_count}"
    )
    print(
        f"Blocked stages                 : "
        f"{result.blocked_stage_count}"
    )
    print(
        f"Failed stages                  : "
        f"{result.failed_stage_count}"
    )
    print(
        f"Skipped stages                 : "
        f"{result.skipped_stage_count}"
    )

    print()
    print("PORTFOLIO SUMMARY")
    print("-" * line_length)

    print(
        f"Initial cash                   : "
        f"${result.initial_cash:,.2f}"
    )
    print(
        f"Final cash balance             : "
        f"${result.final_cash_balance:,.2f}"
    )
    print(
        f"Final market value             : "
        f"${result.final_market_value:,.2f}"
    )
    print(
        f"Final equity                   : "
        f"${result.final_equity:,.2f}"
    )

    print()
    print("RESULT IDS")
    print("-" * line_length)

    print(
        f"Request ID                     : "
        f"{result.request_id}"
    )
    print(
        f"Fill ID                        : "
        f"{result.fill_id}"
    )
    print(
        f"Portfolio Update ID            : "
        f"{result.portfolio_update_id}"
    )
    print(
        f"Valuation ID                   : "
        f"{result.valuation_id}"
    )
    print(
        f"Performance ID                 : "
        f"{result.performance_id}"
    )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Request stage passed           : "
        f"{result.request_stage_passed}"
    )
    print(
        f"Broker stage passed            : "
        f"{result.broker_stage_passed}"
    )
    print(
        f"Portfolio stage passed         : "
        f"{result.portfolio_stage_passed}"
    )
    print(
        f"Valuation stage passed         : "
        f"{result.valuation_stage_passed}"
    )
    print(
        f"Performance stage passed       : "
        f"{result.performance_stage_passed}"
    )
    print(
        f"All required stages passed     : "
        f"{result.all_required_stages_passed}"
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
        "주의: V10.2는 연구용 Paper Trading Pipeline이며 "
        "실제 Broker API 또는 실제 주문을 수행하지 않습니다."
    )


if __name__ == "__main__":
    pipeline_result = run_paper_trading_daily_pipeline()

    save_paper_trading_daily_pipeline(
        pipeline_result
    )
