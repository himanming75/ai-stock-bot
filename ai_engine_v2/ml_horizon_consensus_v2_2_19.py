from __future__ import annotations
import json, os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

def _utcnow(): return datetime.now(timezone.utc).isoformat()
def _atomic(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(v,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(t,p)
def _read_jsonl(p):
    out=[]
    if not p.exists(): return out
    with p.open("r",encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try: out.append(json.loads(line))
                except json.JSONDecodeError: pass
    return out

class MLHorizonConsensusV2219:
    def __init__(self,root):
        self.root=Path(root)
        self.source=self.root/"runtime"/"ai_ml_shadow_inference_v2_2_11"/"ml_shadow_inference_ledger.jsonl"
        self.runtime=self.root/"runtime"/"ai_ml_horizon_consensus_v2_2_19"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_horizon_consensus.json"

    def build(self):
        rows=_read_jsonl(self.source)
        if not rows:
            r={"status":"WAITING_FOR_V2_2_11_INFERENCE","symbol_count":0}
            _atomic(self.latest,r); return r
        inf=rows[-1]
        symbols=[]
        for s in inf.get("symbol_predictions") or []:
            votes=[]
            confs=[]
            for h,p in (s.get("predictions") or {}).items():
                d=str(p.get("predicted_direction") or "")
                if d: votes.append(d)
                c=p.get("prediction_confidence")
                if c is not None: confs.append(float(c))
            counts=Counter(votes)
            winner=counts.most_common(1)[0][0] if counts else None
            agreement=(counts[winner]/len(votes)) if winner and votes else 0.0
            symbols.append({
                "symbol":s.get("symbol"),
                "consensus_direction":winner,
                "horizon_vote_counts":dict(sorted(counts.items())),
                "horizon_agreement":round(agreement,8),
                "mean_horizon_confidence":None if not confs else round(sum(confs)/len(confs),8),
                "all_horizons_agree":bool(votes) and len(counts)==1,
            })
        r={
            "stage":"AI_TRADING_ENGINE_V2_2_19_ML_HORIZON_CONSENSUS",
            "status":"PASS_ML_HORIZON_CONSENSUS",
            "generated_at_utc":_utcnow(),
            "source_inference_id":inf.get("inference_id"),
            "symbol_count":len(symbols),
            "symbols":symbols,
            "research_only":True,
            "execution_change_allowed":False,
            "broker_network_used":False,"orders_submitted":0,"live_trading":False,
        }
        _atomic(self.latest,r); return r
