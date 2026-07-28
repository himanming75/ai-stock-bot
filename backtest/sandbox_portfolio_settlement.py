import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.sandbox_fill_reconciliation import (
    SandboxFillReconciliationItem,
    SandboxFillReconciliationReport,
    SandboxFillReconciliationResult,
    verify_reconciliation_report,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "sandbox_portfolio_settlement"
)
REQUIRED_SETTLE_TEXT = "SETTLE IN MEMORY SANDBOX PORTFOLIO"


@dataclass(frozen=True)
class SandboxPortfolioSettlementPolicy:
    required_source_version: str = "V14.3"
    required_source_status: str = "RECONCILED_IN_MEMORY"
    required_report_status: str = "RECONCILED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_SETTLE_TEXT
    maximum_order_count: int = 20
    minimum_cash_balance: float = 0.0
    require_same_operator: bool = True
    require_exact_order_set: bool = True
    require_source_hash_validation: bool = True
    require_sufficient_cash: bool = True
    require_sufficient_position_for_sell: bool = True
    allow_short_positions: bool = False
    allow_margin: bool = False
    simulation_only: bool = True
    credentials_forbidden: bool = True
    account_access_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxPortfolioPosition:
    instrument: str
    quantity: int
    average_cost: float
    cost_basis: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxSettlementEntry:
    settlement_entry_id: str
    settled_at: str
    sequence: int
    client_order_id: str
    reconciliation_item_id: str
    reconciliation_item_hash: str
    instrument: str
    side: str
    terminal_state: str
    quantity: int
    settlement_price: float | None
    gross_amount: float
    cash_before: float
    cash_after: float
    position_before: int
    position_after: int
    average_cost_before: float
    average_cost_after: float
    settlement_status: str
    simulation_only: bool
    account_read_performed: bool
    account_write_performed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    previous_entry_hash: str
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxPortfolioSettlementLedger:
    settlement_ledger_id: str
    created_at: str
    settlement_status: str
    reconciliation_result_id: str
    reconciliation_report_id: str
    reconciliation_report_hash: str
    session_id: str
    operator: str
    initial_cash: float
    final_cash: float
    initial_positions: tuple[SandboxPortfolioPosition, ...]
    final_positions: tuple[SandboxPortfolioPosition, ...]
    order_count: int
    settled_count: int
    no_change_count: int
    buy_count: int
    sell_count: int
    entries: tuple[SandboxSettlementEntry, ...]
    credentials_used: bool
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
    ledger_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["initial_positions"] = [
            position.to_dict() for position in self.initial_positions
        ]
        payload["final_positions"] = [
            position.to_dict() for position in self.final_positions
        ]
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        payload.pop("ledger_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["ledger_hash"] = self.ledger_hash
        return payload


@dataclass
class SandboxPortfolioSettlementResult:
    version: str
    created_at: str
    settlement_result_id: str
    result_status: str
    result_status_label: str
    settlement_ledger_id: str | None
    ledger_hash: str | None
    order_count: int
    settled_count: int
    no_change_count: int
    initial_cash: float
    final_cash: float
    final_position_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    reconciliation_checks_passed: bool
    cash_checks_passed: bool
    position_checks_passed: bool
    entry_hash_checks_passed: bool
    ledger_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    settlement_completed: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
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
    settlement_policy: SandboxPortfolioSettlementPolicy
    ledger: SandboxPortfolioSettlementLedger | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["settlement_policy"] = self.settlement_policy.to_dict()
        payload["ledger"] = self.ledger.to_dict() if self.ledger else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: SandboxPortfolioSettlementPolicy) -> list[str]:
    if not isinstance(policy, SandboxPortfolioSettlementPolicy):
        return ["Settlement Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.3",
        "required_source_status": "RECONCILED_IN_MEMORY",
        "required_report_status": "RECONCILED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_SETTLE_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.4 기준과 다릅니다.")
    if policy.maximum_order_count <= 0 or policy.minimum_cash_balance < 0:
        errors.append("Settlement 수량 또는 Cash 기준이 올바르지 않습니다.")
    if policy.allow_short_positions or policy.allow_margin:
        errors.append("V14.4에서는 Short 또는 Margin을 허용하지 않습니다.")
    for name in (
        "require_same_operator", "require_exact_order_set",
        "require_source_hash_validation", "require_sufficient_cash",
        "require_sufficient_position_for_sell", "simulation_only",
        "credentials_forbidden", "account_access_disabled",
        "network_access_disabled", "broker_api_disabled",
        "order_submission_disabled", "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.4에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[SandboxFillReconciliationReport | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, SandboxFillReconciliationResult):
        return None, ["Source는 V14.3 Reconciliation Result여야 합니다."]
    if not (
        source.version == "V14.3"
        and source.result_status == "RECONCILED_IN_MEMORY"
        and source.all_checks_passed
        and source.reconciliation_completed
        and source.report is not None
    ):
        errors.append("정상 V14.3 Reconciliation Source가 아닙니다.")
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
        source.broker_api_called,
        source.broker_order_created,
        source.order_submitted,
        source.live_order_created,
        source.live_execution_authorized,
    )):
        errors.append("V14.3 Source 실행 안전장치가 올바르지 않습니다.")
    report = source.report
    if report:
        valid, verify_errors = verify_reconciliation_report(report)
        if not valid:
            errors.extend(verify_errors)
        if source.reconciliation_report_id != report.reconciliation_report_id:
            errors.append("Reconciliation Report ID 연결이 다릅니다.")
        if source.report_hash != report.report_hash:
            errors.append("Reconciliation Report Hash 연결이 다릅니다.")
    return report, errors


