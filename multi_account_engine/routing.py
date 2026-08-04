def route(rows,accounts):
 out=[]
 for r in rows:
  if not r.get("eligible"): continue
  for a in accounts:
   if a.get("enabled") and r.get("profile") in a.get("assigned_profiles",[]):
    out.append({"account_id":a["account_id"],"strategy_id":r.get("strategy_id"),"profile":r.get("profile"),"symbol":r.get("symbol"),"action":r.get("action"),"strategy_score":r.get("strategy_score"),"risk_per_trade_pct":r.get("risk_per_trade_pct"),"maximum_holding_minutes":r.get("maximum_holding_minutes")})
 return out
