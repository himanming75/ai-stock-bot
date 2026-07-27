import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.trading_engine_integration import (
    TradingEngineIntegrationResult,
    require_engine_operation,
    run_trading_engine_integration,
)
from data.market import get_history
from strategy.score import calculate_score


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SIGNAL_ENGINE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "signal_runtime"
)


VALID_SIGNAL_STATUSES = {
    "READY",
    "BLOCKED",
    "FAILED",
}


VALID_SIGNALS = {
    "BUY",
    "HOLD",
    "SELL",
    "NO_SIGNAL",
}


@dataclass(frozen=True)
class RuntimeSignalParameters:
    """
    Signal Engine이 사용하는 Runtime 전략 파라미터입니다.
    """

    entry_score: float
    exit_score: float

    stop_atr_multiple: float
    target_atr_multiple: float

    maximum_holding_days: int
    position_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SignalEngineRuntimeResult:
    """
    V9.1 Signal Engine Runtime Adapter 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_trading_engine_file: str | None

    signal_status: str
    signal: str
    signal_label: str

    current_score: float
    entry_score: float
    exit_score: float
    distance_to_entry: float
    distance_to_exit: float

    latest_date: str
    latest_close: float

    strategy_source: str
    strategy_status: str
    strategy_name: str | None
    strategy_type: str | None

    parameters: RuntimeSignalParameters

    score_payload: dict[str, Any]
    score_reasons: list[str]
    signal_reasons: list[str]

    market_data_loaded: bool
    score_calculated: bool
    runtime_parameters_applied: bool
    signal_generated: bool

    signal_analysis_allowed: bool
    order_generated: bool
    paper_order_generated: bool
    live_order_generated: bool
    execution_blocked: bool

    market_checks_passed: bool
    score_checks_passed: bool
    parameter_checks_passed: bool
    permission_checks_passed: bool
    all_checks_passed: bool

    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["parameters"] = self.parameters.to_dict()
        return payload


def normalize_symbol(symbol: str) -> str:
    """
    종목 코드를 대문자로 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일을 이용해 안전하게 저장합니다.
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

    temporary_path.replace(
        file_path
    )


def is_valid_number(value: Any) -> bool:
    """
    값이 유효한 숫자인지 검사합니다.
    """

    if isinstance(value, bool):
        return False

    try:
        numeric_value = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return False

    return math.isfinite(
        numeric_value
    )


def extract_score(
    score_payload: dict[str, Any],
) -> float:
    """
    calculate_score() 결과 Dictionary에서 점수를 추출합니다.

    기존 score.py 구현에 따라 아래 키들을 순서대로 확인합니다.

    - score
    - total_score
    - current_score
    - final_score
    """

    possible_keys = [
        "score",
        "total_score",
        "current_score",
        "final_score",
    ]

    for key in possible_keys:
        value = score_payload.get(
            key
        )

        if is_valid_number(value):
            return float(value)

    raise RuntimeError(
        "calculate_score() 결과에서 점수를 찾을 수 없습니다. "
        "score, total_score, current_score 또는 final_score "
        "키가 필요합니다."
    )


def extract_score_reasons(
    score_payload: dict[str, Any],
) -> list[str]:
    """
    calculate_score() 결과에서 점수 산정 근거를 추출합니다.
    """

    possible_keys = [
        "reasons",
        "reason",
        "details",
        "components",
        "signals",
    ]

    for key in possible_keys:
        value = score_payload.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            return [
                str(item)
                for item in value
            ]

        if isinstance(
            value,
            str,
        ):
            return [
                value
            ]

        if isinstance(
            value,
            dict,
        ):
            return [
                f"{component}: {component_value}"
                for component, component_value
                in value.items()
            ]

    return [
        "calculate_score()에서 별도의 점수 근거를 반환하지 않았습니다."
    ]