def normalize_positions(
    raw: dict[str, dict[str, Any]] | None,
) -> tuple[dict[str, dict[str, float | int]], list[str]]:
    errors: list[str] = []
    values: dict[str, dict[str, float | int]] = {}
    if raw is None:
        return values, errors
    if not isinstance(raw, dict):
        return values, ["Initial Positions는 dict여야 합니다."]
    for symbol, data in raw.items():
        if not isinstance(symbol, str) or not symbol.strip() or not isinstance(data, dict):
            errors.append("Position 형식이 올바르지 않습니다.")
            continue
        quantity = data.get("quantity")
        average_cost = data.get("average_cost")
        if (
            not isinstance(quantity, int) or isinstance(quantity, bool)
            or quantity < 0
            or not isinstance(average_cost, (int, float))
            or isinstance(average_cost, bool) or average_cost < 0
        ):
            errors.append(f"{symbol}: Position 값이 올바르지 않습니다.")
            continue
        values[symbol.strip().upper()] = {
            "quantity": quantity,
            "average_cost": round(float(average_cost), 6),
        }
    return values, errors


def positions_tuple(
    positions: dict[str, dict[str, float | int]],
) -> tuple[SandboxPortfolioPosition, ...]:
    return tuple(
        SandboxPortfolioPosition(
            instrument=symbol,
            quantity=int(data["quantity"]),
            average_cost=round(float(data["average_cost"]), 6),
            cost_basis=round(
                int(data["quantity"]) * float(data["average_cost"]), 2
            ),
        )
        for symbol, data in sorted(positions.items())
        if int(data["quantity"]) > 0
    )


