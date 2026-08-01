from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.strategy_operations_rc_v87_81_v88_00 import StrategyOperationsRCConfig
StrategyOperationsRCConfig().validate()
p=R/"release/v87_80/output/strategy_execution_final_certificate_v87_80.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V87.81-V88.00 INSTALL CHECK PASS")
