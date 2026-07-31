from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.portfolio_management_pipeline_v77_41_45 import *
def emit(x):print(json.dumps(x.as_dict(),indent=2));return 0 if x.status=="PASS" else 1
