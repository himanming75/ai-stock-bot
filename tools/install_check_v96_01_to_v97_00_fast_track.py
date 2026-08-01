from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_execution_validation_fast_track_v96_01_v97_00 import ValidationConfig
ValidationConfig().validate()
p=ROOT/"release/v96_00/output/controlled_execution_certificate_v96_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V96.01-V97.00 FAST TRACK INSTALL CHECK PASS")
