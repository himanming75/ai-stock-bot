from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.final_network_certification_v86_61_80 import FinalNetworkCertificationConfig
FinalNetworkCertificationConfig().validate()
for p in ["release/v86_20/output/single_order_certificate_v86_20.json","release/v86_40/output/lifecycle_certificate_v86_40.json","release/v86_60/output/position_account_certificate_v86_60.json"]:
 if not (R/p).is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+p)
print("V86.61-V86.80 INSTALL CHECK PASS")