def make_json_safe(
    value: Any,
) -> Any:
    """
    Pandas와 NumPy 값을 JSON 저장이 가능한 형식으로 변환합니다.
    """

    if value is None:
        return None

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if hasattr(
        value,
        "item",
    ):
        try:
            return value.item()

        except (
            ValueError,
            TypeError,
            AttributeError,
        ):
            pass

    if pd.isna(value):
        return None

    return value


def convert_runtime_parameters(
    trading_engine: TradingEngineIntegrationResult,
) -> RuntimeSignalParameters:
    """
    V9.0 Trading Engine 파라미터를
    V9.1 Signal Engine 파라미터로 변환합니다.
    """

    return RuntimeSignalParameters(
        entry_score=float(
            trading_engine.parameters.entry_score
        ),
        exit_score=float(
            trading_engine.parameters.exit_score
        ),
        stop_atr_multiple=float(
            trading_engine.parameters.stop_atr_multiple
        ),
        target_atr_multiple=float(
            trading_engine.parameters.target_atr_multiple
        ),
        maximum_holding_days=int(
            trading_engine.parameters.maximum_holding_days
        ),
        position_percent=float(
            trading_engine.parameters.position_percent
        ),
    )


def validate_signal_parameters(
    parameters: RuntimeSignalParameters,
) -> tuple[
    bool,
    list[str],
]:
    """
    Signal Engine Runtime 파라미터를 검사합니다.
    """

    errors: list[str] = []

    if not (
        0.0
        < parameters.entry_score
        <= 100.0
    ):
        errors.append(
            "Entry Score가 허용 범위를 벗어났습니다."
        )

    if not (
        0.0
        <= parameters.exit_score
        <= 100.0
    ):
        errors.append(
            "Exit Score가 허용 범위를 벗어났습니다."
        )

    if (
        parameters.entry_score
        <= parameters.exit_score
    ):
        errors.append(
            "Entry Score는 Exit Score보다 높아야 합니다."
        )

    if not (
        0.50
        <= parameters.stop_atr_multiple
        <= 5.00
    ):
        errors.append(
            "Stop ATR이 허용 범위를 벗어났습니다."
        )

    if not (
        0.50
        <= parameters.target_atr_multiple
        <= 10.00
    ):
        errors.append(
            "Target ATR이 허용 범위를 벗어났습니다."
        )

    if not (
        1
        <= parameters.maximum_holding_days
        <= 90
    ):
        errors.append(
            "Maximum Holding Days가 허용 범위를 벗어났습니다."
        )

    if not (
        0.0
        < parameters.position_percent
        <= 25.0
    ):
        errors.append(
            "Position Percent가 허용 범위를 벗어났습니다."
        )

    return (
        not errors,
        errors,
    )


def determine_runtime_signal(
    current_score: float,
    entry_score: float,
    exit_score: float,
) -> tuple[
    str,
    str,
    list[str],
]:
    """
    현재 점수와 Runtime 기준점으로 BUY/HOLD/SELL을 결정합니다.

    BUY:
        current_score >= entry_score

    SELL:
        current_score <= exit_score

    HOLD:
        exit_score < current_score < entry_score
    """

    if current_score >= entry_score:
        return (
            "BUY",
            "매수 신호",
            [
                (
                    f"현재 점수 {current_score:.2f}가 "
                    f"매수 기준 {entry_score:.2f} 이상입니다."
                ),
                (
                    "Runtime Entry Score 기준을 충족했습니다."
                ),
            ],
        )

    if current_score <= exit_score:
        return (
            "SELL",
            "매도 신호",
            [
                (
                    f"현재 점수 {current_score:.2f}가 "
                    f"매도 기준 {exit_score:.2f} 이하입니다."
                ),
                (
                    "Runtime Exit Score 기준을 충족했습니다."
                ),
            ],
        )

    return (
        "HOLD",
        "관망 신호",
        [
            (
                f"현재 점수 {current_score:.2f}가 "
                f"매도 기준 {exit_score:.2f}보다 높고 "
                f"매수 기준 {entry_score:.2f}보다 낮습니다."
            ),
            (
                "현재 점수는 BUY 또는 SELL 기준을 "
                "충족하지 않았습니다."
            ),
        ],
    )


