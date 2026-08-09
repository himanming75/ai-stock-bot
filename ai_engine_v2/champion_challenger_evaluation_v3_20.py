from .common import safe_status, num

def evaluate_champion_vs_challenger(champion, shadow, observations=None):
    observations=observations or []
    if not shadow.get("challengers"):
        return safe_status("V3.20_CHAMPION_CHALLENGER_EVALUATION",
            "WAITING_FOR_ELIGIBLE_CHALLENGER",comparison_count=0,comparisons=[])
    if not observations:
        return safe_status("V3.20_CHAMPION_CHALLENGER_EVALUATION",
            "WAITING_FOR_SHADOW_OBSERVATIONS",comparison_count=0,comparisons=[])
    comps=[]
    for row in observations:
        cp=num(row.get("champion_pnl")); xp=num(row.get("challenger_pnl"))
        if cp is None or xp is None: continue
        comps.append({
            "challenger_id":row.get("challenger_id"),
            "champion_pnl":cp,"challenger_pnl":xp,"delta_pnl":xp-cp,
            "champion_drawdown":num(row.get("champion_drawdown")),
            "challenger_drawdown":num(row.get("challenger_drawdown")),
        })
    return safe_status("V3.20_CHAMPION_CHALLENGER_EVALUATION",
        "PASS" if comps else "WAITING_FOR_VALID_OBSERVATIONS",
        comparison_count=len(comps),comparisons=comps)
