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
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

class MLModelHealthGateV2216:
    def __init__(self,root):
        self.root=Path(root)
        self.readiness=self.root/"runtime"/"ai_ml_research_readiness_v2_2_13"/"latest_ml_research_readiness.json"
        self.calibration=self.root/"runtime"/"ai_ml_confidence_calibration_v2_2_14"/"latest_ml_confidence_calibration.json"
        self.drift=self.root/"runtime"/"ai_ml_feature_drift_v2_2_15"/"latest_ml_feature_drift.json"
        self.runtime=self.root/"runtime"/"ai_ml_model_health_v2_2_16"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_model_health.json"

    def evaluate(self):
        rdy=_load(self.readiness); cal=_load(self.calibration); dr=_load(self.drift)
        missing=[]
        if not rdy: missing.append("V2.2.13")
        if not cal: missing.append("V2.2.14")
        if not dr: missing.append("V2.2.15")
        if missing:
            out={
                "status":"WAITING_FOR_MODEL_HEALTH_INPUTS",
                "missing":missing,
                "model_health":"UNKNOWN",
                "research_action":"WAIT",
                "execution_change_allowed":False,
                "model_promotion_allowed":False,
                "broker_network_used":False,"orders_submitted":0,"live_trading":False,
            }
            _atomic(self.latest,out); return out

        ready=bool(rdy.get("research_comparison_ready"))
        drift=str(dr.get("overall_drift_status") or "INSUFFICIENT_DATA")
        cal_ready=bool(cal.get("calibration_interpretation_ready"))

        reasons=[]
        if not ready: reasons.append("RESEARCH_SAMPLE_NOT_READY")
        if drift=="HIGH_DRIFT": reasons.append("HIGH_FEATURE_DRIFT")
        if not cal_ready: reasons.append("CALIBRATION_NOT_READY")

        if "HIGH_FEATURE_DRIFT" in reasons:
            health="RED"
        elif reasons:
            health="YELLOW"
        else:
            health="GREEN"

        action="WAIT"
        if health=="GREEN":
            action="ELIGIBLE_FOR_RESEARCH_COMPARISON"
        elif health=="RED":
            action="RETRAINING_REVIEW_RECOMMENDED"

        out={
            "stage":"AI_TRADING_ENGINE_V2_2_16_MODEL_HEALTH_GATE",
            "status":"PASS_MODEL_HEALTH_EVALUATION",
            "generated_at_utc":_utcnow(),
            "model_health":health,
            "research_action":action,
            "block_reasons":reasons,
            "research_comparison_ready":ready,
            "calibration_interpretation_ready":cal_ready,
            "overall_drift_status":drift,
            "execution_change_allowed":False,
            "selector_change_allowed":False,
            "threshold_change_allowed":False,
            "model_promotion_allowed":False,
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic(self.latest,out)
        return out
