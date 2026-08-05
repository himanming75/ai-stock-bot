from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .history import equity_history, read_json, read_jsonl
from .models import D, HUNDRED, ZERO, ratio, text
from .policy import RiskPolicy
from .scoring import position_risk_scores, severity


class RealtimeRiskMonitoringService:
    def evaluate(
        self,
        *,
        portfolio_snapshot_path: Path,
        portfolio_metrics_ledger_path: Path,
        policy_path: Path,
        output_dir: Path,
    ) -> dict:
        portfolio = read_json(portfolio_snapshot_path)
        metrics_rows = read_jsonl(portfolio_metrics_ledger_path)
        policy = RiskPolicy.load(policy_path)

        account = portfolio.get("account", {})
        exposure = portfolio.get("exposure", {})
        positions = portfolio.get("positions", [])

        equity = D(account.get("equity"))
        cash = D(account.get("cash"))
        buying_power = D(account.get("buying_power"))
        daily_return = D(account.get("daily_return_percent"))
        gross_exposure = D(exposure.get("gross_exposure_percent"))
        net_exposure = abs(D(exposure.get("net_exposure_percent")))

        history = equity_history(metrics_rows, equity)
        peak_equity = max(history) if history else equity
        drawdown_amount = max(ZERO, peak_equity - equity)
        drawdown_percent = ratio(drawdown_amount, peak_equity) * HUNDRED

        cash_reserve_percent = ratio(cash, equity) * HUNDRED
        buying_power_used = max(ZERO, buying_power - cash)
        buying_power_utilization_percent = (
            ratio(buying_power_used, buying_power) * HUNDRED
            if buying_power > ZERO
            else ZERO
        )

        largest_position_percent = max(
            [abs(D(item.get("portfolio_weight_percent"))) for item in positions]
            or [ZERO]
        )

        alerts = []

        def check(code, actual, limit, comparison, level):
            triggered = (
                actual > limit
                if comparison == "max"
                else actual < limit
            )
            if triggered:
                alerts.append(
                    {
                        "code": code,
                        "severity": level,
                        "actual": text(actual),
                        "limit": text(limit),
                    }
                )

        check(
            "DAILY_LOSS_LIMIT_BREACH",
            max(ZERO, -daily_return),
            policy.max_daily_loss_percent,
            "max",
            "CRITICAL",
        )
        check(
            "DRAWDOWN_LIMIT_BREACH",
            drawdown_percent,
            policy.max_drawdown_percent,
            "max",
            "CRITICAL",
        )
        check(
            "SINGLE_POSITION_CONCENTRATION",
            largest_position_percent,
            policy.max_single_position_percent,
            "max",
            "WARNING",
        )
        check(
            "GROSS_EXPOSURE_LIMIT_BREACH",
            gross_exposure,
            policy.max_gross_exposure_percent,
            "max",
            "CRITICAL",
        )
        check(
            "NET_EXPOSURE_LIMIT_BREACH",
            net_exposure,
            policy.max_net_exposure_percent,
            "max",
            "WARNING",
        )
        check(
            "CASH_RESERVE_BELOW_MINIMUM",
            cash_reserve_percent,
            policy.min_cash_reserve_percent,
            "min",
            "WARNING",
        )
        check(
            "BUYING_POWER_UTILIZATION_HIGH",
            buying_power_utilization_percent,
            policy.max_buying_power_utilization_percent,
            "max",
            "WARNING",
        )

        position_scores = position_risk_scores(
            positions,
            policy.max_single_position_percent,
        )
        maximum_position_score = max(
            [D(item["risk_score"]) for item in position_scores] or [ZERO]
        )

        components = {
            "daily_loss_score": min(
                HUNDRED,
                ratio(
                    max(ZERO, -daily_return),
                    policy.max_daily_loss_percent,
                )
                * HUNDRED,
            ),
            "drawdown_score": min(
                HUNDRED,
                ratio(drawdown_percent, policy.max_drawdown_percent)
                * HUNDRED,
            ),
            "concentration_score": min(
                HUNDRED,
                ratio(
                    largest_position_percent,
                    policy.max_single_position_percent,
                )
                * HUNDRED,
            ),
            "gross_exposure_score": min(
                HUNDRED,
                ratio(
                    gross_exposure,
                    policy.max_gross_exposure_percent,
                )
                * HUNDRED,
            ),
            "cash_reserve_score": min(
                HUNDRED,
                ratio(
                    max(
                        ZERO,
                        policy.min_cash_reserve_percent
                        - cash_reserve_percent,
                    ),
                    policy.min_cash_reserve_percent,
                )
                * HUNDRED,
            ),
        }

        portfolio_risk_score = (
            components["daily_loss_score"] * Decimal("0.25")
            + components["drawdown_score"] * Decimal("0.25")
            + components["concentration_score"] * Decimal("0.20")
            + components["gross_exposure_score"] * Decimal("0.20")
            + components["cash_reserve_score"] * Decimal("0.10")
        )
        portfolio_risk_score = min(HUNDRED, portfolio_risk_score)
        risk_level = severity(
            portfolio_risk_score,
            policy.warning_score,
            policy.critical_score,
        )

        if any(item["severity"] == "CRITICAL" for item in alerts):
            risk_level = "CRITICAL"
        elif alerts and risk_level == "NORMAL":
            risk_level = "WARNING"

        generated_at = datetime.now(timezone.utc).isoformat()
        result = {
            "stage": "V331_TO_V340_REALTIME_RISK_MONITORING",
            "status": "PASS",
            "generated_at": generated_at,
            "source_portfolio_generated_at": portfolio.get("generated_at"),
            "source_portfolio_status": portfolio.get("status"),
            "market_is_open": portfolio.get("market", {}).get("is_open"),
            "risk_level": risk_level,
            "portfolio_risk_score": text(portfolio_risk_score),
            "metrics": {
                "equity": text(equity),
                "peak_equity": text(peak_equity),
                "daily_return_percent": text(daily_return),
                "drawdown_amount": text(drawdown_amount),
                "drawdown_percent": text(drawdown_percent),
                "largest_position_percent": text(largest_position_percent),
                "gross_exposure_percent": text(gross_exposure),
                "net_exposure_percent": text(net_exposure),
                "cash_reserve_percent": text(cash_reserve_percent),
                "buying_power_utilization_percent": text(
                    buying_power_utilization_percent
                ),
                "position_count": len(positions),
            },
            "score_components": {
                key: text(value) for key, value in components.items()
            },
            "position_risk_scores": position_scores,
            "maximum_position_risk_score": text(maximum_position_score),
            "alerts": alerts,
            "alert_count": len(alerts),
            "critical_alert_count": sum(
                1 for item in alerts if item["severity"] == "CRITICAL"
            ),
            "policy": {
                "max_daily_loss_percent": text(
                    policy.max_daily_loss_percent
                ),
                "max_drawdown_percent": text(policy.max_drawdown_percent),
                "max_single_position_percent": text(
                    policy.max_single_position_percent
                ),
                "max_gross_exposure_percent": text(
                    policy.max_gross_exposure_percent
                ),
                "max_net_exposure_percent": text(
                    policy.max_net_exposure_percent
                ),
                "min_cash_reserve_percent": text(
                    policy.min_cash_reserve_percent
                ),
                "max_buying_power_utilization_percent": text(
                    policy.max_buying_power_utilization_percent
                ),
            },
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V341_TO_V350_PERFORMANCE_ANALYTICS"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "risk_monitor_latest.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        dashboard = {
            "generated_at": generated_at,
            "risk_level": risk_level,
            "portfolio_risk_score": text(portfolio_risk_score),
            "alert_count": len(alerts),
            "critical_alert_count": result["critical_alert_count"],
            "daily_return_percent": text(daily_return),
            "drawdown_percent": text(drawdown_percent),
            "largest_position_percent": text(largest_position_percent),
            "gross_exposure_percent": text(gross_exposure),
            "cash_reserve_percent": text(cash_reserve_percent),
            "top_position_risks": position_scores[:5],
            "alerts": alerts,
            "broker_write": False,
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        }
        (output_dir / "risk_dashboard.json").write_text(
            json.dumps(dashboard, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with (output_dir / "risk_monitor_ledger.jsonl").open(
            "a", encoding="utf-8"
        ) as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        with (output_dir / "risk_alert_ledger.jsonl").open(
            "a", encoding="utf-8"
        ) as handle:
            for alert in alerts:
                record = dict(alert)
                record["generated_at"] = generated_at
                record["risk_level"] = risk_level
                handle.write(json.dumps(record, sort_keys=True) + "\n")

        summary = {
            "stage": result["stage"],
            "status": "PASS",
            "risk_level": risk_level,
            "portfolio_risk_score": text(portfolio_risk_score),
            "alert_count": len(alerts),
            "critical_alert_count": result["critical_alert_count"],
            "actual_broker_write_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": result["next_fixed_development"],
        }
        (output_dir / "risk_monitor_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result
