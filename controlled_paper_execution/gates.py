from datetime import datetime,timezone
ENABLE_PHRASE="ENABLE_CONTROLLED_PAPER_AUTO_EXECUTION"
def evaluate(proposal,policy,credentials,phrase,clock,account,orders,counter):
    r=[]; o=proposal.get("proposal",{}); a=proposal.get("approval",{})
    if policy.get("paper_submission_enabled") is not True:r.append("PAPER_SUBMISSION_POLICY_DISABLED")
    if phrase!=ENABLE_PHRASE:r.append("ENABLE_PHRASE_MISMATCH")
    if not credentials.get("ready"):r.append("PAPER_CREDENTIALS_MISSING")
    if proposal.get("state")!="PAPER_ORDER_PROPOSAL_AWAITING_APPROVAL":r.append("PROPOSAL_NOT_AWAITING_APPROVAL")
    if o.get("eligible_for_approval") is not True:r.append("PROPOSAL_NOT_ELIGIBLE")
    if a.get("approved") is not True:r.append("APPROVAL_NOT_GRANTED")
    try:
        if datetime.now(timezone.utc)>=datetime.fromisoformat(str(a.get("expires_at"))):r.append("APPROVAL_TOKEN_EXPIRED")
    except:r.append("APPROVAL_EXPIRY_INVALID")
    sym=str(o.get("symbol","")).upper(); side=str(o.get("side","")).upper(); typ=str(o.get("order_type","")).lower(); tif=str(o.get("time_in_force","")).lower(); n=float(o.get("estimated_notional",0))
    if sym not in {str(x).upper() for x in policy.get("allowed_symbols",[])}:r.append("SYMBOL_NOT_ALLOWED")
    if side not in {"BUY","SELL"}:r.append("SIDE_INVALID")
    if typ not in policy.get("allowed_order_types",[]):r.append("ORDER_TYPE_NOT_ALLOWED")
    if tif not in policy.get("allowed_time_in_force",[]):r.append("TIME_IN_FORCE_NOT_ALLOWED")
    if n<=0 or n>float(policy.get("maximum_order_notional",1))+1e-9:r.append("ORDER_NOTIONAL_LIMIT_EXCEEDED")
    if not clock or clock.get("is_open") is not True:r.append("MARKET_NOT_OPEN")
    if not account or account.get("status")!="ACTIVE":r.append("ACCOUNT_NOT_ACTIVE")
    if account and (account.get("trading_blocked") or account.get("account_blocked")):r.append("ACCOUNT_BLOCKED")
    d=[x for x in orders if str(x.get("symbol","")).upper()==sym and str(x.get("side","")).upper()==side and str(x.get("status","")).lower() in {"new","accepted","pending_new","partially_filled"}]
    if d:r.append("DUPLICATE_OPEN_ORDER")
    if int(counter.get("submitted_orders",0))>=int(policy.get("maximum_daily_orders",1)):r.append("DAILY_ORDER_LIMIT_REACHED")
    if proposal.get("proposal_hash") in counter.get("proposal_hashes",[]):r.append("PROPOSAL_ALREADY_SUBMITTED")
    if policy.get("kill_switch_active") is True:r.append("KILL_SWITCH_ACTIVE")
    if policy.get("live_endpoint_enabled") is not False:r.append("LIVE_ENDPOINT_POLICY_INVALID")
    return {"allowed":not r,"blocking_reasons":r,"duplicate_open_order_count":len(d)}
