from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.multi_session_validation_fast_track_v98_01_v99_00 import MultiSessionConfig
MultiSessionConfig().validate()
p=ROOT/"release/v98_00/output/controlled_session_certificate_v98_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V98.01-V99.00 FAST TRACK INSTALL CHECK PASS")
