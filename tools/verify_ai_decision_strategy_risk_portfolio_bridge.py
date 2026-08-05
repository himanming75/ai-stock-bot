from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release/ai_decision_strategy_risk_portfolio_bridge/actual/bridge_snapshot.json"

def main() -> int:
    t = subprocess.run([sys.executable,"-m","unittest","tools.test_ai_decision_strategy_risk_portfolio_bridge","-v"],cwd=ROOT)
    if t.returncode: print("VERIFY: FAIL (unit tests)"); return t.returncode
    r = subprocess.run([sys.executable,"tools/run_ai_decision_strategy_risk_portfolio_bridge.py"],cwd=ROOT)
    if r.returncode: print("VERIFY: FAIL (runner)"); return r.returncode
    p = json.loads(OUT.read_text(encoding="utf-8"))
    required = {"actual_external_network_used":False,"actual_broker_write_performed":False,"actual_order_submission_performed":False,"actual_paper_orders_submitted":0,"actual_live_orders_submitted":0}
    failed=[k for k,v in required.items() if p.get(k)!=v]
    if p.get("status")!="PASS" or failed: print("VERIFY: FAIL",failed); return 1
    print("VERIFY: PASS"); print("NETWORK: OFF"); print("BROKER WRITE: OFF"); print("PAPER ORDERS: 0"); print("LIVE ORDERS: 0")
    return 0
if __name__=="__main__": raise SystemExit(main())
