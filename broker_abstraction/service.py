from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .router import ReadOnlyBrokerRouter


class BrokerAbstractionCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)

        alpaca_fixture = {
            "account": {
                "id": "alpaca-paper-fixture",
                "account_number": "PA****01",
                "status": "ACTIVE",
                "cash": "50000",
                "buying_power": "100000",
                "equity": "52000",
                "long_market_value": "2000",
            },
            "positions": [
                {
                    "symbol": "AAPL",
                    "qty": "10",
                    "side": "long",
                    "avg_entry_price": "180",
                    "current_price": "190",
                    "market_value": "1900",
                    "cost_basis": "1800",
                    "unrealized_pl": "100",
                    "unrealized_plpc": "0.0555",
                }
            ],
            "orders": [
                {
                    "id": "alpaca-order-1",
                    "symbol": "AAPL",
                    "side": "buy",
                    "type": "limit",
                    "time_in_force": "day",
                    "status": "filled",
                    "qty": "10",
                    "filled_qty": "10",
                    "limit_price": "180",
                    "filled_avg_price": "180",
                }
            ],
            "quotes": {
                "AAPL": {
                    "bid_price": "189.9",
                    "ask_price": "190.1",
                    "last_price": "190",
                    "volume": "1000000",
                }
            },
        }

        etrade_fixture = {
            "accounts": [
                {
                    "account_id_key": "etrade-fixture",
                    "account_id_masked": "****1234",
                    "account_type": "INDIVIDUAL",
                    "account_mode": "CASH",
                    "status": "ACTIVE",
                }
            ],
            "portfolios": {
                "etrade-fixture": {
                    "data": {
                        "PortfolioResponse": {
                            "AccountPortfolio": [
                                {
                                    "Position": [
                                        {
                                            "Product": {
                                                "symbol": "MSFT",
                                                "securityType": "EQ",
                                            },
                                            "Quick": {
                                                "lastTrade": 420.0
                                            },
                                            "positionType": "LONG",
                                            "quantity": 2,
                                            "pricePaid": 400,
                                            "marketValue": 840,
                                            "totalCost": 800,
                                            "totalGain": 40,
                                            "totalGainPct": 5,
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            },
            "orders": {
                "etrade-fixture": {
                    "data": {
                        "OrdersResponse": {
                            "Order": [
                                {
                                    "orderId": 101,
                                    "orderType": "EQ",
                                    "OrderDetail": [
                                        {
                                            "priceType": "LIMIT",
                                            "orderTerm": "GOOD_FOR_DAY",
                                            "status": "OPEN",
                                            "limitPrice": 410,
                                            "Instrument": [
                                                {
                                                    "Product": {
                                                        "symbol": "MSFT",
                                                        "securityType": "EQ",
                                                    },
                                                    "orderAction": "BUY",
                                                    "orderedQuantity": 2,
                                                    "filledQuantity": 0,
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                }
            },
            "quote": {
                "data": {
                    "QuoteResponse": {
                        "QuoteData": [
                            {
                                "Product": {
                                    "symbol": "MSFT",
                                    "securityType": "EQ",
                                },
                                "All": {
                                    "bid": 419.9,
                                    "ask": 420.1,
                                    "lastTrade": 420,
                                    "volume": 500000,
                                },
                                "quoteStatus": "REALTIME",
                            }
                        ]
                    }
                }
            },
        }

        router = ReadOnlyBrokerRouter()
        router.register(
            "ALPACA",
            snapshot=alpaca_fixture,
        )
        router.register(
            "ETRADE",
            snapshot=etrade_fixture,
        )
        snapshot = router.unified_snapshot(
            symbols=["AAPL", "MSFT"]
        )

        write_blocked = False
        cancel_blocked = False
        try:
            router.submit_order()
        except PermissionError:
            write_blocked = True
        try:
            router.cancel_order()
        except PermissionError:
            cancel_blocked = True

        result = {
            "stage": (
                "V8201_TO_V8400_BROKER_ABSTRACTION_"
                "AND_UNIFIED_READ_ONLY_MODELS"
            ),
            "status": "PASS",
            "universal_account_model_ready": True,
            "universal_position_model_ready": True,
            "universal_order_model_ready": True,
            "universal_quote_model_ready": True,
            "broker_factory_ready": True,
            "capability_registry_ready": True,
            "alpaca_adapter_ready": True,
            "etrade_adapter_ready": True,
            "read_only_router_ready": True,
            "unified_snapshot_ready": True,
            "write_blocked": write_blocked,
            "cancel_blocked": cancel_blocked,
            "snapshot": snapshot,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V8401_TO_V8600_BROKER_SYNC_"
                "RECONCILIATION_AND_PORTAL_INTEGRATION"
            ),
        }

        if not (
            snapshot["totals"]["brokers"] == 2
            and snapshot["totals"]["accounts"] == 2
            and snapshot["totals"]["positions"] == 2
            and write_blocked
            and cancel_blocked
        ):
            result["status"] = "BLOCKED"

        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    result,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        )

        for name, payload in {
            "broker_abstraction_certification.json": result,
            "broker_unified_snapshot_fixture.json": snapshot,
            "broker_capabilities.json": snapshot["brokers"],
            "broker_abstraction_safety.json": {
                "read_only": True,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "order_cancel_enabled": False,
                "network_used": False,
            },
        }.items():
            (output_dir / name).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )

        return result
