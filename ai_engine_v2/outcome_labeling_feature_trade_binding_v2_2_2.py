from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


MAX_FEATURE_LAG_SECONDS = 1800


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(
            str(value).replace("Z","+00:00")
        ).astimezone(timezone.utc)
    except Exception:
        return None


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _sha256_payload(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",",":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


class OutcomeLabelingFeatureTradeBindingV222:
    """
    Read-only outcome labeling.

    Source labels:
      V2.1.27 completed Alpaca Paper round trips.

    Source features:
      V2.2.1 signal scoring + feature snapshot ledger.

    Binding:
      same symbol, closest feature snapshot at or before entry fill time,
      bounded by MAX_FEATURE_LAG_SECONDS.

    This stage does not recompute P&L and does not alter execution.
    """

    def __init__(self, root):
        self.root=Path(root)
        self.feature_ledger=(
            self.root/"runtime"/
            "ai_signal_scoring_feature_snapshot_v2_2_1"/
            "feature_snapshot_ledger.jsonl"
        )
        self.trade_ledger=(
            self.root/"runtime"/"final_round_trip_ledger_v2_1_27"/
            "completed_round_trips.jsonl"
        )
        self.runtime_dir=(
            self.root/"runtime"/
            "ai_outcome_labeling_feature_trade_binding_v2_2_2"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.outcome_ledger=self.runtime_dir/"labeled_outcomes.jsonl"
        self.unbound_ledger=self.runtime_dir/"unbound_outcomes.jsonl"
        self.latest=self.runtime_dir/"latest_outcome_binding.json"
        self.summary=self.runtime_dir/"latest_binding_summary.json"

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

    def _existing_round_trip_ids(self):
        out=set()
        for row in self._read_jsonl(self.outcome_ledger):
            rid=str(row.get("round_trip_id") or "").strip()
            if rid:
                out.add(rid)
        for row in self._read_jsonl(self.unbound_ledger):
            rid=str(row.get("round_trip_id") or "").strip()
            if rid:
                out.add(rid)
        return out

    @staticmethod
    def _label_trade(trade):
        pnl=_decimal(trade.get("gross_pnl_from_fills"))
        ret=_decimal(trade.get("return_pct_from_fills"))
        if pnl is None or ret is None:
            return None
        if pnl>0:
            label="WIN"
        elif pnl<0:
            label="LOSS"
        else:
            label="FLAT"
        return {
            "outcome_label":label,
            "gross_pnl_from_fills":str(pnl),
            "return_pct_from_fills":str(ret),
            "holding_seconds":trade.get("holding_seconds"),
            "exit_reason":(
                (trade.get("exit") or {}).get("reason")
            ),
            "fees_included":bool(trade.get("fees_included",False)),
            "pnl_semantics":trade.get("pnl_semantics"),
        }

    @staticmethod
    def _feature_candidates(feature_rows, symbol):
        out=[]
        sym=str(symbol or "").upper()
        for snapshot in feature_rows:
            observed=_dt(snapshot.get("observed_at_utc"))
            if observed is None:
                continue
            for item in list(snapshot.get("symbol_rows") or []):
                if str(item.get("symbol") or "").upper()!=sym:
                    continue
                out.append({
                    "observed_at":observed,
                    "snapshot_id":snapshot.get("snapshot_id"),
                    "source_snapshot_sha256":
                        snapshot.get("source_snapshot_sha256"),
                    "symbol_row":item,
                })
        out.sort(key=lambda x:x["observed_at"])
        return out

    def _bind_feature(self, feature_rows, trade):
        symbol=str(trade.get("symbol") or "").upper()
        entry=trade.get("entry") or {}
        entry_time=_dt(entry.get("filled_at"))
        if entry_time is None:
            return None,"ENTRY_FILLED_AT_MISSING_OR_INVALID"

        candidates=self._feature_candidates(feature_rows,symbol)
        preceding=[
            row for row in candidates
            if row["observed_at"]<=entry_time
        ]
        if not preceding:
            return None,"NO_PRE_ENTRY_FEATURE_SNAPSHOT"

        best=max(preceding,key=lambda x:x["observed_at"])
        lag=(entry_time-best["observed_at"]).total_seconds()
        if lag>MAX_FEATURE_LAG_SECONDS:
            return None,"FEATURE_SNAPSHOT_TOO_OLD"

        item=best["symbol_row"]
        return {
            "binding_method":
                "SAME_SYMBOL_CLOSEST_PRE_ENTRY_SNAPSHOT",
            "feature_observed_at_utc":
                best["observed_at"].isoformat(),
            "entry_filled_at_utc":entry_time.isoformat(),
            "feature_lag_seconds":lag,
            "max_feature_lag_seconds":MAX_FEATURE_LAG_SECONDS,
            "snapshot_id":best["snapshot_id"],
            "source_snapshot_sha256":
                best["source_snapshot_sha256"],
            "canonical_analysis_sha256":
                item.get("canonical_analysis_sha256"),
            "shadow_quality_score":
                item.get("quality_score_shadow"),
            "action":item.get("action"),
            "consensus_score":item.get("consensus_score"),
            "trend_alignment":item.get("trend_alignment"),
            "market_regime":item.get("market_regime"),
            "dominant_structure":item.get("dominant_structure"),
            "probability":item.get("probability"),
            "expected_return":item.get("expected_return"),
            "expected_risk":item.get("expected_risk"),
            "reward_risk":item.get("reward_risk"),
            "confidence_calibration":
                item.get("confidence_calibration"),
            "timeframe_consensus":
                item.get("timeframe_consensus"),
            "selector_explanation":
                item.get("selector_explanation"),
            "timeframes":item.get("timeframes"),
        },None

    def _write_summary(self,row):
        self.summary.write_text(
            json.dumps(
                row,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )
        return row

    def build(self):
        if not self.trade_ledger.exists():
            return self._write_summary({
                "status":"WAITING_FOR_V2_1_27_COMPLETED_ROUND_TRIPS",
                "completed_trade_rows":0,
                "feature_snapshot_rows":0,
                "new_labeled_outcomes":0,
                "new_unbound_outcomes":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        trades=self._read_jsonl(self.trade_ledger)
        if not trades:
            return self._write_summary({
                "status":"WAITING_FOR_V2_1_27_COMPLETED_ROUND_TRIPS",
                "completed_trade_rows":0,
                "feature_snapshot_rows":0,
                "new_labeled_outcomes":0,
                "new_unbound_outcomes":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        features=self._read_jsonl(self.feature_ledger)
        if not features:
            return self._write_summary({
                "status":"WAITING_FOR_V2_2_1_FEATURE_SNAPSHOTS",
                "completed_trade_rows":len(trades),
                "feature_snapshot_rows":0,
                "new_labeled_outcomes":0,
                "new_unbound_outcomes":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        existing=self._existing_round_trip_ids()
        labeled=unbound=duplicates=invalid=0
        latest=None

        for trade in trades:
            rid=str(trade.get("round_trip_id") or "").strip()
            if not rid:
                invalid+=1
                continue
            if rid in existing:
                duplicates+=1
                continue

            label=self._label_trade(trade)
            if label is None:
                invalid+=1
                continue

            feature,error=self._bind_feature(features,trade)
            base={
                "stage":
                    "AI_TRADING_ENGINE_V2_2_2_OUTCOME_LABELING_FEATURE_TRADE_BINDING",
                "round_trip_id":rid,
                "evidence_key":trade.get("evidence_key"),
                "symbol":str(trade.get("symbol") or "").upper(),
                "trade_source_stage":trade.get("stage"),
                "trade_source_status":trade.get("status"),
                "trade_source_sha256":_sha256_payload(trade),
                "outcome":label,
                "pnl_recomputed":False,
                "feature_engine_modified":False,
                "execution_selector_modified":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }

            if error:
                row={
                    **base,
                    "status":"UNBOUND_COMPLETED_OUTCOME",
                    "binding_error":error,
                    "feature_binding":None,
                }
                with self.unbound_ledger.open(
                    "a",encoding="utf-8"
                ) as f:
                    f.write(json.dumps(
                        row,
                        sort_keys=True,
                        ensure_ascii=False,
                        default=str,
                    )+"\n")
                unbound+=1
            else:
                row={
                    **base,
                    "status":"LABELED_BOUND_PAPER_OUTCOME",
                    "binding_error":None,
                    "feature_binding":feature,
                }
                row["training_record_sha256"]=_sha256_payload(row)
                with self.outcome_ledger.open(
                    "a",encoding="utf-8"
                ) as f:
                    f.write(json.dumps(
                        row,
                        sort_keys=True,
                        ensure_ascii=False,
                        default=str,
                    )+"\n")
                self.latest.write_text(
                    json.dumps(
                        row,
                        indent=2,
                        sort_keys=True,
                        ensure_ascii=False,
                        default=str,
                    ),
                    encoding="utf-8",
                )
                labeled+=1
                latest=row

            existing.add(rid)

        return self._write_summary({
            "status":"PASS_OUTCOME_LABELING_FEATURE_TRADE_BINDING",
            "completed_trade_rows":len(trades),
            "feature_snapshot_rows":len(features),
            "new_labeled_outcomes":labeled,
            "new_unbound_outcomes":unbound,
            "duplicate_round_trips":duplicates,
            "invalid_trade_rows":invalid,
            "total_existing_outcome_ids":len(existing),
            "latest_bound_round_trip_id":(
                None if latest is None else latest["round_trip_id"]
            ),
            "outcome_ledger":str(self.outcome_ledger),
            "unbound_ledger":str(self.unbound_ledger),
            "pnl_recomputed":False,
            "feature_engine_modified":False,
            "execution_selector_modified":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })
