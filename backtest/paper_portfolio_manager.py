import json
import math
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


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_PORTFOLIO_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_portfolio"
)


VALID_PORTFOLIO_STATUSES = {
    "UPDATED",
    "NO_CHANGE",
    "BLOCKED",
    "FAILED",
}


VALID_PORTFOLIO_ACTIONS = {
    "OPEN_LONG",
    "ADD_LONG",
    "REDUCE_LONG",
    "CLOSE_LONG",
    "NO_ACTION",
    "BLOCKED",
}


VALID_POSITION_STATES = {
    "FLAT",
    "LONG",
}


VALID_SIDES = {
    "BUY",
    "SELL",
}


@dataclass(frozen=True)
class PaperPortfolioPolicy:
    """
    V9.9 Paper Portfolio Manager 정책입니다.

    실제 계좌가 아니라 연구용 가상 포트폴리오만 관리합니다.
    """

    minimum_cash_balance: float = 0.0
    maximum_position_shares: int = 100_000
    maximum_position_value: float = 1_000_000.0

    allow_buy: bool = True
    allow_sell: bool = True

    allow_add_to_position: bool = True
    allow_partial_exit: bool = True

    allow_short_selling: bool = False
    prevent_negative_cash: bool = True
    prevent_negative_shares: bool = True

    reject_duplicate_fills: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperPosition:
    """
    한 종목의 가상 보유 포지션입니다.
    """

    symbol: str

    state: str = "FLAT"
    shares: int = 0

    average_price: float = 0.0
    cost_basis: float = 0.0

    latest_price: float = 0.0
    market_value: float = 0.0

    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0

    realized_pnl: float = 0.0

    opened_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperPortfolioState:
    """
    전체 가상 계좌 상태입니다.
    """

    portfolio_id: str
    created_at: str
    updated_at: str

    initial_cash: float
    cash_balance: float

    total_market_value: float
    total_equity: float

    total_unrealized_pnl: float
    total_realized_pnl: float

    total_commission: float

    processed_fill_ids: list[str] = field(
        default_factory=list
    )

    processed_idempotency_keys: list[str] = field(
        default_factory=list
    )

    positions: dict[str, PaperPosition] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["positions"] = {
            symbol: position.to_dict()
            for symbol, position in self.positions.items()
        }

        return payload


@dataclass
class PaperPortfolioResult:
    """
    V9.9 Paper Portfolio Manager 실행 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    update_id: str

    source_fill_id: str
    source_request_id: str
    source_idempotency_key: str
    source_fill_file: str | None

    portfolio_status: str
    portfolio_status_label: str

    portfolio_action: str
    portfolio_action_label: str

    fill_side: str
    fill_quantity: int
    fill_price: float
    fill_value: float
    commission: float
    cash_effect: float

    previous_cash_balance: float
    updated_cash_balance: float
    cash_change: float

    previous_position_state: str
    updated_position_state: str

    previous_shares: int
    updated_shares: int
    share_change: int

    previous_average_price: float
    updated_average_price: float

    previous_cost_basis: float
    updated_cost_basis: float

    latest_price: float
    position_market_value: float

    transaction_realized_pnl: float
    position_realized_pnl: float

    position_unrealized_pnl: float
    position_unrealized_pnl_percent: float

    total_market_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_equity: float

    source_loaded: bool
    source_valid: bool

    portfolio_loaded: bool
    portfolio_valid: bool

    policy_checks_passed: bool
    duplicate_checks_passed: bool
    cash_checks_passed: bool
    position_checks_passed: bool
    calculation_checks_passed: bool

    portfolio_updated: bool
    all_checks_passed: bool

    duplicate_fill: bool
    execution_blocked: bool

    broker_api_called: bool
    live_order_created: bool
    live_execution_authorized: bool

    portfolio_policy: PaperPortfolioPolicy
    portfolio_state: PaperPortfolioState

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None
    state_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["portfolio_policy"] = (
            self.portfolio_policy.to_dict()
        )

        payload["portfolio_state"] = (
            self.portfolio_state.to_dict()
        )

        return payload


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정규화합니다.
    """

    normalized = str(
        symbol
    ).strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def is_valid_number(
    value: Any,
) -> bool:
    """
    값이 유효하고 유한한 숫자인지 검사합니다.
    """

    if isinstance(
        value,
        bool,
    ):
        return False

    try:
        numeric_value = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return math.isfinite(
        numeric_value
    )


def round_money(
    value: float,
) -> float:
    """
    금액을 소수점 둘째 자리로 반올림합니다.
    """

    return round(
        float(value),
        2,
    )


def round_price(
    value: float,
) -> float:
    """
    가격을 소수점 넷째 자리로 반올림합니다.
    """

    return round(
        float(value),
        4,
    )


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일 방식으로 안전하게 저장합니다.
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


