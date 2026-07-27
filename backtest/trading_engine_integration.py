import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.strategy_runtime_provider import (
    RuntimeStrategyParameters,
    StrategyRuntimeConfiguration,
    get_runtime_parameters,
    is_operation_allowed,
    run_strategy_runtime_provider,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRADING_ENGINE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "integration"
)


VALID_ENGINE_STATUSES = {
    "READY",
    "LIMITED",
    "BLOCKED",
    "FAILED",
}


VALID_ENGINE_MODES = {
    "LIVE_ENGINE",
    "PAPER_ENGINE",
    "ANALYSIS_ENGINE",
    "RESEARCH_ENGINE",
    "BLOCKED_ENGINE",
}


@dataclass(frozen=True)
class TradingEngineParameters:
    """
    Trading Engine에서 실제로 사용할 전략 파라미터입니다.
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
class TradingEngineIntegrationResult:
    """
    V9.0 Trading Engine Integration 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_runtime_provider_file: str | None

    engine_status: str
    engine_mode: str
    engine_label: str

    runtime_mode: str
    provider_status: str
    provider_profile: str

    strategy_source: str
    strategy_status: str
    strategy_name: str | None
    strategy_type: str | None

    parameters: TradingEngineParameters

    configuration_loaded: bool
    signal_engine_ready: bool
    risk_engine_ready: bool
    backtest_engine_ready: bool
    research_engine_ready: bool

    order_execution_ready: bool
    paper_execution_ready: bool
    live_execution_ready: bool

    analysis_allowed: bool
    backtest_allowed: bool
    research_allowed: bool
    paper_execution_allowed: bool
    live_execution_allowed: bool

    engine_checks_passed: bool
    parameter_checks_passed: bool
    permission_checks_passed: bool
    all_checks_passed: bool

    allowed_engine_operations: list[str]
    blocked_engine_operations: list[str]

    reasons: list[str]
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
    Symbol을 대문자로 정규화합니다.
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
    JSON 파일을 임시 파일을 사용해 안전하게 저장합니다.
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


def convert_runtime_parameters(
    runtime_parameters: RuntimeStrategyParameters,
) -> TradingEngineParameters:
    """
    Runtime Provider 파라미터를 Trading Engine 파라미터로 변환합니다.
    """

    return TradingEngineParameters(
        entry_score=float(
            runtime_parameters.entry_score
        ),
        exit_score=float(
            runtime_parameters.exit_score
        ),
        stop_atr_multiple=float(
            runtime_parameters.stop_atr_multiple
        ),
        target_atr_multiple=float(
            runtime_parameters.target_atr_multiple
        ),
        maximum_holding_days=int(
            runtime_parameters.maximum_holding_days
        ),
        position_percent=float(
            runtime_parameters.position_percent
        ),
    )


def validate_engine_parameters(
    parameters: TradingEngineParameters,
) -> tuple[
    bool,
    list[str],
]:
    """
    Trading Engine 파라미터를 검사합니다.
    """

    errors: list[str] = []

    if not 0.0 < parameters.entry_score <= 100.0:
        errors.append(
            "Entry Score가 허용 범위를 벗어났습니다."
        )

    if not 0.0 <= parameters.exit_score <= 100.0:
        errors.append(
            "Exit Score가 허용 범위를 벗어났습니다."
        )

    if parameters.entry_score <= parameters.exit_score:
        errors.append(
            "Entry Score는 Exit Score보다 높아야 합니다."
        )

    if not 0.50 <= parameters.stop_atr_multiple <= 5.00:
        errors.append(
            "Stop ATR이 허용 범위를 벗어났습니다."
        )

    if not 0.50 <= parameters.target_atr_multiple <= 10.00:
        errors.append(
            "Target ATR이 허용 범위를 벗어났습니다."
        )

    if not 1 <= parameters.maximum_holding_days <= 90:
        errors.append(
            "Maximum Holding Days가 허용 범위를 벗어났습니다."
        )

    if not 0.0 < parameters.position_percent <= 25.0:
        errors.append(
            "Position Percent가 허용 범위를 벗어났습니다."
        )

    return (
        not errors,
        errors,
    )


