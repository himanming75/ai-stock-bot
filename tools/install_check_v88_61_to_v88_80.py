from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path: sys.path.insert(0,str(R))
from alpaca_market_data.scheduler_runtime_simulation_v88_61_80 import SchedulerRuntimeSimulationConfig
SchedulerRuntimeSimulationConfig().validate()
p=R/"release/v88_60/output/market_data_operations_certificate_v88_60.json"
if not p.is_file(): raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V88.61-V88.80 INSTALL CHECK PASS")
