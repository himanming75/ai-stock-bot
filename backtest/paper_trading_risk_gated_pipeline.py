import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backtest.paper_portfolio_performance_tracker import (
    PaperPortfolioPerformanceResult,
)
from backtest.paper_trading_daily_pipeline import (
    PaperTradingDailyPipelinePolicy,
    PaperTradingDailyPipelineResult,
    run_paper_trading_daily_pipeline,
)
from backtest.paper_trading_risk_monitor import (
    PaperTradingRiskMonitorPolicy,
    PaperTradingRiskMonitorResult,
    run_paper_trading_risk_monitor,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_RISK_GATED_PIPELINE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_risk_gated_pipeline"
)


VALID_GATED_PIPELINE_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "FAILED",
}


VALID_GATE_STATUSES = {
    "PASSED",
    "WARNING",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperTradingRiskGatedPipelinePolicy:
    """
    V10.5 Paper Trading Risk-Gated Pipeline 정책입니다.

    V10.4 Risk Monitor가 허용한 경우에만
    V10.2 Daily Pipeline을 실행합니다.
    """

    require_risk_checks: bool = True
    allow_safe: bool = True
    allow_warning: bool = True
    block_paused: bool = True
    block_blocked: bool = True
    block_failed: bool = True

    require_daily_pipeline_checks: bool = True
    save_output: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingRiskGateDecision:
    """
    Risk Monitor 결과를 Pipeline 실행 여부로 변환한 결과입니다.
    """

    gate_status: str
    gate_status_label: str

    risk_status: str
    risk_action: str

    gate_passed: bool
    pipeline_execution_allowed: bool

    checks_passed: bool

    reasons: list[str] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingRiskGatedPipelineResult:
    """
    V10.5 Risk-Gated Pipeline 전체 결과입니다.
    """

    version: str
    created_at: str

    gated_pipeline_id: str
    symbol: str

    gated_pipeline_status: str
    gated_pipeline_status_label: str

    risk_monitor_id: str | None
    daily_pipeline_id: str | None

    risk_monitor_executed: bool
    risk_gate_evaluated: bool
    daily_pipeline_requested: bool
    daily_pipeline_executed: bool
    daily_pipeline_skipped: bool

    risk_checks_passed: bool
    gate_checks_passed: bool
    daily_pipeline_checks_passed: bool
    all_checks_passed: bool

    paper_trading_allowed: bool
    risk_gate_blocked: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    gated_policy: PaperTradingRiskGatedPipelinePolicy
    risk_gate_decision: PaperTradingRiskGateDecision

    risk_monitor_result: (
        PaperTradingRiskMonitorResult
        | None
    )
    daily_pipeline_result: (
        PaperTradingDailyPipelineResult
        | None
    )

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["gated_policy"] = (
            self.gated_policy.to_dict()
        )

        payload["risk_gate_decision"] = (
            self.risk_gate_decision.to_dict()
        )

        payload["risk_monitor_result"] = (
            self.risk_monitor_result.to_dict()
            if self.risk_monitor_result is not None
            else None
        )

        payload["daily_pipeline_result"] = (
            self.daily_pipeline_result.to_dict()
            if self.daily_pipeline_result is not None
            else None
        )

        return payload


def normalize_symbol(symbol: str) -> str:
    """
    종목 Symbol을 대문자로 정규화합니다.
    """

    if not isinstance(symbol, str):
        raise TypeError(
            "Symbol은 문자열이어야 합니다."
        )

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "Symbol이 비어 있습니다."
        )

    if not normalized.replace(
        ".",
        "",
    ).replace(
        "-",
        "",
    ).isalnum():
        raise ValueError(
            "Symbol에 허용되지 않은 문자가 있습니다."
        )

    return normalized