def determine_engine_mode(
    provider_profile: str,
) -> tuple[
    str,
    str,
]:
    """
    Runtime Provider Profile을 Trading Engine Mode로 변환합니다.
    """

    normalized_profile = (
        provider_profile
        .strip()
        .upper()
    )

    mapping = {
        "LIVE": (
            "LIVE_ENGINE",
            "실거래 엔진",
        ),
        "PAPER": (
            "PAPER_ENGINE",
            "모의투자 엔진",
        ),
        "ANALYSIS": (
            "ANALYSIS_ENGINE",
            "분석 및 백테스트 엔진",
        ),
        "RESEARCH": (
            "RESEARCH_ENGINE",
            "연구 전용 엔진",
        ),
        "NONE": (
            "BLOCKED_ENGINE",
            "사용 불가능 엔진",
        ),
    }

    return mapping.get(
        normalized_profile,
        (
            "BLOCKED_ENGINE",
            "사용 불가능 엔진",
        ),
    )


def determine_engine_status(
    engine_mode: str,
    provider_ready: bool,
    all_checks_passed: bool,
) -> str:
    """
    Trading Engine 상태를 결정합니다.
    """

    if not all_checks_passed:
        return "FAILED"

    if (
        not provider_ready
        or engine_mode == "BLOCKED_ENGINE"
    ):
        return "BLOCKED"

    if engine_mode in {
        "ANALYSIS_ENGINE",
        "RESEARCH_ENGINE",
    }:
        return "LIMITED"

    return "READY"


def build_engine_operations(
    analysis_allowed: bool,
    backtest_allowed: bool,
    research_allowed: bool,
    paper_execution_allowed: bool,
    live_execution_allowed: bool,
) -> tuple[
    list[str],
    list[str],
]:
    """
    엔진에서 허용된 작업과 차단된 작업을 생성합니다.
    """

    operation_map = {
        "SIGNAL_ANALYSIS": analysis_allowed,
        "BACKTEST": backtest_allowed,
        "RESEARCH": research_allowed,
        "PAPER_ORDER_EXECUTION": (
            paper_execution_allowed
        ),
        "LIVE_ORDER_EXECUTION": (
            live_execution_allowed
        ),
    }

    allowed_operations = [
        operation
        for operation, allowed
        in operation_map.items()
        if allowed
    ]

    blocked_operations = [
        operation
        for operation, allowed
        in operation_map.items()
        if not allowed
    ]

    return (
        allowed_operations,
        blocked_operations,
    )


def validate_engine_permissions(
    engine_mode: str,
    analysis_allowed: bool,
    backtest_allowed: bool,
    research_allowed: bool,
    paper_execution_allowed: bool,
    live_execution_allowed: bool,
) -> tuple[
    bool,
    list[str],
]:
    """
    Engine Mode와 실행 권한의 일관성을 검사합니다.
    """

    errors: list[str] = []

    if engine_mode == "LIVE_ENGINE":
        if not live_execution_allowed:
            errors.append(
                "LIVE_ENGINE인데 실거래 권한이 없습니다."
            )

    elif engine_mode == "PAPER_ENGINE":
        if not paper_execution_allowed:
            errors.append(
                "PAPER_ENGINE인데 모의투자 권한이 없습니다."
            )

        if live_execution_allowed:
            errors.append(
                "PAPER_ENGINE에서 실거래 권한이 활성화되었습니다."
            )

    elif engine_mode == "ANALYSIS_ENGINE":
        if not analysis_allowed:
            errors.append(
                "ANALYSIS_ENGINE에서 분석 권한이 없습니다."
            )

        if not backtest_allowed:
            errors.append(
                "ANALYSIS_ENGINE에서 백테스트 권한이 없습니다."
            )

        if paper_execution_allowed:
            errors.append(
                "ANALYSIS_ENGINE에서 모의 주문 권한이 활성화되었습니다."
            )

        if live_execution_allowed:
            errors.append(
                "ANALYSIS_ENGINE에서 실거래 권한이 활성화되었습니다."
            )

    elif engine_mode == "RESEARCH_ENGINE":
        if not research_allowed:
            errors.append(
                "RESEARCH_ENGINE에서 연구 권한이 없습니다."
            )

        if paper_execution_allowed:
            errors.append(
                "RESEARCH_ENGINE에서 모의 주문 권한이 활성화되었습니다."
            )

        if live_execution_allowed:
            errors.append(
                "RESEARCH_ENGINE에서 실거래 권한이 활성화되었습니다."
            )

    elif engine_mode == "BLOCKED_ENGINE":
        if any(
            [
                analysis_allowed,
                backtest_allowed,
                research_allowed,
                paper_execution_allowed,
                live_execution_allowed,
            ]
        ):
            errors.append(
                "BLOCKED_ENGINE인데 허용된 작업이 있습니다."
            )

    return (
        not errors,
        errors,
    )


