from __future__ import annotations
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.paper_runtime_pipeline_v77_16_20 import *
def print_result(result):
    print(json.dumps(result.as_dict(),indent=2))
    return 0 if result.status=="PASS" else 1
