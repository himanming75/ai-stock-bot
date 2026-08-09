from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo


class DailyPerformanceOperationReportV2132:
    """
    Read-only reporting layer over existing runtime ledgers.

    Sources:
      V2.1.27 completed round trips
      V2.1.29 risk ledger
      V2.1.30 recovery ledger
      V2.1.31 daily operation ledger

    No broker network.
    No signal/order/lifecycle/risk/recovery execution.
    No P&L recomputation from prices.

    Trading P&L fields are aggregated exactly from V2.1.27:
      gross_pnl_from_fills
      return_pct_from_fills
      holding_seconds
      exit.reason
    """

    def __init__(self, root, *, now_fn=None):
        self.root=Path(root)
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))
        self.market_tz=ZoneInfo("America/New_York")

        self.completed_ledger=(
            self.root/"runtime"/"final_round_trip_ledger_v2_1_27"/
            "completed_round_trips.jsonl"
        )
        self.risk_ledger=(
            self.root/"runtime"/"daily_risk_budget_kill_switch_v2_1_29"/
            "risk_ledger.jsonl"
        )
        self.recovery_ledger=(
            self.root/"runtime"/"session_crash_network_restart_recovery_v2_1_30"/
            "recovery_ledger.jsonl"
        )
        self.operation_ledger=(
            self.root/"runtime"/"one_click_daily_paper_operation_v2_1_31"/
            "daily_operation_ledger.jsonl"
        )

        self.runtime_dir=(
            self.root/"runtime"/"daily_performance_operation_report_v2_1_32"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.report_dir=self.runtime_dir/"reports"
        self.report_dir.mkdir(parents=True,exist_ok=True)
        self.validation_ledger=(
            self.runtime_dir/"validation_day_ledger.jsonl"
        )
        self.latest_json=self.runtime_dir/"latest_daily_report.json"
        self.latest_md=self.runtime_dir/"latest_daily_report.md"

    def _now(self):
        return self.now_fn().astimezone(timezone.utc)

    @staticmethod
    def _jsonl(path):
        if not path.exists():
            return []
        rows=[]
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows

    @staticmethod
    def _decimal(value, default="0"):
        try:
            return Decimal(str(value if value is not None else default))
        except (InvalidOperation,ValueError,TypeError):
            return Decimal(default)

    def _market_date_from_dt_value(self,value):
        if not value:
            return None
        try:
            dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        except (ValueError,TypeError):
            return None
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(self.market_tz).date().isoformat()

    def _row_market_date(self,row,source):
        if source=="trade":
            return self._market_date_from_dt_value(
                row.get("completed_at_utc")
            )

        if source=="operation":
            for key in ("started_at_utc","ended_at_utc","completed_at_utc"):
                d=self._market_date_from_dt_value(row.get(key))
                if d:
                    return d
            return None

        if source=="recovery":
            for key in (
                "completed_at_utc","observed_at_utc","rolled_over_at_utc"
            ):
                d=self._market_date_from_dt_value(row.get(key))
                if d:
                    return d

            snap=row.get("broker_snapshot") or {}
            d=self._market_date_from_dt_value(
                snap.get("observed_at_utc")
            )
            if d:
                return d
            snap2=row.get("snapshot") or {}
            return self._market_date_from_dt_value(
                snap2.get("observed_at_utc")
            )

        if source=="risk":
            if row.get("market_date"):
                return str(row["market_date"])
            return self._market_date_from_dt_value(
                row.get("completed_at_utc")
            )

        return None

    def _today_market_date(self):
        return self._now().astimezone(
            self.market_tz
        ).date().isoformat()

    def _source_rows_for_date(self,market_date):
        trades=[
            r for r in self._jsonl(self.completed_ledger)
            if (
                r.get("status")
                =="COMPLETED_ALPACA_PAPER_ROUND_TRIP"
                and self._row_market_date(r,"trade")==market_date
            )
        ]
        risks=[
            r for r in self._jsonl(self.risk_ledger)
            if self._row_market_date(r,"risk")==market_date
        ]
        recoveries=[
            r for r in self._jsonl(self.recovery_ledger)
            if self._row_market_date(r,"recovery")==market_date
        ]
        operations=[
            r for r in self._jsonl(self.operation_ledger)
            if self._row_market_date(r,"operation")==market_date
        ]
        return trades,risks,recoveries,operations

    @staticmethod
    def _trade_summary(trades):
        pnls=[
            DailyPerformanceOperationReportV2132._decimal(
                r.get("gross_pnl_from_fills")
            )
            for r in trades
        ]
        returns=[
            DailyPerformanceOperationReportV2132._decimal(
                r.get("return_pct_from_fills")
            )
            for r in trades
        ]
        holdings=[
            float(r["holding_seconds"])
            for r in trades
            if r.get("holding_seconds") is not None
        ]

        wins=sum(1 for p in pnls if p>0)
        losses=sum(1 for p in pnls if p<0)
        flats=sum(1 for p in pnls if p==0)
        count=len(trades)
        gross=sum(pnls,Decimal("0"))
        win_rate=(
            Decimal(wins)/Decimal(count)*Decimal("100")
            if count else Decimal("0")
        )
        avg_return=(
            sum(returns,Decimal("0"))/Decimal(len(returns))
            if returns else Decimal("0")
        )
        avg_holding=(
            sum(holdings)/len(holdings)
            if holdings else None
        )

        best=None
        worst=None
        if trades:
            best=max(
                trades,
                key=lambda r:DailyPerformanceOperationReportV2132._decimal(
                    r.get("gross_pnl_from_fills")
                ),
            )
            worst=min(
                trades,
                key=lambda r:DailyPerformanceOperationReportV2132._decimal(
                    r.get("gross_pnl_from_fills")
                ),
            )

        exit_reasons=Counter(
            str((r.get("exit") or {}).get("reason") or "UNKNOWN")
            for r in trades
        )
        symbols=Counter(
            str(r.get("symbol") or "UNKNOWN")
            for r in trades
        )

        return {
            "completed_round_trips":count,
            "wins":wins,
            "losses":losses,
            "flat":flats,
            "win_rate_pct":str(win_rate),
            "fill_based_gross_pnl_before_fees":str(gross),
            "average_return_pct_from_fills":str(avg_return),
            "average_holding_seconds":avg_holding,
            "best_trade":DailyPerformanceOperationReportV2132._trade_card(best),
            "worst_trade":DailyPerformanceOperationReportV2132._trade_card(worst),
            "exit_reasons":dict(sorted(exit_reasons.items())),
            "symbols":dict(sorted(symbols.items())),
            "pnl_semantics":"V2.1.27_FILL_BASED_GROSS_PNL_BEFORE_FEES",
        }

    @staticmethod
    def _trade_card(row):
        if not row:
            return None
        return {
            "round_trip_id":row.get("round_trip_id"),
            "symbol":row.get("symbol"),
            "gross_pnl_from_fills":row.get("gross_pnl_from_fills"),
            "return_pct_from_fills":row.get("return_pct_from_fills"),
            "holding_seconds":row.get("holding_seconds"),
            "exit_reason":(row.get("exit") or {}).get("reason"),
            "completed_at_utc":row.get("completed_at_utc"),
        }

    @staticmethod
    def _latest_risk_card(risks):
        candidates=[
            r for r in risks
            if "trading_allowed" in r
        ]
        if not candidates:
            return None
        r=candidates[-1]
        return {
            "status":r.get("status"),
            "trading_allowed":r.get("trading_allowed"),
            "block_reasons":r.get("block_reasons",[]),
            "completed_round_trips_today":
                r.get("completed_round_trips_today"),
            "daily_fill_based_gross_pnl_before_fees":
                r.get("daily_fill_based_gross_pnl_before_fees"),
            "daily_gross_loss_budget_used_usd":
                r.get("daily_gross_loss_budget_used_usd"),
            "consecutive_losses":r.get("consecutive_losses"),
            "remaining_round_trips_today":
                r.get("remaining_round_trips_today"),
            "remaining_daily_gross_loss_budget_usd":
                r.get("remaining_daily_gross_loss_budget_usd"),
            "manual_kill_switch":r.get("manual_kill_switch"),
        }

    @staticmethod
    def _recovery_summary(rows):
        statuses=Counter(str(r.get("status") or "UNKNOWN") for r in rows)
        actions=Counter(
            str(r.get("recovery_action") or "NONE") for r in rows
        )
        blocked=[
            r for r in rows
            if str(r.get("status") or "").startswith("BLOCKED_")
        ]
        network_events=sum(
            1 for r in rows
            if r.get("broker_network_used") is True
            or (r.get("broker_snapshot") or {}).get(
                "actual_external_network_used"
            ) is True
        )
        return {
            "events":len(rows),
            "network_read_events":network_events,
            "blocked_events":len(blocked),
            "statuses":dict(sorted(statuses.items())),
            "actions":dict(sorted(actions.items())),
        }

    @staticmethod
    def _operation_summary(rows):
        statuses=Counter(str(r.get("status") or "UNKNOWN") for r in rows)
        pass_rows=[
            r for r in rows
            if r.get("status")=="PASS_ONE_CLICK_DAILY_PAPER_OPERATION"
        ]
        blocked=[
            r for r in rows
            if str(r.get("status") or "").startswith("BLOCKED_")
        ]
        wait_timeouts=[
            r for r in rows
            if r.get("status")=="STOPPED_MARKET_WAIT_TIMEOUT"
        ]
        starts=[
            r.get("started_at_utc") for r in rows
            if r.get("started_at_utc")
        ]
        ends=[
            r.get("ended_at_utc") for r in rows
            if r.get("ended_at_utc")
        ]
        return {
            "events":len(rows),
            "successful_paper_operations":len(pass_rows),
            "blocked_operations":len(blocked),
            "market_wait_timeouts":len(wait_timeouts),
            "statuses":dict(sorted(statuses.items())),
            "first_session_start_utc":min(starts) if starts else None,
            "last_session_end_utc":max(ends) if ends else None,
        }

    def _kill_switch_event_count(self,risks):
        return sum(
            1 for r in risks
            if r.get("status") in {
                "PASS_KILL_SWITCH_ENGAGED",
                "BLOCKED_BY_DAILY_RISK_OR_KILL_SWITCH",
            }
            or bool(
                (r.get("manual_kill_switch") or {}).get("engaged")
            )
        )

    def _validation_dates(self):
        dates=set()
        for row in self._jsonl(self.operation_ledger):
            if row.get("status")=="PASS_ONE_CLICK_DAILY_PAPER_OPERATION":
                d=self._row_market_date(row,"operation")
                if d:
                    dates.add(d)
        return sorted(dates)

    def _validation_rows(self):
        return self._jsonl(self.validation_ledger)

    def _append_validation_once(self,row):
        existing={
            str(r.get("market_date"))
            for r in self._validation_rows()
            if r.get("market_date")
        }
        if row["market_date"] in existing:
            return False
        with self.validation_ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")
        return True

    def build(self, market_date=None):
        market_date=str(market_date or self._today_market_date())
        trades,risks,recoveries,operations=(
            self._source_rows_for_date(market_date)
        )

        trade_summary=self._trade_summary(trades)
        risk_summary=self._latest_risk_card(risks)
        recovery_summary=self._recovery_summary(recoveries)
        operation_summary=self._operation_summary(operations)

        successful_operation=(
            operation_summary["successful_paper_operations"]>0
        )
        validation_eligible=successful_operation
        validation_dates=set(self._validation_dates())
        if validation_eligible:
            validation_dates.add(market_date)

        report={
            "stage":
                "BROKER_INTEGRATION_V2_1_32_DAILY_PERFORMANCE_OPERATION_REPORT",
            "status":"PASS_DAILY_PERFORMANCE_OPERATION_REPORT",
            "market_date":market_date,
            "generated_at_utc":self._now().isoformat(),
            "trade_performance":trade_summary,
            "risk":risk_summary,
            "recovery_operations":recovery_summary,
            "daily_operation":operation_summary,
            "kill_switch_events":self._kill_switch_event_count(risks),
            "validation_day":{
                "eligible":validation_eligible,
                "criterion":
                    "AT_LEAST_ONE_PASS_ONE_CLICK_DAILY_PAPER_OPERATION",
                "qualified_validation_days_total":
                    len(validation_dates),
                "target_trading_days":10,
                "remaining_to_target":
                    max(0,10-len(validation_dates)),
            },
            "source_counts":{
                "v2_1_27_completed_round_trips":len(trades),
                "v2_1_29_risk_rows":len(risks),
                "v2_1_30_recovery_rows":len(recoveries),
                "v2_1_31_operation_rows":len(operations),
            },
            "broker_network_used":False,
            "broker_write_performed":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }

        fingerprint=hashlib.sha256(
            json.dumps(
                report,
                sort_keys=True,
                separators=(",",":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        report["report_sha256"]=fingerprint

        json_path=self.report_dir/f"{market_date}_daily_report.json"
        md_path=self.report_dir/f"{market_date}_daily_report.md"
        json_path.write_text(
            json.dumps(report,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        md=self._markdown(report)
        md_path.write_text(md,encoding="utf-8")
        self.latest_json.write_text(
            json.dumps(report,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        self.latest_md.write_text(md,encoding="utf-8")

        if validation_eligible:
            validation_row={
                "market_date":market_date,
                "status":"QUALIFIED_PAPER_VALIDATION_DAY",
                "report_sha256":fingerprint,
                "completed_round_trips":
                    trade_summary["completed_round_trips"],
                "fill_based_gross_pnl_before_fees":
                    trade_summary["fill_based_gross_pnl_before_fees"],
                "operation_statuses":
                    operation_summary["statuses"],
                "recorded_at_utc":self._now().isoformat(),
            }
            new_validation=self._append_validation_once(validation_row)
        else:
            new_validation=False

        report["validation_day"]["new_validation_ledger_row"]=new_validation
        # Rewrite final report with ledger result.
        json_path.write_text(
            json.dumps(report,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        md=self._markdown(report)
        md_path.write_text(md,encoding="utf-8")
        self.latest_json.write_text(
            json.dumps(report,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        self.latest_md.write_text(md,encoding="utf-8")
        return report

    @staticmethod
    def _markdown(r):
        t=r["trade_performance"]
        risk=r["risk"]
        rec=r["recovery_operations"]
        op=r["daily_operation"]
        val=r["validation_day"]

        lines=[
            f"# Daily Paper Performance & Operation Report — {r['market_date']}",
            "",
            "## Trading Performance",
            "",
            f"- Completed round trips: {t['completed_round_trips']}",
            f"- Wins / Losses / Flat: {t['wins']} / {t['losses']} / {t['flat']}",
            f"- Win rate: {t['win_rate_pct']}%",
            f"- Gross P&L before fees: ${t['fill_based_gross_pnl_before_fees']}",
            f"- Average return from fills: {t['average_return_pct_from_fills']}%",
            f"- Average holding seconds: {t['average_holding_seconds']}",
            f"- Exit reasons: {json.dumps(t['exit_reasons'],sort_keys=True)}",
            "",
            "## Risk",
            "",
        ]
        if risk is None:
            lines.append("- No V2.1.29 risk status found for this market date.")
        else:
            lines.extend([
                f"- Trading allowed: {risk.get('trading_allowed')}",
                f"- Block reasons: {risk.get('block_reasons')}",
                f"- Daily loss budget used: ${risk.get('daily_gross_loss_budget_used_usd')}",
                f"- Consecutive losses: {risk.get('consecutive_losses')}",
                f"- Remaining round trips: {risk.get('remaining_round_trips_today')}",
            ])

        lines.extend([
            "",
            "## Recovery / Operations",
            "",
            f"- Recovery events: {rec['events']}",
            f"- Recovery blocked events: {rec['blocked_events']}",
            f"- Recovery network-read events: {rec['network_read_events']}",
            f"- Daily operation events: {op['events']}",
            f"- Successful Paper operations: {op['successful_paper_operations']}",
            f"- Blocked operations: {op['blocked_operations']}",
            f"- Kill-switch/risk-block events: {r['kill_switch_events']}",
            "",
            "## Validation Progress",
            "",
            f"- Validation-day eligible: {val['eligible']}",
            f"- Qualified validation days: {val['qualified_validation_days_total']} / {val['target_trading_days']}",
            f"- Remaining: {val['remaining_to_target']}",
            "",
            "## Accounting Note",
            "",
            "- P&L source: V2.1.27 fill-based gross P&L before fees.",
            "- This is not broker tax-lot realized P&L and does not include fees.",
            "- V2.1.32 performs no broker network calls and submits no orders.",
            "",
        ])

        if t["best_trade"]:
            lines.extend([
                "## Best Trade",
                "",
                "```json",
                json.dumps(t["best_trade"],indent=2,sort_keys=True),
                "```",
                "",
            ])
        if t["worst_trade"]:
            lines.extend([
                "## Worst Trade",
                "",
                "```json",
                json.dumps(t["worst_trade"],indent=2,sort_keys=True),
                "```",
                "",
            ])

        return "\n".join(lines)
