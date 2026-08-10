from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


MIN_OUTCOME_SAMPLE = 5


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


def _metrics(rows):
    n=len(rows)
    wins=sum(1 for r in rows if r["label"]=="WIN")
    losses=sum(1 for r in rows if r["label"]=="LOSS")
    flats=sum(1 for r in rows if r["label"]=="FLAT")
    pnls=[r["pnl"] for r in rows]
    rets=[r["return_pct"] for r in rows]
    gross_profit=sum(p for p in pnls if p>0)
    gross_loss_abs=abs(sum(p for p in pnls if p<0))
    gross_pnl=sum(pnls)
    if gross_loss_abs>0:
        pf=gross_profit/gross_loss_abs
    elif gross_profit>0:
        pf="INF"
    else:
        pf=0.0
    return {
        "trades":n,
        "wins":wins,
        "losses":losses,
        "flats":flats,
        "win_rate_pct":round((wins/n*100) if n else 0.0,4),
        "gross_pnl_before_fees":round(gross_pnl,6),
        "average_pnl_before_fees":
            round((gross_pnl/n) if n else 0.0,6),
        "average_return_pct":
            round((sum(rets)/n) if n else 0.0,6),
        "profit_factor":
            pf if pf=="INF" else round(pf,6),
        "expectancy_pnl_per_trade":
            round((gross_pnl/n) if n else 0.0,6),
        "sample_qualified":n>=MIN_OUTCOME_SAMPLE,
        "minimum_sample":MIN_OUTCOME_SAMPLE,
    }


