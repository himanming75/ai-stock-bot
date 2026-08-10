from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from paper_position_lifecycle.rules import evaluate_exit


DEFAULT_MAX_HOLD_SECONDS = 3600
MINIMUM_FUTURE_MARKS = 1


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(
            str(value).replace("Z","+00:00")
        ).astimezone(timezone.utc)
    except Exception:
        return None


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


class ChallengerShadowExecutionSimulatorV227:
    """
    Pure-local counterfactual simulator for V2.2.5 CHALLENGER_ONLY signals.

    Price path:
      sequential V2.2.1 feature snapshots for the same symbol, using the
      canonical 1m feature close as the mark.

    Exit policy:
      existing paper_position_lifecycle.rules.evaluate_exit.

    No broker/network/order activity occurs in this stage.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.feature_ledger=(
            self.root/"runtime"/
            "ai_signal_scoring_feature_snapshot_v2_2_1"/
            "feature_snapshot_ledger.jsonl"
        )
        self.comparison_ledger=(
            self.root/"runtime"/
            "ai_champion_challenger_shadow_comparator_v2_2_5"/
            "comparison_ledger.jsonl"
        )
        self.policy_path=(
            self.root/"release"/"v95_33_to_v95_64"/"input"/
            "position_lifecycle_policy.json"
        )
        self.runtime_dir=(
            self.root/"runtime"/
            "ai_challenger_shadow_execution_simulator_v2_2_7"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.open_ledger=self.runtime_dir/"open_shadow_positions.jsonl"
        self.completed_ledger=self.runtime_dir/"completed_shadow_round_trips.jsonl"
        self.latest=self.runtime_dir/"latest_shadow_simulation.json"
        self.summary=self.runtime_dir/"latest_shadow_simulation_summary.json"

    @staticmethod
    def _read_jsonl(path):
        rows=[]
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    @staticmethod
    def _one_min_close(symbol_row):
        for tf in list(symbol_row.get("timeframes") or []):
            if str(tf.get("timeframe") or "").lower()=="1m":
                features=tf.get("features") or {}
                close=_f(features.get("close"))
                return close if close>0 else None
        return None

    def _feature_index(self):
        by_symbol={}
        by_snapshot={}
        for snap in self._read_jsonl(self.feature_ledger):
            sid=str(snap.get("snapshot_id") or "")
            observed=_dt(snap.get("observed_at_utc"))
            if not sid or observed is None:
                continue
            by_snapshot[sid]=snap
            for row in list(snap.get("symbol_rows") or []):
                symbol=str(row.get("symbol") or "").upper()
                close=self._one_min_close(row)
                if not symbol or close is None:
                    continue
                by_symbol.setdefault(symbol,[]).append({
                    "snapshot_id":sid,
                    "observed_at":observed,
                    "close":close,
                    "row":row,
                })
        for symbol in by_symbol:
            by_symbol[symbol].sort(key=lambda x:x["observed_at"])
        return by_symbol,by_snapshot

    def _existing_keys(self):
        keys=set()
        for path in (self.open_ledger,self.completed_ledger):
            for row in self._read_jsonl(path):
                if row.get("simulation_key"):
                    keys.add(row["simulation_key"])
        return keys

    def _challenger_only_signals(self):
        out=[]
        for comparison in self._read_jsonl(self.comparison_ledger):
            sid=str(comparison.get("feature_snapshot_id") or "")
            observed=_dt(comparison.get("feature_observed_at_utc"))
            if not sid or observed is None:
                continue
            for comp in list(comparison.get("comparisons") or []):
                policy=dict(comp.get("challenger_policy") or {})
                pid=str(policy.get("policy_id") or "UNKNOWN_CHALLENGER")
                for row in list(comp.get("symbol_comparisons") or []):
                    if row.get("classification")!="CHALLENGER_ONLY":
                        continue
                    action=str(row.get("action") or "").upper()
                    if action not in {"BUY","SELL"}:
                        continue
                    symbol=str(row.get("symbol") or "").upper()
                    out.append({
                        "comparison_id":comparison.get("comparison_id"),
                        "feature_snapshot_id":sid,
                        "signal_time":observed,
                        "policy_source":comparison.get("policy_source"),
                        "challenger_policy":policy,
                        "policy_id":pid,
                        "symbol":symbol,
                        "action":action,
                        "quality_score_shadow":
                            row.get("quality_score_shadow"),
                        "canonical_analysis_sha256":
                            row.get("canonical_analysis_sha256"),
                    })
        return out

    @staticmethod
    def _policy_for_shadow(raw):
        # Existing evaluator expects percentage values and holding days.
        # Keep the repo policy exactly as configured.
        return dict(raw)

    @staticmethod
    def _signed_pnl(action,entry,exit_price,qty=1.0):
        if action=="BUY":
            return (exit_price-entry)*qty
        return (entry-exit_price)*qty

    @staticmethod
    def _signed_return_pct(action,entry,exit_price):
        if entry<=0:
            return 0.0
        if action=="BUY":
            return (exit_price/entry-1.0)*100.0
        return (entry/exit_price-1.0)*100.0 if exit_price>0 else 0.0

    @staticmethod
    def _adapt_mark_for_short(action,entry,mark):
        """
        evaluate_exit is long-oriented. For a SELL shadow position, map the
        short return path into an equivalent synthetic long mark while keeping
        the existing stop/take/trailing thresholds unchanged.
        """
        if action=="BUY":
            return mark
        if mark<=0 or entry<=0:
            return mark
        short_return=(entry/mark)-1.0
        return entry*(1.0+short_return)

    def _simulate_one(self,signal,marks,policy):
        signal_time=signal["signal_time"]
        usable=[m for m in marks if m["observed_at"]>=signal_time]
        if len(usable)<MINIMUM_FUTURE_MARKS:
            return None,"WAITING_FOR_FUTURE_PRICE_MARKS"

        entry_mark=usable[0]
        entry_price=entry_mark["close"]
        if entry_price<=0:
            return None,"INVALID_ENTRY_PRICE"

        high_water=entry_price
        final=None
        exit_reason=None
        exit_decision=None

        for mark in usable[1:]:
            elapsed=(mark["observed_at"]-entry_mark["observed_at"]).total_seconds()
            if elapsed<0:
                continue

            synthetic_mark=self._adapt_mark_for_short(
                signal["action"],entry_price,mark["close"]
            )
            high_water=max(high_water,synthetic_mark)

            decision=evaluate_exit(
                {"average_cost":entry_price,"quantity":1.0},
                synthetic_mark,
                0,
                high_water,
                policy,
            )
            if decision.get("action")=="EXIT":
                final=mark
                exit_reason=decision.get("reason")
                exit_decision=decision
                break

            if elapsed>=DEFAULT_MAX_HOLD_SECONDS:
                final=mark
                exit_reason="SHADOW_MAX_HOLD_SECONDS"
                exit_decision={
                    "action":"EXIT",
                    "reason":exit_reason,
                }
                break

        if final is None:
            return {
                "status":"OPEN_CHALLENGER_SHADOW_POSITION",
                "entry_snapshot_id":entry_mark["snapshot_id"],
                "entry_time_utc":entry_mark["observed_at"].isoformat(),
                "entry_price":entry_price,
                "latest_mark_snapshot_id":usable[-1]["snapshot_id"],
                "latest_mark_time_utc":usable[-1]["observed_at"].isoformat(),
                "latest_mark_price":usable[-1]["close"],
                "future_marks_observed":max(0,len(usable)-1),
            },None

        exit_price=final["close"]
        pnl=self._signed_pnl(
            signal["action"],entry_price,exit_price,1.0
        )
        ret=self._signed_return_pct(
            signal["action"],entry_price,exit_price
        )
        holding_seconds=(
            final["observed_at"]-entry_mark["observed_at"]
        ).total_seconds()

        return {
            "status":"COMPLETED_CHALLENGER_SHADOW_ROUND_TRIP",
            "entry_snapshot_id":entry_mark["snapshot_id"],
            "entry_time_utc":entry_mark["observed_at"].isoformat(),
            "entry_price":round(entry_price,8),
            "exit_snapshot_id":final["snapshot_id"],
            "exit_time_utc":final["observed_at"].isoformat(),
            "exit_price":round(exit_price,8),
            "holding_seconds":holding_seconds,
            "exit_reason":exit_reason,
            "exit_decision":exit_decision,
            "quantity":1.0,
            "gross_pnl_before_fees":round(pnl,8),
            "return_pct":round(ret,6),
            "fees_included":False,
            "slippage_included":False,
            "simulation_price_semantics":
                "V2_2_1_CANONICAL_1M_FEATURE_CLOSE",
        },None

    def build(self):
        if not self.comparison_ledger.exists():
            return self._write_summary({
                "status":"WAITING_FOR_V2_2_5_COMPARISON_LEDGER",
                "challenger_only_signals":0,
                "new_completed_shadow_round_trips":0,
                "new_open_shadow_positions":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })
        if not self.feature_ledger.exists():
            return self._write_summary({
                "status":"WAITING_FOR_V2_2_1_FEATURE_LEDGER",
                "challenger_only_signals":0,
                "new_completed_shadow_round_trips":0,
                "new_open_shadow_positions":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })
        if not self.policy_path.exists():
            return self._write_summary({
                "status":"BLOCKED_EXISTING_POSITION_LIFECYCLE_POLICY_MISSING",
                "challenger_only_signals":0,
                "new_completed_shadow_round_trips":0,
                "new_open_shadow_positions":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        raw_policy=json.loads(
            self.policy_path.read_text(encoding="utf-8-sig")
        )
        policy=self._policy_for_shadow(raw_policy)
        by_symbol,_=self._feature_index()
        signals=self._challenger_only_signals()
        existing=self._existing_keys()

        completed=0
        opened=0
        waiting=0
        duplicates=0
        latest=None

        for signal in signals:
            sim_key=_sha({
                "comparison_id":signal["comparison_id"],
                "policy_id":signal["policy_id"],
                "symbol":signal["symbol"],
                "action":signal["action"],
                "feature_snapshot_id":signal["feature_snapshot_id"],
            })
            if sim_key in existing:
                duplicates+=1
                continue

            marks=by_symbol.get(signal["symbol"],[])
            result,error=self._simulate_one(signal,marks,policy)
            if error:
                waiting+=1
                continue

            row={
                "stage":
                    "AI_TRADING_ENGINE_V2_2_7_CHALLENGER_SHADOW_EXECUTION_SIMULATOR",
                "simulation_key":sim_key,
                "comparison_id":signal["comparison_id"],
                "source_feature_snapshot_id":
                    signal["feature_snapshot_id"],
                "policy_source":signal["policy_source"],
                "challenger_policy":signal["challenger_policy"],
                "policy_id":signal["policy_id"],
                "symbol":signal["symbol"],
                "action":signal["action"],
                "quality_score_shadow":
                    signal["quality_score_shadow"],
                "canonical_analysis_sha256":
                    signal["canonical_analysis_sha256"],
                "simulation":result,
                "position_lifecycle_policy":policy,
                "existing_exit_rule_reused":
                    "paper_position_lifecycle.rules.evaluate_exit",
                "counterfactual_only":True,
                "actual_broker_fill":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            row["record_sha256"]=_sha(row)

            if result["status"]=="COMPLETED_CHALLENGER_SHADOW_ROUND_TRIP":
                with self.completed_ledger.open("a",encoding="utf-8") as f:
                    f.write(json.dumps(
                        row,sort_keys=True,ensure_ascii=False,default=str
                    )+"\n")
                completed+=1
            else:
                with self.open_ledger.open("a",encoding="utf-8") as f:
                    f.write(json.dumps(
                        row,sort_keys=True,ensure_ascii=False,default=str
                    )+"\n")
                opened+=1

            existing.add(sim_key)
            latest=row

        if latest is not None:
            self.latest.write_text(
                json.dumps(
                    latest,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str,
                ),
                encoding="utf-8",
            )

        return self._write_summary({
            "status":"PASS_CHALLENGER_SHADOW_EXECUTION_SIMULATION",
            "challenger_only_signals":len(signals),
            "new_completed_shadow_round_trips":completed,
            "new_open_shadow_positions":opened,
            "waiting_for_future_marks":waiting,
            "duplicate_simulations":duplicates,
            "existing_exit_rule_reused":True,
            "price_source":"V2_2_1_CANONICAL_1M_FEATURE_CLOSE",
            "counterfactual_only":True,
            "actual_broker_fills":0,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })

    def _write_summary(self,row):
        self.summary.write_text(
            json.dumps(
                row,indent=2,sort_keys=True,ensure_ascii=False,default=str
            ),
            encoding="utf-8",
        )
        return row