def build_engine_notes(
    engine_status: str,
    engine_mode: str,
    parameter_errors: list[str],
    permission_errors: list[str],
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    엔진 결과 설명을 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if engine_status == "READY":
        reasons.append(
            "Runtime Provider 설정을 Trading Engine에 "
            "정상적으로 연결했습니다."
        )

    elif engine_status == "LIMITED":
        reasons.append(
            "Trading Engine 설정은 준비되었지만 "
            "주문 실행 권한은 제한되었습니다."
        )

    elif engine_status == "BLOCKED":
        reasons.append(
            "Runtime Provider 상태에 따라 "
            "Trading Engine 사용이 차단되었습니다."
        )

    else:
        reasons.append(
            "Trading Engine 통합 검사 중 오류가 확인되었습니다."
        )

    for error in parameter_errors:
        warnings.append(
            f"Parameter error: {error}"
        )

    for error in permission_errors:
        warnings.append(
            f"Permission error: {error}"
        )

    if engine_mode == "ANALYSIS_ENGINE":
        warnings.append(
            "현재 엔진은 분석과 백테스트에만 사용할 수 있습니다."
        )

        warnings.append(
            "모의 주문과 실거래 주문은 모두 차단됩니다."
        )

        next_actions.extend(
            [
                "Signal Engine에서 전략 점수를 계산합니다.",
                "Backtest Engine에서 전략 성과를 검증합니다.",
                "주문 실행 모듈에는 전달하지 않습니다.",
            ]
        )

    elif engine_mode == "RESEARCH_ENGINE":
        warnings.append(
            "현재 엔진은 연구 전용입니다."
        )

        next_actions.extend(
            [
                "연구용 데이터 분석에만 사용합니다.",
                "추가 Walk-Forward 검증을 수행합니다.",
                "주문 실행 엔진과 분리합니다.",
            ]
        )

    elif engine_mode == "PAPER_ENGINE":
        warnings.append(
            "모의투자 엔진이며 실제 주문은 차단됩니다."
        )

        next_actions.extend(
            [
                "모의 주문 계좌만 연결합니다.",
                "체결 로그를 저장합니다.",
                "실거래 Broker Adapter는 연결하지 않습니다.",
            ]
        )

    elif engine_mode == "LIVE_ENGINE":
        warnings.append(
            "실거래 준비 상태이지만 사용자 최종 승인이 필요합니다."
        )

        next_actions.extend(
            [
                "계좌 연결 상태를 확인합니다.",
                "일일 최대 손실 한도를 확인합니다.",
                "사용자 승인 후에만 주문 모듈을 연결합니다.",
            ]
        )

    else:
        next_actions.extend(
            [
                "V8.8 Runtime Guard를 다시 실행합니다.",
                "V8.9 Runtime Provider를 다시 실행합니다.",
                "Provider Blocking Reasons를 확인합니다.",
            ]
        )

    warnings.append(
        "이 모듈은 Trading Engine 설정만 구성하며 "
        "실제 주문을 생성하거나 전송하지 않습니다."
    )

    return (
        reasons,
        warnings,
        next_actions,
    )


def run_trading_engine_integration(
    symbol: str = "AAPL",
    runtime_provider: StrategyRuntimeConfiguration | None = None,
) -> TradingEngineIntegrationResult:
    """
    V8.9 Runtime Provider를 Trading Engine에 연결합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if runtime_provider is None:
        runtime_provider = (
            run_strategy_runtime_provider(
                symbol=normalized_symbol,
            )
        )

    if runtime_provider.symbol != normalized_symbol:
        raise ValueError(
            "Runtime Provider의 Symbol과 요청 Symbol이 "
            "일치하지 않습니다."
        )

    runtime_parameters = get_runtime_parameters(
        runtime_provider
    )

    engine_parameters = convert_runtime_parameters(
        runtime_parameters
    )

    (
        parameter_checks_passed,
        parameter_errors,
    ) = validate_engine_parameters(
        engine_parameters
    )

    (
        engine_mode,
        engine_label,
    ) = determine_engine_mode(
        runtime_provider.provider_profile
    )

    analysis_allowed = is_operation_allowed(
        runtime_provider,
        "ANALYSIS",
    )

    backtest_allowed = is_operation_allowed(
        runtime_provider,
        "BACKTEST",
    )

    research_allowed = is_operation_allowed(
        runtime_provider,
        "RESEARCH",
    )

    paper_execution_allowed = is_operation_allowed(
        runtime_provider,
        "PAPER_EXECUTION",
    )

    live_execution_allowed = is_operation_allowed(
        runtime_provider,
        "LIVE_EXECUTION",
    )

    (
        permission_checks_passed,
        permission_errors,
    ) = validate_engine_permissions(
        engine_mode=engine_mode,
        analysis_allowed=analysis_allowed,
        backtest_allowed=backtest_allowed,
        research_allowed=research_allowed,
        paper_execution_allowed=(
            paper_execution_allowed
        ),
        live_execution_allowed=(
            live_execution_allowed
        ),
    )

    configuration_loaded = (
        runtime_provider.provider_ready
    )

    signal_engine_ready = (
        configuration_loaded
        and analysis_allowed
        and parameter_checks_passed
    )

    risk_engine_ready = (
        configuration_loaded
        and parameter_checks_passed
    )

    backtest_engine_ready = (
        configuration_loaded
        and backtest_allowed
        and parameter_checks_passed
    )

    research_engine_ready = (
        configuration_loaded
        and research_allowed
        and parameter_checks_passed
    )

    paper_execution_ready = (
        configuration_loaded
        and paper_execution_allowed
        and parameter_checks_passed
        and permission_checks_passed
    )

    live_execution_ready = (
        configuration_loaded
        and live_execution_allowed
        and parameter_checks_passed
        and permission_checks_passed
        and not runtime_provider.manual_approval_required
    )

    order_execution_ready = (
        paper_execution_ready
        or live_execution_ready
    )

    engine_checks_passed = (
        configuration_loaded
        and signal_engine_ready
        and risk_engine_ready
    )

    all_checks_passed = (
        runtime_provider.all_checks_passed
        and engine_checks_passed
        and parameter_checks_passed
        and permission_checks_passed
    )

    engine_status = determine_engine_status(
        engine_mode=engine_mode,
        provider_ready=(
            runtime_provider.provider_ready
        ),
        all_checks_passed=all_checks_passed,
    )

    (
        allowed_engine_operations,
        blocked_engine_operations,
    ) = build_engine_operations(
        analysis_allowed=analysis_allowed,
        backtest_allowed=backtest_allowed,
        research_allowed=research_allowed,
        paper_execution_allowed=(
            paper_execution_allowed
        ),
        live_execution_allowed=(
            live_execution_allowed
        ),
    )

    (
        reasons,
        warnings,
        next_actions,
    ) = build_engine_notes(
        engine_status=engine_status,
        engine_mode=engine_mode,
        parameter_errors=parameter_errors,
        permission_errors=permission_errors,
    )

    result = TradingEngineIntegrationResult(
        version="V9.0",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_runtime_provider_file=(
            runtime_provider.latest_path
            or runtime_provider.report_path
            or runtime_provider.source_runtime_guard_file
        ),

        engine_status=engine_status,
        engine_mode=engine_mode,
        engine_label=engine_label,

        runtime_mode=runtime_provider.runtime_mode,
        provider_status=(
            runtime_provider.provider_status
        ),
        provider_profile=(
            runtime_provider.provider_profile
        ),

        strategy_source=(
            runtime_provider.strategy_source
        ),
        strategy_status=(
            runtime_provider.strategy_status
        ),
        strategy_name=(
            runtime_provider.strategy_name
        ),
        strategy_type=(
            runtime_provider.strategy_type
        ),

        parameters=engine_parameters,

        configuration_loaded=(
            configuration_loaded
        ),
        signal_engine_ready=(
            signal_engine_ready
        ),
        risk_engine_ready=(
            risk_engine_ready
        ),
        backtest_engine_ready=(
            backtest_engine_ready
        ),
        research_engine_ready=(
            research_engine_ready
        ),

        order_execution_ready=(
            order_execution_ready
        ),
        paper_execution_ready=(
            paper_execution_ready
        ),
        live_execution_ready=(
            live_execution_ready
        ),

        analysis_allowed=(
            analysis_allowed
        ),
        backtest_allowed=(
            backtest_allowed
        ),
        research_allowed=(
            research_allowed
        ),
        paper_execution_allowed=(
            paper_execution_allowed
        ),
        live_execution_allowed=(
            live_execution_allowed
        ),

        engine_checks_passed=(
            engine_checks_passed
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

        allowed_engine_operations=(
            allowed_engine_operations
        ),
        blocked_engine_operations=(
            blocked_engine_operations
        ),

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_trading_engine_integration(
        result
    )

    return result


def save_trading_engine_integration(
    result: TradingEngineIntegrationResult,
) -> tuple[
    Path,
    Path,
]:
    """
    Trading Engine Integration 결과를 JSON으로 저장합니다.
    """

    TRADING_ENGINE_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        TRADING_ENGINE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "trading_engine_integration_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        TRADING_ENGINE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "trading_engine_integration_latest.json"
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


def is_engine_operation_allowed(
    result: TradingEngineIntegrationResult,
    operation: str,
) -> bool:
    """
    Trading Engine 작업 허용 여부를 반환합니다.
    """

    normalized_operation = (
        operation
        .strip()
        .upper()
    )

    return (
        normalized_operation
        in result.allowed_engine_operations
    )


def require_engine_operation(
    result: TradingEngineIntegrationResult,
    operation: str,
) -> None:
    """
    Trading Engine 작업을 실행하기 전에 권한을 확인합니다.
    """

    normalized_operation = (
        operation
        .strip()
        .upper()
    )

    valid_operations = {
        "SIGNAL_ANALYSIS",
        "BACKTEST",
        "RESEARCH",
        "PAPER_ORDER_EXECUTION",
        "LIVE_ORDER_EXECUTION",
    }

    if normalized_operation not in valid_operations:
        raise ValueError(
            "알 수 없는 Trading Engine Operation입니다: "
            f"{normalized_operation}"
        )

    if (
        normalized_operation
        not in result.allowed_engine_operations
    ):
        raise RuntimeError(
            f"{normalized_operation} 작업은 현재 "
            f"Engine Mode {result.engine_mode}에서 "
            "허용되지 않습니다."
        )


def print_trading_engine_integration(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    V9.0 Trading Engine Integration 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.0 "
        "TRADING ENGINE INTEGRATION"
    )
    print("=" * 140)

    print(
        f"Engine status                  : "
        f"{result.engine_status}"
    )

    print(
        f"Engine mode                    : "
        f"{result.engine_mode}"
    )

    print(
        f"Engine label                   : "
        f"{result.engine_label}"
    )

    print(
        f"Runtime mode                   : "
        f"{result.runtime_mode}"
    )

    print(
        f"Provider status                : "
        f"{result.provider_status}"
    )

    print(
        f"Provider profile               : "
        f"{result.provider_profile}"
    )

    print()
    print("STRATEGY")
    print("-" * 140)

    print(
        f"Strategy source                : "
        f"{result.strategy_source}"
    )

    print(
        f"Strategy status                : "
        f"{result.strategy_status}"
    )

    print(
        f"Strategy name                  : "
        f"{result.strategy_name}"
    )

    print(
        f"Strategy type                  : "
        f"{result.strategy_type}"
    )

    print()
    print("PARAMETERS")
    print("-" * 140)

    print(
        f"Entry score                    : "
        f"{result.parameters.entry_score:.2f}"
    )

    print(
        f"Exit score                     : "
        f"{result.parameters.exit_score:.2f}"
    )

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
    print("ENGINE READINESS")
    print("-" * 140)

    print(
        f"Configuration loaded           : "
        f"{result.configuration_loaded}"
    )

    print(
        f"Signal engine ready            : "
        f"{result.signal_engine_ready}"
    )

    print(
        f"Risk engine ready              : "
        f"{result.risk_engine_ready}"
    )

    print(
        f"Backtest engine ready          : "
        f"{result.backtest_engine_ready}"
    )

    print(
        f"Research engine ready          : "
        f"{result.research_engine_ready}"
    )

    print(
        f"Order execution ready          : "
        f"{result.order_execution_ready}"
    )

    print(
        f"Paper execution ready          : "
        f"{result.paper_execution_ready}"
    )

    print(
        f"Live execution ready           : "
        f"{result.live_execution_ready}"
    )

    print()
    print("ALLOWED ENGINE OPERATIONS")
    print("-" * 140)

    for operation in result.allowed_engine_operations:
        print(
            f"- {operation}"
        )

    print()
    print("BLOCKED ENGINE OPERATIONS")
    print("-" * 140)

    for operation in result.blocked_engine_operations:
        print(
            f"- {operation}"
        )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Engine checks passed           : "
        f"{result.engine_checks_passed}"
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
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 140)

        for reason in result.reasons:
            print(
                f"- {reason}"
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
        f"Source Runtime Provider file   : "
        f"{result.source_runtime_provider_file}"
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
        "주의: 이 모듈은 Trading Engine 설정과 권한만 "
        "구성하며 실제 주문을 생성하거나 전송하지 않습니다."
    )