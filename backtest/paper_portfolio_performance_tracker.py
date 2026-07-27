import json
import math
import statistics
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_portfolio_valuation import (
    PAPER_VALUATION_OUTPUT_DIRECTORY,
    PaperPortfolioValuationResult,
    load_latest_valuation_result,
    run_paper_portfolio_valuation,
    save_paper_portfolio_valuation,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_PERFORMANCE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_portfolio_performance"
)

PERFORMANCE_HISTORY_FILE = (
    PAPER_PERFORMANCE_OUTPUT_DIRECTORY
    / "paper_portfolio_performance_history.json"
)

PERFORMANCE_LATEST_FILE = (
    PAPER_PERFORMANCE_OUTPUT_DIRECTORY
    / "paper_portfolio_performance_latest.json"
)


VALID_PERFORMANCE_STATUSES = {
    "TRACKED",
    "FIRST_SNAPSHOT",
    "NO_CHANGE",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperPortfolioPerformancePolicy:
    """
    V10.1 Portfolio Performance Tracker 정책입니다.

    이 정책은 연구용 Paper Portfolio의 성과만 계산합니다.
    실제 계좌, 실제 주문 또는 Live Execution에는 연결되지 않습니다.
    """

    annual_trading_periods: int = 252
    risk_free_rate_percent: float = 0.0

    minimum_valid_equity: float = 0.01
    maximum_valid_equity: float = 1_000_000_000.0

    drawdown_warning_percent: float = 10.0
    maximum_history_records: int = 10_000

    reject_duplicate_valuation_ids: bool = True
    require_same_portfolio_id: bool = True
    require_successful_valuation: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperPerformanceSnapshot:
    """
    V10.0 Valuation 한 건에서 가져온 성과 추적용 Snapshot입니다.
    """

    snapshot_id: str
    created_at: str

    valuation_id: str
    portfolio_id: str
    valuation_status: str

    initial_cash: float
    cash_balance: float
    total_market_value: float
    total_equity: float

    total_unrealized_pnl: float
    total_realized_pnl: float
    total_commission: float
    total_profit_loss: float

    total_return_percent: float
    cash_weight_percent: float
    invested_weight_percent: float

    position_count: int
    long_position_count: int

    period_profit_loss: float = 0.0
    period_return_percent: float = 0.0

    equity_high_water_mark: float = 0.0
    drawdown_amount: float = 0.0
    drawdown_percent: float = 0.0

    is_profitable_period: bool = False
    is_loss_period: bool = False
    is_flat_period: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperPortfolioPerformanceResult:
    """
    V10.1 Portfolio Performance Tracker 전체 결과입니다.
    """

    version: str
    created_at: str

    performance_id: str
    portfolio_id: str
    source_valuation_id: str
    source_valuation_file: str | None

    performance_status: str
    performance_status_label: str

    history_record_count: int
    performance_period_count: int

    first_snapshot_at: str | None
    latest_snapshot_at: str | None

    initial_equity: float
    previous_equity: float
    current_equity: float

    period_profit_loss: float
    period_return_percent: float

    cumulative_profit_loss: float
    cumulative_return_percent: float

    equity_high_water_mark: float
    current_drawdown_amount: float
    current_drawdown_percent: float
    maximum_drawdown_amount: float
    maximum_drawdown_percent: float

    average_period_return_percent: float
    best_period_return_percent: float
    worst_period_return_percent: float

    return_volatility_percent: float
    annualized_return_percent: float
    annualized_volatility_percent: float
    sharpe_ratio: float

    profitable_period_count: int
    loss_period_count: int
    flat_period_count: int
    win_rate_percent: float

    gross_profit: float
    gross_loss: float
    profit_factor: float

    total_unrealized_pnl: float
    total_realized_pnl: float
    total_commission: float

    source_loaded: bool
    source_valid: bool
    policy_checks_passed: bool
    history_checks_passed: bool
    calculation_checks_passed: bool
    all_checks_passed: bool

    snapshot_added: bool
    duplicate_snapshot: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    performance_policy: PaperPortfolioPerformancePolicy
    latest_snapshot: PaperPerformanceSnapshot
    performance_history: list[PaperPerformanceSnapshot]

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None
    history_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["performance_policy"] = (
            self.performance_policy.to_dict()
        )

        payload["latest_snapshot"] = (
            self.latest_snapshot.to_dict()
        )

        payload["performance_history"] = [
            snapshot.to_dict()
            for snapshot in self.performance_history
        ]

        return payload


def is_valid_number(value: Any) -> bool:
    """
    bool을 제외한 유한한 숫자인지 검사합니다.
    """

    if isinstance(value, bool):
        return False

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return False

    return math.isfinite(numeric_value)


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


def round_ratio(value: float) -> float:
    """
    Ratio를 소수점 여섯째 자리로 반올림합니다.
    """

    return round(float(value), 6)


def parse_datetime(value: str) -> datetime:
    """
    ISO 형식 문자열을 datetime으로 변환합니다.
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "created_at이 비어 있습니다."
        )

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ValueError(
            f"created_at이 ISO 형식이 아닙니다: {value}"
        ) from error


def write_json_file(
    file_path: Path,
    payload: dict[str, Any] | list[Any],
) -> None:
    """
    임시 파일을 이용해 JSON 파일을 안전하게 저장합니다.
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


def read_json_file(file_path: Path) -> Any:
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
        return json.load(file)


def validate_performance_policy(
    policy: PaperPortfolioPerformancePolicy,
) -> tuple[bool, list[str]]:
    """
    V10.1 Performance Policy를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        policy,
        PaperPortfolioPerformancePolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperPortfolioPerformancePolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    boolean_fields = {
        "reject_duplicate_valuation_ids": (
            policy.reject_duplicate_valuation_ids
        ),
        "require_same_portfolio_id": (
            policy.require_same_portfolio_id
        ),
        "require_successful_valuation": (
            policy.require_successful_valuation
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

    if (
        not isinstance(
            policy.annual_trading_periods,
            int,
        )
        or policy.annual_trading_periods <= 0
    ):
        errors.append(
            "Annual Trading Periods는 0보다 큰 int여야 합니다."
        )

    if (
        not isinstance(
            policy.maximum_history_records,
            int,
        )
        or policy.maximum_history_records <= 0
    ):
        errors.append(
            "Maximum History Records는 0보다 큰 int여야 합니다."
        )

    numeric_fields = {
        "risk_free_rate_percent": (
            policy.risk_free_rate_percent
        ),
        "minimum_valid_equity": (
            policy.minimum_valid_equity
        ),
        "maximum_valid_equity": (
            policy.maximum_valid_equity
        ),
        "drawdown_warning_percent": (
            policy.drawdown_warning_percent
        ),
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(value):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if (
        is_valid_number(policy.minimum_valid_equity)
        and policy.minimum_valid_equity <= 0
    ):
        errors.append(
            "Minimum Valid Equity는 0보다 커야 합니다."
        )

    if (
        is_valid_number(policy.maximum_valid_equity)
        and policy.maximum_valid_equity <= 0
    ):
        errors.append(
            "Maximum Valid Equity는 0보다 커야 합니다."
        )

    if (
        is_valid_number(policy.minimum_valid_equity)
        and is_valid_number(policy.maximum_valid_equity)
        and policy.minimum_valid_equity
        >= policy.maximum_valid_equity
    ):
        errors.append(
            "Minimum Valid Equity는 Maximum Valid Equity보다 "
            "작아야 합니다."
        )

    if (
        is_valid_number(policy.drawdown_warning_percent)
        and not 0
        <= policy.drawdown_warning_percent
        <= 100
    ):
        errors.append(
            "Drawdown Warning Percent는 0부터 100 사이여야 합니다."
        )

    if not policy.paper_only:
        errors.append(
            "V10.1에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.1에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def valuation_result_to_dict(
    valuation_result: (
        PaperPortfolioValuationResult
        | dict[str, Any]
    ),
) -> dict[str, Any]:
    """
    V10.0 Valuation 결과를 Dictionary로 정규화합니다.
    """

    if isinstance(
        valuation_result,
        PaperPortfolioValuationResult,
    ):
        return valuation_result.to_dict()

    if isinstance(valuation_result, dict):
        return dict(valuation_result)

    raise TypeError(
        "Valuation 결과는 PaperPortfolioValuationResult "
        "또는 Dictionary 형식이어야 합니다."
    )


def validate_valuation_payload(
    payload: dict[str, Any],
    policy: PaperPortfolioPerformancePolicy,
) -> tuple[bool, list[str]]:
    """
    V10.0 Valuation 결과가 성과 추적에 적합한지 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(payload, dict):
        return (
            False,
            ["Valuation Payload가 Dictionary가 아닙니다."],
        )

    if payload.get("version") != "V10.0":
        errors.append(
            "Valuation 버전이 V10.0이 아닙니다."
        )

    text_fields = {
        "valuation_id": payload.get("valuation_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "created_at": payload.get("created_at"),
        "valuation_status": payload.get(
            "valuation_status"
        ),
    }

    for field_name, value in text_fields.items():
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"{field_name}가 비어 있습니다."
            )

    if isinstance(payload.get("created_at"), str):
        try:
            parse_datetime(payload["created_at"])
        except ValueError as error:
            errors.append(str(error))

    numeric_fields = {
        "initial_cash": payload.get("initial_cash"),
        "cash_balance": payload.get("cash_balance"),
        "updated_total_market_value": payload.get(
            "updated_total_market_value"
        ),
        "updated_total_equity": payload.get(
            "updated_total_equity"
        ),
        "updated_total_unrealized_pnl": payload.get(
            "updated_total_unrealized_pnl"
        ),
        "total_realized_pnl": payload.get(
            "total_realized_pnl"
        ),
        "total_commission": payload.get(
            "total_commission"
        ),
        "total_profit_loss": payload.get(
            "total_profit_loss"
        ),
        "total_return_percent": payload.get(
            "total_return_percent"
        ),
        "cash_weight_percent": payload.get(
            "cash_weight_percent"
        ),
        "invested_weight_percent": payload.get(
            "invested_weight_percent"
        ),
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(value):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    equity = payload.get("updated_total_equity")

    if is_valid_number(equity):
        numeric_equity = float(equity)

        if numeric_equity < policy.minimum_valid_equity:
            errors.append(
                "Updated Total Equity가 최소 허용값보다 낮습니다."
            )

        if numeric_equity > policy.maximum_valid_equity:
            errors.append(
                "Updated Total Equity가 최대 허용값보다 높습니다."
            )

    if policy.require_successful_valuation:
        if payload.get("valuation_status") not in {
            "VALUED",
            "PARTIAL",
            "NO_POSITIONS",
        }:
            errors.append(
                "성과 추적이 가능한 Valuation Status가 아닙니다."
            )

        if not bool(payload.get("all_checks_passed")):
            errors.append(
                "V10.0 Valuation의 All Checks가 통과하지 않았습니다."
            )

    expected_equity_fields = (
        payload.get("cash_balance"),
        payload.get("updated_total_market_value"),
        payload.get("updated_total_equity"),
    )

    if all(
        is_valid_number(value)
        for value in expected_equity_fields
    ):
        expected_equity = round_money(
            float(payload["cash_balance"])
            + float(payload["updated_total_market_value"])
        )

        actual_equity = round_money(
            float(payload["updated_total_equity"])
        )

        if abs(expected_equity - actual_equity) > 0.01:
            errors.append(
                "Cash + Market Value와 Total Equity가 일치하지 않습니다."
            )

    return (not errors, errors)


def snapshot_from_dict(
    payload: dict[str, Any],
) -> PaperPerformanceSnapshot:
    """
    Dictionary를 PaperPerformanceSnapshot으로 변환합니다.
    """

    return PaperPerformanceSnapshot(
        snapshot_id=str(payload["snapshot_id"]),
        created_at=str(payload["created_at"]),
        valuation_id=str(payload["valuation_id"]),
        portfolio_id=str(payload["portfolio_id"]),
        valuation_status=str(
            payload["valuation_status"]
        ),
        initial_cash=float(payload["initial_cash"]),
        cash_balance=float(payload["cash_balance"]),
        total_market_value=float(
            payload["total_market_value"]
        ),
        total_equity=float(payload["total_equity"]),
        total_unrealized_pnl=float(
            payload["total_unrealized_pnl"]
        ),
        total_realized_pnl=float(
            payload["total_realized_pnl"]
        ),
        total_commission=float(
            payload["total_commission"]
        ),
        total_profit_loss=float(
            payload["total_profit_loss"]
        ),
        total_return_percent=float(
            payload["total_return_percent"]
        ),
        cash_weight_percent=float(
            payload["cash_weight_percent"]
        ),
        invested_weight_percent=float(
            payload["invested_weight_percent"]
        ),
        position_count=int(payload["position_count"]),
        long_position_count=int(
            payload["long_position_count"]
        ),
        period_profit_loss=float(
            payload.get("period_profit_loss", 0.0)
        ),
        period_return_percent=float(
            payload.get("period_return_percent", 0.0)
        ),
        equity_high_water_mark=float(
            payload.get(
                "equity_high_water_mark",
                payload["total_equity"],
            )
        ),
        drawdown_amount=float(
            payload.get("drawdown_amount", 0.0)
        ),
        drawdown_percent=float(
            payload.get("drawdown_percent", 0.0)
        ),
        is_profitable_period=bool(
            payload.get("is_profitable_period", False)
        ),
        is_loss_period=bool(
            payload.get("is_loss_period", False)
        ),
        is_flat_period=bool(
            payload.get("is_flat_period", True)
        ),
    )


def validate_performance_snapshot(
    snapshot: PaperPerformanceSnapshot,
    policy: PaperPortfolioPerformancePolicy,
) -> tuple[bool, list[str]]:
    """
    저장된 성과 Snapshot을 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        snapshot,
        PaperPerformanceSnapshot,
    ):
        return (
            False,
            ["Snapshot 형식이 올바르지 않습니다."],
        )

    for field_name, value in {
        "snapshot_id": snapshot.snapshot_id,
        "created_at": snapshot.created_at,
        "valuation_id": snapshot.valuation_id,
        "portfolio_id": snapshot.portfolio_id,
    }.items():
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"{field_name}가 비어 있습니다."
            )

    try:
        parse_datetime(snapshot.created_at)
    except ValueError as error:
        errors.append(str(error))

    numeric_values = {
        "initial_cash": snapshot.initial_cash,
        "cash_balance": snapshot.cash_balance,
        "total_market_value": snapshot.total_market_value,
        "total_equity": snapshot.total_equity,
        "total_unrealized_pnl": (
            snapshot.total_unrealized_pnl
        ),
        "total_realized_pnl": (
            snapshot.total_realized_pnl
        ),
        "total_commission": snapshot.total_commission,
        "total_profit_loss": snapshot.total_profit_loss,
        "total_return_percent": (
            snapshot.total_return_percent
        ),
    }

    for field_name, value in numeric_values.items():
        if not is_valid_number(value):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if is_valid_number(snapshot.total_equity):
        if (
            snapshot.total_equity
            < policy.minimum_valid_equity
        ):
            errors.append(
                "Snapshot Equity가 최소 허용값보다 낮습니다."
            )

        if (
            snapshot.total_equity
            > policy.maximum_valid_equity
        ):
            errors.append(
                "Snapshot Equity가 최대 허용값보다 높습니다."
            )

    return (not errors, errors)


def create_performance_snapshot(
    valuation_payload: dict[str, Any],
) -> PaperPerformanceSnapshot:
    """
    V10.0 Valuation Payload에서 새 성과 Snapshot을 생성합니다.
    """

    return PaperPerformanceSnapshot(
        snapshot_id=str(uuid.uuid4()),
        created_at=str(valuation_payload["created_at"]),
        valuation_id=str(
            valuation_payload["valuation_id"]
        ),
        portfolio_id=str(
            valuation_payload["portfolio_id"]
        ),
        valuation_status=str(
            valuation_payload["valuation_status"]
        ),
        initial_cash=round_money(
            valuation_payload["initial_cash"]
        ),
        cash_balance=round_money(
            valuation_payload["cash_balance"]
        ),
        total_market_value=round_money(
            valuation_payload[
                "updated_total_market_value"
            ]
        ),
        total_equity=round_money(
            valuation_payload["updated_total_equity"]
        ),
        total_unrealized_pnl=round_money(
            valuation_payload[
                "updated_total_unrealized_pnl"
            ]
        ),
        total_realized_pnl=round_money(
            valuation_payload["total_realized_pnl"]
        ),
        total_commission=round_money(
            valuation_payload["total_commission"]
        ),
        total_profit_loss=round_money(
            valuation_payload["total_profit_loss"]
        ),
        total_return_percent=round_percent(
            valuation_payload["total_return_percent"]
        ),
        cash_weight_percent=round_percent(
            valuation_payload["cash_weight_percent"]
        ),
        invested_weight_percent=round_percent(
            valuation_payload[
                "invested_weight_percent"
            ]
        ),
        position_count=int(
            valuation_payload.get("position_count", 0)
        ),
        long_position_count=int(
            valuation_payload.get(
                "long_position_count",
                0,
            )
        ),
    )


def load_performance_history(
    file_path: Path | None = None,
) -> list[PaperPerformanceSnapshot]:
    """
    저장된 V10.1 성과 History를 불러옵니다.

    첫 실행처럼 파일이 없으면 빈 목록을 반환합니다.
    """

    target_path = (
        file_path
        if file_path is not None
        else PERFORMANCE_HISTORY_FILE
    )

    if not target_path.exists():
        return []

    payload = read_json_file(target_path)

    if isinstance(payload, dict):
        raw_history = payload.get(
            "performance_history",
            [],
        )
    elif isinstance(payload, list):
        raw_history = payload
    else:
        raise RuntimeError(
            "Performance History JSON 형식이 올바르지 않습니다."
        )

    if not isinstance(raw_history, list):
        raise RuntimeError(
            "performance_history가 List 형식이 아닙니다."
        )

    history: list[PaperPerformanceSnapshot] = []

    for item in raw_history:
        if not isinstance(item, dict):
            raise RuntimeError(
                "Performance Snapshot이 Dictionary가 아닙니다."
            )

        history.append(snapshot_from_dict(item))

    return history


def prepare_performance_history(
    existing_history: list[PaperPerformanceSnapshot],
    new_snapshot: PaperPerformanceSnapshot,
    policy: PaperPortfolioPerformancePolicy,
) -> tuple[
    list[PaperPerformanceSnapshot],
    bool,
    bool,
    list[str],
]:
    """
    기존 History를 검증하고 새 Snapshot을 안전하게 추가합니다.
    """

    errors: list[str] = []
    valid_history: list[PaperPerformanceSnapshot] = []

    if not isinstance(existing_history, list):
        return (
            [],
            False,
            False,
            ["Existing History가 List 형식이 아닙니다."],
        )

    for index, snapshot in enumerate(existing_history):
        valid, snapshot_errors = (
            validate_performance_snapshot(
                snapshot=snapshot,
                policy=policy,
            )
        )

        if not valid:
            errors.extend(
                [
                    f"History #{index + 1}: {error}"
                    for error in snapshot_errors
                ]
            )
            continue

        if (
            policy.require_same_portfolio_id
            and snapshot.portfolio_id
            != new_snapshot.portfolio_id
        ):
            errors.append(
                (
                    f"History #{index + 1}의 Portfolio ID가 "
                    "현재 Portfolio ID와 다릅니다."
                )
            )
            continue

        valid_history.append(snapshot)

    duplicate_snapshot = any(
        snapshot.valuation_id
        == new_snapshot.valuation_id
        for snapshot in valid_history
    )

    snapshot_added = False

    if not duplicate_snapshot:
        valid_history.append(new_snapshot)
        snapshot_added = True
    elif not policy.reject_duplicate_valuation_ids:
        valid_history = [
            snapshot
            for snapshot in valid_history
            if snapshot.valuation_id
            != new_snapshot.valuation_id
        ]
        valid_history.append(new_snapshot)
        snapshot_added = True

    valid_history.sort(
        key=lambda snapshot: parse_datetime(
            snapshot.created_at
        )
    )

    if (
        len(valid_history)
        > policy.maximum_history_records
    ):
        valid_history = valid_history[
            -policy.maximum_history_records:
        ]

    history_checks_passed = not errors

    return (
        valid_history,
        snapshot_added,
        duplicate_snapshot,
        errors,
    )


def recalculate_snapshot_metrics(
    history: list[PaperPerformanceSnapshot],
) -> None:
    """
    History 전체의 기간 수익률과 Drawdown을 다시 계산합니다.

    History가 과거 날짜로 추가되어도 모든 값이 일관되도록
    처음부터 다시 계산합니다.
    """

    high_water_mark = 0.0

    for index, snapshot in enumerate(history):
        if index == 0:
            period_profit_loss = 0.0
            period_return_percent = 0.0
        else:
            previous_equity = history[
                index - 1
            ].total_equity

            period_profit_loss = round_money(
                snapshot.total_equity
                - previous_equity
            )

            if previous_equity > 0:
                period_return_percent = round_percent(
                    (
                        period_profit_loss
                        / previous_equity
                    )
                    * 100.0
                )
            else:
                period_return_percent = 0.0

        high_water_mark = max(
            high_water_mark,
            snapshot.total_equity,
        )

        drawdown_amount = round_money(
            max(
                high_water_mark
                - snapshot.total_equity,
                0.0,
            )
        )

        if high_water_mark > 0:
            drawdown_percent = round_percent(
                (
                    drawdown_amount
                    / high_water_mark
                )
                * 100.0
            )
        else:
            drawdown_percent = 0.0

        snapshot.period_profit_loss = (
            period_profit_loss
        )
        snapshot.period_return_percent = (
            period_return_percent
        )
        snapshot.equity_high_water_mark = (
            round_money(high_water_mark)
        )
        snapshot.drawdown_amount = drawdown_amount
        snapshot.drawdown_percent = drawdown_percent

        snapshot.is_profitable_period = (
            index > 0
            and period_profit_loss > 0
        )
        snapshot.is_loss_period = (
            index > 0
            and period_profit_loss < 0
        )
        snapshot.is_flat_period = (
            index == 0
            or period_profit_loss == 0
        )


def calculate_performance_metrics(
    history: list[PaperPerformanceSnapshot],
    policy: PaperPortfolioPerformancePolicy,
) -> dict[str, float | int]:
    """
    History에서 V10.1 핵심 성과 지표를 계산합니다.
    """

    if not history:
        raise ValueError(
            "Performance History가 비어 있습니다."
        )

    recalculate_snapshot_metrics(history)

    first_snapshot = history[0]
    latest_snapshot = history[-1]

    performance_snapshots = history[1:]

    period_returns = [
        snapshot.period_return_percent
        for snapshot in performance_snapshots
    ]

    period_profit_losses = [
        snapshot.period_profit_loss
        for snapshot in performance_snapshots
    ]

    initial_equity = round_money(
        first_snapshot.total_equity
    )

    current_equity = round_money(
        latest_snapshot.total_equity
    )

    previous_equity = (
        round_money(history[-2].total_equity)
        if len(history) > 1
        else current_equity
    )

    cumulative_profit_loss = round_money(
        current_equity - initial_equity
    )

    if initial_equity > 0:
        cumulative_return_percent = round_percent(
            (
                cumulative_profit_loss
                / initial_equity
            )
            * 100.0
        )
    else:
        cumulative_return_percent = 0.0

    average_period_return_percent = (
        round_percent(statistics.fmean(period_returns))
        if period_returns
        else 0.0
    )

    best_period_return_percent = (
        round_percent(max(period_returns))
        if period_returns
        else 0.0
    )

    worst_period_return_percent = (
        round_percent(min(period_returns))
        if period_returns
        else 0.0
    )

    return_volatility_percent = (
        round_percent(statistics.stdev(period_returns))
        if len(period_returns) >= 2
        else 0.0
    )

    if period_returns:
        compounded_growth = 1.0

        for period_return in period_returns:
            compounded_growth *= (
                1.0
                + period_return / 100.0
            )

        if compounded_growth > 0:
            annualized_return_percent = round_percent(
                (
                    compounded_growth
                    ** (
                        policy.annual_trading_periods
                        / len(period_returns)
                    )
                    - 1.0
                )
                * 100.0
            )
        else:
            annualized_return_percent = -100.0
    else:
        annualized_return_percent = 0.0

    annualized_volatility_percent = round_percent(
        return_volatility_percent
        * math.sqrt(policy.annual_trading_periods)
    )

    if annualized_volatility_percent > 0:
        sharpe_ratio = round_ratio(
            (
                annualized_return_percent
                - policy.risk_free_rate_percent
            )
            / annualized_volatility_percent
        )
    else:
        sharpe_ratio = 0.0

    profitable_period_count = sum(
        1
        for value in period_profit_losses
        if value > 0
    )

    loss_period_count = sum(
        1
        for value in period_profit_losses
        if value < 0
    )

    flat_period_count = sum(
        1
        for value in period_profit_losses
        if value == 0
    )

    performance_period_count = len(
        period_profit_losses
    )

    if performance_period_count > 0:
        win_rate_percent = round_percent(
            (
                profitable_period_count
                / performance_period_count
            )
            * 100.0
        )
    else:
        win_rate_percent = 0.0

    gross_profit = round_money(
        sum(
            value
            for value in period_profit_losses
            if value > 0
        )
    )

    gross_loss = round_money(
        abs(
            sum(
                value
                for value in period_profit_losses
                if value < 0
            )
        )
    )

    if gross_loss > 0:
        profit_factor = round_ratio(
            gross_profit / gross_loss
        )
    elif gross_profit > 0:
        profit_factor = round_ratio(gross_profit)
    else:
        profit_factor = 0.0

    maximum_drawdown_snapshot = max(
        history,
        key=lambda snapshot: snapshot.drawdown_percent,
    )

    return {
        "history_record_count": len(history),
        "performance_period_count": (
            performance_period_count
        ),
        "initial_equity": initial_equity,
        "previous_equity": previous_equity,
        "current_equity": current_equity,
        "period_profit_loss": (
            latest_snapshot.period_profit_loss
        ),
        "period_return_percent": (
            latest_snapshot.period_return_percent
        ),
        "cumulative_profit_loss": (
            cumulative_profit_loss
        ),
        "cumulative_return_percent": (
            cumulative_return_percent
        ),
        "equity_high_water_mark": (
            latest_snapshot.equity_high_water_mark
        ),
        "current_drawdown_amount": (
            latest_snapshot.drawdown_amount
        ),
        "current_drawdown_percent": (
            latest_snapshot.drawdown_percent
        ),
        "maximum_drawdown_amount": (
            maximum_drawdown_snapshot.drawdown_amount
        ),
        "maximum_drawdown_percent": (
            maximum_drawdown_snapshot.drawdown_percent
        ),
        "average_period_return_percent": (
            average_period_return_percent
        ),
        "best_period_return_percent": (
            best_period_return_percent
        ),
        "worst_period_return_percent": (
            worst_period_return_percent
        ),
        "return_volatility_percent": (
            return_volatility_percent
        ),
        "annualized_return_percent": (
            annualized_return_percent
        ),
        "annualized_volatility_percent": (
            annualized_volatility_percent
        ),
        "sharpe_ratio": sharpe_ratio,
        "profitable_period_count": (
            profitable_period_count
        ),
        "loss_period_count": loss_period_count,
        "flat_period_count": flat_period_count,
        "win_rate_percent": win_rate_percent,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
    }


def build_performance_notes(
    performance_status: str,
    metrics: dict[str, float | int],
    policy: PaperPortfolioPerformancePolicy,
    duplicate_snapshot: bool,
) -> tuple[list[str], list[str], list[str]]:
    """
    Reasons, Warnings, Next Actions를 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if performance_status == "FIRST_SNAPSHOT":
        reasons.append(
            "첫 번째 Valuation Snapshot을 성과 기준점으로 저장했습니다."
        )
    elif performance_status == "TRACKED":
        reasons.append(
            "새 Valuation Snapshot을 추가하고 성과 지표를 계산했습니다."
        )
    elif performance_status == "NO_CHANGE":
        reasons.append(
            "이미 처리한 Valuation이므로 History를 변경하지 않았습니다."
        )
    elif performance_status == "BLOCKED":
        reasons.append(
            "Valuation 또는 History 검사 실패로 추적이 차단되었습니다."
        )
    else:
        reasons.append(
            "Portfolio Performance 계산을 완료하지 못했습니다."
        )

    if duplicate_snapshot:
        warnings.append(
            "동일한 Valuation ID가 History에 이미 존재합니다."
        )

    drawdown_percent = float(
        metrics.get("current_drawdown_percent", 0.0)
    )

    if (
        drawdown_percent
        >= policy.drawdown_warning_percent
    ):
        warnings.append(
            (
                f"현재 Drawdown이 {drawdown_percent:.4f}%로 "
                "설정된 경고 기준 이상입니다."
            )
        )

    if int(
        metrics.get("performance_period_count", 0)
    ) < 2:
        warnings.append(
            "성과 기간이 적어 변동성과 Sharpe Ratio의 의미가 제한적입니다."
        )

    warnings.extend(
        [
            (
                "이 결과는 연구용 Paper Trading "
                "Portfolio 성과입니다."
            ),
            (
                "수익률과 위험 지표는 미래 성과를 보장하지 않습니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 Live Execution은 "
                "모두 차단됩니다."
            ),
        ]
    )

    if performance_status in {
        "TRACKED",
        "FIRST_SNAPSHOT",
        "NO_CHANGE",
    }:
        next_actions = [
            "새로운 V10.0 Valuation마다 V10.1 Tracker를 실행합니다.",
            "성과 History와 최대 Drawdown 변화를 확인합니다.",
            "V10.2에서 Performance Tracker 자동 테스트를 추가합니다.",
        ]
    else:
        next_actions = [
            "V10.0 Valuation 결과와 All Checks 상태를 확인합니다.",
            "Performance History JSON의 형식을 확인합니다.",
            "문제를 수정한 후 V10.1 Tracker를 다시 실행합니다.",
        ]

    return (reasons, warnings, next_actions)


def run_paper_portfolio_performance_tracker(
    valuation_result: (
        PaperPortfolioValuationResult
        | dict[str, Any]
        | None
    ) = None,
    existing_history: (
        list[PaperPerformanceSnapshot]
        | None
    ) = None,
    performance_policy: (
        PaperPortfolioPerformancePolicy
        | None
    ) = None,
    latest_prices: dict[str, float] | None = None,
    initial_cash: float = 10_000.0,
) -> PaperPortfolioPerformanceResult:
    """
    V10.1 Portfolio Performance Tracker를 실행합니다.

    valuation_result가 없으면:

    1. 저장된 최신 V10.0 Valuation을 읽습니다.
    2. 저장 파일도 없으면 V10.0 Valuation을 새로 실행합니다.

    실제 Broker 주문이나 Live Execution은 수행하지 않습니다.
    """

    policy = (
        performance_policy
        if performance_policy is not None
        else PaperPortfolioPerformancePolicy()
    )

    policy_valid, policy_errors = (
        validate_performance_policy(policy)
    )

    source_valuation_file: str | None = None
    source_loaded = False
    source_load_errors: list[str] = []

    if valuation_result is None:
        latest_valuation_path = (
            PAPER_VALUATION_OUTPUT_DIRECTORY
            / "paper_portfolio_valuation_latest.json"
        )

        if latest_valuation_path.exists():
            source_valuation_file = str(
                latest_valuation_path
            )

            try:
                valuation_result = (
                    load_latest_valuation_result()
                )
                source_loaded = True
            except Exception as error:
                source_load_errors.append(
                    f"최신 Valuation 파일 로드 실패: {error}"
                )

        if valuation_result is None:
            generated_valuation = (
                run_paper_portfolio_valuation(
                    latest_prices=latest_prices,
                    initial_cash=initial_cash,
                )
            )

            save_paper_portfolio_valuation(
                generated_valuation
            )

            valuation_result = generated_valuation
            source_valuation_file = (
                generated_valuation.latest_path
                or generated_valuation.report_path
            )
            source_loaded = True
    else:
        source_loaded = True

        if isinstance(
            valuation_result,
            PaperPortfolioValuationResult,
        ):
            source_valuation_file = (
                valuation_result.latest_path
                or valuation_result.report_path
            )

    valuation_payload = valuation_result_to_dict(
        valuation_result
    )

    source_valid, source_errors = (
        validate_valuation_payload(
            payload=valuation_payload,
            policy=policy,
        )
    )

    source_errors.extend(source_load_errors)

    new_snapshot = create_performance_snapshot(
        valuation_payload
    )

    if existing_history is None:
        try:
            existing_history = (
                load_performance_history()
            )
        except Exception as error:
            existing_history = []
            source_errors.append(
                f"기존 Performance History 로드 실패: {error}"
            )

    history: list[PaperPerformanceSnapshot] = list(
        existing_history
    )

    snapshot_added = False
    duplicate_snapshot = False
    history_errors: list[str] = []
    history_checks_passed = False

    if source_valid and policy_valid:
        (
            history,
            snapshot_added,
            duplicate_snapshot,
            history_errors,
        ) = prepare_performance_history(
            existing_history=history,
            new_snapshot=new_snapshot,
            policy=policy,
        )

        history_checks_passed = not history_errors

    if not history:
        history = [new_snapshot]

    metrics = calculate_performance_metrics(
        history=history,
        policy=policy,
    )

    latest_snapshot = history[-1]

    expected_cumulative_pnl = round_money(
        float(metrics["current_equity"])
        - float(metrics["initial_equity"])
    )

    calculation_checks_passed = (
        abs(
            expected_cumulative_pnl
            - float(metrics["cumulative_profit_loss"])
        )
        <= 0.01
        and float(metrics["maximum_drawdown_amount"])
        >= 0
        and float(metrics["maximum_drawdown_percent"])
        >= 0
    )

    if not source_valid:
        performance_status = "BLOCKED"
        performance_status_label = (
            "V10.0 Valuation 검사 실패"
        )
    elif not policy_valid:
        performance_status = "FAILED"
        performance_status_label = (
            "Performance Policy 검사 실패"
        )
    elif not history_checks_passed:
        performance_status = "BLOCKED"
        performance_status_label = (
            "Performance History 검사 실패"
        )
    elif duplicate_snapshot and not snapshot_added:
        performance_status = "NO_CHANGE"
        performance_status_label = (
            "이미 처리한 Valuation"
        )
    elif len(history) == 1:
        performance_status = "FIRST_SNAPSHOT"
        performance_status_label = (
            "첫 성과 기준점 저장 완료"
        )
    else:
        performance_status = "TRACKED"
        performance_status_label = (
            "Portfolio 성과 추적 완료"
        )

    all_checks_passed = (
        source_loaded
        and source_valid
        and policy_valid
        and history_checks_passed
        and calculation_checks_passed
        and performance_status
        in {
            "TRACKED",
            "FIRST_SNAPSHOT",
            "NO_CHANGE",
        }
    )

    reasons, warnings, next_actions = (
        build_performance_notes(
            performance_status=performance_status,
            metrics=metrics,
            policy=policy,
            duplicate_snapshot=duplicate_snapshot,
        )
    )

    warnings.extend(policy_errors)
    warnings.extend(source_errors)
    warnings.extend(history_errors)

    result = PaperPortfolioPerformanceResult(
        version="V10.1",
        created_at=datetime.now().isoformat(),
        performance_id=str(uuid.uuid4()),
        portfolio_id=new_snapshot.portfolio_id,
        source_valuation_id=(
            new_snapshot.valuation_id
        ),
        source_valuation_file=(
            source_valuation_file
        ),
        performance_status=performance_status,
        performance_status_label=(
            performance_status_label
        ),
        history_record_count=int(
            metrics["history_record_count"]
        ),
        performance_period_count=int(
            metrics["performance_period_count"]
        ),
        first_snapshot_at=(
            history[0].created_at
            if history
            else None
        ),
        latest_snapshot_at=(
            latest_snapshot.created_at
            if history
            else None
        ),
        initial_equity=float(
            metrics["initial_equity"]
        ),
        previous_equity=float(
            metrics["previous_equity"]
        ),
        current_equity=float(
            metrics["current_equity"]
        ),
        period_profit_loss=float(
            metrics["period_profit_loss"]
        ),
        period_return_percent=float(
            metrics["period_return_percent"]
        ),
        cumulative_profit_loss=float(
            metrics["cumulative_profit_loss"]
        ),
        cumulative_return_percent=float(
            metrics["cumulative_return_percent"]
        ),
        equity_high_water_mark=float(
            metrics["equity_high_water_mark"]
        ),
        current_drawdown_amount=float(
            metrics["current_drawdown_amount"]
        ),
        current_drawdown_percent=float(
            metrics["current_drawdown_percent"]
        ),
        maximum_drawdown_amount=float(
            metrics["maximum_drawdown_amount"]
        ),
        maximum_drawdown_percent=float(
            metrics["maximum_drawdown_percent"]
        ),
        average_period_return_percent=float(
            metrics["average_period_return_percent"]
        ),
        best_period_return_percent=float(
            metrics["best_period_return_percent"]
        ),
        worst_period_return_percent=float(
            metrics["worst_period_return_percent"]
        ),
        return_volatility_percent=float(
            metrics["return_volatility_percent"]
        ),
        annualized_return_percent=float(
            metrics["annualized_return_percent"]
        ),
        annualized_volatility_percent=float(
            metrics["annualized_volatility_percent"]
        ),
        sharpe_ratio=float(metrics["sharpe_ratio"]),
        profitable_period_count=int(
            metrics["profitable_period_count"]
        ),
        loss_period_count=int(
            metrics["loss_period_count"]
        ),
        flat_period_count=int(
            metrics["flat_period_count"]
        ),
        win_rate_percent=float(
            metrics["win_rate_percent"]
        ),
        gross_profit=float(metrics["gross_profit"]),
        gross_loss=float(metrics["gross_loss"]),
        profit_factor=float(metrics["profit_factor"]),
        total_unrealized_pnl=round_money(
            latest_snapshot.total_unrealized_pnl
        ),
        total_realized_pnl=round_money(
            latest_snapshot.total_realized_pnl
        ),
        total_commission=round_money(
            latest_snapshot.total_commission
        ),
        source_loaded=source_loaded,
        source_valid=source_valid,
        policy_checks_passed=policy_valid,
        history_checks_passed=(
            history_checks_passed
        ),
        calculation_checks_passed=(
            calculation_checks_passed
        ),
        all_checks_passed=all_checks_passed,
        snapshot_added=snapshot_added,
        duplicate_snapshot=duplicate_snapshot,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        performance_policy=policy,
        latest_snapshot=latest_snapshot,
        performance_history=history,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_portfolio_performance(result)

    return result


def save_paper_portfolio_performance(
    result: PaperPortfolioPerformanceResult,
) -> tuple[Path, Path, Path]:
    """
    V10.1 성과 Report, Latest, History JSON을 저장합니다.
    """

    PAPER_PERFORMANCE_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_PERFORMANCE_OUTPUT_DIRECTORY
        / (
            "paper_portfolio_performance_"
            f"{timestamp}.json"
        )
    )

    latest_path = PERFORMANCE_LATEST_FILE
    history_path = PERFORMANCE_HISTORY_FILE

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    result.history_path = str(history_path)

    result_payload = result.to_dict()

    history_payload = {
        "version": "V10.1",
        "updated_at": datetime.now().isoformat(),
        "portfolio_id": result.portfolio_id,
        "history_record_count": len(
            result.performance_history
        ),
        "performance_history": [
            snapshot.to_dict()
            for snapshot in result.performance_history
        ],
    }

    write_json_file(
        report_path,
        result_payload,
    )

    write_json_file(
        latest_path,
        result_payload,
    )

    write_json_file(
        history_path,
        history_payload,
    )

    return (
        report_path,
        latest_path,
        history_path,
    )


def load_latest_performance_result() -> dict[str, Any]:
    """
    저장된 최신 V10.1 성과 결과를 읽습니다.
    """

    payload = read_json_file(
        PERFORMANCE_LATEST_FILE
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            "최신 Performance JSON이 Dictionary가 아닙니다."
        )

    return payload


def print_paper_portfolio_performance(
    result: PaperPortfolioPerformanceResult,
) -> None:
    """
    V10.1 Portfolio Performance 결과를 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.1 PAPER PORTFOLIO PERFORMANCE TRACKER"
    )
    print("=" * line_length)

    print(
        f"Performance status             : "
        f"{result.performance_status}"
    )
    print(
        f"Performance status label       : "
        f"{result.performance_status_label}"
    )
    print(
        f"Performance ID                 : "
        f"{result.performance_id}"
    )
    print(
        f"Portfolio ID                   : "
        f"{result.portfolio_id}"
    )
    print(
        f"Source valuation ID            : "
        f"{result.source_valuation_id}"
    )

    print()
    print("EQUITY PERFORMANCE")
    print("-" * line_length)

    print(
        f"History records                : "
        f"{result.history_record_count}"
    )
    print(
        f"Performance periods            : "
        f"{result.performance_period_count}"
    )
    print(
        f"Initial equity                 : "
        f"${result.initial_equity:,.2f}"
    )
    print(
        f"Previous equity                : "
        f"${result.previous_equity:,.2f}"
    )
    print(
        f"Current equity                 : "
        f"${result.current_equity:,.2f}"
    )
    print(
        f"Period profit/loss             : "
        f"${result.period_profit_loss:,.2f}"
    )
    print(
        f"Period return                  : "
        f"{result.period_return_percent:.4f}%"
    )
    print(
        f"Cumulative profit/loss         : "
        f"${result.cumulative_profit_loss:,.2f}"
    )
    print(
        f"Cumulative return              : "
        f"{result.cumulative_return_percent:.4f}%"
    )

    print()
    print("RISK METRICS")
    print("-" * line_length)

    print(
        f"Equity high-water mark         : "
        f"${result.equity_high_water_mark:,.2f}"
    )
    print(
        f"Current drawdown               : "
        f"${result.current_drawdown_amount:,.2f}"
    )
    print(
        f"Current drawdown %             : "
        f"{result.current_drawdown_percent:.4f}%"
    )
    print(
        f"Maximum drawdown               : "
        f"${result.maximum_drawdown_amount:,.2f}"
    )
    print(
        f"Maximum drawdown %             : "
        f"{result.maximum_drawdown_percent:.4f}%"
    )
    print(
        f"Return volatility              : "
        f"{result.return_volatility_percent:.4f}%"
    )
    print(
        f"Annualized volatility          : "
        f"{result.annualized_volatility_percent:.4f}%"
    )
    print(
        f"Sharpe ratio                   : "
        f"{result.sharpe_ratio:.6f}"
    )

    print()
    print("RETURN STATISTICS")
    print("-" * line_length)

    print(
        f"Average period return          : "
        f"{result.average_period_return_percent:.4f}%"
    )
    print(
        f"Best period return             : "
        f"{result.best_period_return_percent:.4f}%"
    )
    print(
        f"Worst period return            : "
        f"{result.worst_period_return_percent:.4f}%"
    )
    print(
        f"Annualized return              : "
        f"{result.annualized_return_percent:.4f}%"
    )
    print(
        f"Profitable periods             : "
        f"{result.profitable_period_count}"
    )
    print(
        f"Loss periods                   : "
        f"{result.loss_period_count}"
    )
    print(
        f"Flat periods                   : "
        f"{result.flat_period_count}"
    )
    print(
        f"Win rate                       : "
        f"{result.win_rate_percent:.4f}%"
    )
    print(
        f"Gross profit                   : "
        f"${result.gross_profit:,.2f}"
    )
    print(
        f"Gross loss                     : "
        f"${result.gross_loss:,.2f}"
    )
    print(
        f"Profit factor                  : "
        f"{result.profit_factor:.6f}"
    )

    print()
    print("PROFIT AND LOSS")
    print("-" * line_length)

    print(
        f"Total unrealized PnL           : "
        f"${result.total_unrealized_pnl:,.2f}"
    )
    print(
        f"Total realized PnL             : "
        f"${result.total_realized_pnl:,.2f}"
    )
    print(
        f"Total commission               : "
        f"${result.total_commission:,.2f}"
    )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Source loaded                  : "
        f"{result.source_loaded}"
    )
    print(
        f"Source valid                   : "
        f"{result.source_valid}"
    )
    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"History checks passed          : "
        f"{result.history_checks_passed}"
    )
    print(
        f"Calculation checks passed      : "
        f"{result.calculation_checks_passed}"
    )
    print(
        f"Snapshot added                 : "
        f"{result.snapshot_added}"
    )
    print(
        f"Duplicate snapshot             : "
        f"{result.duplicate_snapshot}"
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
        f"Source valuation file          : "
        f"{result.source_valuation_file}"
    )
    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )
    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )
    print(
        f"History file                   : "
        f"{result.history_path or 'Not saved yet'}"
    )

    print("=" * line_length)
    print(
        "주의: 이 결과는 연구용 Paper Trading 성과이며 "
        "실제 Broker 계좌 조회나 증권 주문을 수행하지 않습니다."
    )


if __name__ == "__main__":
    performance_result = (
        run_paper_portfolio_performance_tracker()
    )

    save_paper_portfolio_performance(
        performance_result
    )
