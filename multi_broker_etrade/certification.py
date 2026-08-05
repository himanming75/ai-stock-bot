from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from multi_broker_core.factory import BrokerFactory
from .factory_registration import register_etrade_adapter
from .oauth import hmac_sha1_signature
from .transport import FixtureTransport


ACCOUNT_KEY = "fixture-account-key"


def fixture_responses() -> dict[str, object]:
    return {
        "/v1/accounts/list.json": {
            "AccountListResponse": {
                "Accounts": {
                    "Account": [
                        {
                            "accountId": "****1234",
                            "accountIdKey": ACCOUNT_KEY,
                            "accountMode": "MARGIN",
                            "accountStatus": "ACTIVE",
                            "accountType": "INDIVIDUAL",
                        }
                    ]
                }
            }
        },
        f"/v1/accounts/{ACCOUNT_KEY}/balance.json?instType=BROKERAGE&realTimeNAV=true": {
            "BalanceResponse": {
                "Computed": {
                    "cashAvailableForInvestment": 25000.50,
                    "RealTimeValues": {
                        "totalAccountValue": 100500.75
                    },
                }
            }
        },
        f"/v1/accounts/{ACCOUNT_KEY}/portfolio.json": {
            "PortfolioResponse": {
                "AccountPortfolio": [
                    {
                        "accountId": ACCOUNT_KEY,
                        "Position": [
                            {
                                "Product": {"symbol": "SPY"},
                                "quantity": 10,
                                "pricePaid": 500.00,
                                "marketValue": 5050.00,
                                "totalGain": 50.00,
                            },
                            {
                                "Product": {"symbol": "QQQ"},
                                "quantity": 4,
                                "pricePaid": 450.00,
                                "marketValue": 1820.00,
                                "totalGain": 20.00,
                            },
                        ],
                    }
                ]
            }
        },
        f"/v1/accounts/{ACCOUNT_KEY}/orders.json": {
            "OrdersResponse": {
                "Order": [
                    {
                        "orderId": 987654,
                        "OrderDetail": [
                            {
                                "status": "EXECUTED",
                                "Instrument": [
                                    {
                                        "Product": {"symbol": "SPY"},
                                        "orderAction": "BUY",
                                        "orderedQuantity": 10,
                                        "filledQuantity": 10,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    }


def official_signature_vector_passes() -> bool:
    params = {
        "oauth_consumer_key": "c5bb4dcb7bd6826c7c4340df3f791188",
        "oauth_timestamp": "1344885636",
        "oauth_nonce": "0bba225a40d1bbac2430aa0c6163ce44",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_token": "VbiNYl63EejjlKdQM6FeENzcnrLACrZ2JYD6NQROfVI=",
    }
    signature = hmac_sha1_signature(
        "GET",
        "https://api.etrade.com/v1/accounts/list",
        params,
        "7d30246211192cda43ede3abd9b393b9",
        "XCF9RzyQr4UEPloA+WlC06BnTfYC1P0Fwr3GUw/B0Es=",
    )
    return signature == "UOnPVdzExTAgHkcGWLLfeTaaMSM="


def certify(output_dir: Path) -> dict:
    transport = FixtureTransport(fixture_responses())
    factory = register_etrade_adapter(BrokerFactory())
    adapter = factory.create(
        "ETRADE",
        transport=transport,
        account_id_key=ACCOUNT_KEY,
    )

    account = adapter.get_account()
    positions = adapter.list_positions()
    orders = adapter.list_orders()

    submit_blocked = cancel_blocked = False
    try:
        adapter.submit_order(None)  # type: ignore[arg-type]
    except PermissionError:
        submit_blocked = True
    try:
        adapter.cancel_order("987654")
    except PermissionError:
        cancel_blocked = True

    result = {
        "stage": "V3401_TO_V3600_ETRADE_ADAPTER_FOUNDATION",
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "adapter": adapter.broker_name,
        "factory_implemented_brokers": factory.implemented_brokers(),
        "account": account.to_dict(),
        "positions": [x.to_dict() for x in positions],
        "orders": [x.to_dict() for x in orders],
        "requested_paths": transport.paths_requested,
        "account_mapping_passed": account.equity > 0,
        "positions_mapping_passed": len(positions) == 2,
        "orders_mapping_passed": len(orders) == 1,
        "official_oauth_signature_vector_passed": official_signature_vector_passes(),
        "token_state": adapter.token_state.to_dict(),
        "submit_blocked": submit_blocked,
        "cancel_blocked": cancel_blocked,
        "fixture_transport_used": True,
        "real_credentials_used": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "existing_alpaca_controller_modified": False,
        "existing_market_polling_modified": False,
        "oauth_request_token_exchange_enabled": False,
        "oauth_access_token_exchange_enabled": False,
        "oauth_renew_enabled": False,
        "oauth_revoke_enabled": False,
        "next_fixed_development": "V3601_TO_V3800_ETRADE_OAUTH_SESSION_AND_SANDBOX_READ_VALIDATION",
    }

    if not all(
        [
            result["account_mapping_passed"],
            result["positions_mapping_passed"],
            result["orders_mapping_passed"],
            result["official_oauth_signature_vector_passed"],
            result["submit_blocked"],
            result["cancel_blocked"],
        ]
    ):
        result["status"] = "BLOCKED"

    seed = dict(result)
    seed.pop("generated_at")
    result["certification_fingerprint"] = hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "etrade_adapter_certification.json": result,
        "etrade_adapter_mapping_report.json": {
            "account_mapping_passed": result["account_mapping_passed"],
            "positions_mapping_passed": result["positions_mapping_passed"],
            "orders_mapping_passed": result["orders_mapping_passed"],
            "requested_paths": result["requested_paths"],
        },
        "etrade_oauth_foundation_report.json": {
            "oauth_version": "1.0a",
            "signature_method": "HMAC-SHA1",
            "official_signature_vector_passed": result[
                "official_oauth_signature_vector_passed"
            ],
            "sandbox_base_url": "https://apisb.etrade.com",
            "production_base_url": "https://api.etrade.com",
            "request_token_exchange_enabled": False,
            "access_token_exchange_enabled": False,
            "renew_enabled": False,
            "revoke_enabled": False,
        },
        "etrade_adapter_capabilities.json": adapter.capabilities.to_dict(),
    }
    for name, payload in outputs.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    with (output_dir / "etrade_adapter_ledger.jsonl").open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")
    return result
