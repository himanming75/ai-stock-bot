"""V23.2 Offline Paper Portfolio Update.

Creates a new in-memory paper-account snapshot from a verified V23.1 fill.
The source account and fill are never modified. No network, broker, account
API, credential, or live-order capability exists in this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid


VERSION = "V23.2"
CONFIRMATION_TEXT = "APPLY OFFLINE PAPER PORTFOLIO UPDATE V23.2"
OUTPUT_DIRECTORY = Path("backtest_outputs")
MONEY_QUANTUM = Decimal("0.01")
PRICE_QUANTUM = Decimal("0.0001")
QUANTITY_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class OfflinePaperPortfolioUpdateV232Policy:
    required_account_version: str = "V21.0"
    required_account_status: str = "CREATED_IN_MEMORY"
    required_account_mode: str = "OFFLINE_PAPER"
    required_fill_version: str = "V23.1"
    required_fill_status: str = "SIMULATED_IN_MEMORY"
    required_fill_mode: str = "OFFLINE_PAPER_SIMULATION"
    required_confirmation_text: str = CONFIRMATION_TEXT
    allowed_sides: tuple[str, ...] = ("BUY", "SELL")
    allow_fractional_quantity: bool = True
    short_selling_disabled: bool = True
    negative_cash_disabled: bool = True
    source_mutation_disabled: bool = True
    credentials_forbidden: bool = True
    market_data_api_disabled: bool = True
    account_api_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    broker_order_creation_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePaperPositionV232:
    symbol: str
    quantity: float
    average_cost: float
    last_fill_price: float
    cost_basis: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePaperPortfolioSnapshotV232:
    portfolio_snapshot_id: str
    created_at: str
    account_mode: str
    update_status: str
    source_account_result_id: str
    source_account_hash: str
    source_fill_result_id: str
    source_paper_fill_id: str
    source_fill_hash: str
    operator: str
    currency: str
    cash_balance: float
    positions_market_value: float
    total_equity: float
    positions: tuple[OfflinePaperPositionV232, ...]
    account_mutated: bool
    funds_reserved: bool
    holdings_reserved: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    portfolio_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("portfolio_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["positions"] = [position.to_dict() for position in self.positions]
        return payload


@dataclass
class OfflinePaperPortfolioUpdateV232Result:
    version: str
    created_at: str
    update_result_id: str
    result_status: str
    source_account_result_id: str | None
    source_account_hash: str | None
    source_fill_result_id: str | None
    source_fill_hash: str | None
    portfolio_snapshot_id: str | None
    portfolio_hash: str | None
    update_applied: bool
    policy_checks_passed: bool
    input_checks_passed: bool
    account_source_checks_passed: bool
    fill_source_checks_passed: bool
    source_linkage_checks_passed: bool
    source_unchanged_checks_passed: bool
    portfolio_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    account_mutated: bool
    funds_reserved: bool
    holdings_reserved: bool
    execution_blocked: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    update_policy: OfflinePaperPortfolioUpdateV232Policy
    portfolio: OfflinePaperPortfolioSnapshotV232 | None
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["update_policy"] = self.update_policy.to_dict()
        payload["portfolio"] = self.portfolio.to_dict() if self.portfolio else None
        return payload


def canonical_json(value: Any) -> str:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _decimal(value: Any, name: str, *, allow_zero: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} 형식 오류입니다.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} 형식 오류입니다.") from None
    if not result.is_finite() or result < 0 or (not allow_zero and result == 0):
        raise ValueError(f"{name} 값 오류입니다.")
    return result


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("시간 형식 오류입니다.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("시간대가 필요합니다.")
    return parsed.astimezone(timezone.utc)


def _safe_source(source: Any) -> bool:
    fields = (
        "funds_reserved",
        "holdings_reserved",
        "transmit",
        "credentials_used",
        "market_data_api_called",
        "account_api_called",
        "network_accessed",
        "broker_api_called",
        "broker_order_created",
        "order_submitted",
        "live_execution_authorized",
    )
    return all(getattr(source, name, False) is False for name in fields)


def validate_policy(policy: OfflinePaperPortfolioUpdateV232Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperPortfolioUpdateV232Policy):
        return ["V23.2 Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_account_version": "V21.0",
        "required_account_status": "CREATED_IN_MEMORY",
        "required_account_mode": "OFFLINE_PAPER",
        "required_fill_version": "V23.1",
        "required_fill_status": "SIMULATED_IN_MEMORY",
        "required_fill_mode": "OFFLINE_PAPER_SIMULATION",
        "required_confirmation_text": CONFIRMATION_TEXT,
        "allowed_sides": ("BUY", "SELL"),
    }
    for name, expected_value in expected.items():
        if getattr(policy, name) != expected_value:
            errors.append(f"{name} 정책 오류입니다.")
    for name, value in policy.to_dict().items():
        if name.endswith(("_disabled", "_forbidden")) and value is not True:
            errors.append(f"{name}는 True여야 합니다.")
    return errors


def _account_errors(
    source: Any, policy: OfflinePaperPortfolioUpdateV232Policy
) -> list[str]:
    errors: list[str] = []
    if getattr(source, "version", None) != policy.required_account_version:
        errors.append("V21.0 계좌 Source Version 오류입니다.")
    if getattr(source, "result_status", None) != policy.required_account_status:
        errors.append("V21.0 계좌 상태 오류입니다.")
    if getattr(source, "all_checks_passed", None) is not True:
        errors.append("V21.0 계좌 검증이 완료되지 않았습니다.")
    account = getattr(source, "account", None)
    if account is None:
        errors.append("V21.0 계좌가 없습니다.")
        return errors
    if getattr(account, "account_mode", None) != policy.required_account_mode:
        errors.append("V21.0 계좌 모드 오류입니다.")
    payload = (
        account.payload_without_hash()
        if hasattr(account, "payload_without_hash")
        else {}
    )
    if not payload or sha256_payload(payload) != getattr(account, "account_hash", None):
        errors.append("V21.0 계좌 Hash 검증에 실패했습니다.")
    if getattr(source, "account_hash", None) != getattr(account, "account_hash", None):
        errors.append("V21.0 계좌 Result 연결 Hash 오류입니다.")
    if not _safe_source(source):
        errors.append("V21.0 계좌 Source 안전 플래그 오류입니다.")
    return errors


def _fill_errors(
    source: Any, policy: OfflinePaperPortfolioUpdateV232Policy
) -> list[str]:
    errors: list[str] = []
    if getattr(source, "version", None) != policy.required_fill_version:
        errors.append("V23.1 Fill Source Version 오류입니다.")
    if getattr(source, "result_status", None) != policy.required_fill_status:
        errors.append("V23.1 Fill Result 상태 오류입니다.")
    if getattr(source, "all_checks_passed", None) is not True:
        errors.append("V23.1 Fill 검증이 완료되지 않았습니다.")
    fill = getattr(source, "fill", None)
    if fill is None:
        errors.append("V23.1 Fill이 없습니다.")
        return errors
    if getattr(fill, "fill_mode", None) != policy.required_fill_mode:
        errors.append("V23.1 Fill 모드 오류입니다.")
    if getattr(fill, "fill_status", None) not in {"FILLED", "NOT_FILLED"}:
        errors.append("V23.1 Fill 상태 오류입니다.")
    if getattr(fill, "side", None) not in policy.allowed_sides:
        errors.append("V23.1 Fill 방향 오류입니다.")
    payload = fill.payload_without_hash() if hasattr(fill, "payload_without_hash") else {}
    if not payload or sha256_payload(payload) != getattr(fill, "fill_hash", None):
        errors.append("V23.1 Fill Hash 검증에 실패했습니다.")
    if getattr(source, "fill_hash", None) != getattr(fill, "fill_hash", None):
        errors.append("V23.1 Fill Result 연결 Hash 오류입니다.")
    if getattr(source, "account_mutated", None) is not False or not _safe_source(source):
        errors.append("V23.1 Fill Source 안전 플래그 오류입니다.")
    return errors


def _blocked_result(
    policy: OfflinePaperPortfolioUpdateV232Policy,
    now: datetime,
    reasons: list[str],
    account_source: Any = None,
    fill_source: Any = None,
    *,
    policy_ok: bool = False,
    input_ok: bool = False,
    account_ok: bool = False,
    fill_ok: bool = False,
) -> OfflinePaperPortfolioUpdateV232Result:
    return _result(
        policy,
        now,
        "BLOCKED",
        reasons,
        account_source,
        fill_source,
        None,
        policy_ok=policy_ok,
        input_ok=input_ok,
        account_ok=account_ok,
        fill_ok=fill_ok,
    )


def _result(
    policy: OfflinePaperPortfolioUpdateV232Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    account_source: Any,
    fill_source: Any,
    portfolio: OfflinePaperPortfolioSnapshotV232 | None,
    *,
    policy_ok: bool = False,
    input_ok: bool = False,
    account_ok: bool = False,
    fill_ok: bool = False,
    linkage_ok: bool = False,
    unchanged_ok: bool = False,
    hash_ok: bool = False,
) -> OfflinePaperPortfolioUpdateV232Result:
    all_ok = all(
        (policy_ok, input_ok, account_ok, fill_ok, linkage_ok, unchanged_ok, hash_ok)
    )
    account = getattr(account_source, "account", None)
    fill = getattr(fill_source, "fill", None)
    return OfflinePaperPortfolioUpdateV232Result(
        version=VERSION,
        created_at=now.isoformat(),
        update_result_id=str(uuid.uuid4()),
        result_status=status,
        source_account_result_id=getattr(account_source, "account_result_id", None),
        source_account_hash=getattr(account, "account_hash", None),
        source_fill_result_id=getattr(fill_source, "fill_result_id", None),
        source_fill_hash=getattr(fill, "fill_hash", None),
        portfolio_snapshot_id=portfolio.portfolio_snapshot_id if portfolio else None,
        portfolio_hash=portfolio.portfolio_hash if portfolio else None,
        update_applied=bool(portfolio and portfolio.update_status == "APPLIED"),
        policy_checks_passed=policy_ok,
        input_checks_passed=input_ok,
        account_source_checks_passed=account_ok,
        fill_source_checks_passed=fill_ok,
        source_linkage_checks_passed=linkage_ok,
        source_unchanged_checks_passed=unchanged_ok,
        portfolio_hash_checks_passed=hash_ok,
        safety_checks_passed=all_ok,
        all_checks_passed=all_ok,
        account_mutated=False,
        funds_reserved=False,
        holdings_reserved=False,
        execution_blocked=True,
        transmit=False,
        credentials_used=False,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_execution_authorized=False,
        update_policy=policy,
        portfolio=portfolio,
        reasons=reasons,
    )


def _read_positions(account: Any) -> dict[str, dict[str, Decimal]]:
    positions: dict[str, dict[str, Decimal]] = {}
    for item in getattr(account, "positions", ()):
        symbol = getattr(item, "symbol", None)
        if not isinstance(symbol, str) or not symbol.strip() or symbol in positions:
            raise ValueError("V21.0 보유종목 형식 오류입니다.")
        quantity = _decimal(getattr(item, "quantity", None), "position quantity")
        average = _decimal(getattr(item, "average_cost", None), "average cost")
        positions[symbol] = {"quantity": quantity, "average_cost": average}
    return positions


def apply_offline_paper_portfolio_update_v23_2(
    account_source: Any,
    fill_source: Any,
    operator: Any,
    confirmation_text: Any,
    policy: OfflinePaperPortfolioUpdateV232Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperPortfolioUpdateV232Result:
    policy = policy or OfflinePaperPortfolioUpdateV232Policy()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    policy_errors = validate_policy(policy)
    if policy_errors:
        return _blocked_result(policy, now, policy_errors)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("V23.2 확인 문구가 일치하지 않습니다.")
    if input_errors:
        return _blocked_result(policy, now, input_errors, policy_ok=True)

    account_errors = _account_errors(account_source, policy)
    if account_errors:
        return _blocked_result(
            policy,
            now,
            account_errors,
            account_source,
            fill_source,
            policy_ok=True,
            input_ok=True,
        )
    fill_errors = _fill_errors(fill_source, policy)
    if fill_errors:
        return _blocked_result(
            policy,
            now,
            fill_errors,
            account_source,
            fill_source,
            policy_ok=True,
            input_ok=True,
            account_ok=True,
        )

    account_before = canonical_json(account_source)
    fill_before = canonical_json(fill_source)
    account = account_source.account
    fill = fill_source.fill
    if getattr(account, "operator", None) != operator.strip() or fill.operator != operator.strip():
        return _blocked_result(
            policy,
            now,
            ["Operator가 Source와 일치하지 않습니다."],
            account_source,
            fill_source,
            policy_ok=True,
            input_ok=True,
            account_ok=True,
            fill_ok=True,
        )
    try:
        if now < _parse_utc(account.created_at) or now < _parse_utc(fill.created_at):
            raise ValueError("V23.2 시간이 Source 시간보다 이전입니다.")
        cash = _decimal(account.cash_balance, "cash balance", allow_zero=True)
        positions = _read_positions(account)
    except ValueError as exc:
        return _blocked_result(
            policy,
            now,
            [str(exc)],
            account_source,
            fill_source,
            policy_ok=True,
            input_ok=True,
            account_ok=True,
            fill_ok=True,
        )

    update_status = "NO_CHANGE"
    if fill.fill_status == "FILLED":
        quantity = _decimal(fill.filled_quantity, "filled quantity")
        price = _decimal(fill.simulated_fill_price, "fill price")
        cash_effect = Decimal(str(fill.net_cash_effect))
        if not cash_effect.is_finite():
            return _blocked_result(
                policy,
                now,
                ["V23.1 현금 효과 값 오류입니다."],
                account_source,
                fill_source,
                policy_ok=True,
                input_ok=True,
                account_ok=True,
                fill_ok=True,
            )
        if fill.side == "BUY":
            new_cash = cash + cash_effect
            if new_cash < 0:
                return _blocked_result(
                    policy,
                    now,
                    ["가상계좌 현금이 부족합니다."],
                    account_source,
                    fill_source,
                    policy_ok=True,
                    input_ok=True,
                    account_ok=True,
                    fill_ok=True,
                )
            current = positions.get(
                fill.symbol,
                {"quantity": Decimal("0"), "average_cost": Decimal("0")},
            )
            new_quantity = current["quantity"] + quantity
            new_average = (
                current["quantity"] * current["average_cost"] + quantity * price
            ) / new_quantity
            positions[fill.symbol] = {
                "quantity": new_quantity,
                "average_cost": new_average,
            }
            cash = new_cash
        else:
            current = positions.get(fill.symbol)
            if current is None or current["quantity"] < quantity:
                return _blocked_result(
                    policy,
                    now,
                    ["공매도 또는 보유수량 초과 매도가 차단되었습니다."],
                    account_source,
                    fill_source,
                    policy_ok=True,
                    input_ok=True,
                    account_ok=True,
                    fill_ok=True,
                )
            remaining = current["quantity"] - quantity
            cash += cash_effect
            if remaining == 0:
                del positions[fill.symbol]
            else:
                positions[fill.symbol] = {
                    "quantity": remaining,
                    "average_cost": current["average_cost"],
                }
        update_status = "APPLIED"

    output_positions: list[OfflinePaperPositionV232] = []
    market_value = Decimal("0")
    for symbol in sorted(positions):
        item = positions[symbol]
        last_price = (
            Decimal(str(fill.simulated_fill_price))
            if fill.fill_status == "FILLED" and symbol == fill.symbol
            else item["average_cost"]
        )
        value = item["quantity"] * last_price
        market_value += value
        output_positions.append(
            OfflinePaperPositionV232(
                symbol=symbol,
                quantity=float(item["quantity"].quantize(QUANTITY_QUANTUM)),
                average_cost=float(
                    item["average_cost"].quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)
                ),
                last_fill_price=float(
                    last_price.quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)
                ),
                cost_basis=float(
                    (item["quantity"] * item["average_cost"]).quantize(
                        MONEY_QUANTUM, rounding=ROUND_HALF_UP
                    )
                ),
            )
        )
    cash = cash.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    market_value = market_value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    payload = {
        "portfolio_snapshot_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "account_mode": "OFFLINE_PAPER_PORTFOLIO",
        "update_status": update_status,
        "source_account_result_id": account_source.account_result_id,
        "source_account_hash": account.account_hash,
        "source_fill_result_id": fill_source.fill_result_id,
        "source_paper_fill_id": fill.paper_fill_id,
        "source_fill_hash": fill.fill_hash,
        "operator": operator.strip(),
        "currency": account.currency,
        "cash_balance": float(cash),
        "positions_market_value": float(market_value),
        "total_equity": float(cash + market_value),
        "positions": tuple(output_positions),
        "account_mutated": False,
        "funds_reserved": False,
        "holdings_reserved": False,
        "transmit": False,
        "credentials_used": False,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "broker_order_created": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    portfolio = OfflinePaperPortfolioSnapshotV232(
        **payload, portfolio_hash=sha256_payload(
            {
                **payload,
                "positions": [position.to_dict() for position in output_positions],
            }
        )
    )
    unchanged = (
        account_before == canonical_json(account_source)
        and fill_before == canonical_json(fill_source)
    )
    hash_ok = sha256_payload(portfolio.payload_without_hash()) == portfolio.portfolio_hash
    if not unchanged or not hash_ok:
        return _result(
            policy,
            now,
            "FAILED",
            ["V23.2 생성 무결성 검사에 실패했습니다."],
            account_source,
            fill_source,
            portfolio,
            policy_ok=True,
            input_ok=True,
            account_ok=True,
            fill_ok=True,
            linkage_ok=True,
            unchanged_ok=unchanged,
            hash_ok=hash_ok,
        )
    return _result(
        policy,
        now,
        "UPDATED_IN_MEMORY" if update_status == "APPLIED" else "NO_CHANGE_IN_MEMORY",
        [],
        account_source,
        fill_source,
        portfolio,
        policy_ok=True,
        input_ok=True,
        account_ok=True,
        fill_ok=True,
        linkage_ok=True,
        unchanged_ok=True,
        hash_ok=True,
    )


def verify_offline_paper_portfolio(
    portfolio: OfflinePaperPortfolioSnapshotV232,
) -> tuple[bool, list[str]]:
    if not isinstance(portfolio, OfflinePaperPortfolioSnapshotV232):
        return False, ["V23.2 Portfolio 형식 오류입니다."]
    errors: list[str] = []
    if sha256_payload(portfolio.payload_without_hash()) != portfolio.portfolio_hash:
        errors.append("V23.2 Portfolio Hash가 일치하지 않습니다.")
    if portfolio.account_mode != "OFFLINE_PAPER_PORTFOLIO":
        errors.append("V23.2 Portfolio Mode 오류입니다.")
    if portfolio.update_status not in {"APPLIED", "NO_CHANGE"}:
        errors.append("V23.2 Update Status 오류입니다.")
    if any(
        (
            portfolio.account_mutated,
            portfolio.funds_reserved,
            portfolio.holdings_reserved,
            portfolio.transmit,
            portfolio.credentials_used,
            portfolio.market_data_api_called,
            portfolio.account_api_called,
            portfolio.network_accessed,
            portfolio.broker_api_called,
            portfolio.broker_order_created,
            portfolio.order_submitted,
            portfolio.live_execution_authorized,
        )
    ):
        errors.append("V23.2 안전 플래그 오류입니다.")
    return not errors, errors


def save_portfolio_update_result(
    result: OfflinePaperPortfolioUpdateV232Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / (
        f"offline_paper_portfolio_update_v23_2_{result.update_result_id}.json"
    )
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result.report_path = str(path)
    latest = output_directory / "offline_paper_portfolio_update_v23_2_latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    result.latest_path = str(latest)
    return path


def load_portfolio_update_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
