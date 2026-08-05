from __future__ import annotations


PREVIOUS = {
    "accounts": [
        {
            "broker": "ETRADE",
            "account_id": "individual-brokerage-key",
            "equity": "100000",
            "cash": "25000",
            "buying_power": "25000",
            "status": "ACTIVE",
        },
        {
            "broker": "ETRADE",
            "account_id": "stock-plan-key",
            "equity": "32000",
            "cash": "500",
            "buying_power": "500",
            "status": "ACTIVE",
        },
    ],
    "positions": [
        {
            "account_id": "individual-brokerage-key",
            "symbol": "SPY",
            "quantity": "10",
            "average_price": "500",
            "market_value": "5000",
            "unrealized_pl": "0",
        },
        {
            "account_id": "individual-brokerage-key",
            "symbol": "QQQ",
            "quantity": "4",
            "average_price": "450",
            "market_value": "1800",
            "unrealized_pl": "0",
        },
    ],
    "orders": [
        {
            "account_id": "individual-brokerage-key",
            "order_id": "order-1",
            "symbol": "SPY",
            "status": "OPEN",
            "quantity": "10",
            "filled_quantity": "0",
        },
        {
            "account_id": "stock-plan-key",
            "order_id": "order-2",
            "symbol": "SPY",
            "status": "OPEN",
            "quantity": "2",
            "filled_quantity": "0",
        },
    ],
}

CURRENT = {
    "accounts": [
        {
            "broker": "ETRADE",
            "account_id": "individual-brokerage-key",
            "equity": "100500.75",
            "cash": "24500",
            "buying_power": "24500",
            "status": "ACTIVE",
        },
        {
            "broker": "ETRADE",
            "account_id": "stock-plan-key",
            "equity": "32500",
            "cash": "500",
            "buying_power": "500",
            "status": "ACTIVE",
        },
    ],
    "positions": [
        {
            "account_id": "individual-brokerage-key",
            "symbol": "SPY",
            "quantity": "15",
            "average_price": "503.3333333333333333333333333",
            "market_value": "7575",
            "unrealized_pl": "25",
        },
        {
            "account_id": "stock-plan-key",
            "symbol": "SPY",
            "quantity": "5",
            "average_price": "510",
            "market_value": "2525",
            "unrealized_pl": "-25",
        },
    ],
    "orders": [
        {
            "account_id": "individual-brokerage-key",
            "order_id": "order-1",
            "symbol": "SPY",
            "status": "FILLED",
            "quantity": "10",
            "filled_quantity": "10",
        },
        {
            "account_id": "stock-plan-key",
            "order_id": "order-2",
            "symbol": "SPY",
            "status": "CANCELLED",
            "quantity": "2",
            "filled_quantity": "0",
        },
        {
            "account_id": "individual-brokerage-key",
            "order_id": "order-3",
            "symbol": "QQQ",
            "status": "OPEN",
            "quantity": "4",
            "filled_quantity": "0",
        },
    ],
}
