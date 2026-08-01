from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path: sys.path.insert(0,str(R))
from alpaca_market_data.position_account_reconciliation_v86_41_60 import PositionAccountReconciliationConfig
PositionAccountReconciliationConfig().validate()
print("V86.41-V86.60 INSTALL CHECK PASS")