def is_valid_number(value: Any) -> bool:
    """
    bool이 아닌 유효한 숫자인지 확인합니다.
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


def validate_gated_policy(
    policy: PaperTradingRiskGatedPipelinePolicy,
) -> tuple[bool, list[str]]:
    """
    V10.5 Gated Pipeline Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingRiskGatedPipelinePolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingRiskGatedPipelinePolicy "
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
        "require_daily_pipeline_checks": (
            policy.require_daily_pipeline_checks
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

    if not policy.require_risk_checks:
        errors.append(
            "V10.5에서는 Risk Checks가 필수입니다."
        )

    if not policy.allow_safe:
        errors.append(
            "SAFE 상태를 허용하지 않는 Policy는 사용할 수 없습니다."
        )

    if not policy.block_paused:
        errors.append(
            "PAUSED 상태는 반드시 차단해야 합니다."
        )

    if not policy.block_blocked:
        errors.append(
            "BLOCKED 상태는 반드시 차단해야 합니다."
        )

    if not policy.block_failed:
        errors.append(
            "FAILED 상태는 반드시 차단해야 합니다."
        )

    if not policy.paper_only:
        errors.append(
            "V10.5에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.5에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def validate_risk_result_safety(
    result: PaperTradingRiskMonitorResult,
) -> tuple[bool, list[str]]:
    """
    V10.4 결과가 V10.5에서 사용할 수 있는지 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        result,
        PaperTradingRiskMonitorResult,
    ):
        return (
            False,
            [
                (
                    "Risk Result가 "
                    "PaperTradingRiskMonitorResult "
                    "형식이 아닙니다."
                )
            ],
        )

    if result.version != "V10.4":
        errors.append(
            "Risk Result 버전이 V10.4가 아닙니다."
        )

    if not result.source_loaded:
        errors.append(
            "Risk Result Source가 로드되지 않았습니다."
        )

    if result.execution_blocked is not True:
        errors.append(
            "Risk Result의 Execution이 차단되지 않았습니다."
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
                f"Risk Result의 {field_name}가 False가 아닙니다."
            )

    return (not errors, errors)


def validate_daily_pipeline_safety(
    result: PaperTradingDailyPipelineResult,
) -> tuple[bool, list[str]]:
    """
    실행된 V10.2 Daily Pipeline의 안전 상태를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        result,
        PaperTradingDailyPipelineResult,
    ):
        return (
            False,
            [
                (
                    "Daily Pipeline Result가 "
                    "PaperTradingDailyPipelineResult "
                    "형식이 아닙니다."
                )
            ],
        )

    if result.version != "V10.2":
        errors.append(
            "Daily Pipeline 버전이 V10.2가 아닙니다."
        )

    if result.execution_blocked is not True:
        errors.append(
            "Daily Pipeline Execution이 차단되지 않았습니다."
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
                f"Daily Pipeline의 {field_name}가 False가 아닙니다."
            )

    return (not errors, errors)


