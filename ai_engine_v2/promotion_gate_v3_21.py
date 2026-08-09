from .common import safe_status, num

MIN_COMPARISONS=20

def build_promotion_gate(evaluation):
    comps=evaluation.get("comparisons") or []
    if len(comps)<MIN_COMPARISONS:
        return safe_status("V3.21_PROMOTION_GATE","WAITING_FOR_EVIDENCE",
            required_comparisons=MIN_COMPARISONS,observed_comparisons=len(comps),
            promotion_eligible=False,automatic_promotion=False)
    delta=sum((num(x.get("delta_pnl")) or 0) for x in comps)
    dd_pairs=[x for x in comps if num(x.get("champion_drawdown")) is not None and num(x.get("challenger_drawdown")) is not None]
    dd_better=(sum(num(x["challenger_drawdown"]) for x in dd_pairs) <= sum(num(x["champion_drawdown"]) for x in dd_pairs)) if dd_pairs else False
    eligible=delta>0 and dd_better
    return safe_status("V3.21_PROMOTION_GATE","PASS_ELIGIBLE_FOR_MANUAL_REVIEW" if eligible else "PASS_NOT_ELIGIBLE",
        required_comparisons=MIN_COMPARISONS,observed_comparisons=len(comps),
        aggregate_delta_pnl=delta,drawdown_not_worse=dd_better,
        promotion_eligible=eligible,automatic_promotion=False)
