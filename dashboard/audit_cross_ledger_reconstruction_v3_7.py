from datetime import datetime, timezone
from pathlib import Path
import argparse, importlib.util, json
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def main():
    p=argparse.ArgumentParser(); p.add_argument("--root",default=r"C:\stock-bot"); p.add_argument("--write",action="store_true"); a=p.parse_args(); root=Path(a.root)
    analytics=load(root/"dashboard"/"trade_analytics_v3_5.py","v37_audit"); trades,sources=analytics.collect_closed_trades(root); r=getattr(analytics.collect_closed_trades,"last_reconstruction_audit",{}); numeric=[t for t in trades if t.get("pnl") is not None]
    report={"stage":"V3.7_CROSS_LEDGER_TRADE_RECONSTRUCTION","generated_at_utc":datetime.now(timezone.utc).isoformat(),"status":r.get("status","NOT_RUN"),"closed_trade_sources":sources,"closed_trade_count":len(trades),"numeric_trade_count_after_reconstruction":len(numeric),"net_reconstructed_and_original_pnl":sum(t["pnl"] for t in numeric) if numeric else None,"reconstruction":r,"contracts":{"runtime_source_files_modified":False,"broker_network_used":False,"broker_write_performed":False,"order_submission_performed":False,"price_guessing_used":False}}
    if a.write:
        out=root/"runtime"/"dashboard_cross_ledger_v3_7"/"latest_cross_ledger_reconstruction.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    print(json.dumps(report,indent=2,default=str)); return 0
if __name__=="__main__": raise SystemExit(main())
