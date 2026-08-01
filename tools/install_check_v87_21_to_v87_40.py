from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.strategy_execution_simulation_v87_21_40 import StrategyExecutionSimulationConfig
StrategyExecutionSimulationConfig().validate()
p=R/"release/v87_20/output/strategy_execution_certificate_v87_20.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V87.21-V87.40 INSTALL CHECK PASS")
