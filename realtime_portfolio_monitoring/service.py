from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .change_detector import (
    detect_position_changes,
    load_previous_snapshot,
)
from .client import AlpacaPaperReadOnlyClient
from .metrics import (
    build_position_metrics,
    build_realized_metrics,
)
from .models import (
    HUNDRED,
    decimal_text,
    decimal_value,
    safe_ratio,
)


class RealtimePortfolioMonitoringService:
    def __init__(self, client=None) -> None:
        self.client = (
            client or AlpacaPaperReadOnlyClient()
        )

    def collect_once(
        self,
        *,
        output_dir: Path,
        cycle_number: int,
    ) -> dict:
        account = self.client.get_account()
        positions_raw = self.client.get_positions()
        orders = self.client.get_orders(
            status="all",
            limit=500,
        )
        clock = self.client.get_clock()

        equity = decimal_value(
            account.get("equity")
        )
        last_equity = decimal_value(
            account.get("last_equity")
        )
        cash = decimal_value(
            account.get("cash")
        )
        buying_power = decimal_value(
            account.get("buying_power")
        )
        portfolio_value = decimal_value(
            account.get("portfolio_value")
        )
        long_market_value = decimal_value(
            account.get("long_market_value")
        )
        short_market_value = decimal_value(
            account.get("short_market_value")
        )

        daily_pl = equity - last_equity
        daily_return_percent = (
            safe_ratio(daily_pl, last_equity)
            * HUNDRED
        )

        positions, exposure = (
            build_position_metrics(
                positions_raw,
                equity,
            )
        )
        realized = build_realized_metrics(
            orders
        )

        latest_path = (
            output_dir
            / "portfolio_monitor_latest.json"
        )
        previous = load_previous_snapshot(
            latest_path
        )
        changes = detect_position_changes(
            previous,
            positions,
        )

        generated_at = (
            datetime.now(timezone.utc)
            .isoformat()
        )

        warnings = []
        if account.get("status") != "ACTIVE":
            warnings.append(
                "ACCOUNT_NOT_ACTIVE"
            )
        if equity <= Decimal("0"):
            warnings.append(
                "NON_POSITIVE_EQUITY"
            )
        if buying_power < Decimal("0"):
            warnings.append(
                "NEGATIVE_BUYING_POWER"
            )
        if (
            decimal_value(
                exposure[
                    "gross_exposure_percent"
                ]
            )
            > Decimal("100")
        ):
            warnings.append(
                "GROSS_EXPOSURE_ABOVE_100_PERCENT"
            )

        result = {
            "stage": (
                "V321_TO_V330_"
                "REALTIME_PORTFOLIO_MONITORING"
            ),
            "status": (
                "PASS"
                if not warnings
                else "PASS_WITH_WARNINGS"
            ),
            "cycle_number": cycle_number,
            "generated_at": generated_at,
            "market": {
                "is_open": bool(
                    clock.get("is_open", False)
                ),
                "timestamp": clock.get(
                    "timestamp"
                ),
                "next_open": clock.get(
                    "next_open"
                ),
                "next_close": clock.get(
                    "next_close"
                ),
            },
            "account": {
                "status": account.get("status"),
                "currency": account.get(
                    "currency"
                ),
                "equity": decimal_text(equity),
                "last_equity": decimal_text(
                    last_equity
                ),
                "portfolio_value": decimal_text(
                    portfolio_value
                ),
                "cash": decimal_text(cash),
                "buying_power": decimal_text(
                    buying_power
                ),
                "long_market_value": decimal_text(
                    long_market_value
                ),
                "short_market_value": decimal_text(
                    short_market_value
                ),
                "daily_pl": decimal_text(
                    daily_pl
                ),
                "daily_return_percent": (
                    decimal_text(
                        daily_return_percent
                    )
                ),
            },
            "positions": positions,
            "exposure": exposure,
            "realized_activity": realized,
            "position_changes": changes,
            "warnings": warnings,
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V331_TO_V340_"
                "REALTIME_RISK_MONITORING"
            ),
        }

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        cycle_path = (
            output_dir
            / f"cycle_{cycle_number:04d}.json"
        )
        cycle_path.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        latest_path.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        dashboard = {
            "generated_at": generated_at,
            "status": result["status"],
            "market_is_open": (
                result["market"]["is_open"]
            ),
            "equity": (
                result["account"]["equity"]
            ),
            "cash": result["account"]["cash"],
            "buying_power": (
                result["account"][
                    "buying_power"
                ]
            ),
            "daily_pl": (
                result["account"]["daily_pl"]
            ),
            "daily_return_percent": (
                result["account"][
                    "daily_return_percent"
                ]
            ),
            "position_count": (
                result["exposure"][
                    "position_count"
                ]
            ),
            "gross_exposure_percent": (
                result["exposure"][
                    "gross_exposure_percent"
                ]
            ),
            "net_exposure_percent": (
                result["exposure"][
                    "net_exposure_percent"
                ]
            ),
            "total_unrealized_pl": (
                result["exposure"][
                    "total_unrealized_pl"
                ]
            ),
            "position_change_count": len(
                changes
            ),
            "warnings": warnings,
            "broker_write": False,
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        }

        (
            output_dir
            / "portfolio_dashboard.json"
        ).write_text(
            json.dumps(
                dashboard,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        with (
            output_dir
            / "portfolio_monitor_ledger.jsonl"
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

        with (
            output_dir
            / "portfolio_metrics_ledger.jsonl"
        ).open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    dashboard,
                    sort_keys=True,
                )
                + "\n"
            )

        return result

    def monitor(
        self,
        *,
        output_dir: Path,
        interval_seconds: int = 60,
        max_cycles: int = 5,
    ) -> dict:
        results = []
        for cycle in range(
            1,
            max(1, max_cycles) + 1,
        ):
            result = self.collect_once(
                output_dir=output_dir,
                cycle_number=cycle,
            )
            results.append(result)

            print(
                json.dumps(
                    result,
                    indent=2,
                    sort_keys=True,
                ),
                flush=True,
            )

            if cycle < max_cycles:
                time.sleep(
                    max(1, interval_seconds)
                )

        summary = {
            "stage": (
                "V321_TO_V330_"
                "REALTIME_PORTFOLIO_MONITORING"
            ),
            "status": (
                "PASS"
                if results
                and all(
                    item["status"]
                    in {
                        "PASS",
                        "PASS_WITH_WARNINGS",
                    }
                    for item in results
                )
                else "BLOCKED"
            ),
            "completed_cycles": len(results),
            "last_cycle": (
                results[-1] if results else None
            ),
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V331_TO_V340_"
                "REALTIME_RISK_MONITORING"
            ),
        }

        (
            output_dir
            / "portfolio_monitor_summary.json"
        ).write_text(
            json.dumps(
                summary,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return summary