def validate_market_data(
    market_data: pd.DataFrame,
) -> tuple[
    bool,
    list[str],
]:
    """
    시장 데이터 구조를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        market_data,
        pd.DataFrame,
    ):
        errors.append(
            "시장 데이터가 pandas DataFrame이 아닙니다."
        )

        return (
            False,
            errors,
        )

    if market_data.empty:
        errors.append(
            "시장 데이터가 비어 있습니다."
        )

        return (
            False,
            errors,
        )

    if "Close" not in market_data.columns:
        errors.append(
            "시장 데이터에 Close 열이 없습니다."
        )

    if market_data.index.empty:
        errors.append(
            "시장 데이터의 날짜 Index가 비어 있습니다."
        )

    return (
        not errors,
        errors,
    )


def determine_signal_status(
    market_checks_passed: bool,
    score_checks_passed: bool,
    parameter_checks_passed: bool,
    permission_checks_passed: bool,
    signal_generated: bool,
) -> str:
    """
    Signal Engine 상태를 결정합니다.
    """

    all_checks = (
        market_checks_passed
        and score_checks_passed
        and parameter_checks_passed
        and permission_checks_passed
    )

    if not all_checks:
        return "FAILED"

    if not signal_generated:
        return "BLOCKED"

    return "READY"


def run_signal_engine_runtime_adapter(
    symbol: str = "AAPL",
    period: str = "5y",
    interval: str = "1d",
    trading_engine: TradingEngineIntegrationResult | None = None,
) -> SignalEngineRuntimeResult:
    """
    V9.0 Trading Engine 설정을 사용하여
    현재 시장 점수와 BUY/HOLD/SELL 신호를 생성합니다.

    실제 주문은 생성하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if trading_engine is None:
        trading_engine = run_trading_engine_integration(
            symbol=normalized_symbol
        )

    if trading_engine.symbol != normalized_symbol:
        raise ValueError(
            "Trading Engine Symbol과 요청 Symbol이 "
            "일치하지 않습니다."
        )

    permission_errors: list[str] = []

    try:
        require_engine_operation(
            trading_engine,
            "SIGNAL_ANALYSIS",
        )

        signal_analysis_allowed = True

    except RuntimeError as error:
        signal_analysis_allowed = False
        permission_errors.append(
            str(error)
        )

    permission_checks_passed = (
        signal_analysis_allowed
    )

    parameters = convert_runtime_parameters(
        trading_engine
    )

    (
        parameter_checks_passed,
        parameter_errors,
    ) = validate_signal_parameters(
        parameters
    )

    market_data = get_history(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
    )

    (
        market_checks_passed,
        market_errors,
    ) = validate_market_data(
        market_data
    )

    if not market_checks_passed:
        raise RuntimeError(
            "시장 데이터 검사 실패: "
            + " | ".join(
                market_errors
            )
        )

    latest_row = market_data.iloc[-1]

    latest_index = market_data.index[-1]

    latest_date = (
        latest_index.isoformat()
        if hasattr(
            latest_index,
            "isoformat",
        )
        else str(latest_index)
    )

    latest_close_value = latest_row.get(
        "Close"
    )

    if not is_valid_number(
        latest_close_value
    ):
        raise RuntimeError(
            "최근 Close 가격이 유효한 숫자가 아닙니다."
        )

    latest_close = float(
        latest_close_value
    )

    raw_score_payload = calculate_score(
        latest_row
    )

    if not isinstance(
        raw_score_payload,
        dict,
    ):
        raise RuntimeError(
            "calculate_score() 결과가 Dictionary가 아닙니다."
        )

    score_payload = make_json_safe(
        raw_score_payload
    )

    current_score = extract_score(
        score_payload
    )

    score_checks_passed = (
        is_valid_number(
            current_score
        )
        and 0.0
        <= current_score
        <= 100.0
    )

    if not score_checks_passed:
        raise RuntimeError(
            "현재 점수가 0~100 범위의 유효한 숫자가 아닙니다: "
            f"{current_score}"
        )

    score_reasons = extract_score_reasons(
        score_payload
    )

    (
        signal,
        signal_label,
        signal_reasons,
    ) = determine_runtime_signal(
        current_score=current_score,
        entry_score=parameters.entry_score,
        exit_score=parameters.exit_score,
    )

    runtime_parameters_applied = (
        parameters.entry_score
        == trading_engine.parameters.entry_score
        and parameters.exit_score
        == trading_engine.parameters.exit_score
    )

    signal_generated = (
        signal in {
            "BUY",
            "HOLD",
            "SELL",
        }
        and signal_analysis_allowed
        and market_checks_passed
        and score_checks_passed
        and parameter_checks_passed
    )

    signal_status = determine_signal_status(
        market_checks_passed=(
            market_checks_passed
        ),
        score_checks_passed=(
            score_checks_passed
        ),
        parameter_checks_passed=(
            parameter_checks_passed
        ),
        permission_checks_passed=(
            permission_checks_passed
        ),
        signal_generated=(
            signal_generated
        ),
    )

    warnings: list[str] = []

    warnings.extend(
        market_errors
    )

    warnings.extend(
        parameter_errors
    )

    warnings.extend(
        permission_errors
    )

    warnings.extend(
        [
            (
                "생성된 BUY/HOLD/SELL 값은 분석 신호이며 "
                "증권 주문이 아닙니다."
            ),
            (
                "Signal Engine은 Broker Adapter 또는 "
                "주문 전송 모듈을 호출하지 않습니다."
            ),
            (
                "Paper Order와 Live Order 생성은 "
                "현재 단계에서 모두 차단됩니다."
            ),
        ]
    )

    next_actions = [
        (
            "다음 거래일 데이터가 추가되면 "
            "현재 점수와 신호를 다시 계산합니다."
        ),
        (
            "V9.2 Position State Manager에서 "
            "현재 보유 상태와 신호를 비교합니다."
        ),
        (
            "주문 실행 전 별도의 Risk Manager와 "
            "수동 승인 검사가 필요합니다."
        ),
    ]

    all_checks_passed = (
        trading_engine.all_checks_passed
        and market_checks_passed
        and score_checks_passed
        and parameter_checks_passed
        and permission_checks_passed
        and runtime_parameters_applied
        and signal_generated
    )

    result = SignalEngineRuntimeResult(
        version="V9.1",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_trading_engine_file=(
            trading_engine.latest_path
            or trading_engine.report_path
            or trading_engine.source_runtime_provider_file
        ),

        signal_status=signal_status,
        signal=signal,
        signal_label=signal_label,

        current_score=current_score,
        entry_score=parameters.entry_score,
        exit_score=parameters.exit_score,
        distance_to_entry=(
            parameters.entry_score
            - current_score
        ),
        distance_to_exit=(
            current_score
            - parameters.exit_score
        ),

        latest_date=latest_date,
        latest_close=latest_close,

        strategy_source=(
            trading_engine.strategy_source
        ),
        strategy_status=(
            trading_engine.strategy_status
        ),
        strategy_name=(
            trading_engine.strategy_name
        ),
        strategy_type=(
            trading_engine.strategy_type
        ),

        parameters=parameters,

        score_payload=score_payload,
        score_reasons=score_reasons,
        signal_reasons=signal_reasons,

        market_data_loaded=True,
        score_calculated=True,
        runtime_parameters_applied=(
            runtime_parameters_applied
        ),
        signal_generated=(
            signal_generated
        ),

        signal_analysis_allowed=(
            signal_analysis_allowed
        ),
        order_generated=False,
        paper_order_generated=False,
        live_order_generated=False,
        execution_blocked=True,

        market_checks_passed=(
            market_checks_passed
        ),
        score_checks_passed=(
            score_checks_passed
        ),
        parameter_checks_passed=(
            parameter_checks_passed
        ),
        permission_checks_passed=(
            permission_checks_passed
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        warnings=warnings,
        next_actions=next_actions,
    )

    print_signal_engine_runtime_adapter(
        result
    )

    return result


def save_signal_engine_runtime_adapter(
    result: SignalEngineRuntimeResult,
) -> tuple[
    Path,
    Path,
]:
    """
    V9.1 Signal Engine 결과를 JSON으로 저장합니다.
    """

    SIGNAL_ENGINE_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        SIGNAL_ENGINE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "signal_engine_runtime_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        SIGNAL_ENGINE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "signal_engine_runtime_latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    write_json_file(
        report_path,
        payload,
    )

    write_json_file(
        latest_path,
        payload,
    )

    return (
        report_path,
        latest_path,
    )


def print_signal_engine_runtime_adapter(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    V9.1 Signal Engine 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.1 "
        "SIGNAL ENGINE RUNTIME ADAPTER"
    )
    print("=" * 140)

    print(
        f"Signal status                  : "
        f"{result.signal_status}"
    )

    print(
        f"Signal                         : "
        f"{result.signal}"
    )

    print(
        f"Signal label                   : "
        f"{result.signal_label}"
    )

    print()
    print("MARKET")
    print("-" * 140)

    print(
        f"Latest date                    : "
        f"{result.latest_date}"
    )

    print(
        f"Latest close                   : "
        f"${result.latest_close:,.2f}"
    )

    print()
    print("SCORE")
    print("-" * 140)

    print(
        f"Current score                  : "
        f"{result.current_score:.2f}"
    )

    print(
        f"Entry score                    : "
        f"{result.entry_score:.2f}"
    )

    print(
        f"Exit score                     : "
        f"{result.exit_score:.2f}"
    )

    print(
        f"Distance to entry              : "
        f"{result.distance_to_entry:+.2f}"
    )

    print(
        f"Distance from exit             : "
        f"{result.distance_to_exit:+.2f}"
    )

    print()
    print("SIGNAL REASONS")
    print("-" * 140)

    for reason in result.signal_reasons:
        print(
            f"- {reason}"
        )

    print()
    print("SCORE REASONS")
    print("-" * 140)

    for reason in result.score_reasons:
        print(
            f"- {reason}"
        )

    print()
    print("RUNTIME PARAMETERS")
    print("-" * 140)

    print(
        f"Stop ATR                       : "
        f"{result.parameters.stop_atr_multiple:.2f}"
    )

    print(
        f"Target ATR                     : "
        f"{result.parameters.target_atr_multiple:.2f}"
    )

    print(
        f"Maximum holding days           : "
        f"{result.parameters.maximum_holding_days}"
    )

    print(
        f"Position percent               : "
        f"{result.parameters.position_percent:.2f}%"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Signal analysis allowed        : "
        f"{result.signal_analysis_allowed}"
    )

    print(
        f"Order generated                : "
        f"{result.order_generated}"
    )

    print(
        f"Paper order generated          : "
        f"{result.paper_order_generated}"
    )

    print(
        f"Live order generated           : "
        f"{result.live_order_generated}"
    )

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Market checks passed           : "
        f"{result.market_checks_passed}"
    )

    print(
        f"Score checks passed            : "
        f"{result.score_checks_passed}"
    )

    print(
        f"Parameter checks passed        : "
        f"{result.parameter_checks_passed}"
    )

    print(
        f"Permission checks passed       : "
        f"{result.permission_checks_passed}"
    )

    print(
        f"Runtime parameters applied     : "
        f"{result.runtime_parameters_applied}"
    )

    print(
        f"Signal generated               : "
        f"{result.signal_generated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 140)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 140)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Trading Engine file     : "
        f"{result.source_trading_engine_file}"
    )

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 140)

    print(
        "주의: 이 모듈은 분석용 BUY/HOLD/SELL 신호만 "
        "생성하며 실제 주문을 생성하거나 전송하지 않습니다."
    )