from __future__ import annotations

import argparse

from .daily_performance_operation_report_v2_1_32 import (
    DailyPerformanceOperationReportV2132,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--market-date",default=None)
    a=p.parse_args()

    print("V2.1.32 DAILY PERFORMANCE + OPERATION REPORT")
    print("V2.1.27 completed trades: READ-ONLY")
    print("V2.1.29 risk ledger: READ-ONLY")
    print("V2.1.30 recovery ledger: READ-ONLY")
    print("V2.1.31 operation ledger: READ-ONLY")
    print("Broker network: NONE")
    print("Orders: NONE")
    print("Live trading: LOCKED")

    c=DailyPerformanceOperationReportV2132(a.root)
    r=c.build(a.market_date)

    print("\n=== V2.1.32 RESULT ===")
    print("STATUS:",r["status"])
    print("MARKET DATE:",r["market_date"])
    print("COMPLETED ROUND TRIPS:",
          r["trade_performance"]["completed_round_trips"])
    print("WINS:",r["trade_performance"]["wins"])
    print("LOSSES:",r["trade_performance"]["losses"])
    print("WIN RATE %:",r["trade_performance"]["win_rate_pct"])
    print("GROSS PNL BEFORE FEES:",
          r["trade_performance"]["fill_based_gross_pnl_before_fees"])
    print("AVERAGE RETURN %:",
          r["trade_performance"]["average_return_pct_from_fills"])
    print("AVERAGE HOLDING SECONDS:",
          r["trade_performance"]["average_holding_seconds"])
    print("KILL/RISK BLOCK EVENTS:",r["kill_switch_events"])
    print("VALIDATION DAY ELIGIBLE:",
          r["validation_day"]["eligible"])
    print("VALIDATION DAYS:",
          r["validation_day"]["qualified_validation_days_total"],
          "/",
          r["validation_day"]["target_trading_days"])
    print("REMAINING VALIDATION DAYS:",
          r["validation_day"]["remaining_to_target"])
    print("REPORT SHA256:",r["report_sha256"])
    print("BROKER NETWORK USED:",r["broker_network_used"])
    print("PAPER ORDERS SUBMITTED:",r["paper_orders_submitted"])
    print("LIVE ORDERS SUBMITTED:",r["live_orders_submitted"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
