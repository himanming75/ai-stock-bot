from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path

def _utcnow(): return datetime.now(timezone.utc).isoformat()
def _atomic(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(v,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(t,p)
def _load(p):
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

class MLUncertaintyV2220:
    def __init__(self,root):
        self.root=Path(root)
        self.source=self.root/"runtime"/"ai_ml_horizon_consensus_v2_2_19"/"latest_ml_horizon_consensus.json"
        self.runtime=self.root/"runtime"/"ai_ml_uncertainty_v2_2_20"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_uncertainty.json"

    def build(self):
        c=_load(self.source)
        if not c:
            r={"status":"WAITING_FOR_V2_2_19_CONSENSUS"}
            _atomic(self.latest,r); return r
        out=[]
        for s in c.get("symbols") or []:
            agreement=float(s.get("horizon_agreement") or 0.0)
            conf=s.get("mean_horizon_confidence")
            conf=float(conf) if conf is not None else 0.0
            uncertainty=(1.0-agreement)*0.65+(1.0-conf)*0.35
            if uncertainty>=0.65: band="HIGH"
            elif uncertainty>=0.35: band="MEDIUM"
            else: band="LOW"
            out.append({
                "symbol":s.get("symbol"),
                "consensus_direction":s.get("consensus_direction"),
                "uncertainty_score":round(uncertainty,8),
                "uncertainty_band":band,
                "horizon_agreement":agreement,
                "mean_horizon_confidence":conf,
            })
        r={
            "stage":"AI_TRADING_ENGINE_V2_2_20_ML_UNCERTAINTY",
            "status":"PASS_ML_UNCERTAINTY_EVALUATION",
            "generated_at_utc":_utcnow(),
            "symbols":out,
            "research_only":True,
            "execution_use_allowed":False,
            "broker_network_used":False,"orders_submitted":0,"live_trading":False,
        }
        _atomic(self.latest,r); return r
