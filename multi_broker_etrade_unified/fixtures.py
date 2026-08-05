from __future__ import annotations


ACCOUNTS = [
    {
        "broker": "ETRADE",
        "account_id": "individual-brokerage-key",
        "currency": "USD",
        "equity": "100500.75",
        "cash": "25000.50",
        "buying_power": "25000.50",
        "status": "ACTIVE",
        "alias": "PRIMARY_BROKERAGE",
    },
    {
        "broker": "ETRADE",
        "account_id": "stock-plan-key",
        "currency": "USD",
        "equity": "32500.00",
        "cash": "500.00",
        "buying_power": "500.00",
        "status": "ACTIVE",
        "alias": "STOCK_PLAN",
    },
]

POSITIONS = [
    {
        "broker": "ETRADE",
        "account_id": "individual-brokerage-key",
        "symbol": "SPY",
        "quantity": "10",
        "average_price": "500",
        "market_value": "5050",
        "unrealized_pl": "50",
    },
    {
        "broker": "ETRADE",
        "account_id": "stock-plan-key",
        "symbol": "SPY",
        "quantity": "5",
        "average_price": "510",
        "market_value": "2525",
        "unrealized_pl": "-25",
    },
    {
        "broker": "ETRADE",
        "account_id": "individual-brokerage-key",
        "symbol": "QQQ",
        "quantity": "4",
        "average_price": "450",
        "market_value": "1820",
        "unrealized_pl": "20",
    },
]

ORDERS = [
    {
        "broker": "ETRADE",
        "account_id": "individual-brokerage-key",
        "order_id": "order-1",
        "symbol": "SPY",
        "side": "BUY",
        "quantity": "10",
        "filled_quantity": "10",
        "status": "EXECUTED",
    },
    {
        "broker": "ETRADE",
        "account_id": "stock-plan-key",
        "order_id": "order-2",
        "symbol": "SPY",
        "side": "SELL",
        "quantity": "2",
        "filled_quantity": "0",
        "status": "OPEN",
    },
    {
        "broker": "ETRADE",
        "account_id": "individual-brokerage-key",
        "order_id": "order-3",
        "symbol": "QQQ",
        "side": "BUY",
        "quantity": "4",
        "filled_quantity": "0",
        "status": "CANCELLED",
    },
]
