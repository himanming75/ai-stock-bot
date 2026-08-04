from __future__ import annotations
from typing import Any

def select(signals:list[dict[str,Any]],policy:dict[str,Any])->list[dict[str,Any]]:
    actionable=[s for s in signals if s.get("action") in {"BUY","SELL"}]
    actionable.sort(key=lambda x:abs(float(x.get("change_pct",0))),reverse=True)
    return actionable[:int(policy.get("maximum_candidates_per_cycle",1))]
