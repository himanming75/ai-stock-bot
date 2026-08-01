from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.single_order_network_optin_fast_track_v94_01_v95_00 import NetworkOptInConfig
NetworkOptInConfig().validate()
p=ROOT/"release/v94_00/output/submission_fast_track_certificate_v94_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V94.01-V95.00 FAST TRACK INSTALL CHECK PASS")
