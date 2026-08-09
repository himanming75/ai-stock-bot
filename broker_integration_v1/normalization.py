from datetime import datetime, timezone
from decimal import Decimal

from broker.contracts_v77_1 import (
    AccountSnapshot,
    BrokerOrder,
    BrokerOrderRequest,
    BrokerOrderStatus,
    BrokerPosition,
    OrderSide,
    OrderType,
    TimeInForce,
)

def D(v, default="0"):
    if v is None or v == "":
        return Decimal(default)
    return Decimal(str(v))

def mask_account(value):
    raw=str(value or "").strip()
    if not raw:
        return "UNKNOWN"
    if len(raw)<=4:
        return "*"*len(raw)
    return "*"*(len(raw)-4)+raw[-4:]

def normalize_etrade_position(row):
    product=row.get("Product") or row.get("product") or {}
    symbol=product.get("symbol") or row.get("symbol") or "UNKNOWN"
    quantity=D(row.get("quantity") or row.get("qty"))
    price=D(row.get("pricePaid") or row.get("averageEntryPrice") or 0)
    market_value=D(row.get("marketValue") or 0)
    unrealized=D(row.get("totalGain") or row.get("unrealizedPnl") or 0)
    p=BrokerPosition(
        symbol=str(symbol),
        quantity=quantity,
        average_entry_price=price,
        market_value=market_value,
        unrealized_pnl=unrealized,
    )
    p.validate()
    return p

def _map_status(value):
    v=str(value or "").upper()
    if v in {"OPEN","NEW","ACCEPTED"}:
        return BrokerOrderStatus.ACCEPTED
    if v in {"PARTIAL","PARTIALLY_FILLED"}:
        return BrokerOrderStatus.PARTIALLY_FILLED
    if v in {"FILLED","EXECUTED"}:
        return BrokerOrderStatus.FILLED
    if v in {"CANCELLED","CANCELED"}:
        return BrokerOrderStatus.CANCELED
    return BrokerOrderStatus.ACCEPTED

def normalize_etrade_open_order(row):
    details=(row.get("OrderDetail") or row.get("orderDetail") or [{}])
    detail=details[0] if isinstance(details,list) and details else details if isinstance(details,dict) else {}
    instrument=(detail.get("Instrument") or detail.get("instrument") or [{}])
    instrument=instrument[0] if isinstance(instrument,list) and instrument else instrument if isinstance(instrument,dict) else {}
    product=instrument.get("Product") or instrument.get("product") or {}
    symbol=product.get("symbol") or instrument.get("symbol") or "UNKNOWN"
    qty=D(instrument.get("orderedQuantity") or instrument.get("quantity") or 1)
    action=str(instrument.get("orderAction") or "BUY").upper()
    side=OrderSide.SELL if "SELL" in action else OrderSide.BUY
    req=BrokerOrderRequest(
        client_order_id=str(row.get("clientOrderId") or row.get("orderId") or "etrade-readonly"),
        symbol=str(symbol),
        side=side,
        quantity=qty,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        strategy_id="ETRADE_READONLY_IMPORT",
    )
    req.validate()
    status=_map_status(row.get("orderStatus") or detail.get("status"))
    filled=D(instrument.get("filledQuantity") or 0)
    if status is BrokerOrderStatus.FILLED:
        filled=qty
    submitted=datetime.now(timezone.utc)
    order=BrokerOrder(
        broker_order_id=str(row.get("orderId") or "ETRADE-UNKNOWN"),
        request=req,
        status=status,
        filled_quantity=filled,
        average_fill_price=None,
        submitted_at_utc=submitted,
        updated_at_utc=submitted,
    )
    order.validate()
    return order

def normalize_etrade_account(account_id, balance_payload, portfolio_payload, orders_payload):
    bal=(balance_payload or {}).get("BalanceResponse") or balance_payload or {}
    computed=bal.get("Computed") or bal.get("computed") or {}
    cash=D(computed.get("cashAvailableForInvestment") or computed.get("cashAvailable") or 0)
    buying=D(computed.get("marginBuyingPower") or computed.get("buyingPower") or cash)
    equity=D(computed.get("RealTimeValues",{}).get("totalAccountValue") or computed.get("totalAccountValue") or 0)

    pp=(portfolio_payload or {}).get("PortfolioResponse") or portfolio_payload or {}
    accounts=pp.get("AccountPortfolio") or pp.get("accountPortfolio") or []
    positions=[]
    for acct in accounts if isinstance(accounts,list) else [accounts]:
        for row in (acct.get("Position") or acct.get("position") or []):
            positions.append(normalize_etrade_position(row))

    op=(orders_payload or {}).get("OrdersResponse") or orders_payload or {}
    rows=op.get("Order") or op.get("order") or []
    open_orders=[]
    for row in rows if isinstance(rows,list) else [rows]:
        try:
            order=normalize_etrade_open_order(row)
        except Exception:
            continue
        if order.status not in {
            BrokerOrderStatus.FILLED,
            BrokerOrderStatus.CANCELED,
            BrokerOrderStatus.REJECTED,
            BrokerOrderStatus.EXPIRED,
            BrokerOrderStatus.ERROR,
            BrokerOrderStatus.SUBMISSION_BLOCKED,
        }:
            open_orders.append(order)

    snap=AccountSnapshot(
        account_id_masked=mask_account(account_id),
        currency="USD",
        cash=cash,
        buying_power=buying,
        equity=equity,
        positions=tuple(positions),
        open_orders=tuple(open_orders),
        captured_at_utc=datetime.now(timezone.utc),
    )
    snap.validate()
    return snap
