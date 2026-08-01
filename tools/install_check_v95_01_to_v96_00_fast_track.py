from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_execution_fast_track_v95_01_v96_00 import ControlledExecutionConfig
ControlledExecutionConfig().validate()
p=ROOT/"release/v95_00/output/single_order_network_optin_certificate_v95_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V95.01-V96.00 FAST TRACK INSTALL CHECK PASS")
