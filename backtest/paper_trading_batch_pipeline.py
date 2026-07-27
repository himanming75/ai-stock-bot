import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backtest.paper_trading_daily_pipeline import (
    PaperTradingDailyPipelineResult,
    run_paper_trading_daily_pipeline,
    save_paper_trading_daily_pipeline,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_BATCH_PIPELINE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_batch_pipeline"
)


VALID_BATCH_STATUSES = {
    "COMPLETED",
    "PARTIAL",
    "BLOCKED",
    "FAILED",
}


VALID_SYMBOL_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "FAILED",
    "SKIPPED",
}


@dataclass(frozen=True)
class PaperTradingBatchPipelinePolicy:
    """
    V10.3 Multi-Symbol Paper Trading Batch Pipeline 정책입니다.

    여러 종목을 순차 실행하며 종목별 실패를 격리합니다.
    실제 Broker 주문과 Live Execution은 항상 차단합니다.
    """

    minimum_symbol_count: int = 1
    maximum_symbol_count: int = 50

    reject_duplicate_symbols: bool = False
    continue_on_symbol_failure: bool = True
    require_all_symbols_success: bool = False

    save_daily_pipeline_outputs: bool = True
    save_batch_output: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingBatchSymbolResult:
    """
    한 종목의 V10.2 Pipeline 실행 요약입니다.
    """

    symbol: str
    sequence: int

    symbol_status: str
    symbol_status_label: str

    started_at: str | None
    completed_at: str | None

    pipeline_id: str | None
    pipeline_status: str | None

    completed_stage_count: int
    blocked_stage_count: int
    failed_stage_count: int
    skipped_stage_count: int

    initial_cash: float
    final_cash_balance: float
    final_market_value: float
    final_equity: float

    all_checks_passed: bool
    output_saved: bool
    output_paths: list[str] = field(
        default_factory=list
    )

    execution_blocked: bool = True
    broker_api_called: bool = False
    broker_order_created: bool = False
    live_order_created: bool = False
    live_execution_authorized: bool = False

    error_message: str | None = None

    reasons: list[str] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )

    pipeline_result: (
        PaperTradingDailyPipelineResult
        | None
    ) = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["pipeline_result"] = (
            self.pipeline_result.to_dict()
            if self.pipeline_result is not None
            else None
        )

        return payload


@dataclass
class PaperTradingBatchPipelineResult:
    """
    V10.3 Multi-Symbol Batch Pipeline 전체 결과입니다.
    """

    version: str
    created_at: str

    batch_id: str
    batch_status: str
    batch_status_label: str

    requested_symbols: list[str]
    normalized_symbols: list[str]
    duplicate_symbols: list[str]

    requested_symbol_count: int
    unique_symbol_count: int

    completed_symbol_count: int
    blocked_symbol_count: int
    failed_symbol_count: int
    skipped_symbol_count: int

    success_rate_percent: float

    initial_cash: float
    final_cash_balance: float
    final_market_value: float
    final_equity: float
    batch_equity_change: float
    batch_equity_change_percent: float

    policy_checks_passed: bool
    symbol_checks_passed: bool
    result_checks_passed: bool
    all_required_symbols_passed: bool
    all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    batch_policy: PaperTradingBatchPipelinePolicy
    symbol_results: dict[
        str,
        PaperTradingBatchSymbolResult,
    ]

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["batch_policy"] = (
            self.batch_policy.to_dict()
        )

        payload["symbol_results"] = {
            symbol: result.to_dict()
            for symbol, result
            in self.symbol_results.items()
        }

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


def is_valid_number(value: Any) -> bool:
    """
    bool을 제외한 유한 숫자인지 검사합니다.
    """

    if isinstance(value, bool):
        return False

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return False

    return (
        numeric_value == numeric_value
        and numeric_value
        not in {
            float("inf"),
            float("-inf"),
        }
    )


def round_money(value: float) -> float:
    """
    금액을 소수점 둘째 자리로 반올림합니다.
    """

    return round(float(value), 2)


def round_percent(value: float) -> float:
    """
    비율을 소수점 넷째 자리로 반올림합니다.
    """

    return round(float(value), 4)


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


