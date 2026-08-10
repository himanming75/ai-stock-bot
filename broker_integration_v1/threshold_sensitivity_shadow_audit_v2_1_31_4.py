from __future__ import annotations

import bisect
import json
import math
import os
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_dt(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _finite(v):
    try:
        return math.isfinite(float(v))
    except (TypeError,ValueError):
        return False


def _atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(tmp,path)


class ThresholdSensitivityShadowAuditV21314:
    """
    Read-only threshold audit over existing V2.2.1 canonical feature snapshots.

    It does not call a broker, submit an order, or mutate the live selector.
    Outcomes are snapshot-to-snapshot signed price returns, NOT broker P&L.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.policy_path=(
            self.root/"release"/
            "broker_integration_v2_1_31_4_threshold_sensitivity_shadow_audit"/
            "config"/"threshold_sensitivity_policy.json"
        )
        self.feature_ledger=(
            self.root/"runtime"/
            "ai_signal_scoring_feature_snapshot_v2_2_1"/
            "feature_snapshot_ledger.jsonl"
        )
        self.runtime=(
            self.root/"runtime"/
            "threshold_sensitivity_shadow_audit_v2_1_31_4"
        )
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_threshold_sensitivity_audit.json"
        self.signal_ledger=self.runtime/"threshold_signal_ledger.jsonl"

    def policy(self):
        p=json.loads(self.policy_path.read_text(encoding="utf-8-sig"))
        th=[float(x) for x in p["confidence_thresholds"]]
        if th != sorted(th) or len(set(th))!=len(th):
            raise RuntimeError("INVALID_CONFIDENCE_THRESHOLD_GRID")
        if 0.75 not in th:
            raise RuntimeError("CURRENT_THRESHOLD_075_MUST_BE_PRESENT")
        if float(p["actual_execution_threshold_unchanged"]) != 0.75:
            raise RuntimeError("ACTUAL_THRESHOLD_GUARD_CHANGED")
        if p.get("actual_execution_threshold_modified") is not False:
            raise RuntimeError("ACTUAL_THRESHOLD_MODIFICATION_FORBIDDEN")
        return p

    @staticmethod
    def _read_jsonl(path):
        if not path.exists():
            return []
        rows=[]
        with path.open("r",encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows

    @staticmethod
    def _confidence(src):
        ex=dict(src.get("selector_explanation") or {})
        inp=dict(ex.get("current_selector_inputs") or {})
        if _finite(inp.get("calibrated_confidence")):
            return float(inp["calibrated_confidence"])
        cal=dict(src.get("confidence_calibration") or {})
        return float(cal.get("calibrated_confidence",0.0))

    @staticmethod
    def _rr(src):
        ex=dict(src.get("selector_explanation") or {})
        inp=dict(ex.get("current_selector_inputs") or {})
        if _finite(inp.get("reward_risk")):
            return float(inp["reward_risk"])
        return float(src.get("reward_risk",0.0) or 0.0)

    @staticmethod
    def _action(src):
        ex=dict(src.get("selector_explanation") or {})
        inp=dict(ex.get("current_selector_inputs") or {})
        return str(inp.get("action") or src.get("action") or "HOLD").upper()

    @staticmethod
    def _price(src):
        # Prefer 1m; otherwise shortest available timeframe close.
        candidates=[]
        for tf in list(src.get("timeframes") or []):
            features=dict(tf.get("features") or {})
            close=features.get("close")
            if not _finite(close) or float(close)<=0:
                continue
            name=str(tf.get("timeframe") or "")
            rank={"1m":1,"5m":5,"15m":15,"30m":30,"60m":60}.get(name,999)
            candidates.append((rank,float(close),name))
        if not candidates:
            return None,None
        candidates.sort(key=lambda x:x[0])
        return candidates[0][1],candidates[0][2]

    def _points(self):
        snapshots=self._read_jsonl(self.feature_ledger)
        points=[]
        for snap in snapshots:
            ts=snap.get("observed_at_utc")
            if not ts:
                continue
            try:
                dt=_parse_dt(ts)
            except Exception:
                continue
            for src in list(snap.get("symbol_rows") or []):
                price,price_tf=self._price(src)
                symbol=str(src.get("symbol") or "").upper()
                if not symbol or price is None:
                    continue
                points.append({
                    "timestamp":dt,
                    "timestamp_iso":dt.isoformat().replace("+00:00","Z"),
                    "snapshot_id":snap.get("snapshot_id"),
                    "symbol":symbol,
                    "action":self._action(src),
                    "confidence":self._confidence(src),
                    "reward_risk":self._rr(src),
                    "price":price,
                    "price_timeframe":price_tf,
                })
        points.sort(key=lambda x:(x["symbol"],x["timestamp"]))
        return points

    @staticmethod
    def _build_symbol_index(points):
        by=defaultdict(list)
        for p in points:
            by[p["symbol"]].append(p)
        idx={}
        for symbol,rows in by.items():
            rows.sort(key=lambda x:x["timestamp"])
            idx[symbol]={
                "rows":rows,
                "times":[r["timestamp"] for r in rows],
            }
        return idx

    @staticmethod
    def _resolve_future(index,symbol,entry_dt,horizon,tolerance):
        item=index.get(symbol)
        if not item:
            return None
        target=entry_dt+timedelta(minutes=int(horizon))
        times=item["times"]
        pos=bisect.bisect_left(times,target)
        if pos>=len(times):
            return None
        future=item["rows"][pos]
        lag=(future["timestamp"]-target).total_seconds()/60.0
        if lag < 0 or lag > float(tolerance):
            return None
        return future,lag

    def audit(self):
        p=self.policy()
        if not self.feature_ledger.exists():
            result={
                "status":"WAITING_FOR_V2_2_1_FEATURE_SNAPSHOTS",
                "feature_ledger_exists":False,
                "actual_execution_threshold":0.75,
                "actual_execution_threshold_modified":False,
                "actual_selector_modified":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
            _atomic_json(self.latest,result)
            return result

        points=self._points()
        if not points:
            result={
                "status":"WAITING_FOR_USABLE_FEATURE_SNAPSHOTS",
                "feature_ledger_exists":True,
                "usable_points":0,
                "actual_execution_threshold":0.75,
                "actual_execution_threshold_modified":False,
                "actual_selector_modified":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
            _atomic_json(self.latest,result)
            return result

        index=self._build_symbol_index(points)
        thresholds=[float(x) for x in p["confidence_thresholds"]]
        horizons=[int(x) for x in p["horizons_minutes"]]
        min_rr=float(p["min_reward_risk"])
        tolerance=int(p["resolution_tolerance_minutes"])
        allowed_actions=set(map(str.upper,p["action_filter"]))

        # Unique hypothetical signals keyed by threshold+symbol+snapshot.
        signals=[]
        for pt in points:
            if pt["action"] not in allowed_actions:
                continue
            if pt["reward_risk"] < min_rr:
                continue
            for th in thresholds:
                if pt["confidence"] >= th:
                    signals.append({
                        "threshold":th,
                        "symbol":pt["symbol"],
                        "entry_timestamp":pt["timestamp_iso"],
                        "action":pt["action"],
                        "confidence":pt["confidence"],
                        "reward_risk":pt["reward_risk"],
                        "entry_price":pt["price"],
                        "entry_price_timeframe":pt["price_timeframe"],
                        "snapshot_id":pt["snapshot_id"],
                    })

        agg={}
        for th in thresholds:
            th_signals=[s for s in signals if s["threshold"]==th]
            horizon_reports={}
            for h in horizons:
                signed_returns=[]
                abs_forward=[]
                resolved_rows=[]
                for s in th_signals:
                    future=self._resolve_future(
                        index,s["symbol"],_parse_dt(s["entry_timestamp"]),
                        h,tolerance
                    )
                    if future is None:
                        continue
                    frow,lag=future
                    raw=(frow["price"]/s["entry_price"]-1.0)*100.0
                    signed=raw if s["action"]=="BUY" else -raw
                    signed_returns.append(signed)
                    abs_forward.append(raw)
                    resolved_rows.append({
                        "symbol":s["symbol"],
                        "action":s["action"],
                        "entry_timestamp":s["entry_timestamp"],
                        "resolved_timestamp":frow["timestamp_iso"],
                        "resolution_lag_minutes":round(lag,6),
                        "entry_price":s["entry_price"],
                        "future_price":frow["price"],
                        "signed_return_pct":round(signed,6),
                    })

                wins=sum(1 for x in signed_returns if x>0)
                losses=sum(1 for x in signed_returns if x<0)
                flats=sum(1 for x in signed_returns if x==0)
                horizon_reports[f"{h}m"]={
                    "signal_count":len(th_signals),
                    "resolved_count":len(signed_returns),
                    "unresolved_count":len(th_signals)-len(signed_returns),
                    "directional_wins":wins,
                    "directional_losses":losses,
                    "directional_flats":flats,
                    "directional_win_rate_pct":(
                        None if not signed_returns
                        else round(wins/len(signed_returns)*100.0,4)
                    ),
                    "average_signed_return_pct":(
                        None if not signed_returns
                        else round(sum(signed_returns)/len(signed_returns),6)
                    ),
                    "median_signed_return_pct":(
                        None if not signed_returns
                        else round(statistics.median(signed_returns),6)
                    ),
                    "best_signed_return_pct":(
                        None if not signed_returns
                        else round(max(signed_returns),6)
                    ),
                    "worst_signed_return_pct":(
                        None if not signed_returns
                        else round(min(signed_returns),6)
                    ),
                    "outcome_basis":"SNAPSHOT_TO_SNAPSHOT_PRICE_RETURN_NOT_BROKER_FILL_PNL",
                }

            unique_symbols=sorted(set(s["symbol"] for s in th_signals))
            agg[f"{th:.2f}"]={
                "confidence_threshold":th,
                "min_reward_risk":min_rr,
                "signal_count":len(th_signals),
                "symbols":unique_symbols,
                "horizons":horizon_reports,
                "is_current_execution_threshold":abs(th-0.75)<1e-12,
                "execution_enabled_by_this_audit":False,
            }

        current=agg.get("0.75",{})
        current_signals=int(current.get("signal_count",0))
        incremental={}
        for key,val in agg.items():
            incremental[key]={
                "signal_count":val["signal_count"],
                "additional_signals_vs_075":
                    int(val["signal_count"])-current_signals,
            }

        # Evidence ranking: 5m resolved avg signed return, then resolved count.
        rankable=[]
        for key,val in agg.items():
            h=val["horizons"]["5m"]
            if h["resolved_count"]>0 and h["average_signed_return_pct"] is not None:
                rankable.append((
                    h["average_signed_return_pct"],
                    h["resolved_count"],
                    float(key)
                ))
        best=None
        if rankable:
            rankable.sort(reverse=True)
            best=rankable[0][2]

        result={
            "stage":"BROKER_INTEGRATION_V2_1_31_4_THRESHOLD_SENSITIVITY_SHADOW_AUDIT",
            "status":"PASS_THRESHOLD_SENSITIVITY_SHADOW_AUDIT",
            "feature_snapshot_count":
                len(set(p["snapshot_id"] for p in points if p.get("snapshot_id"))),
            "usable_symbol_points":len(points),
            "thresholds":agg,
            "incremental_signal_counts":incremental,
            "best_5m_threshold_by_current_shadow_evidence":best,
            "best_threshold_is_research_only":True,
            "minimum_reward_risk_held_constant":min_rr,
            "actual_execution_threshold":0.75,
            "actual_execution_threshold_modified":False,
            "actual_selector_modified":False,
            "counterfactual_orders_submitted":0,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic_json(self.latest,result)
        return result

    def status(self):
        if not self.latest.exists():
            return {
                "status":"WAITING_FOR_FIRST_THRESHOLD_AUDIT",
                "actual_execution_threshold":0.75,
                "actual_execution_threshold_modified":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
        return json.loads(self.latest.read_text(encoding="utf-8"))