def make_entry(
    item: SandboxFillReconciliationItem,
    sequence: int,
    settled_at: str,
    cash: float,
    positions: dict[str, dict[str, float | int]],
    previous_hash: str,
) -> tuple[SandboxSettlementEntry, float, list[str]]:
    errors: list[str] = []
    symbol = item.instrument
    current = positions.setdefault(symbol, {"quantity": 0, "average_cost": 0.0})
    before_quantity = int(current["quantity"])
    before_average = float(current["average_cost"])
    after_quantity = before_quantity
    after_average = before_average
    after_cash = cash
    price = item.observed_fill_price
    gross = 0.0
    status = "NO_CHANGE_CANCELLED"
    if item.expected_terminal_state == "FILLED_SIMULATED":
        if price is None or price <= 0:
            errors.append(f"{item.client_order_id}: Settlement Price가 없습니다.")
        else:
            gross = round(item.lifecycle_filled_quantity * price, 2)
            if item.side == "BUY":
                if cash < gross:
                    errors.append(f"{item.client_order_id}: 가상 Cash가 부족합니다.")
                else:
                    after_cash = round(cash - gross, 2)
                    after_quantity = before_quantity + item.lifecycle_filled_quantity
                    total_cost = before_quantity * before_average + gross
                    after_average = round(total_cost / after_quantity, 6)
                    status = "SETTLED_IN_MEMORY"
            elif item.side == "SELL":
                if before_quantity < item.lifecycle_filled_quantity:
                    errors.append(f"{item.client_order_id}: 가상 Position이 부족합니다.")
                else:
                    after_quantity = before_quantity - item.lifecycle_filled_quantity
                    after_cash = round(cash + gross, 2)
                    after_average = before_average if after_quantity else 0.0
                    status = "SETTLED_IN_MEMORY"
            else:
                errors.append(f"{item.client_order_id}: Side가 올바르지 않습니다.")
    elif item.expected_terminal_state != "CANCELLED_SIMULATED":
        errors.append(f"{item.client_order_id}: Terminal State가 올바르지 않습니다.")
    if not errors:
        current["quantity"] = after_quantity
        current["average_cost"] = after_average
    draft = SandboxSettlementEntry(
        settlement_entry_id=str(uuid.uuid4()),
        settled_at=settled_at,
        sequence=sequence,
        client_order_id=item.client_order_id,
        reconciliation_item_id=item.reconciliation_item_id,
        reconciliation_item_hash=item.item_hash,
        instrument=symbol,
        side=item.side,
        terminal_state=item.expected_terminal_state,
        quantity=item.lifecycle_filled_quantity,
        settlement_price=price,
        gross_amount=gross,
        cash_before=cash,
        cash_after=after_cash if not errors else cash,
        position_before=before_quantity,
        position_after=after_quantity if not errors else before_quantity,
        average_cost_before=before_average,
        average_cost_after=after_average if not errors else before_average,
        settlement_status=status if not errors else "BLOCKED",
        simulation_only=True,
        account_read_performed=False,
        account_write_performed=False,
        broker_api_called=False,
        order_submitted=False,
        live_execution_authorized=False,
        previous_entry_hash=previous_hash,
        entry_hash="",
    )
    entry = SandboxSettlementEntry(
        **{
            **asdict(draft),
            "entry_hash": sha256_payload(draft.payload_without_hash()),
        }
    )
    return entry, entry.cash_after, errors


