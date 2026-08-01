from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.submission_enablement_fast_track_v93_01_v94_00 import FastTrackConfig
FastTrackConfig().validate()
p=ROOT/"release/v93_00/output/actual_paper_submission_rc_certificate_v93_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V93.01-V94.00 FAST TRACK INSTALL CHECK PASS")
