from __future__ import annotations
import json, math, os
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

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
            if not line.strip(): continue
            try: out.append(json.loads(line))
            except json.JSONDecodeError: continue
    return out

def _finite(v):
    try: return math.isfinite(float(v))
    except (TypeError,ValueError): return False

class MLResearchReadinessV2213:
    """
    Statistical sufficiency/readiness gate over V2.2.12 outcomes.
    It never promotes a model or changes trading behavior.
    """
    def __init__(self,root):
        self.root=Path(root)
        self.source=self.root/"runtime"/"ai_ml_prediction_outcome_v2_2_12"/"ml_prediction_outcome_ledger.jsonl"
        self.runtime=self.root/"runtime"/"ai_ml_research_readiness_v2_2_13"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_research_readiness.json"

    def evaluate(self):
        rows=_read_jsonl(self.source)
        if not self.source.exists():
            r={
                "status":"WAITING_FOR_V2_2_12_OUTCOMES",
                "research_comparison_ready":False,
                "selector_change_allowed":False,
                "model_promotion_allowed":False,
                "broker_network_used":False,"orders_submitted":0,"live_trading":False,
            }
            _atomic_json(self.latest,r); return r

        min_total=200
        min_horizon=40
        min_edge=30
        min_each_actual_class=5
        by_h=defaultdict(list)
        for row in rows:
            by_h[str(row.get("horizon"))].append(row)

        horizons={}
        ready_h=[]
        for h,hrows in sorted(by_h.items(),key=lambda kv:int(str(kv[0]).replace("m",""))):
            n=len(hrows)
            edge=[r for r in hrows if r.get("edge_ready")]
            actual=Counter(str(r.get("actual_direction")) for r in hrows)
            pred=Counter(str(r.get("predicted_direction")) for r in hrows)
            correct=sum(1 for r in hrows if r.get("direction_correct"))
            conf=[float(r["prediction_confidence"]) for r in hrows if _finite(r.get("prediction_confidence"))]
            class_ok=all(actual.get(c,0)>=min_each_actual_class for c in ("DOWN","FLAT","UP"))
            reasons=[]
            if n<min_horizon: reasons.append("INSUFFICIENT_HORIZON_SAMPLES")
            if len(edge)<min_edge: reasons.append("INSUFFICIENT_EDGE_READY_SAMPLES")
            if not class_ok: reasons.append("INSUFFICIENT_ACTUAL_CLASS_COVERAGE")
            ready=(len(reasons)==0)
            if ready: ready_h.append(h)
            horizons[h]={
                "resolved_count":n,
                "edge_ready_count":len(edge),
                "direction_accuracy_pct":None if not n else round(correct/n*100,6),
                "average_confidence":None if not conf else round(sum(conf)/len(conf),8),
                "actual_direction_counts":dict(sorted(actual.items())),
                "predicted_direction_counts":dict(sorted(pred.items())),
                "class_coverage_ready":class_ok,
                "research_ready":ready,
                "block_reasons":reasons,
            }

        overall_reasons=[]
        if len(rows)<min_total:
            overall_reasons.append("INSUFFICIENT_TOTAL_RESOLVED_OUTCOMES")
        if not ready_h:
            overall_reasons.append("NO_HORIZON_MEETS_RESEARCH_READINESS")
        overall_ready=(len(overall_reasons)==0)
        r={
            "stage":"AI_TRADING_ENGINE_V2_2_13_ML_RESEARCH_READINESS",
            "status":"PASS_ML_RESEARCH_READINESS_EVALUATION",
            "generated_at_utc":_utcnow(),
            "total_resolved_outcomes":len(rows),
            "minimum_total_resolved_outcomes":min_total,
            "minimum_per_horizon":min_horizon,
            "minimum_edge_ready_per_horizon":min_edge,
            "minimum_each_actual_class":min_each_actual_class,
            "research_ready_horizons":ready_h,
            "research_comparison_ready":overall_ready,
            "block_reasons":overall_reasons,
            "horizons":horizons,
            "selector_change_allowed":False,
            "threshold_change_allowed":False,
            "model_promotion_allowed":False,
            "paper_execution_change_allowed":False,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic_json(self.latest,r)
        return r

    def status(self):
        if self.latest.exists():
            try: return json.loads(self.latest.read_text(encoding="utf-8"))
            except Exception: pass
        return self.evaluate()
