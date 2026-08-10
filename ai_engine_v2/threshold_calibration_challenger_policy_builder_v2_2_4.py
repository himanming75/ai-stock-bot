from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path

MIN_GLOBAL_SAMPLE = 5
MIN_SEGMENT_SAMPLE = 5

CHAMPION_MIN_CONFIDENCE = 0.75
CHAMPION_MIN_REWARD_RISK = 1.00

CONFIDENCE_GRID = (0.70,0.75,0.80,0.85,0.90)
REWARD_RISK_GRID = (0.90,1.00,1.15,1.25,1.50)


def _f(value,default=0.0):
    try:
        return float(value)
    except (TypeError,ValueError):
        return default


def _sha(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",",":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _pf_number(value):
    if value=="INF":
        return 999999.0
    return _f(value)


class ThresholdCalibrationChallengerPolicyBuilderV224:
    """
    Read-only threshold calibration candidate builder.

    Champion execution settings remain unchanged. V2.2.4 only creates
    challenger policy candidates for later shadow comparison.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.segmentation_report=(
            self.root/"runtime"/
            "ai_performance_segmentation_feature_attribution_v2_2_3"/
            "latest_performance_segmentation.json"
        )
        self.labeled_outcomes=(
            self.root/"runtime"/
            "ai_outcome_labeling_feature_trade_binding_v2_2_2"/
            "labeled_outcomes.jsonl"
        )
        self.runtime_dir=(
            self.root/"runtime"/
            "ai_threshold_calibration_challenger_policy_v2_2_4"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.policy_json=self.runtime_dir/"challenger_policy_registry.json"
        self.report_json=self.runtime_dir/"latest_challenger_calibration.json"
        self.report_md=self.runtime_dir/"latest_challenger_calibration.md"

    @staticmethod
    def _read_jsonl(path):
        if not path.exists():
            return []
        rows=[]
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    @staticmethod
    def _normalize(row):
        outcome=row.get("outcome") or {}
        feature=row.get("feature_binding") or {}
        confidence=(
            feature.get("confidence_calibration") or {}
        ).get("calibrated_confidence",0)
        return {
            "round_trip_id":row.get("round_trip_id"),
            "symbol":str(row.get("symbol") or "UNKNOWN").upper(),
            "label":str(outcome.get("outcome_label") or "UNKNOWN").upper(),
            "pnl":_f(outcome.get("gross_pnl_from_fills")),
            "return_pct":_f(outcome.get("return_pct_from_fills")),
            "confidence":_f(confidence),
            "reward_risk":_f(feature.get("reward_risk")),
            "market_regime":str(
                feature.get("market_regime") or "UNKNOWN"
            ).upper(),
        }

    @staticmethod
    def _metrics(rows):
        n=len(rows)
        wins=sum(1 for r in rows if r["label"]=="WIN")
        losses=sum(1 for r in rows if r["label"]=="LOSS")
        gross_profit=sum(r["pnl"] for r in rows if r["pnl"]>0)
        gross_loss=abs(sum(r["pnl"] for r in rows if r["pnl"]<0))
        pnl=sum(r["pnl"] for r in rows)
        avg_return=sum(r["return_pct"] for r in rows)/n if n else 0.0
        if gross_loss>0:
            pf=gross_profit/gross_loss
        elif gross_profit>0:
            pf="INF"
        else:
            pf=0.0
        return {
            "trades":n,
            "wins":wins,
            "losses":losses,
            "win_rate_pct":round((wins/n*100) if n else 0.0,4),
            "gross_pnl_before_fees":round(pnl,6),
            "average_return_pct":round(avg_return,6),
            "profit_factor":(
                pf if pf=="INF" else round(pf,6)
            ),
            "expectancy_pnl_per_trade":round((pnl/n) if n else 0.0,6),
        }

    @staticmethod
    def _score(metrics):
        if metrics["trades"]<MIN_GLOBAL_SAMPLE:
            return None
        pf=_pf_number(metrics["profit_factor"])
        expectancy=metrics["expectancy_pnl_per_trade"]
        win_rate=metrics["win_rate_pct"]/100.0
        pnl=metrics["gross_pnl_before_fees"]

        # Ranking only; not used for execution.
        return round(
            expectancy*0.45
            + min(pf,5.0)*0.20
            + win_rate*0.20
            + pnl*0.15,
            6,
        )

    def _global_candidates(self,rows):
        out=[]
        for conf,rr in product(CONFIDENCE_GRID,REWARD_RISK_GRID):
            selected=[
                r for r in rows
                if r["confidence"]>=conf and r["reward_risk"]>=rr
            ]
            metrics=self._metrics(selected)
            score=self._score(metrics)
            out.append({
                "policy_type":"GLOBAL_THRESHOLD",
                "min_confidence":conf,
                "min_reward_risk":rr,
                "metrics":metrics,
                "sample_qualified":
                    metrics["trades"]>=MIN_GLOBAL_SAMPLE,
                "challenger_score":score,
                "execution_enabled":False,
            })
        out.sort(
            key=lambda c:(
                c["challenger_score"] is not None,
                -999999 if c["challenger_score"] is None
                else c["challenger_score"],
                c["metrics"]["trades"],
            ),
            reverse=True,
        )
        return out

    def _regime_candidates(self,rows):
        regimes=sorted({r["market_regime"] for r in rows})
        out=[]
        for regime in regimes:
            regime_rows=[r for r in rows if r["market_regime"]==regime]
            if len(regime_rows)<MIN_SEGMENT_SAMPLE:
                out.append({
                    "policy_type":"REGIME_THRESHOLD",
                    "market_regime":regime,
                    "status":"INSUFFICIENT_SAMPLE",
                    "trades":len(regime_rows),
                    "minimum_required":MIN_SEGMENT_SAMPLE,
                    "execution_enabled":False,
                })
                continue

            best=None
            for conf,rr in product(CONFIDENCE_GRID,REWARD_RISK_GRID):
                selected=[
                    r for r in regime_rows
                    if r["confidence"]>=conf and r["reward_risk"]>=rr
                ]
                metrics=self._metrics(selected)
                score=self._score(metrics)
                candidate={
                    "policy_type":"REGIME_THRESHOLD",
                    "market_regime":regime,
                    "min_confidence":conf,
                    "min_reward_risk":rr,
                    "metrics":metrics,
                    "sample_qualified":
                        metrics["trades"]>=MIN_GLOBAL_SAMPLE,
                    "challenger_score":score,
                    "execution_enabled":False,
                }
                if score is None:
                    continue
                if (
                    best is None
                    or score>best["challenger_score"]
                    or (
                        score==best["challenger_score"]
                        and metrics["trades"]>best["metrics"]["trades"]
                    )
                ):
                    best=candidate

            out.append(
                best if best is not None else {
                    "policy_type":"REGIME_THRESHOLD",
                    "market_regime":regime,
                    "status":"NO_SAMPLE_QUALIFIED_CANDIDATE",
                    "execution_enabled":False,
                }
            )
        return out

    def _markdown(self,report):
        lines=[
            "# V2.2.4 Threshold Calibration + Challenger Policy Builder",
            "",
            f"- Labeled outcomes: {report['labeled_outcomes']}",
            f"- Calibration ready: {str(report['calibration_ready']).upper()}",
            "- Champion execution policy modified: FALSE",
            "- Challenger execution enabled: FALSE",
            "- Promotion enabled: FALSE",
            "",
            "## Champion",
            "",
            f"- min_confidence: {CHAMPION_MIN_CONFIDENCE}",
            f"- min_reward_risk: {CHAMPION_MIN_REWARD_RISK}",
            "",
            "## Top Global Challengers",
            "",
            "| Rank | Confidence | RR | Trades | Win % | P&L | PF | Score |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for i,c in enumerate(report["top_global_challengers"],1):
            m=c["metrics"]
            lines.append(
                f"| {i} | {c['min_confidence']} | {c['min_reward_risk']} | "
                f"{m['trades']} | {m['win_rate_pct']} | "
                f"{m['gross_pnl_before_fees']} | {m['profit_factor']} | "
                f"{c['challenger_score']} |"
            )
        lines += [
            "",
            "## Safety",
            "",
            "These candidates are shadow-only. No threshold is applied to Paper execution.",
            "",
        ]
        return "\n".join(lines)

    def build(self):
        rows=[
            self._normalize(r)
            for r in self._read_jsonl(self.labeled_outcomes)
            if r.get("status")=="LABELED_BOUND_PAPER_OUTCOME"
        ]

        champion={
            "policy_id":"CHAMPION_V2_2_4_BASELINE",
            "source":
                "paper_autonomous_execution.signals.select_candidate",
            "min_confidence":CHAMPION_MIN_CONFIDENCE,
            "min_reward_risk":CHAMPION_MIN_REWARD_RISK,
            "execution_enabled":True,
            "modified_by_v2_2_4":False,
        }

        if not rows:
            report={
                "stage":
                    "AI_TRADING_ENGINE_V2_2_4_THRESHOLD_CALIBRATION_CHALLENGER_POLICY_BUILDER",
                "status":"WAITING_FOR_V2_2_2_LABELED_OUTCOMES",
                "labeled_outcomes":0,
                "calibration_ready":False,
                "minimum_global_sample":MIN_GLOBAL_SAMPLE,
                "champion":champion,
                "challenger_registry":[],
                "top_global_challengers":[],
                "regime_challengers":[],
                "promotion_enabled":False,
                "challenger_execution_enabled":False,
                "champion_execution_modified":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            self.report_json.write_text(
                json.dumps(report,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            self.policy_json.write_text(
                json.dumps(
                    {
                        "champion":champion,
                        "challengers":[],
                        "promotion_enabled":False,
                    },
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            return report

        globals_=self._global_candidates(rows)
        qualified=[
            c for c in globals_
            if c["sample_qualified"]
            and c["challenger_score"] is not None
        ]
        top=qualified[:5]
        regimes=self._regime_candidates(rows)

        challengers=[]
        for i,c in enumerate(top,1):
            challengers.append({
                "policy_id":f"CHALLENGER_GLOBAL_{i}",
                **c,
            })
        for c in regimes:
            if c.get("challenger_score") is not None:
                challengers.append({
                    "policy_id":
                        f"CHALLENGER_REGIME_{c['market_regime']}",
                    **c,
                })

        registry={
            "stage":"AI_TRADING_ENGINE_V2_2_4_POLICY_REGISTRY",
            "champion":champion,
            "challengers":challengers,
            "promotion_enabled":False,
            "challenger_execution_enabled":False,
            "registry_sha256":None,
        }
        registry["registry_sha256"]=_sha({
            k:v for k,v in registry.items()
            if k!="registry_sha256"
        })

        report={
            "stage":
                "AI_TRADING_ENGINE_V2_2_4_THRESHOLD_CALIBRATION_CHALLENGER_POLICY_BUILDER",
            "status":"PASS_THRESHOLD_CALIBRATION_CHALLENGER_POLICY_BUILD",
            "labeled_outcomes":len(rows),
            "calibration_ready":len(rows)>=MIN_GLOBAL_SAMPLE,
            "minimum_global_sample":MIN_GLOBAL_SAMPLE,
            "minimum_segment_sample":MIN_SEGMENT_SAMPLE,
            "champion":champion,
            "candidate_grid_size":
                len(CONFIDENCE_GRID)*len(REWARD_RISK_GRID),
            "global_candidates_evaluated":len(globals_),
            "qualified_global_candidates":len(qualified),
            "top_global_challengers":top,
            "regime_challengers":regimes,
            "challenger_registry_count":len(challengers),
            "promotion_enabled":False,
            "challenger_execution_enabled":False,
            "champion_execution_modified":False,
            "execution_selector_modified":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }

        self.policy_json.write_text(
            json.dumps(
                registry,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.report_json.write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.report_md.write_text(
            self._markdown(report),
            encoding="utf-8",
        )
        return report
