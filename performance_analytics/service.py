from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .history import (
    normalized_equity_points,
    read_json,
    read_jsonl,
)
from .models import D, ZERO, HUNDRED, ratio, text
from .statistics import (
    aggregate_by_period,
    decimal_mean,
    decimal_std,
    equity_curve,
    period_returns,
    streaks,
)


class PerformanceAnalyticsService:
    def evaluate(
        self,
        *,
        portfolio_metrics_ledger_path: Path,
        portfolio_snapshot_path: Path,
        risk_snapshot_path: Path,
        output_dir: Path,
        annualization_periods: int = 252,
        risk_free_rate_percent: str = "0",
    ) -> dict:
        metrics_rows = read_jsonl(portfolio_metrics_ledger_path)
        portfolio = read_json(portfolio_snapshot_path)
        risk = read_json(risk_snapshot_path)
        points = normalized_equity_points(metrics_rows)

        returns = period_returns(points)
        return_values = [
            item["return_decimal"] for item in returns
        ]
        positive = [value for value in return_values if value > ZERO]
        negative = [value for value in return_values if value < ZERO]

        mean_return = decimal_mean(return_values)
        volatility = decimal_std(return_values)
        downside_deviation = decimal_std(
            [min(ZERO, value) for value in return_values]
        )

        annualization = Decimal(annualization_periods)
        sqrt_annualization = Decimal(
            str(annualization_periods ** 0.5)
        )
        risk_free_period = (
            D(risk_free_rate_percent)
            / HUNDRED
            / annualization
        )

        sharpe = (
            (mean_return - risk_free_period)
            / volatility
            * sqrt_annualization
            if volatility > ZERO
            else ZERO
        )
        sortino = (
            (mean_return - risk_free_period)
            / downside_deviation
            * sqrt_annualization
            if downside_deviation > ZERO
            else ZERO
        )

        curve = equity_curve(points)
        maximum_drawdown = max(
            [D(item["drawdown_percent"]) for item in curve]
            or [ZERO]
        )
        start_equity = points[0]["equity"] if points else ZERO
        end_equity = points[-1]["equity"] if points else ZERO
        total_pnl = end_equity - start_equity
        total_return_percent = (
            ratio(total_pnl, start_equity) * HUNDRED
            if start_equity > ZERO
            else ZERO
        )

        positive_period_rate = (
            ratio(
                Decimal(len(positive)),
                Decimal(len(return_values)),
            )
            * HUNDRED
            if return_values
            else ZERO
        )
        negative_period_rate = (
            ratio(
                Decimal(len(negative)),
                Decimal(len(return_values)),
            )
            * HUNDRED
            if return_values
            else ZERO
        )

        warnings = []
        if len(points) < 2:
            warnings.append("INSUFFICIENT_EQUITY_HISTORY")
        if len(points) < 30:
            warnings.append(
                "LIMITED_SAMPLE_SIZE_FOR_RISK_ADJUSTED_METRICS"
            )
        warnings.append(
            "INSUFFICIENT_REALIZED_TRADE_DATA_FOR_WIN_RATE_PROFIT_FACTOR"
        )

        generated_at = datetime.now(timezone.utc).isoformat()
        result = {
            "stage": "V341_TO_V350_PERFORMANCE_ANALYTICS",
            "status": (
                "PASS_WITH_WARNINGS" if warnings else "PASS"
            ),
            "generated_at": generated_at,
            "source_portfolio_generated_at": portfolio.get(
                "generated_at"
            ),
            "source_risk_generated_at": risk.get("generated_at"),
            "observation_count": len(points),
            "return_observation_count": len(return_values),
            "summary": {
                "start_equity": text(start_equity),
                "end_equity": text(end_equity),
                "total_pnl": text(total_pnl),
                "total_return_percent": text(
                    total_return_percent
                ),
                "mean_period_return_percent": text(
                    mean_return * HUNDRED
                ),
                "period_volatility_percent": text(
                    volatility * HUNDRED
                ),
                "annualized_sharpe_ratio": text(sharpe),
                "annualized_sortino_ratio": text(sortino),
                "maximum_drawdown_percent": text(
                    maximum_drawdown
                ),
                "positive_period_count": len(positive),
                "negative_period_count": len(negative),
                "flat_period_count": (
                    len(return_values)
                    - len(positive)
                    - len(negative)
                ),
                "positive_period_rate_percent": text(
                    positive_period_rate
                ),
                "negative_period_rate_percent": text(
                    negative_period_rate
                ),
                **streaks(return_values),
            },
            "trade_statistics": {
                "win_rate": None,
                "loss_rate": None,
                "profit_factor": None,
                "average_win": None,
                "average_loss": None,
                "expectancy": None,
                "status": (
                    "INSUFFICIENT_REALIZED_TRADE_DATA"
                ),
                "note": (
                    "Equity observations support portfolio-period "
                    "analytics, but closed-trade realized PnL records "
                    "are required for trade-level statistics."
                ),
            },
            "daily_performance": aggregate_by_period(
                points, "day"
            ),
            "weekly_performance": aggregate_by_period(
                points, "week"
            ),
            "monthly_performance": aggregate_by_period(
                points, "month"
            ),
            "equity_curve": curve,
            "period_returns": [
                {
                    "start": item["start"],
                    "end": item["end"],
                    "return_percent": text(
                        item["return_percent"]
                    ),
                }
                for item in returns
            ],
            "current_risk_context": {
                "risk_level": risk.get("risk_level"),
                "portfolio_risk_score": risk.get(
                    "portfolio_risk_score"
                ),
                "alert_count": risk.get("alert_count"),
            },
            "warnings": warnings,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V351_TO_V360_SYSTEM_HEALTH_MONITORING"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "performance_analytics_latest.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        dashboard = {
            "generated_at": generated_at,
            "status": result["status"],
            "observation_count": len(points),
            "total_pnl": result["summary"]["total_pnl"],
            "total_return_percent": result["summary"][
                "total_return_percent"
            ],
            "annualized_sharpe_ratio": result["summary"][
                "annualized_sharpe_ratio"
            ],
            "annualized_sortino_ratio": result["summary"][
                "annualized_sortino_ratio"
            ],
            "maximum_drawdown_percent": result["summary"][
                "maximum_drawdown_percent"
            ],
            "positive_period_rate_percent": result["summary"][
                "positive_period_rate_percent"
            ],
            "risk_level": risk.get("risk_level"),
            "trade_statistics_status": result[
                "trade_statistics"
            ]["status"],
            "warnings": warnings,
            "broker_write": False,
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        }
        (output_dir / "performance_dashboard.json").write_text(
            json.dumps(dashboard, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        (output_dir / "equity_curve.json").write_text(
            json.dumps(curve, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with (output_dir / "performance_ledger.jsonl").open(
            "a", encoding="utf-8"
        ) as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        summary = {
            "stage": result["stage"],
            "status": result["status"],
            "observation_count": len(points),
            "total_return_percent": result["summary"][
                "total_return_percent"
            ],
            "maximum_drawdown_percent": result["summary"][
                "maximum_drawdown_percent"
            ],
            "annualized_sharpe_ratio": result["summary"][
                "annualized_sharpe_ratio"
            ],
            "annualized_sortino_ratio": result["summary"][
                "annualized_sortino_ratio"
            ],
            "warnings": warnings,
            "actual_broker_write_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": result[
                "next_fixed_development"
            ],
        }
        (output_dir / "performance_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result
