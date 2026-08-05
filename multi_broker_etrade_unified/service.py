from __future__ import annotations
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .aggregation import (
    D,
    aggregate_positions,
    normalize_orders,
    order_statistics,
)
from .fixtures import ACCOUNTS, ORDERS, POSITIONS


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(
        {
            key
            for row in rows
            for key in row
        }
    )
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=keys,
        )
        writer.writeheader()
        writer.writerows(rows)


class ETradeUnifiedPortfolioService:
    def evaluate(
        self,
        *,
        output_dir: Path,
    ) -> dict:
        now = datetime.now(timezone.utc)

        unified_positions = aggregate_positions(
            POSITIONS
        )
        normalized_orders = normalize_orders(
            ORDERS
        )
        stats = order_statistics(
            normalized_orders
        )

        total_equity = sum(
            (D(item["equity"]) for item in ACCOUNTS),
            Decimal("0"),
        )
        total_cash = sum(
            (D(item["cash"]) for item in ACCOUNTS),
            Decimal("0"),
        )
        total_buying_power = sum(
            (
                D(item["buying_power"])
                for item in ACCOUNTS
            ),
            Decimal("0"),
        )
        total_market_value = sum(
            (
                item.total_market_value
                for item in unified_positions
            ),
            Decimal("0"),
        )
        total_unrealized_pl = sum(
            (
                item.total_unrealized_pl
                for item in unified_positions
            ),
            Decimal("0"),
        )

        per_account = []
        for account in ACCOUNTS:
            account_id = account["account_id"]
            account_positions = [
                item
                for item in POSITIONS
                if item["account_id"] == account_id
            ]
            account_orders = [
                item
                for item in normalized_orders
                if item.account_id == account_id
            ]
            per_account.append({
                "broker": "ETRADE",
                "account_id": account_id,
                "alias": account["alias"],
                "equity": account["equity"],
                "cash": account["cash"],
                "buying_power": (
                    account["buying_power"]
                ),
                "position_count": len(
                    account_positions
                ),
                "order_count": len(
                    account_orders
                ),
                "open_order_count": sum(
                    1
                    for item in account_orders
                    if item.open_order
                ),
                "market_value": str(
                    sum(
                        (
                            D(
                                item["market_value"]
                            )
                            for item in account_positions
                        ),
                        Decimal("0"),
                    )
                ),
                "unrealized_pl": str(
                    sum(
                        (
                            D(
                                item["unrealized_pl"]
                            )
                            for item in account_positions
                        ),
                        Decimal("0"),
                    )
                ),
            })

        result = {
            "stage": (
                "V4201_TO_V4400_ETRADE_UNIFIED_PORTFOLIO_"
                "POSITIONS_AND_ORDERS_ROUTING"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "FIXTURE_MULTI_ACCOUNT_READ_ONLY"
            ),
            "account_count": len(ACCOUNTS),
            "position_record_count": len(POSITIONS),
            "unified_symbol_count": len(
                unified_positions
            ),
            "order_record_count": len(
                normalized_orders
            ),
            "totals": {
                "equity": str(total_equity),
                "cash": str(total_cash),
                "buying_power": str(
                    total_buying_power
                ),
                "market_value": str(
                    total_market_value
                ),
                "unrealized_pl": str(
                    total_unrealized_pl
                ),
                "currency": "USD",
            },
            "per_account": per_account,
            "unified_positions": [
                item.to_dict()
                for item in unified_positions
            ],
            "unified_orders": [
                item.to_dict()
                for item in normalized_orders
            ],
            "order_statistics": stats,
            "duplicate_symbol_aggregation_ready": True,
            "weighted_average_price_ready": True,
            "account_breakdown_ready": True,
            "canonical_order_status_ready": True,
            "open_order_detection_ready": True,
            "production_network_read_performed": False,
            "sandbox_network_read_performed": False,
            "real_credentials_used": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "existing_alpaca_controller_modified": False,
            "existing_market_polling_modified": False,
            "key_issuance_blocks_code_development": False,
            "deferred_external_validation": (
                "REFRESH_WITH_ACTUAL_ETRADE_READ_AFTER_KEY_ISSUANCE"
            ),
            "next_fixed_development": (
                "V4401_TO_V4600_ETRADE_PORTFOLIO_RECONCILIATION_"
                "AND_CHANGE_DETECTION"
            ),
        }

        spy = next(
            item
            for item in unified_positions
            if item.symbol == "SPY"
        )
        checks = (
            result["account_count"] == 2,
            result["unified_symbol_count"] == 2,
            spy.total_quantity == Decimal("15"),
            spy.weighted_average_price
            == Decimal("503.3333333333333333333333333"),
            stats["open_order_count"] == 1,
            stats["filled_order_count"] == 1,
            stats["cancelled_order_count"] == 1,
        )
        if not all(checks):
            result["status"] = "BLOCKED"

        seed = dict(result)
        seed.pop("generated_at")
        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    seed,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        write_json(
            output_dir
            / "etrade_unified_portfolio_certification.json",
            result,
        )
        write_json(
            output_dir
            / "etrade_unified_positions.json",
            {
                "items": result[
                    "unified_positions"
                ]
            },
        )
        write_json(
            output_dir
            / "etrade_unified_orders.json",
            {
                "items": result[
                    "unified_orders"
                ],
                "statistics": stats,
            },
        )
        write_json(
            output_dir
            / "etrade_per_account_summary.json",
            {
                "items": per_account
            },
        )
        write_json(
            output_dir
            / "etrade_unified_portfolio_dashboard.json",
            {
                "status": result["status"],
                "account_count": (
                    result["account_count"]
                ),
                "symbol_count": (
                    result[
                        "unified_symbol_count"
                    ]
                ),
                "totals": result["totals"],
                "order_statistics": stats,
                "network_used": False,
                "broker_write": False,
            },
        )
        write_csv(
            output_dir
            / "etrade_unified_positions.csv",
            [
                {
                    key: (
                        json.dumps(value)
                        if isinstance(
                            value,
                            (list, dict),
                        )
                        else value
                    )
                    for key, value
                    in item.to_dict().items()
                }
                for item in unified_positions
            ],
        )
        write_csv(
            output_dir
            / "etrade_unified_orders.csv",
            [
                item.to_dict()
                for item in normalized_orders
            ],
        )

        with (
            output_dir
            / "etrade_unified_portfolio_ledger.jsonl"
        ).open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                )
                + "\n"
            )

        return result
