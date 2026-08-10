from __future__ import annotations

import json
import math
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


MIN_ACTIONABLE_SAMPLE = 5


def _decimal(value, default=Decimal("0")):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _bin(value, cuts, labels):
    v=_float(value)
    for cut,label in zip(cuts,labels):
        if v<cut:
            return label
    return labels[-1]


def confidence_bin(value):
    return _bin(
        value,
        (0.75,0.80,0.85,0.90),
        ("<0.75","0.75-0.80","0.80-0.85","0.85-0.90","0.90+"),
    )


def reward_risk_bin(value):
    return _bin(
        value,
        (1.0,1.25,1.50,2.0),
        ("<1.00","1.00-1.25","1.25-1.50","1.50-2.00","2.00+"),
    )


def alignment_bin(value):
    return _bin(
        value,
        (0.50,0.65,0.80,0.90),
        ("<0.50","0.50-0.65","0.65-0.80","0.80-0.90","0.90+"),
    )


def quality_bin(value):
    return _bin(
        value,
        (0.50,0.60,0.70,0.80),
        ("<0.50","0.50-0.60","0.60-0.70","0.70-0.80","0.80+"),
    )


def _safe_mean(values):
    return sum(values)/len(values) if values else 0.0


def _metrics(rows):
    trades=len(rows)
    wins=[r for r in rows if r["label"]=="WIN"]
    losses=[r for r in rows if r["label"]=="LOSS"]
    flats=[r for r in rows if r["label"]=="FLAT"]

    pnls=[r["pnl"] for r in rows]
    returns=[r["return_pct"] for r in rows]
    holdings=[
        r["holding_seconds"] for r in rows
        if r["holding_seconds"] is not None
    ]

    gross_profit=sum(p for p in pnls if p>0)
    gross_loss_abs=abs(sum(p for p in pnls if p<0))
    gross_pnl=sum(pnls)

    if gross_loss_abs>0:
        profit_factor=gross_profit/gross_loss_abs
    elif gross_profit>0:
        profit_factor=None  # positive infinity, rendered explicitly below
    else:
        profit_factor=0.0

    avg_winner=_safe_mean([r["pnl"] for r in wins])
    avg_loser=_safe_mean([r["pnl"] for r in losses])

    result={
        "trades":trades,
        "wins":len(wins),
        "losses":len(losses),
        "flats":len(flats),
        "win_rate_pct":round((len(wins)/trades*100) if trades else 0.0,4),
        "loss_rate_pct":round((len(losses)/trades*100) if trades else 0.0,4),
        "gross_pnl_before_fees":round(gross_pnl,6),
        "average_pnl_before_fees":round(_safe_mean(pnls),6),
        "average_return_pct":round(_safe_mean(returns),6),
        "average_holding_seconds":(
            None if not holdings else round(_safe_mean(holdings),3)
        ),
        "gross_profit":round(gross_profit,6),
        "gross_loss_abs":round(gross_loss_abs,6),
        "profit_factor":(
            "INF" if profit_factor is None else round(profit_factor,6)
        ),
        "average_winner_pnl":round(avg_winner,6),
        "average_loser_pnl":round(avg_loser,6),
        "expectancy_pnl_per_trade":round(_safe_mean(pnls),6),
        "minimum_actionable_sample":MIN_ACTIONABLE_SAMPLE,
        "actionable_sample":trades>=MIN_ACTIONABLE_SAMPLE,
    }
    return result


