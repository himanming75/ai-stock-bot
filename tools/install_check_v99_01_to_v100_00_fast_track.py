from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.final_production_candidate_fast_track_v99_01_v100_00 import FinalCandidateConfig
FinalCandidateConfig().validate()
p=ROOT/"release/v99_00/output/multi_session_certificate_v99_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V99.01-V100.00 FAST TRACK INSTALL CHECK PASS")
