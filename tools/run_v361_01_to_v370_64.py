from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from controlled_paper_execution.engine import execute
from controlled_paper_execution.io import read_json
from controlled_paper_execution.policy import load,validate
p=argparse.ArgumentParser();p.add_argument("--proposal",default="release/v351_01_to_v360_64/actual/latest_paper_order_proposal.json");p.add_argument("--allow-paper-network",action="store_true");p.add_argument("--enable-phrase",default="");a=p.parse_args()
policy=load(ROOT);v=validate(policy)
if not v["valid"]:
 print(json.dumps({"stage":"V370.64","state":"CONTROLLED_PAPER_EXECUTION_BLOCKED","status":"PASS","blocking_reasons":["POLICY_NOT_SAFE_FOR_INSTALL_DEFAULT"]+v["failed"],"actual_paper_orders_submitted":0,"actual_live_orders_submitted":0},indent=2,sort_keys=True));raise SystemExit(0)
r=execute(ROOT,read_json(ROOT/a.proposal),policy,a.enable_phrase,a.allow_paper_network);print(json.dumps(r,indent=2,sort_keys=True))