def read_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽어 Dictionary로 반환합니다.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(
            file
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def create_empty_portfolio(
    initial_cash: float = 10_000.0,
) -> PaperPortfolioState:
    """
    새로운 빈 Paper Portfolio를 생성합니다.
    """

    if not is_valid_number(
        initial_cash
    ):
        raise ValueError(
            "Initial Cash가 유효한 숫자가 아닙니다."
        )

    initial_cash = round_money(
        initial_cash
    )

    if initial_cash <= 0:
        raise ValueError(
            "Initial Cash는 0보다 커야 합니다."
        )

    now = datetime.now().isoformat()

    return PaperPortfolioState(
        portfolio_id=str(
            uuid.uuid4()
        ),
        created_at=now,
        updated_at=now,

        initial_cash=initial_cash,
        cash_balance=initial_cash,

        total_market_value=0.0,
        total_equity=initial_cash,

        total_unrealized_pnl=0.0,
        total_realized_pnl=0.0,

        total_commission=0.0,

        processed_fill_ids=[],
        processed_idempotency_keys=[],
        positions={},
    )


def copy_position(
    position: PaperPosition,
) -> PaperPosition:
    """
    Position 객체를 복사합니다.
    """

    return PaperPosition(
        symbol=position.symbol,
        state=position.state,
        shares=position.shares,
        average_price=position.average_price,
        cost_basis=position.cost_basis,
        latest_price=position.latest_price,
        market_value=position.market_value,
        unrealized_pnl=position.unrealized_pnl,
        unrealized_pnl_percent=(
            position.unrealized_pnl_percent
        ),
        realized_pnl=position.realized_pnl,
        opened_at=position.opened_at,
        updated_at=position.updated_at,
    )


def copy_portfolio_state(
    portfolio: PaperPortfolioState,
) -> PaperPortfolioState:
    """
    Portfolio 상태를 깊은 복사합니다.
    """

    return PaperPortfolioState(
        portfolio_id=portfolio.portfolio_id,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,

        initial_cash=portfolio.initial_cash,
        cash_balance=portfolio.cash_balance,

        total_market_value=(
            portfolio.total_market_value
        ),
        total_equity=portfolio.total_equity,

        total_unrealized_pnl=(
            portfolio.total_unrealized_pnl
        ),
        total_realized_pnl=(
            portfolio.total_realized_pnl
        ),

        total_commission=(
            portfolio.total_commission
        ),

        processed_fill_ids=list(
            portfolio.processed_fill_ids
        ),

        processed_idempotency_keys=list(
            portfolio.processed_idempotency_keys
        ),

        positions={
            symbol: copy_position(
                position
            )
            for symbol, position in portfolio.positions.items()
        },
    )


def position_from_dict(
    payload: dict[str, Any],
) -> PaperPosition:
    """
    Dictionary를 PaperPosition으로 변환합니다.
    """

    return PaperPosition(
        symbol=normalize_symbol(
            payload.get(
                "symbol",
                "",
            )
        ),
        state=str(
            payload.get(
                "state",
                "FLAT",
            )
        ),
        shares=int(
            payload.get(
                "shares",
                0,
            )
        ),
        average_price=float(
            payload.get(
                "average_price",
                0.0,
            )
        ),
        cost_basis=float(
            payload.get(
                "cost_basis",
                0.0,
            )
        ),
        latest_price=float(
            payload.get(
                "latest_price",
                0.0,
            )
        ),
        market_value=float(
            payload.get(
                "market_value",
                0.0,
            )
        ),
        unrealized_pnl=float(
            payload.get(
                "unrealized_pnl",
                0.0,
            )
        ),
        unrealized_pnl_percent=float(
            payload.get(
                "unrealized_pnl_percent",
                0.0,
            )
        ),
        realized_pnl=float(
            payload.get(
                "realized_pnl",
                0.0,
            )
        ),
        opened_at=payload.get(
            "opened_at"
        ),
        updated_at=payload.get(
            "updated_at"
        ),
    )


def portfolio_from_dict(
    payload: dict[str, Any],
) -> PaperPortfolioState:
    """
    Dictionary를 PaperPortfolioState로 변환합니다.
    """

    raw_positions = payload.get(
        "positions",
        {},
    )

    positions: dict[str, PaperPosition] = {}

    if isinstance(
        raw_positions,
        dict,
    ):
        for symbol, position_payload in raw_positions.items():
            if not isinstance(
                position_payload,
                dict,
            ):
                continue

            normalized_symbol = normalize_symbol(
                symbol
            )

            positions[normalized_symbol] = position_from_dict(
                position_payload
            )

    return PaperPortfolioState(
        portfolio_id=str(
            payload.get(
                "portfolio_id",
                uuid.uuid4(),
            )
        ),
        created_at=str(
            payload.get(
                "created_at",
                datetime.now().isoformat(),
            )
        ),
        updated_at=str(
            payload.get(
                "updated_at",
                datetime.now().isoformat(),
            )
        ),

        initial_cash=float(
            payload.get(
                "initial_cash",
                10_000.0,
            )
        ),
        cash_balance=float(
            payload.get(
                "cash_balance",
                10_000.0,
            )
        ),

        total_market_value=float(
            payload.get(
                "total_market_value",
                0.0,
            )
        ),
        total_equity=float(
            payload.get(
                "total_equity",
                10_000.0,
            )
        ),

        total_unrealized_pnl=float(
            payload.get(
                "total_unrealized_pnl",
                0.0,
            )
        ),
        total_realized_pnl=float(
            payload.get(
                "total_realized_pnl",
                0.0,
            )
        ),

        total_commission=float(
            payload.get(
                "total_commission",
                0.0,
            )
        ),

        processed_fill_ids=[
            str(value)
            for value in payload.get(
                "processed_fill_ids",
                [],
            )
        ],

        processed_idempotency_keys=[
            str(value)
            for value in payload.get(
                "processed_idempotency_keys",
                [],
            )
        ],

        positions=positions,
    )


def validate_portfolio_policy(
    policy: PaperPortfolioPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    Paper Portfolio 정책을 검사합니다.
    """

    errors: list[str] = []

    numeric_fields = {
        "minimum_cash_balance": (
            policy.minimum_cash_balance
        ),
        "maximum_position_value": (
            policy.maximum_position_value
        ),
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(
            value
        ):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if (
        is_valid_number(
            policy.minimum_cash_balance
        )
        and policy.minimum_cash_balance < 0
    ):
        errors.append(
            "Minimum Cash Balance가 음수입니다."
        )

    if (
        is_valid_number(
            policy.maximum_position_value
        )
        and policy.maximum_position_value <= 0
    ):
        errors.append(
            "Maximum Position Value가 0 이하입니다."
        )

    if not isinstance(
        policy.maximum_position_shares,
        int,
    ):
        errors.append(
            "Maximum Position Shares가 int 형식이 아닙니다."
        )

    elif policy.maximum_position_shares <= 0:
        errors.append(
            "Maximum Position Shares가 0 이하입니다."
        )

    boolean_fields = {
        "allow_buy": policy.allow_buy,
        "allow_sell": policy.allow_sell,
        "allow_add_to_position": (
            policy.allow_add_to_position
        ),
        "allow_partial_exit": (
            policy.allow_partial_exit
        ),
        "allow_short_selling": (
            policy.allow_short_selling
        ),
        "prevent_negative_cash": (
            policy.prevent_negative_cash
        ),
        "prevent_negative_shares": (
            policy.prevent_negative_shares
        ),
        "reject_duplicate_fills": (
            policy.reject_duplicate_fills
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if policy.allow_short_selling:
        errors.append(
            "V9.9에서는 Short Selling을 허용하지 않습니다."
        )

    if not policy.paper_only:
        errors.append(
            "V9.9에서는 Paper Only가 반드시 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V9.9에서는 Live Execution Disabled가 "
            "반드시 True여야 합니다."
        )

    return (
        not errors,
        errors,
    )


def validate_paper_fill(
    fill: PaperBrokerFillResult,
) -> tuple[
    bool,
    list[str],
]:
    """
    V9.8 Paper Broker Fill 결과를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        fill,
        PaperBrokerFillResult,
    ):
        errors.append(
            "Fill 결과가 PaperBrokerFillResult 형식이 아닙니다."
        )

        return (
            False,
            errors,
        )

    if fill.version != "V9.8":
        errors.append(
            "Fill 버전이 V9.8이 아닙니다."
        )

    if not fill.symbol:
        errors.append(
            "Fill Symbol이 비어 있습니다."
        )

    if fill.fill_status != "FILLED":
        errors.append(
            "Fill Status가 FILLED가 아닙니다."
        )

    if fill.fill_action not in {
        "PAPER_BUY_FILL",
        "PAPER_SELL_FILL",
    }:
        errors.append(
            "Fill Action이 유효하지 않습니다."
        )

    if fill.side not in VALID_SIDES:
        errors.append(
            "Fill Side가 BUY 또는 SELL이 아닙니다."
        )

    if not isinstance(
        fill.filled_quantity,
        int,
    ):
        errors.append(
            "Filled Quantity가 int 형식이 아닙니다."
        )

    elif fill.filled_quantity <= 0:
        errors.append(
            "Filled Quantity가 0 이하입니다."
        )

    if not is_valid_number(
        fill.fill_price
    ):
        errors.append(
            "Fill Price가 유효한 숫자가 아닙니다."
        )

    elif fill.fill_price <= 0:
        errors.append(
            "Fill Price가 0 이하입니다."
        )

    if not is_valid_number(
        fill.gross_fill_value
    ):
        errors.append(
            "Gross Fill Value가 유효한 숫자가 아닙니다."
        )

    elif fill.gross_fill_value <= 0:
        errors.append(
            "Gross Fill Value가 0 이하입니다."
        )

    expected_value = round_money(
        fill.filled_quantity
        * fill.fill_price
    )

    if abs(
        fill.gross_fill_value
        - expected_value
    ) > 0.01:
        errors.append(
            "Gross Fill Value 계산이 일치하지 않습니다."
        )

    if not is_valid_number(
        fill.commission
    ):
        errors.append(
            "Commission이 유효한 숫자가 아닙니다."
        )

    elif fill.commission < 0:
        errors.append(
            "Commission이 음수입니다."
        )

    if not is_valid_number(
        fill.total_cash_effect
    ):
        errors.append(
            "Total Cash Effect가 유효한 숫자가 아닙니다."
        )

    if fill.side == "BUY":
        expected_cash_effect = -round_money(
            fill.gross_fill_value
            + fill.commission
        )

        if fill.total_cash_effect >= 0:
            errors.append(
                "BUY Fill의 Cash Effect가 음수가 아닙니다."
            )

    else:
        expected_cash_effect = round_money(
            fill.gross_fill_value
            - fill.commission
        )

        if fill.total_cash_effect <= 0:
            errors.append(
                "SELL Fill의 Cash Effect가 양수가 아닙니다."
            )

    if abs(
        fill.total_cash_effect
        - expected_cash_effect
    ) > 0.01:
        errors.append(
            "Total Cash Effect 계산이 일치하지 않습니다."
        )

    if not fill.paper_fill_created:
        errors.append(
            "Paper Fill Created가 False입니다."
        )

    if not fill.execution_simulated:
        errors.append(
            "Execution Simulated가 False입니다."
        )

    if not fill.all_checks_passed:
        errors.append(
            "V9.8 검사가 모두 통과되지 않았습니다."
        )

    if fill.broker_api_called:
        errors.append(
            "실제 Broker API가 호출되었습니다."
        )

    if fill.broker_order_created:
        errors.append(
            "실제 Broker Order가 생성되었습니다."
        )

    if fill.live_order_created:
        errors.append(
            "Live Order가 생성되었습니다."
        )

    if fill.live_execution_authorized:
        errors.append(
            "Live Execution이 허용되었습니다."
        )

    if not fill.actual_execution_blocked:
        errors.append(
            "실제 Execution이 차단되지 않았습니다."
        )

    if not fill.fill_id:
        errors.append(
            "Fill ID가 비어 있습니다."
        )

    if not fill.idempotency_key:
        errors.append(
            "Idempotency Key가 비어 있습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_portfolio_state(
    portfolio: PaperPortfolioState,
) -> tuple[
    bool,
    list[str],
]:
    """
    Paper Portfolio 상태를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        portfolio,
        PaperPortfolioState,
    ):
        errors.append(
            "Portfolio가 PaperPortfolioState 형식이 아닙니다."
        )

        return (
            False,
            errors,
        )

    if not portfolio.portfolio_id:
        errors.append(
            "Portfolio ID가 비어 있습니다."
        )

    numeric_fields = {
        "initial_cash": portfolio.initial_cash,
        "cash_balance": portfolio.cash_balance,
        "total_market_value": (
            portfolio.total_market_value
        ),
        "total_equity": portfolio.total_equity,
        "total_unrealized_pnl": (
            portfolio.total_unrealized_pnl
        ),
        "total_realized_pnl": (
            portfolio.total_realized_pnl
        ),
        "total_commission": (
            portfolio.total_commission
        ),
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(
            value
        ):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if portfolio.initial_cash <= 0:
        errors.append(
            "Initial Cash가 0 이하입니다."
        )

    if not isinstance(
        portfolio.processed_fill_ids,
        list,
    ):
        errors.append(
            "Processed Fill IDs가 List 형식이 아닙니다."
        )

    if not isinstance(
        portfolio.processed_idempotency_keys,
        list,
    ):
        errors.append(
            "Processed Idempotency Keys가 List 형식이 아닙니다."
        )

    if not isinstance(
        portfolio.positions,
        dict,
    ):
        errors.append(
            "Positions가 Dictionary 형식이 아닙니다."
        )

        return (
            not errors,
            errors,
        )

    for symbol, position in portfolio.positions.items():
        if normalize_symbol(
            symbol
        ) != symbol:
            errors.append(
                f"Position Symbol이 정규화되지 않았습니다: {symbol}"
            )

        if position.state not in VALID_POSITION_STATES:
            errors.append(
                f"Position State가 올바르지 않습니다: "
                f"{position.state}"
            )

        if not isinstance(
            position.shares,
            int,
        ):
            errors.append(
                f"{symbol} Shares가 int 형식이 아닙니다."
            )

        elif position.shares < 0:
            errors.append(
                f"{symbol} Shares가 음수입니다."
            )

        if position.state == "FLAT":
            if position.shares != 0:
                errors.append(
                    f"{symbol} FLAT Position의 Shares가 "
                    "0이 아닙니다."
                )

        if position.state == "LONG":
            if position.shares <= 0:
                errors.append(
                    f"{symbol} LONG Position의 Shares가 "
                    "0 이하입니다."
                )

        if position.shares == 0:
            if abs(
                position.cost_basis
            ) > 0.01:
                errors.append(
                    f"{symbol} Shares가 0인데 Cost Basis가 "
                    "0이 아닙니다."
                )

    expected_equity = round_money(
        portfolio.cash_balance
        + portfolio.total_market_value
    )

    if abs(
        portfolio.total_equity
        - expected_equity
    ) > 0.01:
        errors.append(
            "Total Equity가 Cash + Market Value와 "
            "일치하지 않습니다."
        )

    return (
        not errors,
        errors,
    )


def get_or_create_position(
    portfolio: PaperPortfolioState,
    symbol: str,
) -> PaperPosition:
    """
    종목 Position을 조회하거나 새로 생성합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if normalized_symbol not in portfolio.positions:
        portfolio.positions[normalized_symbol] = PaperPosition(
            symbol=normalized_symbol
        )

    return portfolio.positions[
        normalized_symbol
    ]


def determine_portfolio_action(
    side: str,
    previous_shares: int,
    fill_quantity: int,
) -> tuple[
    str,
    str,
]:
    """
    Fill을 기준으로 Portfolio Action을 결정합니다.
    """

    if side == "BUY":
        if previous_shares == 0:
            return (
                "OPEN_LONG",
                "신규 Long 포지션 생성",
            )

        return (
            "ADD_LONG",
            "기존 Long 포지션 추가 매수",
        )

    if side == "SELL":
        if fill_quantity < previous_shares:
            return (
                "REDUCE_LONG",
                "기존 Long 포지션 일부 매도",
            )

        if fill_quantity == previous_shares:
            return (
                "CLOSE_LONG",
                "기존 Long 포지션 전체 종료",
            )

        return (
            "BLOCKED",
            "보유 수량 초과 매도 차단",
        )

    return (
        "NO_ACTION",
        "적용할 Portfolio Action 없음",
    )


def calculate_buy_update(
    position: PaperPosition,
    fill: PaperBrokerFillResult,
) -> tuple[
    int,
    float,
    float,
]:
    """
    BUY Fill 적용 후 수량, 평균가격, Cost Basis를 계산합니다.
    """

    previous_shares = position.shares
    previous_cost_basis = position.cost_basis

    added_cost = round_money(
        fill.gross_fill_value
        + fill.commission
    )

    updated_shares = (
        previous_shares
        + fill.filled_quantity
    )

    updated_cost_basis = round_money(
        previous_cost_basis
        + added_cost
    )

    if updated_shares <= 0:
        updated_average_price = 0.0

    else:
        updated_average_price = round_price(
            updated_cost_basis
            / updated_shares
        )

    return (
        updated_shares,
        updated_average_price,
        updated_cost_basis,
    )


def calculate_sell_update(
    position: PaperPosition,
    fill: PaperBrokerFillResult,
) -> tuple[
    int,
    float,
    float,
    float,
]:
    """
    SELL Fill 적용 후 수량, 평균가격, Cost Basis,
    Transaction Realized PnL을 계산합니다.
    """

    if fill.filled_quantity > position.shares:
        raise RuntimeError(
            "매도 수량이 현재 보유 수량보다 많습니다."
        )

    cost_removed = round_money(
        position.average_price
        * fill.filled_quantity
    )

    net_proceeds = round_money(
        fill.gross_fill_value
        - fill.commission
    )

    transaction_realized_pnl = round_money(
        net_proceeds
        - cost_removed
    )

    updated_shares = (
        position.shares
        - fill.filled_quantity
    )

    updated_cost_basis = round_money(
        position.cost_basis
        - cost_removed
    )

    if updated_shares == 0:
        updated_average_price = 0.0
        updated_cost_basis = 0.0

    else:
        updated_average_price = round_price(
            updated_cost_basis
            / updated_shares
        )

    return (
        updated_shares,
        updated_average_price,
        updated_cost_basis,
        transaction_realized_pnl,
    )


def update_position_metrics(
    position: PaperPosition,
    latest_price: float,
) -> None:
    """
    현재가격을 이용해 시장가치와 미실현 손익을 계산합니다.
    """

    position.latest_price = round_price(
        latest_price
    )

    if position.shares <= 0:
        position.state = "FLAT"
        position.shares = 0
        position.average_price = 0.0
        position.cost_basis = 0.0
        position.market_value = 0.0
        position.unrealized_pnl = 0.0
        position.unrealized_pnl_percent = 0.0

        return

    position.state = "LONG"

    position.market_value = round_money(
        position.shares
        * position.latest_price
    )

    position.unrealized_pnl = round_money(
        position.market_value
        - position.cost_basis
    )

    if position.cost_basis > 0:
        position.unrealized_pnl_percent = round(
            (
                position.unrealized_pnl
                / position.cost_basis
            )
            * 100.0,
            4,
        )

    else:
        position.unrealized_pnl_percent = 0.0


def recalculate_portfolio_totals(
    portfolio: PaperPortfolioState,
) -> None:
    """
    모든 Position을 이용해 Portfolio 합계를 다시 계산합니다.
    """

    portfolio.total_market_value = round_money(
        sum(
            position.market_value
            for position in portfolio.positions.values()
        )
    )

    portfolio.total_unrealized_pnl = round_money(
        sum(
            position.unrealized_pnl
            for position in portfolio.positions.values()
        )
    )

    portfolio.total_realized_pnl = round_money(
        sum(
            position.realized_pnl
            for position in portfolio.positions.values()
        )
    )

    portfolio.total_equity = round_money(
        portfolio.cash_balance
        + portfolio.total_market_value
    )

    portfolio.updated_at = datetime.now().isoformat()


def check_duplicate_fill(
    portfolio: PaperPortfolioState,
    fill: PaperBrokerFillResult,
) -> bool:
    """
    Fill ID 또는 Idempotency Key가 이미 처리되었는지 검사합니다.
    """

    return (
        fill.fill_id
        in portfolio.processed_fill_ids
        or fill.idempotency_key
        in portfolio.processed_idempotency_keys
    )


def validate_fill_against_policy(
    portfolio: PaperPortfolioState,
    position: PaperPosition,
    fill: PaperBrokerFillResult,
    policy: PaperPortfolioPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    Fill을 Portfolio에 적용할 수 있는지 정책을 검사합니다.
    """

    errors: list[str] = []

    if fill.side == "BUY":
        if not policy.allow_buy:
            errors.append(
                "Portfolio Policy에서 BUY가 허용되지 않습니다."
            )

        if (
            position.shares > 0
            and not policy.allow_add_to_position
        ):
            errors.append(
                "기존 Position 추가 매수가 허용되지 않습니다."
            )

        proposed_shares = (
            position.shares
            + fill.filled_quantity
        )

        proposed_value = round_money(
            proposed_shares
            * fill.fill_price
        )

        if (
            proposed_shares
            > policy.maximum_position_shares
        ):
            errors.append(
                "적용 후 Shares가 최대 허용 수량을 초과합니다."
            )

        if (
            proposed_value
            > policy.maximum_position_value
        ):
            errors.append(
                "적용 후 Position Value가 최대 허용 금액을 "
                "초과합니다."
            )

        proposed_cash = round_money(
            portfolio.cash_balance
            + fill.total_cash_effect
        )

        if (
            policy.prevent_negative_cash
            and proposed_cash
            < policy.minimum_cash_balance
        ):
            errors.append(
                "Fill 적용 후 Cash Balance가 최소 현금보다 "
                "낮아집니다."
            )

    elif fill.side == "SELL":
        if not policy.allow_sell:
            errors.append(
                "Portfolio Policy에서 SELL이 허용되지 않습니다."
            )

        if (
            policy.prevent_negative_shares
            and fill.filled_quantity
            > position.shares
        ):
            errors.append(
                "매도 수량이 보유 수량을 초과합니다."
            )

        if (
            fill.filled_quantity
            < position.shares
            and not policy.allow_partial_exit
        ):
            errors.append(
                "부분 매도가 허용되지 않습니다."
            )

        if (
            position.shares == 0
            and not policy.allow_short_selling
        ):
            errors.append(
                "보유 수량 없이 SELL할 수 없습니다."
            )

    return (
        not errors,
        errors,
    )


def build_portfolio_notes(
    status: str,
    action: str,
    fill_errors: list[str],
    portfolio_errors: list[str],
    policy_errors: list[str],
    duplicate_fill: bool,
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    Reasons, Warnings, Next Actions를 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if status == "UPDATED":
        reasons.append(
            "V9.8 Paper Fill을 가상 Portfolio에 반영했습니다."
        )

        reasons.append(
            f"Portfolio Action은 {action}입니다."
        )

    elif status == "NO_CHANGE":
        reasons.append(
            "Portfolio 상태를 변경하지 않았습니다."
        )

    else:
        reasons.append(
            "안전 검사 또는 정책 검사로 Portfolio 반영이 "
            "차단되었습니다."
        )

    if duplicate_fill:
        reasons.append(
            "동일한 Fill ID 또는 Idempotency Key가 "
            "이미 처리되었습니다."
        )

    warnings.extend(
        fill_errors
    )

    warnings.extend(
        portfolio_errors
    )

    warnings.extend(
        policy_errors
    )

    warnings.extend(
        [
            (
                "이 Portfolio는 연구용 Paper Trading "
                "가상 계좌입니다."
            ),
            (
                "실제 Broker 계좌의 현금이나 보유 수량을 "
                "조회하지 않습니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 Live Execution은 "
                "모두 차단됩니다."
            ),
            (
                "시장가격은 V9.8의 가상 Fill Price를 사용합니다."
            ),
        ]
    )

    if status == "UPDATED":
        next_actions = [
            (
                "다음 시장가격으로 Position Market Value를 "
                "재평가합니다."
            ),
            (
                "Daily PnL과 Portfolio Equity 기록을 "
                "생성합니다."
            ),
            (
                "처리된 Fill ID와 Idempotency Key를 "
                "중복 방지 목록에 유지합니다."
            ),
            (
                "V10.0 Paper Portfolio Valuation 단계로 "
                "전달합니다."
            ),
        ]

    elif duplicate_fill:
        next_actions = [
            (
                "기존 처리 결과를 확인합니다."
            ),
            (
                "동일 Fill을 다시 Portfolio에 반영하지 않습니다."
            ),
        ]

    else:
        next_actions = [
            (
                "Fill, Portfolio 및 Policy 오류를 확인합니다."
            ),
            (
                "문제를 수정한 후 새로운 Fill 결과로 "
                "다시 실행합니다."
            ),
        ]

    return (
        reasons,
        warnings,
        next_actions,
    )


def run_paper_portfolio_manager(
    symbol: str = "AAPL",
    fill_result: PaperBrokerFillResult | None = None,
    portfolio_state: PaperPortfolioState | None = None,
    portfolio_policy: PaperPortfolioPolicy | None = None,
    initial_cash: float = 10_000.0,
) -> PaperPortfolioResult:
    """
    V9.8 가상 Fill을 V9.9 가상 Portfolio에 반영합니다.

    실제 Broker 계좌나 실제 주문에는 연결하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    policy = (
        portfolio_policy
        if portfolio_policy is not None
        else PaperPortfolioPolicy()
    )

    (
        policy_valid,
        policy_errors,
    ) = validate_portfolio_policy(
        policy
    )

    if fill_result is None:
        fill_result = run_paper_broker_simulator(
            symbol=normalized_symbol,
            account_cash=initial_cash,
        )

        save_paper_broker_fill(
            fill_result
        )

    if fill_result.symbol != normalized_symbol:
        raise ValueError(
            "Fill Symbol과 요청 Symbol이 일치하지 않습니다."
        )

    (
        fill_valid,
        fill_errors,
    ) = validate_paper_fill(
        fill_result
    )

    if portfolio_state is None:
        working_portfolio = create_empty_portfolio(
            initial_cash=initial_cash
        )

        portfolio_loaded = True

    else:
        working_portfolio = copy_portfolio_state(
            portfolio_state
        )

        portfolio_loaded = True

    (
        portfolio_valid,
        portfolio_errors,
    ) = validate_portfolio_state(
        working_portfolio
    )

    position = get_or_create_position(
        portfolio=working_portfolio,
        symbol=normalized_symbol,
    )

    previous_cash_balance = round_money(
        working_portfolio.cash_balance
    )

    previous_position_state = position.state
    previous_shares = position.shares

    previous_average_price = round_price(
        position.average_price
    )

    previous_cost_basis = round_money(
        position.cost_basis
    )

    duplicate_fill = check_duplicate_fill(
        portfolio=working_portfolio,
        fill=fill_result,
    )

    duplicate_checks_passed = (
        not duplicate_fill
        or not policy.reject_duplicate_fills
    )

    (
        fill_policy_valid,
        fill_policy_errors,
    ) = validate_fill_against_policy(
        portfolio=working_portfolio,
        position=position,
        fill=fill_result,
        policy=policy,
    )

    policy_errors.extend(
        fill_policy_errors
    )

    policy_checks_passed = (
        policy_valid
        and fill_policy_valid
    )

    (
        portfolio_action,
        portfolio_action_label,
    ) = determine_portfolio_action(
        side=fill_result.side,
        previous_shares=previous_shares,
        fill_quantity=fill_result.filled_quantity,
    )

    cash_checks_passed = False
    position_checks_passed = False
    calculation_checks_passed = False

    portfolio_updated = False

    transaction_realized_pnl = 0.0

    if not fill_valid:
        portfolio_status = "FAILED"
        portfolio_status_label = (
            "Paper Fill 검사 실패"
        )

        portfolio_action = "BLOCKED"
        portfolio_action_label = (
            "유효하지 않은 Fill 차단"
        )

    elif not portfolio_valid:
        portfolio_status = "FAILED"
        portfolio_status_label = (
            "Portfolio 상태 검사 실패"
        )

        portfolio_action = "BLOCKED"
        portfolio_action_label = (
            "유효하지 않은 Portfolio 차단"
        )

    elif duplicate_fill and policy.reject_duplicate_fills:
        portfolio_status = "NO_CHANGE"
        portfolio_status_label = (
            "중복 Fill 감지"
        )

        portfolio_action = "NO_ACTION"
        portfolio_action_label = (
            "중복 Fill 반영 없음"
        )

    elif not policy_checks_passed:
        portfolio_status = "BLOCKED"
        portfolio_status_label = (
            "Portfolio Policy 검사 실패"
        )

        portfolio_action = "BLOCKED"
        portfolio_action_label = (
            "정책에 의해 Portfolio 반영 차단"
        )

    else:
        proposed_cash = round_money(
            working_portfolio.cash_balance
            + fill_result.total_cash_effect
        )

        cash_checks_passed = (
            not policy.prevent_negative_cash
            or proposed_cash
            >= policy.minimum_cash_balance
        )

        if not cash_checks_passed:
            portfolio_status = "BLOCKED"
            portfolio_status_label = (
                "현금 잔액 검사 실패"
            )

            portfolio_action = "BLOCKED"
            portfolio_action_label = (
                "현금 부족으로 Fill 반영 차단"
            )

        else:
            if fill_result.side == "BUY":
                (
                    updated_shares,
                    updated_average_price,
                    updated_cost_basis,
                ) = calculate_buy_update(
                    position=position,
                    fill=fill_result,
                )

                transaction_realized_pnl = 0.0

            else:
                (
                    updated_shares,
                    updated_average_price,
                    updated_cost_basis,
                    transaction_realized_pnl,
                ) = calculate_sell_update(
                    position=position,
                    fill=fill_result,
                )

            position_checks_passed = (
                updated_shares >= 0
                and updated_cost_basis >= 0
            )

            if not position_checks_passed:
                portfolio_status = "BLOCKED"
                portfolio_status_label = (
                    "Position 계산 검사 실패"
                )

                portfolio_action = "BLOCKED"
                portfolio_action_label = (
                    "잘못된 Position 결과 차단"
                )

            else:
                working_portfolio.cash_balance = (
                    proposed_cash
                )

                working_portfolio.total_commission = (
                    round_money(
                        working_portfolio.total_commission
                        + fill_result.commission
                    )
                )

                position.shares = updated_shares
                position.average_price = (
                    updated_average_price
                )
                position.cost_basis = (
                    updated_cost_basis
                )

                position.realized_pnl = round_money(
                    position.realized_pnl
                    + transaction_realized_pnl
                )

                now = datetime.now().isoformat()

                if (
                    previous_shares == 0
                    and updated_shares > 0
                ):
                    position.opened_at = (
                        fill_result.created_at
                    )

                if updated_shares == 0:
                    position.opened_at = None

                position.updated_at = now

                update_position_metrics(
                    position=position,
                    latest_price=fill_result.fill_price,
                )

                if (
                    fill_result.fill_id
                    not in working_portfolio.processed_fill_ids
                ):
                    working_portfolio.processed_fill_ids.append(
                        fill_result.fill_id
                    )

                if (
                    fill_result.idempotency_key
                    not in working_portfolio.processed_idempotency_keys
                ):
                    working_portfolio.processed_idempotency_keys.append(
                        fill_result.idempotency_key
                    )

                recalculate_portfolio_totals(
                    working_portfolio
                )

                calculation_checks_passed = (
                    abs(
                        working_portfolio.total_equity
                        - (
                            working_portfolio.cash_balance
                            + working_portfolio.total_market_value
                        )
                    )
                    <= 0.01
                )

                portfolio_updated = (
                    cash_checks_passed
                    and position_checks_passed
                    and calculation_checks_passed
                )

                if portfolio_updated:
                    portfolio_status = "UPDATED"
                    portfolio_status_label = (
                        "Paper Portfolio 업데이트 완료"
                    )

                else:
                    portfolio_status = "FAILED"
                    portfolio_status_label = (
                        "Portfolio 최종 계산 검사 실패"
                    )

    updated_position = get_or_create_position(
        portfolio=working_portfolio,
        symbol=normalized_symbol,
    )

    all_checks_passed = (
        fill_valid
        and portfolio_valid
        and policy_checks_passed
        and duplicate_checks_passed
        and cash_checks_passed
        and position_checks_passed
        and calculation_checks_passed
        and portfolio_updated
    )

    (
        reasons,
        warnings,
        next_actions,
    ) = build_portfolio_notes(
        status=portfolio_status,
        action=portfolio_action,
        fill_errors=fill_errors,
        portfolio_errors=portfolio_errors,
        policy_errors=policy_errors,
        duplicate_fill=duplicate_fill,
    )

    reasons.extend(
        [
            (
                f"Fill Side는 {fill_result.side}입니다."
            ),
            (
                f"Fill Quantity는 "
                f"{fill_result.filled_quantity}주입니다."
            ),
            (
                f"Fill Price는 "
                f"${fill_result.fill_price:,.4f}입니다."
            ),
            (
                f"Fill Cash Effect는 "
                f"${fill_result.total_cash_effect:,.2f}입니다."
            ),
        ]
    )

    if portfolio_updated:
        reasons.extend(
            [
                (
                    f"현금 잔액은 "
                    f"${previous_cash_balance:,.2f}에서 "
                    f"${working_portfolio.cash_balance:,.2f}로 "
                    "변경되었습니다."
                ),
                (
                    f"보유 수량은 {previous_shares}주에서 "
                    f"{updated_position.shares}주로 변경되었습니다."
                ),
                (
                    f"평균 매입가격은 "
                    f"${updated_position.average_price:,.4f}입니다."
                ),
                (
                    f"총 계좌가치는 "
                    f"${working_portfolio.total_equity:,.2f}입니다."
                ),
            ]
        )

    result = PaperPortfolioResult(
        version="V9.9",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        update_id=str(
            uuid.uuid4()
        ),

        source_fill_id=fill_result.fill_id,
        source_request_id=fill_result.request_id,
        source_idempotency_key=(
            fill_result.idempotency_key
        ),
        source_fill_file=(
            fill_result.latest_path
            or fill_result.report_path
            or fill_result.source_request_file
        ),

        portfolio_status=portfolio_status,
        portfolio_status_label=(
            portfolio_status_label
        ),

        portfolio_action=portfolio_action,
        portfolio_action_label=(
            portfolio_action_label
        ),

        fill_side=fill_result.side,
        fill_quantity=fill_result.filled_quantity,
        fill_price=round_price(
            fill_result.fill_price
        ),
        fill_value=round_money(
            fill_result.gross_fill_value
        ),
        commission=round_money(
            fill_result.commission
        ),
        cash_effect=round_money(
            fill_result.total_cash_effect
        ),

        previous_cash_balance=(
            previous_cash_balance
        ),
        updated_cash_balance=round_money(
            working_portfolio.cash_balance
        ),
        cash_change=round_money(
            working_portfolio.cash_balance
            - previous_cash_balance
        ),

        previous_position_state=(
            previous_position_state
        ),
        updated_position_state=(
            updated_position.state
        ),

        previous_shares=previous_shares,
        updated_shares=updated_position.shares,
        share_change=(
            updated_position.shares
            - previous_shares
        ),

        previous_average_price=(
            previous_average_price
        ),
        updated_average_price=round_price(
            updated_position.average_price
        ),

        previous_cost_basis=previous_cost_basis,
        updated_cost_basis=round_money(
            updated_position.cost_basis
        ),

        latest_price=round_price(
            updated_position.latest_price
        ),
        position_market_value=round_money(
            updated_position.market_value
        ),

        transaction_realized_pnl=round_money(
            transaction_realized_pnl
        ),
        position_realized_pnl=round_money(
            updated_position.realized_pnl
        ),

        position_unrealized_pnl=round_money(
            updated_position.unrealized_pnl
        ),
        position_unrealized_pnl_percent=round(
            updated_position.unrealized_pnl_percent,
            4,
        ),

        total_market_value=round_money(
            working_portfolio.total_market_value
        ),
        total_unrealized_pnl=round_money(
            working_portfolio.total_unrealized_pnl
        ),
        total_realized_pnl=round_money(
            working_portfolio.total_realized_pnl
        ),
        total_equity=round_money(
            working_portfolio.total_equity
        ),

        source_loaded=True,
        source_valid=fill_valid,

        portfolio_loaded=portfolio_loaded,
        portfolio_valid=portfolio_valid,

        policy_checks_passed=(
            policy_checks_passed
        ),
        duplicate_checks_passed=(
            duplicate_checks_passed
        ),
        cash_checks_passed=(
            cash_checks_passed
        ),
        position_checks_passed=(
            position_checks_passed
        ),
        calculation_checks_passed=(
            calculation_checks_passed
        ),

        portfolio_updated=(
            portfolio_updated
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        duplicate_fill=duplicate_fill,
        execution_blocked=True,

        broker_api_called=False,
        live_order_created=False,
        live_execution_authorized=False,

        portfolio_policy=policy,
        portfolio_state=working_portfolio,

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_portfolio_result(
        result
    )

    return result


def save_paper_portfolio_result(
    result: PaperPortfolioResult,
) -> tuple[
    Path,
    Path,
    Path,
]:
    """
    V9.9 결과와 최신 Portfolio 상태를 JSON으로 저장합니다.
    """

    PAPER_PORTFOLIO_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_PORTFOLIO_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_portfolio_update_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_PORTFOLIO_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_portfolio_update_latest.json"
        )
    )

    state_path = (
        PAPER_PORTFOLIO_OUTPUT_DIRECTORY
        / "paper_portfolio_state_latest.json"
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    result.state_path = str(
        state_path
    )

    result_payload = result.to_dict()
    state_payload = result.portfolio_state.to_dict()

    write_json_file(
        report_path,
        result_payload,
    )

    write_json_file(
        latest_path,
        result_payload,
    )

    write_json_file(
        state_path,
        state_payload,
    )

    return (
        report_path,
        latest_path,
        state_path,
    )


def load_latest_portfolio_state(
    initial_cash: float = 10_000.0,
) -> PaperPortfolioState:
    """
    저장된 최신 Portfolio 상태를 읽습니다.

    파일이 없으면 새로운 빈 Portfolio를 생성합니다.
    """

    state_path = (
        PAPER_PORTFOLIO_OUTPUT_DIRECTORY
        / "paper_portfolio_state_latest.json"
    )

    if not state_path.exists():
        return create_empty_portfolio(
            initial_cash=initial_cash
        )

    payload = read_json_file(
        state_path
    )

    portfolio = portfolio_from_dict(
        payload
    )

    (
        portfolio_valid,
        portfolio_errors,
    ) = validate_portfolio_state(
        portfolio
    )

    if not portfolio_valid:
        raise RuntimeError(
            "저장된 Portfolio 상태가 유효하지 않습니다: "
            f"{portfolio_errors}"
        )

    return portfolio


def print_paper_portfolio_result(
    result: PaperPortfolioResult,
) -> None:
    """
    V9.9 Paper Portfolio 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.9 "
        "PAPER PORTFOLIO MANAGER"
    )
    print("=" * 140)

    print(
        f"Portfolio status               : "
        f"{result.portfolio_status}"
    )

    print(
        f"Portfolio status label         : "
        f"{result.portfolio_status_label}"
    )

    print(
        f"Portfolio action               : "
        f"{result.portfolio_action}"
    )

    print(
        f"Portfolio action label         : "
        f"{result.portfolio_action_label}"
    )

    print(
        f"Update ID                      : "
        f"{result.update_id}"
    )

    print(
        f"Source Fill ID                 : "
        f"{result.source_fill_id}"
    )

    print()
    print("FILL")
    print("-" * 140)

    print(
        f"Side                           : "
        f"{result.fill_side}"
    )

    print(
        f"Quantity                       : "
        f"{result.fill_quantity}"
    )

    print(
        f"Fill price                     : "
        f"${result.fill_price:,.4f}"
    )

    print(
        f"Fill value                     : "
        f"${result.fill_value:,.2f}"
    )

    print(
        f"Commission                     : "
        f"${result.commission:,.2f}"
    )

    print(
        f"Cash effect                    : "
        f"${result.cash_effect:,.2f}"
    )

    print()
    print("CASH")
    print("-" * 140)

    print(
        f"Previous cash balance          : "
        f"${result.previous_cash_balance:,.2f}"
    )

    print(
        f"Updated cash balance           : "
        f"${result.updated_cash_balance:,.2f}"
    )

    print(
        f"Cash change                    : "
        f"${result.cash_change:,.2f}"
    )

    print()
    print("POSITION")
    print("-" * 140)

    print(
        f"Previous state                 : "
        f"{result.previous_position_state}"
    )

    print(
        f"Updated state                  : "
        f"{result.updated_position_state}"
    )

    print(
        f"Previous shares                : "
        f"{result.previous_shares}"
    )

    print(
        f"Updated shares                 : "
        f"{result.updated_shares}"
    )

    print(
        f"Share change                   : "
        f"{result.share_change:+d}"
    )

    print(
        f"Previous average price         : "
        f"${result.previous_average_price:,.4f}"
    )

    print(
        f"Updated average price          : "
        f"${result.updated_average_price:,.4f}"
    )

    print(
        f"Previous cost basis            : "
        f"${result.previous_cost_basis:,.2f}"
    )

    print(
        f"Updated cost basis             : "
        f"${result.updated_cost_basis:,.2f}"
    )

    print(
        f"Latest price                   : "
        f"${result.latest_price:,.4f}"
    )

    print(
        f"Position market value          : "
        f"${result.position_market_value:,.2f}"
    )

    print()
    print("PROFIT AND LOSS")
    print("-" * 140)

    print(
        f"Transaction realized PnL       : "
        f"${result.transaction_realized_pnl:,.2f}"
    )

    print(
        f"Position realized PnL          : "
        f"${result.position_realized_pnl:,.2f}"
    )

    print(
        f"Position unrealized PnL        : "
        f"${result.position_unrealized_pnl:,.2f}"
    )

    print(
        f"Position unrealized PnL %      : "
        f"{result.position_unrealized_pnl_percent:.4f}%"
    )

    print()
    print("PORTFOLIO TOTALS")
    print("-" * 140)

    print(
        f"Total market value             : "
        f"${result.total_market_value:,.2f}"
    )

    print(
        f"Total unrealized PnL           : "
        f"${result.total_unrealized_pnl:,.2f}"
    )

    print(
        f"Total realized PnL             : "
        f"${result.total_realized_pnl:,.2f}"
    )

    print(
        f"Total equity                   : "
        f"${result.total_equity:,.2f}"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Source loaded                  : "
        f"{result.source_loaded}"
    )

    print(
        f"Source valid                   : "
        f"{result.source_valid}"
    )

    print(
        f"Portfolio loaded               : "
        f"{result.portfolio_loaded}"
    )

    print(
        f"Portfolio valid                : "
        f"{result.portfolio_valid}"
    )

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )

    print(
        f"Duplicate checks passed        : "
        f"{result.duplicate_checks_passed}"
    )

    print(
        f"Cash checks passed             : "
        f"{result.cash_checks_passed}"
    )

    print(
        f"Position checks passed         : "
        f"{result.position_checks_passed}"
    )

    print(
        f"Calculation checks passed      : "
        f"{result.calculation_checks_passed}"
    )

    print(
        f"Portfolio updated              : "
        f"{result.portfolio_updated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Duplicate fill                 : "
        f"{result.duplicate_fill}"
    )

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )

    print(
        f"Broker API called              : "
        f"{result.broker_api_called}"
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
        f"Source Fill file               : "
        f"{result.source_fill_file}"
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
        f"Portfolio state file           : "
        f"{result.state_path or 'Not saved yet'}"
    )

    print("=" * 140)

    print(
        "주의: 이 Portfolio는 연구용 Paper Trading "
        "가상 계좌이며 실제 Broker 계좌나 실제 주문과 "
        "연결되지 않습니다."
    )