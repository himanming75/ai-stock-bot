from .common import safe_status, num

def build_portfolio_intelligence(status_payload):
    broker=status_payload.get("broker_snapshot") or {}
    positions=broker.get("positions") or broker.get("position_rows") or []
    if isinstance(positions,dict):
        positions=list(positions.values())
    values=[]
    for p in positions if isinstance(positions,list) else []:
        v=num(p.get("market_value") or p.get("value"))
        if v is not None and v>=0:
            values.append((str(p.get("symbol") or "UNKNOWN"),v))
    total=sum(v for _,v in values)
    alloc=[{"symbol":s,"weight":v/total if total else None,"market_value":v} for s,v in values]
    max_weight=max((x["weight"] or 0 for x in alloc),default=0)
    warnings=[]
    if max_weight>0.6:
        warnings.append("CONCENTRATION_ABOVE_60_PERCENT")
    return safe_status("V3.24_PORTFOLIO_RISK_INTELLIGENCE","PASS_ADVISORY",
        position_count=len(alloc),allocation=alloc,max_position_weight=max_weight or None,
        warnings=warnings,advisory_only=True,position_change_performed=False)
