from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path

def _utcnow(): return datetime.now(timezone.utc).isoformat()
def _load(p):
    if not p.exists(): return {}
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return {}
def _atomic(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(v,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(t,p)

class MLResearchRecommendationV2222:
    def __init__(self,root):
        self.root=Path(root)
        self.health=self.root/"runtime"/"ai_ml_model_health_v2_2_16"/"latest_ml_model_health.json"
        self.consensus=self.root/"runtime"/"ai_ml_horizon_consensus_v2_2_19"/"latest_ml_horizon_consensus.json"
        self.uncertainty=self.root/"runtime"/"ai_ml_uncertainty_v2_2_20"/"latest_ml_uncertainty.json"
        self.regime=self.root/"runtime"/"ai_ml_regime_segmentation_v2_2_21"/"latest_ml_regime_segmentation.json"
        self.runtime=self.root/"runtime"/"ai_ml_research_recommendation_v2_2_22"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_research_recommendation.json"

    def build(self):
        h=_load(self.health); c=_load(self.consensus); u=_load(self.uncertainty); r=_load(self.regime)
        ready=(h.get("model_health")=="GREEN" and bool(r.get("interpretation_ready")))
        action="WAIT_FOR_MORE_VALIDATION_DATA"
        if h.get("model_health")=="RED":
            action="RETRAINING_REVIEW"
        elif ready:
            action="RESEARCH_COMPARISON_ALLOWED"
        out={
            "stage":"AI_TRADING_ENGINE_V2_2_22_ML_RESEARCH_RECOMMENDATION",
            "status":"PASS_ML_RESEARCH_RECOMMENDATION",
            "generated_at_utc":_utcnow(),
            "model_health":h.get("model_health","UNKNOWN"),
            "recommended_research_action":action,
            "research_comparison_allowed":ready,
            "consensus_symbol_count":c.get("symbol_count",0),
            "uncertainty_available":bool(u.get("symbols")),
            "regime_interpretation_ready":bool(r.get("interpretation_ready")),
            "automatic_execution_change":False,
            "automatic_selector_change":False,
            "automatic_threshold_change":False,
            "automatic_model_promotion":False,
            "broker_network_used":False,"orders_submitted":0,"live_trading":False,
        }
        _atomic(self.latest,out); return out
