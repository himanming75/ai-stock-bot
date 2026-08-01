from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.strategy_execution_reconciliation_v87_41_60 import StrategyExecutionReconciliationConfig
StrategyExecutionReconciliationConfig().validate()
p=R/"release/v87_40/output/strategy_execution_sim_certificate_v87_40.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V87.41-V87.60 INSTALL CHECK PASS")
