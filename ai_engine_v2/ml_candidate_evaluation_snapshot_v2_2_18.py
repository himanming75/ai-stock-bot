from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path

def _utcnow():
    return datetime.now(timezone.utc).isoformat()

def _atomic(path,v):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+".tmp")
    t.write_text(json.dumps(v,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(t,path)

def _load(path):
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {}

class MLCandidateEvaluationSnapshotV2218:
    def __init__(self,root):
        self.root=Path(root)
        self.training=self.root/"runtime"/"ai_ml_model_training_validation_v2_2_10"/"latest_training_report.json"
        self.health=self.root/"runtime"/"ai_ml_model_health_v2_2_16"/"latest_ml_model_health.json"
        self.trigger=self.root/"runtime"/"ai_ml_retraining_trigger_v2_2_17"/"latest_ml_retraining_trigger.json"
        self.runtime=self.root/"runtime"/"ai_ml_candidate_evaluation_v2_2_18"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_candidate_evaluation_snapshot.json"

    def build(self):
        t=_load(self.training); h=_load(self.health); g=_load(self.trigger)
        out={
            "stage":"AI_TRADING_ENGINE_V2_2_18_CANDIDATE_EVALUATION_SNAPSHOT",
            "status":"PASS_CANDIDATE_EVALUATION_SNAPSHOT",
            "generated_at_utc":_utcnow(),
            "training_status":t.get("status"),
            "best_shadow_research_horizon":t.get("best_test_horizon_for_shadow_research"),
            "edge_ready_horizons":t.get("edge_ready_horizons",[]),
            "model_health":h.get("model_health","UNKNOWN"),
            "research_action":h.get("research_action","WAIT"),
            "retraining_recommended":bool(g.get("retraining_recommended")),
            "candidate_research_ready":(
                h.get("model_health")=="GREEN"
                and bool(h.get("research_comparison_ready"))
            ),
            "automatic_promotion":False,
            "manual_promotion":False,
            "execution_selector_modified":False,
            "threshold_modified":False,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic(self.latest,out)
        return out