def evaluate_risk_gate(
    risk_result: PaperTradingRiskMonitorResult,
    policy: PaperTradingRiskGatedPipelinePolicy,
) -> PaperTradingRiskGateDecision:
    """
    V10.4 Risk Action을 V10.5 실행 결정으로 변환합니다.
    """

    risk_valid, risk_errors = (
        validate_risk_result_safety(
            risk_result
        )
    )

    risk_status = risk_result.risk_status
    risk_action = risk_result.risk_action

    reasons: list[str] = []
    warnings: list[str] = list(risk_errors)

    if not risk_valid:
        gate_status = "FAILED"
        gate_status_label = (
            "Risk Result 안전 검사 실패"
        )
        gate_passed = False
    elif (
        not risk_result.all_checks_passed
        or risk_status == "FAILED"
    ):
        gate_status = "FAILED"
        gate_status_label = (
            "Risk Monitor 검사 실패"
        )
        gate_passed = False
    elif (
        risk_status == "SAFE"
        and risk_action == "ALLOW"
        and policy.allow_safe
    ):
        gate_status = "PASSED"
        gate_status_label = (
            "Risk Gate 통과"
        )
        gate_passed = True
    elif (
        risk_status == "WARNING"
        and risk_action == "WARNING"
        and policy.allow_warning
        and risk_result.paper_trading_allowed
    ):
        gate_status = "WARNING"
        gate_status_label = (
            "Risk 경고 조건부 통과"
        )
        gate_passed = True
        warnings.append(
            "Risk Warning 상태에서 Policy에 따라 실행을 허용했습니다."
        )
    else:
        gate_status = "BLOCKED"
        gate_status_label = (
            "Risk Gate 차단"
        )
        gate_passed = False

    if gate_passed:
        reasons.append(
            (
                f"Risk Status {risk_status}, "
                f"Action {risk_action} 조건으로 "
                "Paper Pipeline 실행을 허용합니다."
            )
        )
    else:
        reasons.append(
            (
                f"Risk Status {risk_status}, "
                f"Action {risk_action} 조건으로 "
                "Paper Pipeline 실행을 차단합니다."
            )
        )

    checks_passed = (
        risk_valid
        and gate_status
        in VALID_GATE_STATUSES
    )

    return PaperTradingRiskGateDecision(
        gate_status=gate_status,
        gate_status_label=gate_status_label,
        risk_status=risk_status,
        risk_action=risk_action,
        gate_passed=gate_passed,
        pipeline_execution_allowed=(
            gate_passed
        ),
        checks_passed=checks_passed,
        reasons=reasons,
        warnings=warnings,
    )


