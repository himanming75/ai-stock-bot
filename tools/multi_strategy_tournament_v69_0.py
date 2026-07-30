from __future__ import annotations
import argparse, hashlib, json
from decimal import Decimal
from pathlib import Path

VERSION="69.0"
SCHEMA_VERSION="v69.0.multi_strategy_tournament.1"

class TournamentError(ValueError): pass

def canonical_json(x):
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def sha256_of(x):
    return hashlib.sha256(canonical_json(x).encode()).hexdigest()

def read_json(path):
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise TournamentError(f"file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise TournamentError(f"invalid JSON: {path}") from e
    if not isinstance(data,dict): raise TournamentError("top-level JSON must be an object")
    return data

def D(x): return Decimal(str(x))

def validate_v68(r,name):
    if r.get("status")!="PASS": raise TournamentError(f"{name}: status must be PASS")
    if r.get("pipeline_status")!="PASS": raise TournamentError(f"{name}: pipeline_status must be PASS")
    if r.get("network_used") is not False: raise TournamentError(f"{name}: network_used must be false")
    if r.get("approved_for_live") is not False: raise TournamentError(f"{name}: approved_for_live must be false")
    if r.get("schema_version")!="v68.0.analytics_pipeline_orchestrator.1":
        raise TournamentError(f"{name}: unsupported schema")
    overall=r.get("analytics",{}).get("overall")
    if not isinstance(overall,dict): raise TournamentError(f"{name}: missing analytics.overall")
    for k in ("trade_count","win_rate","profit_factor","expectancy","net_pnl"):
        if k not in overall: raise TournamentError(f"{name}: missing {k}")
    if r.get("closed_trade_count")!=overall["trade_count"]:
        raise TournamentError(f"{name}: closed trade count mismatch")

def inferred_name(r,fallback):
    ranking=r.get("analytics",{}).get("strategy_ranking",[])
    if isinstance(ranking,list) and len(ranking)==1 and ranking[0].get("strategy"):
        return str(ranking[0]["strategy"])
    return fallback

def score(win_rate,profit_factor,expectancy,trade_count):
    return win_rate*D(40)+min(profit_factor,D(10))*D(20)+expectancy*D(2)+min(D(trade_count)/D(100),D(1))*D(10)

def candidate(r,source,explicit=None):
    validate_v68(r,source)
    o=r["analytics"]["overall"]
    name=explicit or inferred_name(r,source)
    count=int(o["trade_count"]); wr=D(o["win_rate"]); pf=D(o["profit_factor"]); ex=D(o["expectancy"]); pnl=D(o["net_pnl"])
    gate=str(r.get("quality_gate",{}).get("quality_gate","UNKNOWN"))
    promotion=str(r.get("promotion",{}).get("promotion_state","UNKNOWN"))
    eligible=gate in {"APPROVE","WATCH"} and promotion in {"EXTENDED_PAPER_APPROVED","WATCHLIST"} and count>=20
    c={"strategy":name,"source_name":source,"eligible":eligible,"trade_count":count,
       "win_rate":f"{wr:.6f}","profit_factor":f"{pf:.6f}","expectancy":f"{ex:.4f}",
       "net_pnl":f"{pnl:.4f}","quality_gate":gate,"promotion_state":promotion,
       "tournament_score":f"{score(wr,pf,ex,count):.6f}",
       "source_pipeline_report_sha256":r.get("pipeline_report_sha256"),
       "network_used":False,"approved_for_live":False}
    c["candidate_sha256"]=sha256_of(c)
    return c

def build_tournament(items,minimum_candidates=2):
    if minimum_candidates<1: raise TournamentError("minimum_candidates must be at least 1")
    if len(items)<minimum_candidates: raise TournamentError(f"at least {minimum_candidates} candidates are required")
    cs=[candidate(r,s,n) for s,r,n in items]
    names=[c["strategy"] for c in cs]
    if len(names)!=len(set(names)): raise TournamentError("strategy names must be unique")
    ranked=sorted(cs,key=lambda x:(x["eligible"],D(x["tournament_score"]),D(x["expectancy"]),D(x["profit_factor"]),D(x["win_rate"]),D(x["net_pnl"]),x["strategy"]),reverse=True)
    for i,row in enumerate(ranked,1): row["rank"]=i
    eligible=[x for x in ranked if x["eligible"]]
    champion=eligible[0]["strategy"] if eligible else None
    report={"status":"PASS","decision":"strategy_champion_selected" if champion else "no_eligible_strategy",
            "tournament_state":"CHAMPION_SELECTED" if champion else "NO_ELIGIBLE_STRATEGY",
            "candidate_count":len(ranked),"eligible_candidate_count":len(eligible),
            "champion_strategy":champion,"runner_up_strategy":eligible[1]["strategy"] if len(eligible)>1 else None,
            "ranking":ranked,"requires_walk_forward_validation":True,
            "network_used":False,"approved_for_live":False,
            "schema_version":SCHEMA_VERSION,"version":VERSION}
    report["tournament_report_sha256"]=sha256_of(report)
    return report

def parse_input(raw):
    if "=" in raw:
        n,p=raw.split("=",1)
        if not n.strip() or not p.strip(): raise TournamentError("invalid named input")
        return n.strip(),Path(p.strip())
    return None,Path(raw)

def run(raw_inputs,output,minimum_candidates=2):
    items=[]
    for raw in raw_inputs:
        name,path=parse_input(raw)
        items.append((path.stem,read_json(path),name))
    report=build_tournament(items,minimum_candidates)
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--input",action="append",required=True)
    p.add_argument("--minimum-candidates",type=int,default=2)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        r=run(a.input,a.output,a.minimum_candidates)
    except Exception as e:
        print(json.dumps({"status":"FAIL","decision":"strategy_tournament_failed","error":str(e),
                          "network_used":False,"approved_for_live":False,"version":VERSION},indent=2))
        return 1
    winner=next((x for x in r["ranking"] if x["strategy"]==r["champion_strategy"]),None)
    print(json.dumps({"status":r["status"],"decision":r["decision"],"candidate_count":r["candidate_count"],
                      "eligible_candidate_count":r["eligible_candidate_count"],"champion_strategy":r["champion_strategy"],
                      "runner_up_strategy":r["runner_up_strategy"],"champion_score":winner["tournament_score"] if winner else None,
                      "requires_walk_forward_validation":True,"approved_for_live":False,"network_used":False,
                      "tournament_report_sha256":r["tournament_report_sha256"]},indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