class ChampionChallengerOutcomeComparatorV226:
    """
    Join actual V2.2.2 Paper outcomes to the V2.2.5 shadow-comparison snapshot
    that produced the entry feature evidence.

    This stage uses realized outcomes only. It never fabricates counterfactual
    P&L for CHALLENGER_ONLY signals that were not actually executed.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.outcome_ledger=(
            self.root/"runtime"/
            "ai_outcome_labeling_feature_trade_binding_v2_2_2"/
            "labeled_outcomes.jsonl"
        )
        self.comparison_ledger=(
            self.root/"runtime"/
            "ai_champion_challenger_shadow_comparator_v2_2_5"/
            "comparison_ledger.jsonl"
        )
        self.runtime_dir=(
            self.root/"runtime"/
            "ai_champion_challenger_outcome_comparator_v2_2_6"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.bound_ledger=self.runtime_dir/"bound_policy_outcomes.jsonl"
        self.unbound_ledger=self.runtime_dir/"unbound_policy_outcomes.jsonl"
        self.latest=self.runtime_dir/"latest_outcome_comparison.json"
        self.report_json=self.runtime_dir/"latest_outcome_comparison_report.json"
        self.report_md=self.runtime_dir/"latest_outcome_comparison_report.md"

    @staticmethod
    def _read_jsonl(path):
        rows=[]
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _comparison_index(self,comparisons):
        # Exact snapshot_id is the primary causal binding key.
        by_snapshot=defaultdict(list)
        for row in comparisons:
            sid=str(row.get("feature_snapshot_id") or "")
            if sid:
                by_snapshot[sid].append(row)
        return by_snapshot

    @staticmethod
    def _symbol_policy_rows(comparison,symbol):
        sym=str(symbol or "").upper()
        out=[]
        for comp in list(comparison.get("comparisons") or []):
            policy=dict(comp.get("challenger_policy") or {})
            prow=None
            for row in list(comp.get("symbol_comparisons") or []):
                if str(row.get("symbol") or "").upper()==sym:
                    prow=row
                    break
            if prow is not None:
                out.append({
                    "challenger_policy":policy,
                    "symbol_comparison":prow,
                })
        return out

    @staticmethod
    def _outcome_base(outcome):
        o=outcome.get("outcome") or {}
        return {
            "round_trip_id":outcome.get("round_trip_id"),
            "evidence_key":outcome.get("evidence_key"),
            "symbol":str(outcome.get("symbol") or "").upper(),
            "label":str(o.get("outcome_label") or "UNKNOWN").upper(),
            "pnl":_f(o.get("gross_pnl_from_fills")),
            "return_pct":_f(o.get("return_pct_from_fills")),
            "holding_seconds":o.get("holding_seconds"),
            "exit_reason":o.get("exit_reason"),
            "training_record_sha256":
                outcome.get("training_record_sha256"),
        }

    def _existing_bound_keys(self):
        out=set()
        for row in self._read_jsonl(self.bound_ledger):
            key=row.get("binding_key")
            if key:
                out.add(key)
        return out

    def _markdown(self,report):
        lines=[
            "# V2.2.6 Champion vs Challenger Outcome Comparator",
            "",
            f"- Actual labeled Paper outcomes: {report['actual_outcomes']}",
            f"- Bound actual outcomes: {report['bound_actual_outcomes']}",
            f"- Unbound actual outcomes: {report['unbound_actual_outcomes']}",
            "- Counterfactual P&L fabricated: FALSE",
            "- Challenger execution enabled: FALSE",
            "- Promotion enabled: FALSE",
            "",
            "## Per Challenger",
            "",
            "| Policy | BOTH Trades | BOTH Win % | BOTH P&L | Champion-Only Trades | Champion-Only P&L | Challenger-Only Shadow Signals | Outcome Sample Qualified |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for pid,row in sorted(report["per_challenger"].items()):
            both=row["realized_both"]
            co=row["realized_champion_only"]
            lines.append(
                f"| {pid} | {both['trades']} | {both['win_rate_pct']} | "
                f"{both['gross_pnl_before_fees']} | {co['trades']} | "
                f"{co['gross_pnl_before_fees']} | "
                f"{row['challenger_only_shadow_signal_count']} | "
                f"{row['outcome_sample_qualified']} |"
            )
        lines += [
            "",
            "## Interpretation",
            "",
            "BOTH means the actual Champion trade would also have passed the Challenger.",
            "CHAMPION_ONLY means the actual Champion trade would have been rejected by the Challenger.",
            "CHALLENGER_ONLY signals have no realized trade outcome in this stage because the Challenger did not execute.",
            "",
        ]
        return "\n".join(lines)

    def build(self):
        outcomes=[
            r for r in self._read_jsonl(self.outcome_ledger)
            if r.get("status")=="LABELED_BOUND_PAPER_OUTCOME"
        ]
        if not outcomes:
            result={
                "status":"WAITING_FOR_V2_2_2_LABELED_OUTCOMES",
                "actual_outcomes":0,
                "bound_actual_outcomes":0,
                "unbound_actual_outcomes":0,
                "counterfactual_pnl_fabricated":False,
                "challenger_execution_enabled":False,
                "promotion_enabled":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            self.report_json.write_text(
                json.dumps(result,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            return result

        comparisons=self._read_jsonl(self.comparison_ledger)
        if not comparisons:
            result={
                "status":"WAITING_FOR_V2_2_5_COMPARISON_LEDGER",
                "actual_outcomes":len(outcomes),
                "bound_actual_outcomes":0,
                "unbound_actual_outcomes":len(outcomes),
                "counterfactual_pnl_fabricated":False,
                "challenger_execution_enabled":False,
                "promotion_enabled":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            self.report_json.write_text(
                json.dumps(result,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            return result

        index=self._comparison_index(comparisons)
        existing=self._existing_bound_keys()
        new_bound=0
        new_unbound=0
        duplicate_bindings=0
        bound_rows=[]

        for outcome in outcomes:
            feature=outcome.get("feature_binding") or {}
            sid=str(feature.get("snapshot_id") or "")
            symbol=str(outcome.get("symbol") or "").upper()
            matches=index.get(sid) or []
            if not matches:
                row={
                    "status":"UNBOUND_OUTCOME_NO_MATCHING_V2_2_5_SNAPSHOT",
                    "round_trip_id":outcome.get("round_trip_id"),
                    "symbol":symbol,
                    "feature_snapshot_id":sid or None,
                    "reason":"NO_EXACT_FEATURE_SNAPSHOT_COMPARISON",
                    "counterfactual_pnl_fabricated":False,
                }
                with self.unbound_ledger.open("a",encoding="utf-8") as f:
                    f.write(json.dumps(row,sort_keys=True)+"\n")
                new_unbound+=1
                continue

            # Multiple comparison rows for same snapshot may exist from policy
            # registry evolution. Bind each distinct comparison_id explicitly.
            for comparison in matches:
                policy_rows=self._symbol_policy_rows(comparison,symbol)
                if not policy_rows:
                    row={
                        "status":"UNBOUND_OUTCOME_SYMBOL_NOT_IN_COMPARISON",
                        "round_trip_id":outcome.get("round_trip_id"),
                        "symbol":symbol,
                        "feature_snapshot_id":sid,
                        "comparison_id":comparison.get("comparison_id"),
                        "reason":"SYMBOL_NOT_FOUND",
                        "counterfactual_pnl_fabricated":False,
                    }
                    with self.unbound_ledger.open("a",encoding="utf-8") as f:
                        f.write(json.dumps(row,sort_keys=True)+"\n")
                    new_unbound+=1
                    continue

                for pr in policy_rows:
                    policy=pr["challenger_policy"]
                    sc=pr["symbol_comparison"]
                    pid=str(policy.get("policy_id") or "UNKNOWN_CHALLENGER")
                    binding_key=_sha({
                        "round_trip_id":outcome.get("round_trip_id"),
                        "comparison_id":comparison.get("comparison_id"),
                        "policy_id":pid,
                        "symbol":symbol,
                    })
                    if binding_key in existing:
                        duplicate_bindings+=1
                        continue

                    classification=str(sc.get("classification") or "UNKNOWN")
                    base=self._outcome_base(outcome)
                    row={
                        "stage":
                            "AI_TRADING_ENGINE_V2_2_6_CHAMPION_CHALLENGER_OUTCOME_COMPARATOR",
                        "status":"BOUND_REALIZED_POLICY_OUTCOME",
                        "binding_key":binding_key,
                        "comparison_id":comparison.get("comparison_id"),
                        "feature_snapshot_id":sid,
                        "feature_observed_at_utc":
                            comparison.get("feature_observed_at_utc"),
                        "policy_source":comparison.get("policy_source"),
                        "challenger_policy":policy,
                        "classification":classification,
                        "actual_outcome":base,
                        "realized_outcome_available":True,
                        "counterfactual_outcome":None,
                        "counterfactual_pnl_fabricated":False,
                        "challenger_execution_enabled":False,
                        "promotion_enabled":False,
                        "execution_selector_modified":False,
                        "broker_network_used":False,
                        "paper_orders_submitted":0,
                        "live_orders_submitted":0,
                    }
                    row["bound_record_sha256"]=_sha(row)
                    with self.bound_ledger.open("a",encoding="utf-8") as f:
                        f.write(
                            json.dumps(
                                row,
                                sort_keys=True,
                                ensure_ascii=False,
                            )+"\n"
                        )
                    self.latest.write_text(
                        json.dumps(
                            row,
                            indent=2,
                            sort_keys=True,
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                    existing.add(binding_key)
                    new_bound+=1
                    bound_rows.append(row)

        # Report uses all historical bound rows, not just this run.
        historical=self._read_jsonl(self.bound_ledger)
        per=defaultdict(lambda:{
            "both":[],
            "champion_only":[],
            "other_realized":[],
            "policy":None,
        })
        for row in historical:
            pid=str(
                (row.get("challenger_policy") or {}).get("policy_id")
                or "UNKNOWN_CHALLENGER"
            )
            per[pid]["policy"]=row.get("challenger_policy")
            a=row.get("actual_outcome") or {}
            metric_row={
                "label":str(a.get("label") or "UNKNOWN"),
                "pnl":_f(a.get("pnl")),
                "return_pct":_f(a.get("return_pct")),
            }
            cls=row.get("classification")
            if cls=="BOTH":
                per[pid]["both"].append(metric_row)
            elif cls=="CHAMPION_ONLY":
                per[pid]["champion_only"].append(metric_row)
            else:
                # Kept visible because realized Challenger-only outcomes should
                # not normally exist under Champion-only execution.
                per[pid]["other_realized"].append(metric_row)

        # Count all Challenger-only shadow signals from V2.2.5 independently
        # of realized outcomes. This is coverage, not P&L.
        challenger_only_counts=defaultdict(int)
        for comparison in comparisons:
            for comp in list(comparison.get("comparisons") or []):
                pid=str(
                    (comp.get("challenger_policy") or {}).get("policy_id")
                    or "UNKNOWN_CHALLENGER"
                )
                challenger_only_counts[pid]+=sum(
                    1 for row in list(comp.get("symbol_comparisons") or [])
                    if row.get("classification")=="CHALLENGER_ONLY"
                )

        per_report={}
        for pid,data in per.items():
            both=_metrics(data["both"])
            champion_only=_metrics(data["champion_only"])
            other=_metrics(data["other_realized"])
            realized_total=(
                both["trades"]
                +champion_only["trades"]
                +other["trades"]
            )
            per_report[pid]={
                "challenger_policy":data["policy"],
                "realized_both":both,
                "realized_champion_only":champion_only,
                "unexpected_other_realized":other,
                "realized_trade_outcomes":realized_total,
                "challenger_only_shadow_signal_count":
                    challenger_only_counts.get(pid,0),
                "challenger_only_realized_outcomes_available":False,
                "outcome_sample_qualified":
                    realized_total>=MIN_OUTCOME_SAMPLE,
                "minimum_outcome_sample":MIN_OUTCOME_SAMPLE,
                "promotion_evidence_ready":
                    realized_total>=MIN_OUTCOME_SAMPLE,
            }

        report={
            "stage":
                "AI_TRADING_ENGINE_V2_2_6_CHAMPION_CHALLENGER_OUTCOME_COMPARATOR",
            "status":"PASS_CHAMPION_CHALLENGER_OUTCOME_COMPARISON",
            "actual_outcomes":len(outcomes),
            "comparison_snapshots":len(comparisons),
            "bound_actual_outcomes":
                len({r.get("actual_outcome",{}).get("round_trip_id")
                     for r in historical}),
            "bound_policy_outcome_rows":len(historical),
            "unbound_actual_outcomes":new_unbound,
            "new_bound_policy_outcome_rows":new_bound,
            "duplicate_bindings":duplicate_bindings,
            "per_challenger":dict(per_report),
            "minimum_outcome_sample":MIN_OUTCOME_SAMPLE,
            "counterfactual_pnl_fabricated":False,
            "challenger_only_outcome_method":
                "NOT_AVAILABLE_UNTIL_SHADOW_EXECUTION_SIMULATION",
            "promotion_enabled":False,
            "challenger_execution_enabled":False,
            "execution_selector_modified":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
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
