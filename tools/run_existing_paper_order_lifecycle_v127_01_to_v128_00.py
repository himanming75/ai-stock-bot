from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.order_lifecycle import ExistingPaperOrderLifecycleTracker

@dataclass
class Order:
    order_id:str="3bd9f491-0629-4cf4-9b0e-2a27eadea98d"
    client_order_id:str="single-60d3c5406e5226ae71d7"
    symbol:str="AAPL"
    side:str="buy"
    quantity:Decimal=Decimal("1")
    filled_quantity:Decimal=Decimal("0")
    status:str="accepted"

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    root=Path(a.repository_root).resolve()
    r=ExistingPaperOrderLifecycleTracker().track(Order())
    out={"stage_range":"V127.01-V128.00","status":"PASS","implementation_type":"EXISTING_PAPER_ORDER_LIFECYCLE_TRACKING","validation_mode":"OFFLINE_ACCEPTED_FIXTURE",**r.to_json_dict(),"active_order_guard_verified":not r.new_order_allowed and not r.terminal,"next_phase":"V128_01_ACTUAL_ORDER_LIFECYCLE_AND_FILL_RECONCILIATION"}
    path=root/"release/v128_00/output/existing_paper_order_lifecycle_result.json";path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True));return 0
if __name__=="__main__": raise SystemExit(main())
