from __future__ import annotations
import json, math, os
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

class MLConfidenceCalibrationV2214:
    """
    Reliability diagnostics for V2.2.10/V2.2.11 ML probabilities using
    V2.2.12 resolved outcomes. Research-only; no execution changes.
    """
    def __init__(self,root):
        self.root=Path(root)
        self.source=(
            self.root/"runtime"/"ai_ml_prediction_outcome_v2_2_12"/
            "ml_prediction_outcome_ledger.jsonl"
        )
        self.readiness=(
            self.root/"runtime"/"ai_ml_research_readiness_v2_2_13"/
            "latest_ml_research_readiness.json"
        )
        self.runtime=(
            self.root/"runtime"/"ai_ml_confidence_calibration_v2_2_14"
        )
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_confidence_calibration.json"

    @staticmethod
    def _bin_index(conf,bins=10):
        c=max(0.0,min(1.0,float(conf)))
        return min(bins-1,int(c*bins))

    @staticmethod
    def _multiclass_brier(row):
        probs=dict(row.get("class_probabilities") or {})
        actual=str(row.get("actual_direction") or "")
        labels=("DOWN","FLAT","UP")
        if not all(_finite(probs.get(k)) for k in labels):
            return None
        return sum(
            (float(probs[k])-(1.0 if actual==k else 0.0))**2
            for k in labels
        ) / len(labels)

    def evaluate(self):
        if not self.source.exists():
            r={
                "status":"WAITING_FOR_V2_2_12_OUTCOMES",
                "calibration_interpretation_ready":False,
                "execution_use_allowed":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
            _atomic_json(self.latest,r)
            return r

        rows=_read_jsonl(self.source)
        by_h=defaultdict(list)
        for row in rows:
            if _finite(row.get("prediction_confidence")):
                by_h[str(row.get("horizon"))].append(row)

        readiness={}
        if self.readiness.exists():
            try:
                readiness=json.loads(self.readiness.read_text(encoding="utf-8"))
            except Exception:
                readiness={}

        horizon_readiness=set(readiness.get("research_ready_horizons") or [])
        horizons={}
        for h,hrows in sorted(
            by_h.items(),
            key=lambda kv:int(str(kv[0]).replace("m",""))
        ):
            bins=[[] for _ in range(10)]
            briers=[]
            for row in hrows:
                conf=float(row["prediction_confidence"])
                bins[self._bin_index(conf)].append(row)
                b=self._multiclass_brier(row)
                if b is not None:
                    briers.append(b)

            bin_reports=[]
            ece=0.0
            n=len(hrows)
            for i,brows in enumerate(bins):
                lo=i/10.0
                hi=(i+1)/10.0
                if not brows:
                    bin_reports.append({
                        "bin":i,
                        "range":[round(lo,1),round(hi,1)],
                        "count":0,
                        "mean_confidence":None,
                        "observed_accuracy":None,
                        "calibration_gap":None,
                    })
                    continue
                mean_conf=sum(float(r["prediction_confidence"]) for r in brows)/len(brows)
                acc=sum(1 for r in brows if r.get("direction_correct"))/len(brows)
                gap=acc-mean_conf
                ece+=(len(brows)/n)*abs(gap)
                bin_reports.append({
                    "bin":i,
                    "range":[round(lo,1),round(hi,1)],
                    "count":len(brows),
                    "mean_confidence":round(mean_conf,8),
                    "observed_accuracy":round(acc,8),
                    "calibration_gap":round(gap,8),
                })

            avg_conf=sum(float(r["prediction_confidence"]) for r in hrows)/n if n else None
            accuracy=sum(1 for r in hrows if r.get("direction_correct"))/n if n else None
            overconfidence=(
                None if n==0 else max(0.0,float(avg_conf)-float(accuracy))
            )
            horizons[h]={
                "resolved_probability_rows":n,
                "research_ready":h in horizon_readiness,
                "mean_confidence":None if avg_conf is None else round(avg_conf,8),
                "observed_accuracy":None if accuracy is None else round(accuracy,8),
                "expected_calibration_error":None if not n else round(ece,8),
                "mean_multiclass_brier":(
                    None if not briers else round(sum(briers)/len(briers),8)
                ),
                "overconfidence_amount":(
                    None if overconfidence is None else round(overconfidence,8)
                ),
                "bins":bin_reports,
                "interpretation_allowed":h in horizon_readiness,
            }

        ready=bool(horizon_readiness)
        r={
            "stage":"AI_TRADING_ENGINE_V2_2_14_ML_CONFIDENCE_CALIBRATION",
            "status":"PASS_ML_CONFIDENCE_CALIBRATION_EVALUATION",
            "generated_at_utc":_utcnow(),
            "total_probability_outcomes":sum(len(v) for v in by_h.values()),
            "research_ready_horizons":sorted(
                horizon_readiness,
                key=lambda x:int(str(x).replace("m",""))
            ),
            "calibration_interpretation_ready":ready,
            "horizons":horizons,
            "metrics":[
                "EXPECTED_CALIBRATION_ERROR",
                "MULTICLASS_BRIER",
                "CONFIDENCE_MINUS_ACCURACY",
                "10_BIN_RELIABILITY",
            ],
            "research_only":True,
            "execution_use_allowed":False,
            "selector_modified":False,
            "threshold_modified":False,
            "model_modified":False,
            "model_promotion_allowed":False,
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
