from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_broker_operations_v86_81_v87_00 import PaperBrokerOperationsConfig
PaperBrokerOperationsConfig().validate()
p=R/"release/v86_80/output/final_network_certificate_v86_80.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V86.81-V87.00 INSTALL CHECK PASS")
