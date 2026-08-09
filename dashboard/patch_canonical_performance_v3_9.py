
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/operations_dashboard_v3_2.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if "V3.9_CANONICAL_PERFORMANCE_UNIFICATION" in text:
        print("V3.9 SERVER PATCH ALREADY PRESENT")
        return 0

    old = '''        payload["trade_analytics"] = analytics_module.build_trade_analytics(root, payload)
        payload["trade_analytics_status"] = payload["trade_analytics"].get("status", "PASS")
'''

    new = '''        payload["trade_analytics"] = analytics_module.build_trade_analytics(root, payload)
        payload["trade_analytics_status"] = payload["trade_analytics"].get("status", "PASS")

        # V3.9_CANONICAL_PERFORMANCE_UNIFICATION
        analytics_historical = (
            payload["trade_analytics"].get("historical") or {}
        )
        analytics_validation = (
            payload["trade_analytics"].get("validation") or {}
        )

        payload["performance"] = {
            "validation_closed_trades": int(
                analytics_validation.get("numeric_trade_count", 0) or 0
            ),
            "historical_closed_trades": int(
                analytics_historical.get("numeric_trade_count", 0) or 0
            ),
            "historical_realized_pnl": (
                analytics_historical.get("net_realized_pnl")
            ),
            "win_rate": analytics_historical.get("win_rate"),
            "profit_factor": analytics_historical.get("profit_factor"),
            "canonical_source": True,
            "source_ledger": (
                (payload["trade_analytics"].get("source_ledgers") or [None])[0]
            ),
        }

        canonical_daily = []
        for item in payload["trade_analytics"].get("daily") or []:
            value = item.get("net_realized_pnl")
            if value is None:
                continue
            canonical_daily.append(
                {
                    "date": item.get("date"),
                    "value": value,
                }
            )

        payload.setdefault("visualization", {})
        payload["visualization"]["daily_realized_pnl"] = canonical_daily[-30:]
        payload["visualization"].setdefault("summary", {})
        payload["visualization"]["summary"]["historical_realized_pnl"] = (
            analytics_historical.get("net_realized_pnl")
        )
        payload["visualization"]["summary"]["daily_realized_point_count"] = len(
            canonical_daily
        )
        payload["visualization"]["summary"]["closed_trade_numeric_pnl_count"] = int(
            analytics_historical.get("numeric_trade_count", 0) or 0
        )
'''

    if old not in text:
        raise RuntimeError("V3.9 analytics success block marker not found")

    text = text.replace(old, new, 1)
    target.write_text(text, encoding="utf-8")
    print("V3.9 CANONICAL PERFORMANCE UNIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
