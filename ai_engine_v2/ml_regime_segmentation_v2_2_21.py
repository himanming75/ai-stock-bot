from __future__ import annotations
import json, os
from collections import defaultdict
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

class MLRegimeSegmentationV2221:
    def __init__(self,root):
        self.root=Path(root)
        self.source=self.root/"runtime"/"ai_ml_prediction_outcome_v2_2_12"/"ml_prediction_outcome_ledger.jsonl"
        self.runtime=self.root/"runtime"/"ai_ml_regime_segmentation_v2_2_21"
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_ml_regime_segmentation.json"

    @staticmethod
    def _regime(features):
        vol=features.get("rolling_volatility_20")
        trend=features.get("close_vs_sma20_pct")
        try: vol=float(vol); trend=float(trend)
        except Exception: return "UNKNOWN"
        vol_band="HIGH_VOL" if vol>=0.25 else "LOW_VOL"
        trend_band="UPTREND" if trend>0.15 else ("DOWNTREND" if trend<-0.15 else "SIDEWAYS")
        return f"{vol_band}_{trend_band}"

    def build(self):
        rows=_read_jsonl(self.source)
        groups=defaultdict(list)
        for r in rows:
            groups[(str(r.get("horizon")),self._regime(r.get("feature_values") or {}))].append(r)
        report={}
        for (h,reg),vals in sorted(groups.items()):
            n=len(vals)
            correct=sum(1 for x in vals if x.get("direction_correct"))
            report.setdefault(h,{})[reg]={
                "count":n,
                "accuracy_pct":None if not n else round(correct/n*100,6),
            }
        r={
            "stage":"AI_TRADING_ENGINE_V2_2_21_ML_REGIME_SEGMENTATION",
            "status":"PASS_ML_REGIME_SEGMENTATION",
            "generated_at_utc":_utcnow(),
            "total_outcomes":len(rows),
            "horizon_regimes":report,
            "interpretation_ready":len(rows)>=200,
            "research_only":True,
            "execution_change_allowed":False,
            "broker_network_used":False,"orders_submitted":0,"live_trading":False,
        }
        _atomic(self.latest,r); return r