def run_paper_trading_risk_gated_pipeline(
    symbol: str = "AAPL",
    account_cash: float = 10_000.0,
    latest_prices: dict[str, float] | None = None,
    performance_result: (
        PaperPortfolioPerformanceResult
        | dict[str, Any]
        | None
    ) = None,
    gated_policy: (
        PaperTradingRiskGatedPipelinePolicy
        | None
    ) = None,
    risk_monitor_policy: (
        PaperTradingRiskMonitorPolicy
        | None
    ) = None,
    daily_pipeline_policy: (
        PaperTradingDailyPipelinePolicy
        | None
    ) = None,
    risk_monitor_result: (
        PaperTradingRiskMonitorResult
        | None
    ) = None,
    daily_pipeline_runner: (
        Callable[..., PaperTradingDailyPipelineResult]
        | None
    ) = None,
) -> PaperTradingRiskGatedPipelineResult:
    """
    V10.4 Risk Monitor를 먼저 실행한 뒤,
    허용된 경우에만 V10.2 Daily Pipeline을 실행합니다.

    실제 Broker API와 Live Execution은 수행하지 않습니다.
    """

    normalized_symbol = normalize_symbol(symbol)

    if (
        not is_valid_number(account_cash)
        or float(account_cash) <= 0
    ):
        raise ValueError(
            "Account Cash는 0보다 큰 숫자여야 합니다."
        )

    policy = (
        gated_policy
        if gated_policy is not None
        else PaperTradingRiskGatedPipelinePolicy()
    )

    policy_valid, policy_errors = (
        validate_gated_policy(policy)
    )

    risk_result: (
        PaperTradingRiskMonitorResult
        | None
    ) = None
    daily_result: (
        PaperTradingDailyPipelineResult
        | None
    ) = None

    risk_monitor_executed = False
    risk_gate_evaluated = False
    daily_pipeline_requested = False
    daily_pipeline_executed = False
    daily_pipeline_skipped = True

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
            policy=policy,
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
                    "Paper Pipeline을 차단합니다."
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
        daily_pipeline_requested = True

        try:
            runner = (
                daily_pipeline_runner
                if daily_pipeline_runner is not None
                else run_paper_trading_daily_pipeline
            )

            daily_result = runner(
                symbol=normalized_symbol,
                account_cash=float(
                    account_cash
                ),
                latest_prices=latest_prices,
                pipeline_policy=(
                    daily_pipeline_policy
                ),
            )

            daily_pipeline_executed = True
            daily_pipeline_skipped = False
        except Exception as error:
            warnings.append(
                f"Daily Pipeline 실행 실패: {error}"
            )
    else:
        reasons.append(
            "Risk Gate가 Daily Pipeline 실행 전에 차단했습니다."
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

    if daily_result is not None:
        (
            daily_safety_valid,
            daily_safety_errors,
        ) = validate_daily_pipeline_safety(
            daily_result
        )
        warnings.extend(daily_safety_errors)

        daily_pipeline_checks_passed = bool(
            daily_safety_valid
            and (
                daily_result.all_checks_passed
                if policy.require_daily_pipeline_checks
                else True
            )
        )
    else:
        daily_pipeline_checks_passed = (
            not gate_decision.gate_passed
            and daily_pipeline_skipped
        )

    if not policy_valid:
        gated_pipeline_status = "FAILED"
        gated_pipeline_status_label = (
            "Gated Pipeline Policy 검사 실패"
        )
    elif not risk_checks_passed:
        gated_pipeline_status = "FAILED"
        gated_pipeline_status_label = (
            "Risk Monitor 검사 실패"
        )
    elif gate_decision.gate_passed:
        if (
            daily_pipeline_executed
            and daily_pipeline_checks_passed
        ):
            gated_pipeline_status = "COMPLETED"
            gated_pipeline_status_label = (
                "Risk 통과 후 Daily Pipeline 완료"
            )
        else:
            gated_pipeline_status = "FAILED"
            gated_pipeline_status_label = (
                "Daily Pipeline 실행 또는 검사 실패"
            )
    else:
        gated_pipeline_status = "BLOCKED"
        gated_pipeline_status_label = (
            "Risk Gate에서 Pipeline 차단"
        )

    paper_trading_allowed = bool(
        gate_decision.gate_passed
        and daily_pipeline_executed
    )

    risk_gate_blocked = (
        not gate_decision.gate_passed
    )

    all_checks_passed = bool(
        policy_valid
        and risk_checks_passed
        and gate_checks_passed
        and daily_pipeline_checks_passed
        and gated_pipeline_status
        in {
            "COMPLETED",
            "BLOCKED",
        }
    )

    if gated_pipeline_status == "COMPLETED":
        reasons.append(
            "Risk Gate 통과 후 V10.2 Daily Pipeline을 완료했습니다."
        )
        next_actions = [
            "Daily Pipeline과 Performance 결과를 확인합니다.",
            "다음 Paper 거래 전 V10.4 Risk Monitor를 다시 실행합니다.",
        ]
    elif gated_pipeline_status == "BLOCKED":
        reasons.append(
            "Risk Gate가 V10.2 Daily Pipeline 실행을 차단했습니다."
        )
        next_actions = [
            "Risk Monitor의 Triggered Rule을 확인합니다.",
            "Risk가 회복될 때까지 신규 Paper 거래를 중단합니다.",
        ]
    else:
        next_actions = [
            "Warnings와 실패 원인을 확인합니다.",
            "입력 또는 Policy를 수정한 후 V10.5를 다시 실행합니다.",
        ]

    warnings.extend(
        [
            (
                "V10.5는 연구용 Paper Trading "
                "Risk-Gated Pipeline입니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    result = PaperTradingRiskGatedPipelineResult(
        version="V10.5",
        created_at=datetime.now().isoformat(),
        gated_pipeline_id=str(uuid.uuid4()),
        symbol=normalized_symbol,
        gated_pipeline_status=(
            gated_pipeline_status
        ),
        gated_pipeline_status_label=(
            gated_pipeline_status_label
        ),
        risk_monitor_id=(
            risk_result.monitor_id
            if risk_result is not None
            else None
        ),
        daily_pipeline_id=(
            daily_result.pipeline_id
            if daily_result is not None
            else None
        ),
        risk_monitor_executed=(
            risk_monitor_executed
        ),
        risk_gate_evaluated=(
            risk_gate_evaluated
        ),
        daily_pipeline_requested=(
            daily_pipeline_requested
        ),
        daily_pipeline_executed=(
            daily_pipeline_executed
        ),
        daily_pipeline_skipped=(
            daily_pipeline_skipped
        ),
        risk_checks_passed=(
            risk_checks_passed
        ),
        gate_checks_passed=(
            gate_checks_passed
        ),
        daily_pipeline_checks_passed=(
            daily_pipeline_checks_passed
        ),
        all_checks_passed=(
            all_checks_passed
        ),
        paper_trading_allowed=(
            paper_trading_allowed
        ),
        risk_gate_blocked=risk_gate_blocked,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        gated_policy=policy,
        risk_gate_decision=(
            gate_decision
        ),
        risk_monitor_result=risk_result,
        daily_pipeline_result=daily_result,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_risk_gated_pipeline(
        result
    )

    return result


def save_paper_trading_risk_gated_pipeline(
    result: PaperTradingRiskGatedPipelineResult,
) -> tuple[Path, Path]:
    """
    V10.5 Report와 Latest JSON을 저장합니다.
    """

    PAPER_RISK_GATED_PIPELINE_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_RISK_GATED_PIPELINE_OUTPUT_DIRECTORY
        / (
            "paper_trading_risk_gated_pipeline_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_RISK_GATED_PIPELINE_OUTPUT_DIRECTORY
        / (
            "paper_trading_risk_gated_pipeline_"
            "latest.json"
        )
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_risk_gated_pipeline() -> (
    dict[str, Any]
):
    """
    저장된 최신 V10.5 결과를 읽습니다.
    """

    latest_path = (
        PAPER_RISK_GATED_PIPELINE_OUTPUT_DIRECTORY
        / (
            "paper_trading_risk_gated_pipeline_"
            "latest.json"
        )
    )

    return read_json_file(latest_path)


def print_paper_trading_risk_gated_pipeline(
    result: PaperTradingRiskGatedPipelineResult,
) -> None:
    """
    V10.5 결과를 터미널에 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.5 PAPER TRADING RISK-GATED PIPELINE"
    )
    print("=" * line_length)

    print(
        f"Gated pipeline status          : "
        f"{result.gated_pipeline_status}"
    )
    print(
        f"Gated pipeline status label    : "
        f"{result.gated_pipeline_status_label}"
    )
    print(
        f"Gated pipeline ID              : "
        f"{result.gated_pipeline_id}"
    )
    print(
        f"Symbol                         : "
        f"{result.symbol}"
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
    print(
        f"Risk gate blocked              : "
        f"{result.risk_gate_blocked}"
    )

    print()
    print("DAILY PIPELINE")
    print("-" * line_length)

    print(
        f"Daily pipeline ID              : "
        f"{result.daily_pipeline_id}"
    )
    print(
        f"Daily pipeline requested       : "
        f"{result.daily_pipeline_requested}"
    )
    print(
        f"Daily pipeline executed        : "
        f"{result.daily_pipeline_executed}"
    )
    print(
        f"Daily pipeline skipped         : "
        f"{result.daily_pipeline_skipped}"
    )

    if result.daily_pipeline_result is not None:
        print(
            f"Daily pipeline status          : "
            f"{result.daily_pipeline_result.pipeline_status}"
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
        f"Daily pipeline checks passed   : "
        f"{result.daily_pipeline_checks_passed}"
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
        "주의: V10.5는 연구용 Paper Trading Pipeline이며 "
        "실제 Broker 주문을 수행하지 않습니다."
    )


if __name__ == "__main__":
    gated_result = (
        run_paper_trading_risk_gated_pipeline()
    )

    if gated_result.gated_policy.save_output:
        save_paper_trading_risk_gated_pipeline(
            gated_result
        )
