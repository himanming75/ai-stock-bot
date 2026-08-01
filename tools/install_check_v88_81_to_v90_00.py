from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path: sys.path.insert(0,str(R))
from alpaca_market_data.fast_track_v88_81_v90_00 import FastTrackConfig
FastTrackConfig().validate()
required=[
"release/v88_20/output/scheduler_foundation_certificate_v88_20.json",
"release/v88_40/output/runtime_loop_certificate_v88_40.json",
"release/v88_60/output/market_data_operations_certificate_v88_60.json",
"release/v88_80/output/scheduler_runtime_sim_certificate_v88_80.json"]
missing=[p for p in required if not (R/p).is_file()]
if missing: raise SystemExit("MISSING SOURCE CERTIFICATES: "+", ".join(missing))
print("V88.81-V90.00 FAST TRACK INSTALL CHECK PASS")
