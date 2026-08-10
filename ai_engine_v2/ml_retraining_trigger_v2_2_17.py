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

class MLRetrainingTriggerPlannerV2217:
    def __init__(self,root):
        self.root=Path(root)
        self.health=self.root/"runtime"/"ai_ml_model_health_v2_2_16"/"latest_ml_model_health.json"
        self.runtime=self.root/"runtime"/"ai_ml_retraining_trigger_v2_2_17"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_retraining_trigger.json"

    def evaluate(self):
        h=_load(self.health)
        if not h:
            out={"status":"WAITING_FOR_V2_2_16_MODEL_HEALTH","retraining_recommended":False}
            _atomic(self.latest,out); return out

        health=h.get("model_health")
        reasons=list(h.get("block_reasons") or [])
        recommended=(health=="RED")
        out={
            "stage":"AI_TRADING_ENGINE_V2_2_17_RETRAINING_TRIGGER_PLANNER",
            "status":"PASS_RETRAINING_TRIGGER_EVALUATION",
            "generated_at_utc":_utcnow(),
            "model_health":health,
            "retraining_recommended":recommended,
            "retraining_reason":(
                "MODEL_HEALTH_RED" if recommended else "NO_RETRAINING_TRIGGER"
            ),
            "source_health_reasons":reasons,
            "automatic_retraining_allowed":False,
            "automatic_model_replacement_allowed":False,
            "manual_research_retraining_command_allowed":True,
            "execution_change_allowed":False,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic(self.latest,out)
        return out