def validate_batch_policy(
    policy: PaperTradingBatchPipelinePolicy,
) -> tuple[bool, list[str]]:
    """
    V10.3 Batch Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingBatchPipelinePolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingBatchPipelinePolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    integer_fields = {
        "minimum_symbol_count": (
            policy.minimum_symbol_count
        ),
        "maximum_symbol_count": (
            policy.maximum_symbol_count
        ),
    }

    for field_name, value in integer_fields.items():
        if not isinstance(value, int):
            errors.append(
                f"{field_name}가 int 형식이 아닙니다."
            )
        elif value <= 0:
            errors.append(
                f"{field_name}는 0보다 커야 합니다."
            )

    if (
        isinstance(policy.minimum_symbol_count, int)
        and isinstance(
            policy.maximum_symbol_count,
            int,
        )
        and policy.minimum_symbol_count
        > policy.maximum_symbol_count
    ):
        errors.append(
            "Minimum Symbol Count는 Maximum Symbol Count보다 "
            "클 수 없습니다."
        )

    boolean_fields = {
        "reject_duplicate_symbols": (
            policy.reject_duplicate_symbols
        ),
        "continue_on_symbol_failure": (
            policy.continue_on_symbol_failure
        ),
        "require_all_symbols_success": (
            policy.require_all_symbols_success
        ),
        "save_daily_pipeline_outputs": (
            policy.save_daily_pipeline_outputs
        ),
        "save_batch_output": (
            policy.save_batch_output
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
            "V10.3에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.3에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def normalize_symbols(
    symbols: list[str] | tuple[str, ...],
) -> tuple[list[str], list[str]]:
    """
    Symbol 목록을 정규화하고 중복 목록을 반환합니다.

    첫 번째로 등장한 순서는 유지합니다.
    """

    if not isinstance(symbols, (list, tuple)):
        raise TypeError(
            "symbols는 List 또는 Tuple 형식이어야 합니다."
        )

    normalized_symbols: list[str] = []
    duplicate_symbols: list[str] = []
    seen: set[str] = set()

    for raw_symbol in symbols:
        normalized_symbol = normalize_symbol(
            raw_symbol
        )

        if normalized_symbol in seen:
            if (
                normalized_symbol
                not in duplicate_symbols
            ):
                duplicate_symbols.append(
                    normalized_symbol
                )
            continue

        seen.add(normalized_symbol)
        normalized_symbols.append(
            normalized_symbol
        )

    return (
        normalized_symbols,
        duplicate_symbols,
    )


def validate_symbol_batch(
    requested_symbols: list[str] | tuple[str, ...],
    normalized_symbols: list[str],
    duplicate_symbols: list[str],
    policy: PaperTradingBatchPipelinePolicy,
) -> tuple[bool, list[str]]:
    """
    Batch Symbol 개수와 중복 정책을 검사합니다.
    """

    errors: list[str] = []

    if (
        len(normalized_symbols)
        < policy.minimum_symbol_count
    ):
        errors.append(
            "고유 Symbol 수가 Minimum Symbol Count보다 적습니다."
        )

    if (
        len(normalized_symbols)
        > policy.maximum_symbol_count
    ):
        errors.append(
            "고유 Symbol 수가 Maximum Symbol Count를 초과합니다."
        )

    if (
        policy.reject_duplicate_symbols
        and duplicate_symbols
    ):
        errors.append(
            (
                "중복 Symbol이 허용되지 않습니다: "
                f"{', '.join(duplicate_symbols)}"
            )
        )

    if len(requested_symbols) == 0:
        errors.append(
            "요청 Symbol 목록이 비어 있습니다."
        )

    return (not errors, errors)


def normalize_latest_prices(
    latest_prices: dict[str, float] | None,
) -> dict[str, float]:
    """
    여러 종목의 최신 가격 Dictionary를 정규화합니다.
    """

    if latest_prices is None:
        return {}

    if not isinstance(latest_prices, dict):
        raise TypeError(
            "latest_prices는 Dictionary 형식이어야 합니다."
        )

    normalized: dict[str, float] = {}

    for symbol, price in latest_prices.items():
        normalized_symbol = normalize_symbol(
            symbol
        )

        if not is_valid_number(price):
            raise ValueError(
                f"{normalized_symbol} 가격이 유효하지 않습니다."
            )

        numeric_price = float(price)

        if numeric_price <= 0:
            raise ValueError(
                f"{normalized_symbol} 가격은 0보다 커야 합니다."
            )

        normalized[
            normalized_symbol
        ] = round(numeric_price, 4)

    return normalized


def create_skipped_symbol_result(
    symbol: str,
    sequence: int,
    initial_cash: float,
    reason: str,
) -> PaperTradingBatchSymbolResult:
    """
    실행되지 않은 종목 결과를 생성합니다.
    """

    return PaperTradingBatchSymbolResult(
        symbol=symbol,
        sequence=sequence,
        symbol_status="SKIPPED",
        symbol_status_label="Batch 정책에 의해 실행 중단",
        started_at=None,
        completed_at=datetime.now().isoformat(),
        pipeline_id=None,
        pipeline_status=None,
        completed_stage_count=0,
        blocked_stage_count=0,
        failed_stage_count=0,
        skipped_stage_count=5,
        initial_cash=round_money(initial_cash),
        final_cash_balance=round_money(initial_cash),
        final_market_value=0.0,
        final_equity=round_money(initial_cash),
        all_checks_passed=False,
        output_saved=False,
        output_paths=[],
        error_message=None,
        reasons=[reason],
        warnings=[],
        pipeline_result=None,
    )


def summarize_daily_pipeline(
    symbol: str,
    sequence: int,
    pipeline_result: PaperTradingDailyPipelineResult,
    output_paths: tuple[Path, ...] | list[Path] | None,
) -> PaperTradingBatchSymbolResult:
    """
    V10.2 Result를 V10.3 종목별 요약으로 변환합니다.
    """

    if pipeline_result.pipeline_status == "COMPLETED":
        symbol_status = "COMPLETED"
        symbol_status_label = (
            "V10.2 Daily Pipeline 완료"
        )
    elif pipeline_result.pipeline_status == "BLOCKED":
        symbol_status = "BLOCKED"
        symbol_status_label = (
            "V10.2 Daily Pipeline 검사 차단"
        )
    elif pipeline_result.pipeline_status == "FAILED":
        symbol_status = "FAILED"
        symbol_status_label = (
            "V10.2 Daily Pipeline 실행 실패"
        )
    else:
        symbol_status = "BLOCKED"
        symbol_status_label = (
            "V10.2 Daily Pipeline 일부 완료"
        )

    paths = list(output_paths or [])

    return PaperTradingBatchSymbolResult(
        symbol=symbol,
        sequence=sequence,
        symbol_status=symbol_status,
        symbol_status_label=symbol_status_label,
        started_at=pipeline_result.created_at,
        completed_at=datetime.now().isoformat(),
        pipeline_id=pipeline_result.pipeline_id,
        pipeline_status=pipeline_result.pipeline_status,
        completed_stage_count=(
            pipeline_result.completed_stage_count
        ),
        blocked_stage_count=(
            pipeline_result.blocked_stage_count
        ),
        failed_stage_count=(
            pipeline_result.failed_stage_count
        ),
        skipped_stage_count=(
            pipeline_result.skipped_stage_count
        ),
        initial_cash=round_money(
            pipeline_result.initial_cash
        ),
        final_cash_balance=round_money(
            pipeline_result.final_cash_balance
        ),
        final_market_value=round_money(
            pipeline_result.final_market_value
        ),
        final_equity=round_money(
            pipeline_result.final_equity
        ),
        all_checks_passed=(
            pipeline_result.all_checks_passed
        ),
        output_saved=bool(paths),
        output_paths=[
            str(path)
            for path in paths
        ],
        execution_blocked=(
            pipeline_result.execution_blocked
        ),
        broker_api_called=(
            pipeline_result.broker_api_called
        ),
        broker_order_created=(
            pipeline_result.broker_order_created
        ),
        live_order_created=(
            pipeline_result.live_order_created
        ),
        live_execution_authorized=(
            pipeline_result
            .live_execution_authorized
        ),
        error_message=None,
        reasons=list(pipeline_result.reasons),
        warnings=list(pipeline_result.warnings),
        pipeline_result=pipeline_result,
    )


def create_failed_symbol_result(
    symbol: str,
    sequence: int,
    initial_cash: float,
    started_at: str,
    error: Exception,
) -> PaperTradingBatchSymbolResult:
    """
    종목 실행 중 예외가 발생한 결과를 생성합니다.
    """

    error_message = (
        f"{type(error).__name__}: {error}"
    )

    return PaperTradingBatchSymbolResult(
        symbol=symbol,
        sequence=sequence,
        symbol_status="FAILED",
        symbol_status_label="종목 Pipeline 예외 발생",
        started_at=started_at,
        completed_at=datetime.now().isoformat(),
        pipeline_id=None,
        pipeline_status="FAILED",
        completed_stage_count=0,
        blocked_stage_count=0,
        failed_stage_count=1,
        skipped_stage_count=4,
        initial_cash=round_money(initial_cash),
        final_cash_balance=round_money(initial_cash),
        final_market_value=0.0,
        final_equity=round_money(initial_cash),
        all_checks_passed=False,
        output_saved=False,
        output_paths=[],
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        error_message=error_message,
        reasons=[
            "종목별 V10.2 Pipeline을 완료하지 못했습니다."
        ],
        warnings=[error_message],
        pipeline_result=None,
    )


def validate_symbol_result_safety(
    result: PaperTradingBatchSymbolResult,
) -> tuple[bool, list[str]]:
    """
    종목별 결과가 Paper-only 안전 조건을 지키는지 검사합니다.
    """

    errors: list[str] = []

    if result.symbol_status not in VALID_SYMBOL_STATUSES:
        errors.append(
            "Symbol Status가 유효하지 않습니다."
        )

    if not result.execution_blocked:
        errors.append(
            "Execution이 차단되지 않았습니다."
        )

    if result.broker_api_called:
        errors.append(
            "실제 Broker API가 호출되었습니다."
        )

    if result.broker_order_created:
        errors.append(
            "실제 Broker Order가 생성되었습니다."
        )

    if result.live_order_created:
        errors.append(
            "Live Order가 생성되었습니다."
        )

    if result.live_execution_authorized:
        errors.append(
            "Live Execution이 허용되었습니다."
        )

    return (not errors, errors)


def run_paper_trading_batch_pipeline(
    symbols: list[str] | tuple[str, ...],
    account_cash: float = 10_000.0,
    latest_prices: dict[str, float] | None = None,
    batch_policy: (
        PaperTradingBatchPipelinePolicy
        | None
    ) = None,
    daily_pipeline_runner: (
        Callable[..., PaperTradingDailyPipelineResult]
        | None
    ) = None,
) -> PaperTradingBatchPipelineResult:
    """
    여러 종목에 V10.2 Daily Pipeline을 순차 실행합니다.

    기본 설정에서는 한 종목이 실패해도 다음 종목을 계속 실행합니다.
    실제 Broker API 또는 Live Execution은 수행하지 않습니다.
    """

    policy = (
        batch_policy
        if batch_policy is not None
        else PaperTradingBatchPipelinePolicy()
    )

    policy_valid, policy_errors = (
        validate_batch_policy(policy)
    )

    requested_symbols = [
        str(symbol)
        for symbol in symbols
    ] if isinstance(symbols, (list, tuple)) else []

    normalization_errors: list[str] = []

    try:
        (
            normalized_symbols,
            duplicate_symbols,
        ) = normalize_symbols(symbols)
    except Exception as error:
        normalized_symbols = []
        duplicate_symbols = []
        normalization_errors.append(
            f"Symbol 정규화 실패: {error}"
        )

    symbol_valid, symbol_errors = (
        validate_symbol_batch(
            requested_symbols=(
                requested_symbols
            ),
            normalized_symbols=(
                normalized_symbols
            ),
            duplicate_symbols=(
                duplicate_symbols
            ),
            policy=policy,
        )
    )

    normalized_prices: dict[str, float] = {}
    price_errors: list[str] = []

    try:
        normalized_prices = (
            normalize_latest_prices(
                latest_prices
            )
        )
    except Exception as error:
        price_errors.append(
            f"Latest Prices 검사 실패: {error}"
        )

    input_checks_passed = (
        policy_valid
        and symbol_valid
        and not normalization_errors
        and not price_errors
    )

    runner = (
        daily_pipeline_runner
        if daily_pipeline_runner is not None
        else run_paper_trading_daily_pipeline
    )

    symbol_results: dict[
        str,
        PaperTradingBatchSymbolResult,
    ] = {}

    stop_remaining_symbols = False

    if input_checks_passed:
        for sequence, symbol in enumerate(
            normalized_symbols,
            start=1,
        ):
            if stop_remaining_symbols:
                symbol_results[symbol] = (
                    create_skipped_symbol_result(
                        symbol=symbol,
                        sequence=sequence,
                        initial_cash=account_cash,
                        reason=(
                            "이전 종목 실패 후 Batch 정책에 "
                            "따라 실행하지 않았습니다."
                        ),
                    )
                )
                continue

            started_at = datetime.now().isoformat()

            try:
                pipeline_result = runner(
                    symbol=symbol,
                    account_cash=account_cash,
                    latest_prices=normalized_prices,
                )

                output_paths: tuple[Path, ...] = ()

                if policy.save_daily_pipeline_outputs:
                    output_paths = tuple(
                        save_paper_trading_daily_pipeline(
                            pipeline_result
                        )
                    )

                symbol_result = summarize_daily_pipeline(
                    symbol=symbol,
                    sequence=sequence,
                    pipeline_result=pipeline_result,
                    output_paths=output_paths,
                )

            except Exception as error:
                symbol_result = (
                    create_failed_symbol_result(
                        symbol=symbol,
                        sequence=sequence,
                        initial_cash=account_cash,
                        started_at=started_at,
                        error=error,
                    )
                )

            symbol_results[symbol] = symbol_result

            if (
                symbol_result.symbol_status
                != "COMPLETED"
                and not policy.continue_on_symbol_failure
            ):
                stop_remaining_symbols = True

    completed_symbol_count = sum(
        result.symbol_status == "COMPLETED"
        for result in symbol_results.values()
    )
    blocked_symbol_count = sum(
        result.symbol_status == "BLOCKED"
        for result in symbol_results.values()
    )
    failed_symbol_count = sum(
        result.symbol_status == "FAILED"
        for result in symbol_results.values()
    )
    skipped_symbol_count = sum(
        result.symbol_status == "SKIPPED"
        for result in symbol_results.values()
    )

    unique_symbol_count = len(normalized_symbols)

    if unique_symbol_count > 0:
        success_rate_percent = round_percent(
            (
                completed_symbol_count
                / unique_symbol_count
            )
            * 100.0
        )
    else:
        success_rate_percent = 0.0

    result_safety_errors: list[str] = []

    for symbol, symbol_result in (
        symbol_results.items()
    ):
        safe, safety_errors = (
            validate_symbol_result_safety(
                symbol_result
            )
        )

        if not safe:
            result_safety_errors.extend(
                [
                    f"{symbol}: {error}"
                    for error in safety_errors
                ]
            )

    result_checks_passed = (
        len(symbol_results)
        == unique_symbol_count
        and not result_safety_errors
    )

    all_required_symbols_passed = (
        completed_symbol_count
        == unique_symbol_count
        and unique_symbol_count > 0
    )

    if not input_checks_passed:
        batch_status = "FAILED"
        batch_status_label = (
            "Batch 입력 또는 정책 검사 실패"
        )
    elif all_required_symbols_passed:
        batch_status = "COMPLETED"
        batch_status_label = (
            "모든 종목 Daily Pipeline 완료"
        )
    elif (
        policy.require_all_symbols_success
        and not all_required_symbols_passed
    ):
        batch_status = "BLOCKED"
        batch_status_label = (
            "일부 종목 실패로 전체 Batch 차단"
        )
    elif completed_symbol_count > 0:
        batch_status = "PARTIAL"
        batch_status_label = (
            "일부 종목 Daily Pipeline 완료"
        )
    elif failed_symbol_count > 0:
        batch_status = "FAILED"
        batch_status_label = (
            "모든 실행 종목 Pipeline 실패"
        )
    else:
        batch_status = "BLOCKED"
        batch_status_label = (
            "완료된 종목 없음"
        )

    all_checks_passed = (
        input_checks_passed
        and result_checks_passed
        and (
            all_required_symbols_passed
            or (
                not policy.require_all_symbols_success
                and completed_symbol_count > 0
            )
        )
        and batch_status
        in {
            "COMPLETED",
            "PARTIAL",
        }
    )

    completed_results = [
        result
        for result in symbol_results.values()
        if result.symbol_status == "COMPLETED"
    ]

    if completed_results:
        last_completed_result = (
            completed_results[-1]
        )

        final_cash_balance = round_money(
            last_completed_result.final_cash_balance
        )
        final_market_value = round_money(
            last_completed_result.final_market_value
        )
        final_equity = round_money(
            last_completed_result.final_equity
        )
    else:
        final_cash_balance = round_money(
            account_cash
        )
        final_market_value = 0.0
        final_equity = round_money(account_cash)

    batch_equity_change = round_money(
        final_equity - account_cash
    )

    if account_cash > 0:
        batch_equity_change_percent = (
            round_percent(
                (
                    batch_equity_change
                    / account_cash
                )
                * 100.0
            )
        )
    else:
        batch_equity_change_percent = 0.0

    reasons: list[str] = []

    if batch_status == "COMPLETED":
        reasons.append(
            "모든 고유 Symbol의 V10.2 Pipeline이 완료되었습니다."
        )
    elif batch_status == "PARTIAL":
        reasons.append(
            "일부 Symbol은 완료되고 일부는 실패 또는 차단되었습니다."
        )
    else:
        reasons.append(
            "Batch 입력 검사 또는 종목 Pipeline 실패로 완료되지 않았습니다."
        )

    warnings: list[str] = []
    warnings.extend(policy_errors)
    warnings.extend(symbol_errors)
    warnings.extend(normalization_errors)
    warnings.extend(price_errors)
    warnings.extend(result_safety_errors)

    if duplicate_symbols:
        warnings.append(
            (
                "중복 제거된 Symbol: "
                f"{', '.join(duplicate_symbols)}"
            )
        )

    warnings.extend(
        [
            (
                "V10.3는 연구용 Multi-Symbol "
                "Paper Trading Batch입니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
            (
                "Batch Success Rate는 미래 투자 성과를 "
                "의미하지 않습니다."
            ),
        ]
    )

    if batch_status in {"COMPLETED", "PARTIAL"}:
        next_actions = [
            "종목별 Status와 최초 실패 단계를 확인합니다.",
            "Batch Report와 Latest JSON을 저장합니다.",
            "V10.4에서 Multi-Symbol Batch 통합 테스트를 추가합니다.",
        ]
    else:
        next_actions = [
            "Batch Policy와 Symbol 목록을 확인합니다.",
            "실패 종목의 Error Message와 Warnings를 확인합니다.",
            "문제를 수정한 후 V10.3 Batch를 다시 실행합니다.",
        ]

    result = PaperTradingBatchPipelineResult(
        version="V10.3",
        created_at=datetime.now().isoformat(),
        batch_id=str(uuid.uuid4()),
        batch_status=batch_status,
        batch_status_label=batch_status_label,
        requested_symbols=requested_symbols,
        normalized_symbols=normalized_symbols,
        duplicate_symbols=duplicate_symbols,
        requested_symbol_count=len(
            requested_symbols
        ),
        unique_symbol_count=unique_symbol_count,
        completed_symbol_count=(
            completed_symbol_count
        ),
        blocked_symbol_count=blocked_symbol_count,
        failed_symbol_count=failed_symbol_count,
        skipped_symbol_count=skipped_symbol_count,
        success_rate_percent=success_rate_percent,
        initial_cash=round_money(account_cash),
        final_cash_balance=final_cash_balance,
        final_market_value=final_market_value,
        final_equity=final_equity,
        batch_equity_change=batch_equity_change,
        batch_equity_change_percent=(
            batch_equity_change_percent
        ),
        policy_checks_passed=policy_valid,
        symbol_checks_passed=(
            symbol_valid
            and not normalization_errors
            and not price_errors
        ),
        result_checks_passed=(
            result_checks_passed
        ),
        all_required_symbols_passed=(
            all_required_symbols_passed
        ),
        all_checks_passed=all_checks_passed,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        batch_policy=policy,
        symbol_results=symbol_results,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_batch_pipeline(result)

    return result


def save_paper_trading_batch_pipeline(
    result: PaperTradingBatchPipelineResult,
) -> tuple[Path, Path]:
    """
    V10.3 Batch Report와 Latest JSON을 저장합니다.
    """

    PAPER_BATCH_PIPELINE_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_BATCH_PIPELINE_OUTPUT_DIRECTORY
        / (
            "paper_trading_batch_pipeline_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_BATCH_PIPELINE_OUTPUT_DIRECTORY
        / "paper_trading_batch_pipeline_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_batch_pipeline() -> (
    dict[str, Any]
):
    """
    저장된 최신 V10.3 Batch 결과를 읽습니다.
    """

    latest_path = (
        PAPER_BATCH_PIPELINE_OUTPUT_DIRECTORY
        / "paper_trading_batch_pipeline_latest.json"
    )

    return read_json_file(latest_path)


def print_paper_trading_batch_pipeline(
    result: PaperTradingBatchPipelineResult,
) -> None:
    """
    V10.3 Batch Pipeline 결과를 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.3 MULTI-SYMBOL PAPER TRADING "
        "BATCH PIPELINE"
    )
    print("=" * line_length)

    print(
        f"Batch status                   : "
        f"{result.batch_status}"
    )
    print(
        f"Batch status label             : "
        f"{result.batch_status_label}"
    )
    print(
        f"Batch ID                       : "
        f"{result.batch_id}"
    )

    print()
    print("SYMBOL COUNTS")
    print("-" * line_length)

    print(
        f"Requested symbols              : "
        f"{result.requested_symbol_count}"
    )
    print(
        f"Unique symbols                 : "
        f"{result.unique_symbol_count}"
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
    print(
        f"Success rate                   : "
        f"{result.success_rate_percent:.4f}%"
    )

    print()
    print("SYMBOL RESULTS")
    print("-" * line_length)

    for symbol in result.normalized_symbols:
        symbol_result = result.symbol_results.get(
            symbol
        )

        if symbol_result is None:
            print(
                f"{symbol:<12}: MISSING RESULT"
            )
            continue

        print(
            f"{symbol_result.sequence:>2}. "
            f"{symbol:<10}: "
            f"{symbol_result.symbol_status:<10} "
            f"| Pipeline={symbol_result.pipeline_status} "
            f"| Equity=${symbol_result.final_equity:,.2f}"
        )

        if symbol_result.error_message:
            print(
                f"    Error                       : "
                f"{symbol_result.error_message}"
            )

    print()
    print("BATCH PORTFOLIO SUMMARY")
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
    print(
        f"Batch equity change            : "
        f"${result.batch_equity_change:,.2f}"
    )
    print(
        f"Batch equity change %          : "
        f"{result.batch_equity_change_percent:.4f}%"
    )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"Symbol checks passed           : "
        f"{result.symbol_checks_passed}"
    )
    print(
        f"Result checks passed           : "
        f"{result.result_checks_passed}"
    )
    print(
        f"All required symbols passed    : "
        f"{result.all_required_symbols_passed}"
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
        "주의: V10.3는 연구용 Multi-Symbol Paper Trading "
        "Batch이며 실제 Broker 주문을 수행하지 않습니다."
    )


if __name__ == "__main__":
    batch_result = run_paper_trading_batch_pipeline(
        symbols=[
            "AAPL",
            "MSFT",
            "NVDA",
        ]
    )

    save_paper_trading_batch_pipeline(
        batch_result
    )