def verify_settlement_entry(
    entry: SandboxSettlementEntry,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if entry.settlement_status not in {
        "SETTLED_IN_MEMORY", "NO_CHANGE_CANCELLED"
    }:
        errors.append(f"{entry.client_order_id}: Settlement Status가 다릅니다.")
    if entry.terminal_state == "FILLED_SIMULATED":
        if not (
            entry.quantity > 0 and entry.settlement_price is not None
            and entry.settlement_price > 0
            and entry.gross_amount
            == round(entry.quantity * entry.settlement_price, 2)
        ):
            errors.append(f"{entry.client_order_id}: 체결 금액이 다릅니다.")
    if entry.terminal_state == "CANCELLED_SIMULATED":
        if not (
            entry.quantity == 0 and entry.settlement_price is None
            and entry.gross_amount == 0
            and entry.cash_before == entry.cash_after
            and entry.position_before == entry.position_after
        ):
            errors.append(f"{entry.client_order_id}: 취소 주문이 Portfolio를 변경했습니다.")
    if any((
        not entry.simulation_only, entry.account_read_performed,
        entry.account_write_performed, entry.broker_api_called,
        entry.order_submitted, entry.live_execution_authorized,
    )):
        errors.append(f"{entry.client_order_id}: 실제 실행 흔적이 있습니다.")
    if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
        errors.append(f"{entry.client_order_id}: Entry Hash가 다릅니다.")
    return not errors, errors


def verify_settlement_ledger(
    ledger: SandboxPortfolioSettlementLedger,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if ledger.settlement_status != "SETTLED_IN_MEMORY":
        errors.append("Settlement Ledger 상태가 올바르지 않습니다.")
    if ledger.order_count != len(ledger.entries) or not ledger.entries:
        errors.append("Settlement Entry Count가 일치하지 않습니다.")
    if ledger.settled_count + ledger.no_change_count != ledger.order_count:
        errors.append("Settlement 집계가 일치하지 않습니다.")
    previous_hash = "0" * 64
    seen: set[str] = set()
    for sequence, entry in enumerate(ledger.entries, start=1):
        if entry.client_order_id in seen:
            errors.append("중복 Settlement Order ID가 있습니다.")
        seen.add(entry.client_order_id)
        if entry.sequence != sequence or entry.previous_entry_hash != previous_hash:
            errors.append(f"{entry.client_order_id}: Entry Hash Chain이 끊겼습니다.")
        valid, entry_errors = verify_settlement_entry(entry)
        if not valid:
            errors.extend(entry_errors)
        previous_hash = entry.entry_hash
    if ledger.entries:
        if ledger.entries[0].cash_before != ledger.initial_cash:
            errors.append("Initial Cash 연결이 다릅니다.")
        if ledger.entries[-1].cash_after != ledger.final_cash:
            errors.append("Final Cash 연결이 다릅니다.")
    if ledger.final_cash < 0 or any(p.quantity <= 0 for p in ledger.final_positions):
        errors.append("가상 Portfolio 잔액이 올바르지 않습니다.")
    if any((
        ledger.credentials_used, ledger.dns_lookup_performed,
        ledger.socket_created, ledger.http_request_sent,
        ledger.network_accessed, ledger.account_accessed,
        ledger.account_updated, ledger.broker_api_called,
        ledger.broker_order_created, ledger.order_submitted,
        ledger.live_order_created, ledger.live_execution_authorized,
    )):
        errors.append("Settlement Ledger에 외부 실행 흔적이 있습니다.")
    if ledger.ledger_hash != sha256_payload(ledger.payload_without_hash()):
        errors.append("Settlement Ledger Hash가 일치하지 않습니다.")
    return not errors, errors


def settle_sandbox_portfolio(
    source: SandboxFillReconciliationResult,
    operator: str,
    confirmation_text: str,
    initial_cash: float,
    initial_positions: dict[str, dict[str, Any]] | None = None,
    policy: SandboxPortfolioSettlementPolicy | None = None,
    now: datetime | None = None,
) -> SandboxPortfolioSettlementResult:
    policy = policy or SandboxPortfolioSettlementPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Settlement 확인 문구가 일치하지 않습니다.")
    if (
        not isinstance(initial_cash, (int, float))
        or isinstance(initial_cash, bool) or initial_cash < 0
    ):
        input_errors.append("Initial Cash가 올바르지 않습니다.")
        clean_cash = 0.0
    else:
        clean_cash = round(float(initial_cash), 2)
    positions, position_input_errors = normalize_positions(initial_positions)
    input_errors.extend(position_input_errors)
    initial_position_values = positions_tuple(positions)
    report, source_errors = validate_source(source)
    if report:
        if report.operator != clean_operator:
            input_errors.append("Reconciliation Operator와 Settlement Operator가 다릅니다.")
        if report.order_count > policy.maximum_order_count:
            input_errors.append("허용된 최대 주문 수를 초과했습니다.")

    entries: tuple[SandboxSettlementEntry, ...] = ()
    ledger: SandboxPortfolioSettlementLedger | None = None
    settlement_errors: list[str] = []
    preliminary_errors = policy_errors + input_errors + source_errors
    if not preliminary_errors and report:
        values: list[SandboxSettlementEntry] = []
        cash = clean_cash
        previous_hash = "0" * 64
        for sequence, item in enumerate(report.items, start=1):
            entry, cash, errors = make_entry(
                item, sequence, created_at, cash, positions, previous_hash
            )
            values.append(entry)
            settlement_errors.extend(errors)
            previous_hash = entry.entry_hash
        entries = tuple(values)
        if cash < policy.minimum_cash_balance:
            settlement_errors.append("Final Cash가 Policy 최저 기준 미만입니다.")
    if not preliminary_errors and not settlement_errors and report:
        final_position_values = positions_tuple(positions)
        draft = SandboxPortfolioSettlementLedger(
            settlement_ledger_id=str(uuid.uuid4()),
            created_at=created_at,
            settlement_status="SETTLED_IN_MEMORY",
            reconciliation_result_id=source.reconciliation_result_id,
            reconciliation_report_id=report.reconciliation_report_id,
            reconciliation_report_hash=report.report_hash,
            session_id=report.session_id,
            operator=clean_operator,
            initial_cash=clean_cash,
            final_cash=entries[-1].cash_after,
            initial_positions=initial_position_values,
            final_positions=final_position_values,
            order_count=len(entries),
            settled_count=sum(e.settlement_status == "SETTLED_IN_MEMORY" for e in entries),
            no_change_count=sum(e.settlement_status == "NO_CHANGE_CANCELLED" for e in entries),
            buy_count=sum(e.side == "BUY" and e.settlement_status == "SETTLED_IN_MEMORY" for e in entries),
            sell_count=sum(e.side == "SELL" and e.settlement_status == "SETTLED_IN_MEMORY" for e in entries),
            entries=entries,
            credentials_used=False, dns_lookup_performed=False,
            socket_created=False, http_request_sent=False,
            network_accessed=False, account_accessed=False,
            account_updated=False, broker_api_called=False,
            broker_order_created=False, order_submitted=False,
            live_order_created=False, live_execution_authorized=False,
            ledger_hash="",
        )
        ledger = SandboxPortfolioSettlementLedger(
            **{
                **asdict(draft),
                "initial_positions": draft.initial_positions,
                "final_positions": draft.final_positions,
                "entries": draft.entries,
                "ledger_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        valid, ledger_errors = verify_settlement_ledger(ledger)
        if not valid:
            settlement_errors.extend(ledger_errors)
    all_errors = preliminary_errors + settlement_errors
    passed = bool(ledger) and not all_errors
    status = "SETTLED_IN_MEMORY" if passed else (
        "BLOCKED" if not source_errors else "FAILED"
    )
    hash_ok = bool(ledger) and not settlement_errors
    return SandboxPortfolioSettlementResult(
        version="V14.4", created_at=created_at,
        settlement_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "SETTLED_IN_MEMORY": "Sandbox Portfolio 가상 정산 완료",
            "BLOCKED": "Settlement 입력 또는 잔액 기준 차단",
            "FAILED": "V14.3 Source 검증 실패",
        }[status],
        settlement_ledger_id=ledger.settlement_ledger_id if ledger else None,
        ledger_hash=ledger.ledger_hash if ledger else None,
        order_count=len(entries),
        settled_count=ledger.settled_count if ledger else 0,
        no_change_count=ledger.no_change_count if ledger else 0,
        initial_cash=clean_cash,
        final_cash=ledger.final_cash if ledger else clean_cash,
        final_position_count=len(ledger.final_positions) if ledger else 0,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        reconciliation_checks_passed=bool(report) and not source_errors,
        cash_checks_passed=passed,
        position_checks_passed=passed,
        entry_hash_checks_passed=hash_ok,
        ledger_hash_checks_passed=hash_ok,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        settlement_completed=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        credentials_used=False, dns_lookup_performed=False,
        socket_created=False, http_request_sent=False,
        network_accessed=False, account_accessed=False,
        account_updated=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_order_created=False, live_execution_authorized=False,
        settlement_policy=policy, ledger=ledger,
        reasons=[
            "모의 Fill을 In-Memory Cash와 Position에 반영했습니다."
            if passed else "Sandbox Portfolio Settlement가 차단되었습니다."
        ],
        warnings=all_errors + [
            "이 Portfolio는 Simulation이며 실제 Broker 계좌가 아닙니다."
        ],
        next_actions=[
            "Final Cash, Position, Average Cost와 Hash Chain을 확인합니다.",
            "실제 계좌 잔고 또는 세금 기록으로 사용하지 않습니다.",
        ],
    )


def save_settlement_result(
    result: SandboxPortfolioSettlementResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"sandbox_portfolio_settlement_{stamp}.json"
    latest = directory / "latest_sandbox_portfolio_settlement.json"
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


def load_settlement_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V14.4":
        raise ValueError("V14.4 결과 파일이 아닙니다.")
    raw = payload.get("ledger")
    if raw:
        ledger = SandboxPortfolioSettlementLedger(
            **{
                **raw,
                "initial_positions": tuple(
                    SandboxPortfolioPosition(**item)
                    for item in raw.get("initial_positions", [])
                ),
                "final_positions": tuple(
                    SandboxPortfolioPosition(**item)
                    for item in raw.get("final_positions", [])
                ),
                "entries": tuple(
                    SandboxSettlementEntry(**item)
                    for item in raw.get("entries", [])
                ),
            }
        )
        valid, errors = verify_settlement_ledger(ledger)
        if not valid:
            raise ValueError(
                "저장된 Settlement Ledger가 올바르지 않습니다: "
                + "; ".join(errors)
            )
    return payload
