from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_session_execution_fast_track_v97_01_v98_00 import ControlledSessionConfig
ControlledSessionConfig().validate()
p=ROOT/"release/v97_00/output/controlled_validation_certificate_v97_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V97.01-V98.00 FAST TRACK INSTALL CHECK PASS")
