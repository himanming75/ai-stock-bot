from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_scheduler_foundation_v88_01_20 import PaperSchedulerFoundationConfig
PaperSchedulerFoundationConfig().validate()
p=R/"release/v88_00/output/strategy_operations_rc_certificate_v88_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V88.01-V88.20 INSTALL CHECK PASS")
