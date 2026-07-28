import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.sandbox_portfolio_settlement import (
    SandboxPortfolioSettlementLedger,
    SandboxPortfolioSettlementResult,
    verify_settlement_ledger,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "sandbox_portfolio_valuation_refresh"
)
REQUIRED_REFRESH_TEXT = "REFRESH IN MEMORY SANDBOX PORTFOLIO VALUATION"


@dataclass(frozen=True)
class SandboxPortfolioValuationPolicy:
    required_source_version: str = "V14.4"
    required_source_status: str = "SETTLED_IN_MEMORY"
    required_ledger_status: str = "SETTLED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_REFRESH_TEXT
    maximum_position_count: int = 100
    require_same_operator: bool = True
    require_exact_price_set: bool = True
    require_positive_prices: bool = True
    require_source_hash_validation: bool = True
    simulation_only: bool = True
    market_data_api_disabled: bool = True
    credentials_forbidden: bool = True
    account_access_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxPositionValuation:
    position_valuation_id: str
    valued_at: str
    instrument: str
    quantity: int
    average_cost: float
    cost_basis: float
    simulated_current_price: float
    market_value: float
    unrealized_profit_loss: float
    unrealized_return_percent: float
    price_source: str
    simulation_only: bool
    market_data_api_called: bool
    account_accessed: bool
    broker_api_called: bool
    live_execution_authorized: bool
    valuation_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("valuation_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxPortfolioValuationSnapshot:
    valuation_snapshot_id: str
    created_at: str
    valuation_status: str
    settlement_result_id: str
    settlement_ledger_id: str
    settlement_ledger_hash: str
    session_id: str
    operator: str
    initial_cash: float
    cash_balance: float
    position_count: int
    total_cost_basis: float
    total_market_value: float
    total_unrealized_profit_loss: float
    total_equity: float
    total_profit_loss: float
    total_return_percent: float
    valuations: tuple[SandboxPositionValuation, ...]
    credentials_used: bool
    market_data_api_called: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    account_updated: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    snapshot_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["valuations"] = [
            valuation.to_dict() for valuation in self.valuations
        ]
        payload.pop("snapshot_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["snapshot_hash"] = self.snapshot_hash
        return payload


@dataclass
class SandboxPortfolioValuationRefreshResult:
    version: str
    created_at: str
    valuation_result_id: str
    result_status: str
    result_status_label: str
    valuation_snapshot_id: str | None
    snapshot_hash: str | None
    position_count: int
    cash_balance: float
    total_cost_basis: float
    total_market_value: float
    total_unrealized_profit_loss: float
    total_equity: float
    total_profit_loss: float
    total_return_percent: float
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    settlement_checks_passed: bool
    price_checks_passed: bool
    calculation_checks_passed: bool
    valuation_hash_checks_passed: bool
    snapshot_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    valuation_refresh_completed: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    account_updated: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    valuation_policy: SandboxPortfolioValuationPolicy
    snapshot: SandboxPortfolioValuationSnapshot | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["valuation_policy"] = self.valuation_policy.to_dict()
        payload["snapshot"] = self.snapshot.to_dict() if self.snapshot else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: SandboxPortfolioValuationPolicy) -> list[str]:
    if not isinstance(policy, SandboxPortfolioValuationPolicy):
        return ["Valuation Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.4",
        "required_source_status": "SETTLED_IN_MEMORY",
        "required_ledger_status": "SETTLED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_REFRESH_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.5 기준과 다릅니다.")
    if policy.maximum_position_count <= 0:
        errors.append("Maximum Position Count가 올바르지 않습니다.")
    for name in (
        "require_same_operator", "require_exact_price_set",
        "require_positive_prices", "require_source_hash_validation",
        "simulation_only", "market_data_api_disabled",
        "credentials_forbidden", "account_access_disabled",
        "network_access_disabled", "broker_api_disabled",
        "order_submission_disabled", "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.5에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[SandboxPortfolioSettlementLedger | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, SandboxPortfolioSettlementResult):
        return None, ["Source는 V14.4 Settlement Result여야 합니다."]
    if not (
        source.version == "V14.4"
        and source.result_status == "SETTLED_IN_MEMORY"
        and source.all_checks_passed
        and source.settlement_completed
        and source.ledger is not None
    ):
        errors.append("정상 V14.4 Settlement Source가 아닙니다.")
    if any((
        source.paper_execution_authorized,
        source.automatic_execution_authorized,
        not source.execution_blocked,
        source.credentials_used,
        source.dns_lookup_performed,
        source.socket_created,
        source.http_request_sent,
        source.network_accessed,
        source.account_accessed,
        source.account_updated,
        source.broker_api_called,
        source.broker_order_created,
        source.order_submitted,
        source.live_order_created,
        source.live_execution_authorized,
    )):
        errors.append("V14.4 Source 실행 안전장치가 올바르지 않습니다.")
    ledger = source.ledger
    if ledger:
        valid, verify_errors = verify_settlement_ledger(ledger)
        if not valid:
            errors.extend(verify_errors)
        if source.settlement_ledger_id != ledger.settlement_ledger_id:
            errors.append("Settlement Ledger ID 연결이 다릅니다.")
        if source.ledger_hash != ledger.ledger_hash:
            errors.append("Settlement Ledger Hash 연결이 다릅니다.")
    return ledger, errors


def build_valuation(
    position: Any,
    price: float,
    valued_at: str,
) -> SandboxPositionValuation:
    market_value = round(position.quantity * price, 2)
    profit_loss = round(market_value - position.cost_basis, 2)
    return_percent = round(
        (profit_loss / position.cost_basis * 100)
        if position.cost_basis else 0.0,
        6,
    )
    draft = SandboxPositionValuation(
        position_valuation_id=str(uuid.uuid4()),
        valued_at=valued_at,
        instrument=position.instrument,
        quantity=position.quantity,
        average_cost=position.average_cost,
        cost_basis=position.cost_basis,
        simulated_current_price=price,
        market_value=market_value,
        unrealized_profit_loss=profit_loss,
        unrealized_return_percent=return_percent,
        price_source="MANUAL_SIMULATED_INPUT",
        simulation_only=True,
        market_data_api_called=False,
        account_accessed=False,
        broker_api_called=False,
        live_execution_authorized=False,
        valuation_hash="",
    )
    return SandboxPositionValuation(
        **{
            **asdict(draft),
            "valuation_hash": sha256_payload(draft.payload_without_hash()),
        }
    )


def verify_position_valuation(
    valuation: SandboxPositionValuation,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected_value = round(
        valuation.quantity * valuation.simulated_current_price, 2
    )
    expected_profit = round(expected_value - valuation.cost_basis, 2)
    expected_return = round(
        (expected_profit / valuation.cost_basis * 100)
        if valuation.cost_basis else 0.0,
        6,
    )
    if (
        valuation.quantity <= 0
        or valuation.average_cost < 0
        or valuation.simulated_current_price <= 0
    ):
        errors.append(f"{valuation.instrument}: Valuation 입력이 올바르지 않습니다.")
    if (
        valuation.market_value != expected_value
        or valuation.unrealized_profit_loss != expected_profit
        or valuation.unrealized_return_percent != expected_return
    ):
        errors.append(f"{valuation.instrument}: Valuation 계산이 다릅니다.")
    if valuation.price_source != "MANUAL_SIMULATED_INPUT":
        errors.append(f"{valuation.instrument}: Price Source가 올바르지 않습니다.")
    if any((
        not valuation.simulation_only,
        valuation.market_data_api_called,
        valuation.account_accessed,
        valuation.broker_api_called,
        valuation.live_execution_authorized,
    )):
        errors.append(f"{valuation.instrument}: 외부 실행 흔적이 있습니다.")
    if valuation.valuation_hash != sha256_payload(
        valuation.payload_without_hash()
    ):
        errors.append(f"{valuation.instrument}: Valuation Hash가 다릅니다.")
    return not errors, errors


def verify_valuation_snapshot(
    snapshot: SandboxPortfolioValuationSnapshot,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if snapshot.valuation_status != "VALUED_IN_MEMORY":
        errors.append("Valuation Snapshot 상태가 올바르지 않습니다.")
    if snapshot.position_count != len(snapshot.valuations):
        errors.append("Position Count가 일치하지 않습니다.")
    symbols: set[str] = set()
    for valuation in snapshot.valuations:
        if valuation.instrument in symbols:
            errors.append("중복 Position Valuation이 있습니다.")
        symbols.add(valuation.instrument)
        valid, valuation_errors = verify_position_valuation(valuation)
        if not valid:
            errors.extend(valuation_errors)
    cost = round(sum(x.cost_basis for x in snapshot.valuations), 2)
    market = round(sum(x.market_value for x in snapshot.valuations), 2)
    unrealized = round(sum(
        x.unrealized_profit_loss for x in snapshot.valuations
    ), 2)
    equity = round(snapshot.cash_balance + market, 2)
    total_profit = round(equity - snapshot.initial_cash, 2)
    total_return = round(
        (total_profit / snapshot.initial_cash * 100)
        if snapshot.initial_cash else 0.0,
        6,
    )
    if (
        snapshot.total_cost_basis != cost
        or snapshot.total_market_value != market
        or snapshot.total_unrealized_profit_loss != unrealized
        or snapshot.total_equity != equity
        or snapshot.total_profit_loss != total_profit
        or snapshot.total_return_percent != total_return
    ):
        errors.append("Portfolio Valuation 합계가 일치하지 않습니다.")
    if any((
        snapshot.credentials_used, snapshot.market_data_api_called,
        snapshot.dns_lookup_performed, snapshot.socket_created,
        snapshot.http_request_sent, snapshot.network_accessed,
        snapshot.account_accessed, snapshot.account_updated,
        snapshot.broker_api_called, snapshot.order_submitted,
        snapshot.live_execution_authorized,
    )):
        errors.append("Valuation Snapshot에 외부 실행 흔적이 있습니다.")
    if snapshot.snapshot_hash != sha256_payload(snapshot.payload_without_hash()):
        errors.append("Valuation Snapshot Hash가 일치하지 않습니다.")
    return not errors, errors


def refresh_sandbox_portfolio_valuation(
    source: SandboxPortfolioSettlementResult,
    operator: str,
    confirmation_text: str,
    simulated_prices: dict[str, float],
    policy: SandboxPortfolioValuationPolicy | None = None,
    now: datetime | None = None,
) -> SandboxPortfolioValuationRefreshResult:
    policy = policy or SandboxPortfolioValuationPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Valuation 확인 문구가 일치하지 않습니다.")
    if not isinstance(simulated_prices, dict):
        simulated_prices = {}
        input_errors.append("Simulated Prices는 dict여야 합니다.")
    ledger, source_errors = validate_source(source)
    clean_prices: dict[str, float] = {}
    if ledger:
        if ledger.operator != clean_operator:
            input_errors.append("Settlement Operator와 Valuation Operator가 다릅니다.")
        symbols = {p.instrument for p in ledger.final_positions}
        if set(simulated_prices) != symbols:
            input_errors.append("Price 대상 종목이 Final Position과 다릅니다.")
        for symbol, price in simulated_prices.items():
            if (
                not isinstance(price, (int, float))
                or isinstance(price, bool) or price <= 0
            ):
                input_errors.append(f"{symbol}: Simulated Price가 올바르지 않습니다.")
            else:
                clean_prices[symbol] = round(float(price), 6)
        if len(ledger.final_positions) > policy.maximum_position_count:
            input_errors.append("허용된 최대 Position 수를 초과했습니다.")

    valuations: tuple[SandboxPositionValuation, ...] = ()
    snapshot: SandboxPortfolioValuationSnapshot | None = None
    snapshot_errors: list[str] = []
    preliminary_errors = policy_errors + input_errors + source_errors
    if not preliminary_errors and ledger:
        valuations = tuple(
            build_valuation(
                position, clean_prices[position.instrument], created_at
            )
            for position in ledger.final_positions
        )
        cost = round(sum(x.cost_basis for x in valuations), 2)
        market = round(sum(x.market_value for x in valuations), 2)
        unrealized = round(sum(x.unrealized_profit_loss for x in valuations), 2)
        equity = round(ledger.final_cash + market, 2)
        profit = round(equity - ledger.initial_cash, 2)
        return_percent = round(
            (profit / ledger.initial_cash * 100)
            if ledger.initial_cash else 0.0,
            6,
        )
        draft = SandboxPortfolioValuationSnapshot(
            valuation_snapshot_id=str(uuid.uuid4()),
            created_at=created_at,
            valuation_status="VALUED_IN_MEMORY",
            settlement_result_id=source.settlement_result_id,
            settlement_ledger_id=ledger.settlement_ledger_id,
            settlement_ledger_hash=ledger.ledger_hash,
            session_id=ledger.session_id,
            operator=clean_operator,
            initial_cash=ledger.initial_cash,
            cash_balance=ledger.final_cash,
            position_count=len(valuations),
            total_cost_basis=cost,
            total_market_value=market,
            total_unrealized_profit_loss=unrealized,
            total_equity=equity,
            total_profit_loss=profit,
            total_return_percent=return_percent,
            valuations=valuations,
            credentials_used=False, market_data_api_called=False,
            dns_lookup_performed=False, socket_created=False,
            http_request_sent=False, network_accessed=False,
            account_accessed=False, account_updated=False,
            broker_api_called=False, order_submitted=False,
            live_execution_authorized=False, snapshot_hash="",
        )
        snapshot = SandboxPortfolioValuationSnapshot(
            **{
                **asdict(draft),
                "valuations": draft.valuations,
                "snapshot_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        valid, snapshot_errors = verify_valuation_snapshot(snapshot)
        if not valid:
            snapshot_errors = list(snapshot_errors)
    all_errors = preliminary_errors + snapshot_errors
    passed = bool(snapshot) and not all_errors
    status = "VALUED_IN_MEMORY" if passed else (
        "BLOCKED" if not source_errors else "FAILED"
    )
    hash_ok = bool(snapshot) and not snapshot_errors
    return SandboxPortfolioValuationRefreshResult(
        version="V14.5", created_at=created_at,
        valuation_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "VALUED_IN_MEMORY": "Sandbox Portfolio 가상 평가 완료",
            "BLOCKED": "Valuation 입력 또는 가격 차단",
            "FAILED": "V14.4 Source 검증 실패",
        }[status],
        valuation_snapshot_id=snapshot.valuation_snapshot_id if snapshot else None,
        snapshot_hash=snapshot.snapshot_hash if snapshot else None,
        position_count=len(valuations),
        cash_balance=snapshot.cash_balance if snapshot else 0.0,
        total_cost_basis=snapshot.total_cost_basis if snapshot else 0.0,
        total_market_value=snapshot.total_market_value if snapshot else 0.0,
        total_unrealized_profit_loss=(
            snapshot.total_unrealized_profit_loss if snapshot else 0.0
        ),
        total_equity=snapshot.total_equity if snapshot else 0.0,
        total_profit_loss=snapshot.total_profit_loss if snapshot else 0.0,
        total_return_percent=snapshot.total_return_percent if snapshot else 0.0,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        settlement_checks_passed=bool(ledger) and not source_errors,
        price_checks_passed=bool(clean_prices) and not input_errors,
        calculation_checks_passed=passed,
        valuation_hash_checks_passed=hash_ok,
        snapshot_hash_checks_passed=hash_ok,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        valuation_refresh_completed=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        credentials_used=False, market_data_api_called=False,
        dns_lookup_performed=False, socket_created=False,
        http_request_sent=False, network_accessed=False,
        account_accessed=False, account_updated=False,
        broker_api_called=False, broker_order_created=False,
        order_submitted=False, live_order_created=False,
        live_execution_authorized=False,
        valuation_policy=policy, snapshot=snapshot,
        reasons=[
            "수동 모의 가격으로 가상 Portfolio Valuation을 갱신했습니다."
            if passed else "Sandbox Portfolio Valuation Refresh가 차단되었습니다."
        ],
        warnings=all_errors + [
            "입력 가격은 Simulation이며 실제 시장 시세가 아닙니다."
        ],
        next_actions=[
            "Market Value, Unrealized P/L, Total Equity 및 Hash를 확인합니다.",
            "실제 투자 성과나 세금 자료로 사용하지 않습니다.",
        ],
    )


def save_valuation_result(
    result: SandboxPortfolioValuationRefreshResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"sandbox_portfolio_valuation_{stamp}.json"
    latest = directory / "latest_sandbox_portfolio_valuation.json"
    payload = result.to_dict()
    for path in (report, latest):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_valuation_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V14.5":
        raise ValueError("V14.5 결과 파일이 아닙니다.")
    raw = payload.get("snapshot")
    if raw:
        snapshot = SandboxPortfolioValuationSnapshot(
            **{
                **raw,
                "valuations": tuple(
                    SandboxPositionValuation(**item)
                    for item in raw.get("valuations", [])
                ),
            }
        )
        valid, errors = verify_valuation_snapshot(snapshot)
        if not valid:
            raise ValueError(
                "저장된 Valuation Snapshot이 올바르지 않습니다: "
                + "; ".join(errors)
            )
    return payload
