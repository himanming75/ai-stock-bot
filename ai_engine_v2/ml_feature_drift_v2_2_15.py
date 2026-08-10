from __future__ import annotations
import csv, json, math, os, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

def _utcnow():
    return datetime.now(timezone.utc).isoformat()

def _atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True,default=str),encoding="utf-8")
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

def _finite(v):
    try:
        return math.isfinite(float(v))
    except (TypeError,ValueError):
        return False

def _mean(xs):
    return sum(xs)/len(xs) if xs else None

def _std(xs):
    if len(xs)<2:
        return None
    m=_mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs)/len(xs))

def _quantile(xs,q):
    if not xs:
        return None
    ys=sorted(xs)
    if len(ys)==1:
        return ys[0]
    pos=(len(ys)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:
        return ys[lo]
    w=pos-lo
    return ys[lo]*(1-w)+ys[hi]*w

class MLFeatureDriftMonitorV2215:
    """
    Compares V2.2.9 training feature distributions with recent V2.2.11
    inference feature distributions. Research-only.
    """
    def __init__(self,root):
        self.root=Path(root)
        self.dataset_root=(
            self.root/"runtime"/"ai_training_dataset_builder_v2_2_9"/"datasets"
        )
        self.inference_ledger=(
            self.root/"runtime"/"ai_ml_shadow_inference_v2_2_11"/
            "ml_shadow_inference_ledger.jsonl"
        )
        self.runtime=(
            self.root/"runtime"/"ai_ml_feature_drift_v2_2_15"
        )
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_feature_drift.json"

    def _training_values(self):
        values=defaultdict(list)
        paths=sorted(self.dataset_root.glob("train_*m.csv"))
        # Use all horizon train files but dedupe row identity to avoid the same
        # feature vector being counted four times.
        seen=set()
        for path in paths:
            with path.open("r",encoding="utf-8",newline="") as f:
                reader=csv.DictReader(f)
                for row in reader:
                    key=(row.get("timestamp"),row.get("symbol"))
                    if key in seen:
                        continue
                    seen.add(key)
                    for name,val in row.items():
                        if name in {
                            "timestamp","market_date","symbol","feed",
                            "target_horizon_min","target_return_pct",
                            "target_mfe_pct","target_mae_pct",
                            "target_direction","target_timestamp"
                        }:
                            continue
                        if _finite(val):
                            values[name].append(float(val))
        return values,len(seen)

    def _current_values(self):
        values=defaultdict(list)
        rows=_read_jsonl(self.inference_ledger)
        # Recent unique symbol/timestamp feature vectors.
        seen=set()
        for inf in rows[-200:]:
            for srow in inf.get("symbol_predictions") or []:
                key=(srow.get("symbol"),srow.get("feature_timestamp"))
                if key in seen:
                    continue
                seen.add(key)
                for name,val in (srow.get("feature_values") or {}).items():
                    if _finite(val):
                        values[name].append(float(val))
        return values,len(seen)

    @staticmethod
    def _feature_report(train,current):
        tm=_mean(train); ts=_std(train)
        cm=_mean(current); cs=_std(current)
        med_train=_quantile(train,0.5)
        med_cur=_quantile(current,0.5)
        q25=_quantile(train,0.25); q75=_quantile(train,0.75)
        iqr=(q75-q25) if q25 is not None and q75 is not None else None

        z_shift=None
        if tm is not None and cm is not None and ts not in (None,0):
            z_shift=abs(cm-tm)/ts

        median_shift_iqr=None
        if med_train is not None and med_cur is not None and iqr not in (None,0):
            median_shift_iqr=abs(med_cur-med_train)/abs(iqr)

        scale_ratio=None
        if ts not in (None,0) and cs is not None:
            scale_ratio=cs/ts

        severity="INSUFFICIENT"
        if len(train)>=30 and len(current)>=10:
            severity="LOW"
            score=max(
                z_shift or 0.0,
                median_shift_iqr or 0.0,
                abs(math.log(scale_ratio)) if scale_ratio and scale_ratio>0 else 0.0,
            )
            if score>=2.0:
                severity="HIGH"
            elif score>=1.0:
                severity="MEDIUM"

        return {
            "training_count":len(train),
            "current_count":len(current),
            "training_mean":None if tm is None else round(tm,8),
            "current_mean":None if cm is None else round(cm,8),
            "training_std":None if ts is None else round(ts,8),
            "current_std":None if cs is None else round(cs,8),
            "training_median":None if med_train is None else round(med_train,8),
            "current_median":None if med_cur is None else round(med_cur,8),
            "mean_shift_training_std_units":None if z_shift is None else round(z_shift,8),
            "median_shift_training_iqr_units":None if median_shift_iqr is None else round(median_shift_iqr,8),
            "current_to_training_std_ratio":None if scale_ratio is None else round(scale_ratio,8),
            "severity":severity,
        }

    def evaluate(self):
        if not self.dataset_root.exists() or not self.inference_ledger.exists():
            r={
                "status":"WAITING_FOR_TRAINING_DATASET_AND_V2_2_11_INFERENCE",
                "drift_interpretation_ready":False,
                "execution_change_allowed":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
            _atomic_json(self.latest,r)
            return r

        train,train_rows=self._training_values()
        current,current_rows=self._current_values()
        names=sorted(set(train)&set(current))
        reports={}
        high=[]; medium=[]
        for name in names:
            rep=self._feature_report(train[name],current[name])
            reports[name]=rep
            if rep["severity"]=="HIGH":
                high.append(name)
            elif rep["severity"]=="MEDIUM":
                medium.append(name)

        ready=(train_rows>=100 and current_rows>=30 and bool(names))
        if not ready:
            overall="INSUFFICIENT_DATA"
        elif high:
            overall="HIGH_DRIFT"
        elif medium:
            overall="MEDIUM_DRIFT"
        else:
            overall="LOW_DRIFT"

        r={
            "stage":"AI_TRADING_ENGINE_V2_2_15_ML_FEATURE_DRIFT",
            "status":"PASS_ML_FEATURE_DRIFT_EVALUATION",
            "generated_at_utc":_utcnow(),
            "training_unique_feature_rows":train_rows,
            "current_unique_feature_rows":current_rows,
            "feature_count":len(names),
            "features":reports,
            "high_drift_features":high,
            "medium_drift_features":medium,
            "overall_drift_status":overall,
            "drift_interpretation_ready":ready,
            "research_only":True,
            "automatic_retraining_allowed":False,
            "automatic_model_replacement_allowed":False,
            "execution_change_allowed":False,
            "selector_modified":False,
            "threshold_modified":False,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic_json(self.latest,r)
        return r

    def status(self):
        if self.latest.exists():
            try:
                return json.loads(self.latest.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self.evaluate()