class PerformanceSegmentationFeatureAttributionV223:
    """
    Read-only performance segmentation over V2.2.2 labeled Paper outcomes.

    No execution thresholds are modified. Segment statistics are descriptive
    evidence only until adequate samples exist.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.source=(
            self.root/"runtime"/
            "ai_outcome_labeling_feature_trade_binding_v2_2_2"/
            "labeled_outcomes.jsonl"
        )
        self.runtime_dir=(
            self.root/"runtime"/
            "ai_performance_segmentation_feature_attribution_v2_2_3"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.json_report=self.runtime_dir/"latest_performance_segmentation.json"
        self.md_report=self.runtime_dir/"latest_performance_segmentation.md"

    @staticmethod
    def _read_jsonl(path):
        rows=[]
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows

    @staticmethod
    def _normalize(row):
        outcome=row.get("outcome") or {}
        feature=row.get("feature_binding") or {}
        calibration=feature.get("confidence_calibration") or {}
        confidence=_float(
            calibration.get(
                "calibrated_confidence",
                calibration.get("raw_confidence",0.0),
            )
        )

        holding=outcome.get("holding_seconds")
        return {
            "round_trip_id":row.get("round_trip_id"),
            "symbol":str(row.get("symbol") or "UNKNOWN").upper(),
            "label":str(outcome.get("outcome_label") or "UNKNOWN").upper(),
            "pnl":_float(outcome.get("gross_pnl_from_fills")),
            "return_pct":_float(outcome.get("return_pct_from_fills")),
            "holding_seconds":(
                None if holding is None else _float(holding)
            ),
            "exit_reason":str(outcome.get("exit_reason") or "UNKNOWN").upper(),
            "action":str(feature.get("action") or "UNKNOWN").upper(),
            "market_regime":str(
                feature.get("market_regime") or "UNKNOWN"
            ).upper(),
            "dominant_structure":str(
                feature.get("dominant_structure") or "UNKNOWN"
            ).upper(),
            "confidence":confidence,
            "reward_risk":_float(feature.get("reward_risk")),
            "alignment":_float(feature.get("trend_alignment")),
            "quality_score":_float(feature.get("shadow_quality_score")),
            "probability":_float(feature.get("probability")),
            "feature_lag_seconds":_float(feature.get("feature_lag_seconds")),
        }

    @staticmethod
    def _segment(rows,key_fn):
        groups=defaultdict(list)
        for row in rows:
            groups[str(key_fn(row))].append(row)
        result={}
        for key in sorted(groups):
            result[key]=_metrics(groups[key])
        return result

    @staticmethod
    def _rank_actionable(segment):
        candidates=[]
        for key,metrics in segment.items():
            if not metrics["actionable_sample"]:
                continue
            pf=metrics["profit_factor"]
            pf_num=999999.0 if pf=="INF" else _float(pf)
            candidates.append((
                metrics["gross_pnl_before_fees"],
                metrics["win_rate_pct"],
                pf_num,
                key,
            ))
        candidates.sort(reverse=True)
        return [row[3] for row in candidates]

    def _markdown(self,report):
        lines=[
            "# V2.2.3 Performance Segmentation + Feature Attribution",
            "",
            f"- Labeled outcomes: {report['labeled_outcomes']}",
            f"- Minimum actionable sample per segment: {MIN_ACTIONABLE_SAMPLE}",
            f"- Calibration ready: {str(report['calibration_ready']).upper()}",
            "- Execution selector modified: FALSE",
            "- Broker network: OFF",
            "",
            "## Overall",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
        overall=report["overall"]
        for key in (
            "trades","wins","losses","flats","win_rate_pct",
            "gross_pnl_before_fees","average_return_pct",
            "average_holding_seconds","profit_factor",
            "expectancy_pnl_per_trade",
        ):
            lines.append(f"| {key} | {overall.get(key)} |")

        for title,key in (
            ("Symbol","by_symbol"),
            ("Market Regime","by_market_regime"),
            ("Dominant Structure","by_dominant_structure"),
            ("Confidence Bin","by_confidence_bin"),
            ("Reward/Risk Bin","by_reward_risk_bin"),
            ("Alignment Bin","by_alignment_bin"),
            ("Quality Score Bin","by_quality_bin"),
            ("Exit Reason","by_exit_reason"),
            ("Action","by_action"),
        ):
            lines.extend([
                "",
                f"## {title}",
                "",
                "| Segment | Trades | Win % | Gross P&L | Avg Return % | Profit Factor | Actionable |",
                "|---|---:|---:|---:|---:|---:|---|",
            ])
            for seg,m in report[key].items():
                lines.append(
                    f"| {seg} | {m['trades']} | {m['win_rate_pct']} | "
                    f"{m['gross_pnl_before_fees']} | {m['average_return_pct']} | "
                    f"{m['profit_factor']} | {m['actionable_sample']} |"
                )

        lines.extend([
            "",
            "## Interpretation Guard",
            "",
            "Segments below the minimum actionable sample are descriptive only.",
            "V2.2.3 does not change confidence, reward/risk, or execution thresholds.",
            "",
        ])
        return "\n".join(lines)

    def build(self):
        raw=self._read_jsonl(self.source)
        if not raw:
            result={
                "status":"WAITING_FOR_V2_2_2_LABELED_OUTCOMES",
                "labeled_outcomes":0,
                "minimum_actionable_sample":MIN_ACTIONABLE_SAMPLE,
                "calibration_ready":False,
                "execution_selector_modified":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            self.json_report.write_text(
                json.dumps(result,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            return result

        rows=[
            self._normalize(row)
            for row in raw
            if row.get("status")=="LABELED_BOUND_PAPER_OUTCOME"
        ]
        if not rows:
            return {
                "status":"WAITING_FOR_V2_2_2_LABELED_OUTCOMES",
                "labeled_outcomes":0,
                "minimum_actionable_sample":MIN_ACTIONABLE_SAMPLE,
                "calibration_ready":False,
                "execution_selector_modified":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }

        report={
            "stage":
                "AI_TRADING_ENGINE_V2_2_3_PERFORMANCE_SEGMENTATION_FEATURE_ATTRIBUTION",
            "status":"PASS_PERFORMANCE_SEGMENTATION_FEATURE_ATTRIBUTION",
            "labeled_outcomes":len(rows),
            "minimum_actionable_sample":MIN_ACTIONABLE_SAMPLE,
            "overall":_metrics(rows),
            "by_symbol":self._segment(rows,lambda r:r["symbol"]),
            "by_market_regime":
                self._segment(rows,lambda r:r["market_regime"]),
            "by_dominant_structure":
                self._segment(rows,lambda r:r["dominant_structure"]),
            "by_confidence_bin":
                self._segment(rows,lambda r:confidence_bin(r["confidence"])),
            "by_reward_risk_bin":
                self._segment(rows,lambda r:reward_risk_bin(r["reward_risk"])),
            "by_alignment_bin":
                self._segment(rows,lambda r:alignment_bin(r["alignment"])),
            "by_quality_bin":
                self._segment(rows,lambda r:quality_bin(r["quality_score"])),
            "by_exit_reason":
                self._segment(rows,lambda r:r["exit_reason"]),
            "by_action":
                self._segment(rows,lambda r:r["action"]),
            "calibration_ready":len(rows)>=MIN_ACTIONABLE_SAMPLE,
            "execution_selector_modified":False,
            "feature_engine_modified":False,
            "threshold_change_recommended_from_stage":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }

        report["actionable_rankings"]={
            "confidence_bins":
                self._rank_actionable(report["by_confidence_bin"]),
            "reward_risk_bins":
                self._rank_actionable(report["by_reward_risk_bin"]),
            "alignment_bins":
                self._rank_actionable(report["by_alignment_bin"]),
            "quality_bins":
                self._rank_actionable(report["by_quality_bin"]),
            "market_regimes":
                self._rank_actionable(report["by_market_regime"]),
        }

        self.json_report.write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.md_report.write_text(
            self._markdown(report),
            encoding="utf-8",
        )
        return report
