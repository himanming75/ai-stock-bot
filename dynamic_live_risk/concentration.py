from __future__ import annotations
from typing import Any

def evaluate(candidate:dict[str,Any],positions:list[dict[str,Any]],policy:dict[str,Any])->dict[str,Any]:
    sector_map=policy.get("sector_map",{})
    symbol=str(candidate.get("symbol",""))
    candidate_sector=sector_map.get(symbol,"UNKNOWN")
    same_sector=sum(1 for p in positions if sector_map.get(str(p.get("symbol","")),"UNKNOWN")==candidate_sector)
    symbol_exists=any(str(p.get("symbol",""))==symbol for p in positions)
    checks={
        "symbol_not_already_held":not symbol_exists,
        "sector_position_limit_clear":same_sector<int(policy.get("maximum_positions_per_sector",2)),
        "correlation_cluster_clear":int(policy.get("current_correlation_cluster_count",0))<int(policy.get("maximum_correlation_cluster_count",2)),
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "candidate_sector":candidate_sector,
        "same_sector_position_count":same_sector,
        "checks":checks,
        "failed":failed,
        "passed":not failed,
    }
