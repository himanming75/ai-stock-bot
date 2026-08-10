from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .fast_data_acceleration_v2_2_8 import FastDataAccelerationV228


def _dt(value):
    d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if d.tzinfo is None:
        d=d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(
        json.dumps(value,indent=2,sort_keys=True,default=str),
        encoding="utf-8",
    )
    os.replace(tmp,path)


def _read_jsonl(path):
    out=[]
    if not path.exists():
        return out
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _append_jsonl(path,rows):
    if not rows:
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")


def _sha(payload):
    return hashlib.sha256(
        json.dumps(
            payload,sort_keys=True,separators=(",",":"),default=str
        ).encode("utf-8")
    ).hexdigest()


def _finite(v):
    try:
        return math.isfinite(float(v))
    except (TypeError,ValueError):
        return False


class MLPredictionOutcomeResolverV2212:
    """
    Resolve V2.2.11 shadow predictions against later real market bars.

    Research-only. Does not alter selectors, thresholds, models, promotion,
    broker state, Paper orders, or Live orders.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.fast=FastDataAccelerationV228(self.root)
        self.inference_runtime=(
            self.root/"runtime"/"ai_ml_shadow_inference_v2_2_11"
        )
        self.inference_ledger=(
            self.inference_runtime/"ml_shadow_inference_ledger.jsonl"
        )
        self.runtime=(
            self.root/"runtime"/"ai_ml_prediction_outcome_v2_2_12"
        )
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.outcome_ledger=self.runtime/"ml_prediction_outcome_ledger.jsonl"
        self.latest=self.runtime/"latest_ml_prediction_outcome.json"
        self.metrics=self.runtime/"latest_ml_prediction_metrics.json"

    def preflight(self):
        missing=[]
        if not self.inference_ledger.exists():
            missing.append(str(self.inference_ledger))
        if not self.fast.raw_bars.exists():
            missing.append(str(self.fast.raw_bars))
        result={
            "status":(
                "PASS_ML_PREDICTION_OUTCOME_PREFLIGHT"
                if not missing
                else "WAITING_FOR_V2_2_11_INFERENCE_AND_MARKET_BARS"
            ),
            "missing":missing,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
            "execution_selector_modified":False,
            "automatic_promotion":False,
            "live_trading":False,
        }
        _atomic_json(self.latest,result)
        return result

    def _market_index(self):
        grouped=defaultdict(dict)
        for source in (self.fast.raw_bars,self.fast.live_ledger):
            for row in _read_jsonl(source):
                symbol=str(row.get("symbol") or "").upper()
                ts=row.get("timestamp")
                close=row.get("close")
                if not symbol or not ts or not _finite(close) or float(close)<=0:
                    continue
                grouped[symbol][str(ts)]={
                    "timestamp":str(ts),
                    "dt":_dt(ts),
                    "close":float(close),
                    "feed":row.get("feed"),
                }
        out={}
        for symbol,by_ts in grouped.items():
            rows=sorted(by_ts.values(),key=lambda x:x["dt"])
            out[symbol]=rows
        return out

    @staticmethod
    def _future_mark(rows,target,tolerance_minutes=2):
        # First bar at/after target, but never farther than tolerance.
        for row in rows:
            if row["dt"] < target:
                continue
            lag=(row["dt"]-target).total_seconds()/60.0
            if lag<=float(tolerance_minutes):
                return row,lag
            return None,None
        return None,None

    def _existing_keys(self):
        keys=set()
        for row in _read_jsonl(self.outcome_ledger):
            if row.get("outcome_id"):
                keys.add(row["outcome_id"])
        return keys

    @staticmethod
    def _direction(ret,deadband=0.02):
        if ret>deadband:
            return "UP"
        if ret<-deadband:
            return "DOWN"
        return "FLAT"

    def resolve(self):
        pre=self.preflight()
        if pre["status"]!="PASS_ML_PREDICTION_OUTCOME_PREFLIGHT":
            return pre

        market=self._market_index()
        existing=self._existing_keys()
        new_rows=[]
        waiting=0
        candidates=0

        for inf in _read_jsonl(self.inference_ledger):
            inference_id=inf.get("inference_id")
            for srow in list(inf.get("symbol_predictions") or []):
                symbol=str(srow.get("symbol") or "").upper()
                feature_ts=srow.get("feature_timestamp")
                feature_values=srow.get("feature_values") or {}
                entry_close=None
                # V2.2.11 feature rows are sourced from V2.2.8.1 rows; locate
                # exact entry close from market index by timestamp.
                rows=market.get(symbol,[])
                entry_dt=_dt(feature_ts) if feature_ts else None
                if entry_dt is None:
                    continue
                for r in rows:
                    if r["dt"]==entry_dt:
                        entry_close=r["close"]
                        break
                if not entry_close or entry_close<=0:
                    continue

                for hkey,pred in (srow.get("predictions") or {}).items():
                    try:
                        minutes=int(str(hkey).replace("m",""))
                    except Exception:
                        continue
                    candidates+=1
                    target=entry_dt+timedelta(minutes=minutes)
                    mark,lag=self._future_mark(rows,target,2)
                    if mark is None:
                        waiting+=1
                        continue
                    ret=(mark["close"]/entry_close-1.0)*100.0
                    actual=self._direction(ret)
                    predicted=str(pred.get("predicted_direction") or "")
                    correct=(predicted==actual)
                    identity={
                        "inference_id":inference_id,
                        "symbol":symbol,
                        "feature_timestamp":feature_ts,
                        "horizon":hkey,
                    }
                    oid=_sha(identity)
                    if oid in existing:
                        continue
                    row={
                        "stage":"AI_TRADING_ENGINE_V2_2_12_ML_PREDICTION_OUTCOME",
                        "outcome_id":oid,
                        "resolved_at_utc":_utcnow(),
                        "inference_id":inference_id,
                        "symbol":symbol,
                        "feature_timestamp":feature_ts,
                        "target_timestamp_utc":target.isoformat(),
                        "actual_mark_timestamp":mark["timestamp"],
                        "mark_lag_minutes":round(float(lag),6),
                        "horizon":hkey,
                        "horizon_minutes":minutes,
                        "entry_close":entry_close,
                        "outcome_close":mark["close"],
                        "forward_return_pct":round(ret,8),
                        "predicted_direction":predicted,
                        "actual_direction":actual,
                        "direction_correct":bool(correct),
                        "prediction_confidence":pred.get(
                            "prediction_confidence"
                        ),
                        "class_probabilities":pred.get(
                            "class_probabilities"
                        ),
                        "selected_model":pred.get("selected_model"),
                        "edge_ready":bool(pred.get("edge_ready")),
                        "feature_values":feature_values,
                        "shadow_only":True,
                        "broker_network_used":False,
                        "paper_orders_submitted":0,
                        "live_orders_submitted":0,
                        "execution_selector_modified":False,
                        "automatic_promotion":False,
                        "live_trading":False,
                    }
                    new_rows.append(row)
                    existing.add(oid)

        _append_jsonl(self.outcome_ledger,new_rows)
        metrics=self.build_metrics()
        result={
            "stage":"AI_TRADING_ENGINE_V2_2_12_ML_PREDICTION_OUTCOME",
            "status":"PASS_ML_PREDICTION_OUTCOME_RESOLUTION",
            "candidate_predictions":candidates,
            "new_resolved_outcomes":len(new_rows),
            "waiting_for_future_marks":waiting,
            "total_resolved_outcomes":metrics["total_resolved_outcomes"],
            "horizon_metrics":metrics["horizons"],
            "shadow_only":True,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
            "execution_selector_modified":False,
            "automatic_promotion":False,
            "live_trading":False,
        }
        _atomic_json(self.latest,result)
        return result

    def build_metrics(self):
        rows=_read_jsonl(self.outcome_ledger)
        by_h=defaultdict(list)
        for row in rows:
            by_h[str(row.get("horizon"))].append(row)

        horizons={}
        for hkey,hrows in sorted(
            by_h.items(),
            key=lambda kv:int(str(kv[0]).replace("m",""))
        ):
            n=len(hrows)
            correct=sum(1 for r in hrows if r.get("direction_correct"))
            pred_counts=Counter(
                str(r.get("predicted_direction")) for r in hrows
            )
            actual_counts=Counter(
                str(r.get("actual_direction")) for r in hrows
            )
            confident=[
                r for r in hrows
                if _finite(r.get("prediction_confidence"))
            ]
            avg_conf=(
                None if not confident
                else sum(float(r["prediction_confidence"]) for r in confident)
                    /len(confident)
            )
            edge=[r for r in hrows if r.get("edge_ready")]
            edge_correct=sum(1 for r in edge if r.get("direction_correct"))
            horizons[hkey]={
                "resolved_count":n,
                "direction_accuracy_pct":(
                    None if not n else round(correct/n*100.0,6)
                ),
                "average_prediction_confidence":(
                    None if avg_conf is None else round(avg_conf,8)
                ),
                "predicted_direction_counts":dict(
                    sorted(pred_counts.items())
                ),
                "actual_direction_counts":dict(
                    sorted(actual_counts.items())
                ),
                "edge_ready_count":len(edge),
                "edge_ready_accuracy_pct":(
                    None if not edge
                    else round(edge_correct/len(edge)*100.0,6)
                ),
            }

        result={
            "stage":"AI_TRADING_ENGINE_V2_2_12_ML_PREDICTION_METRICS",
            "status":"PASS_ML_PREDICTION_METRICS",
            "generated_at_utc":_utcnow(),
            "total_resolved_outcomes":len(rows),
            "horizons":horizons,
            "research_only":True,
            "selector_change_recommendation_enabled":False,
            "model_promotion_enabled":False,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic_json(self.metrics,result)
        return result

    def status(self):
        if self.latest.exists():
            try:
                return json.loads(self.latest.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self.preflight()
