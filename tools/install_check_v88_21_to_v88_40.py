from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.strategy_runtime_loop_v88_21_40 import StrategyRuntimeLoopConfig
StrategyRuntimeLoopConfig().validate()
p=R/"release/v88_20/output/scheduler_foundation_certificate_v88_20.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V88.21-V88.40 INSTALL CHECK PASS")
