from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.strategy_execution_operations_v87_01_20 import StrategyExecutionOperationsConfig
StrategyExecutionOperationsConfig().validate()
p=R/"release/v87_00/output/operations_certificate_v87_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V87.01-V87.20 INSTALL CHECK PASS")
