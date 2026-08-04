def evaluate(account,snapshot):
 eq=float(snapshot.get("equity",account.get("capital_limit",0)) or 0); pnl=float(snapshot.get("day_pnl",0) or 0); peak=float(snapshot.get("peak_equity",eq) or eq); pc=int(snapshot.get("position_count",0) or 0); od=int(snapshot.get("orders_today",0) or 0)
 dl=abs(pnl)/eq*100 if eq and pnl<0 else 0; dd=(peak-eq)/peak*100 if peak else 0
 c={"kill_switch_clear":account.get("kill_switch_enabled") is False,"daily_loss_within_limit":dl<=float(account["daily_loss_limit_pct"]),"drawdown_within_limit":dd<=float(account["maximum_drawdown_pct"]),"position_count_within_limit":pc<int(account["maximum_positions"]),"orders_within_limit":od<int(account["maximum_orders_per_day"]),"capital_within_limit":eq<=float(account["capital_limit"])}
 f=[k for k,v in c.items() if not v]
 return {"account_id":account["account_id"],"checks":c,"failed":f,"passed":not f,"metrics":{"equity":round(eq,2),"day_pnl":round(pnl,2),"daily_loss_pct":round(dl,4),"drawdown_pct":round(dd,4),"position_count":pc,"orders_today":od}}
