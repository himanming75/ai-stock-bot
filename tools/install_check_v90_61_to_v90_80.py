from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_release_candidate_v90_61_80 import ActualPaperReleaseCandidateConfig
ActualPaperReleaseCandidateConfig().validate()
p=ROOT/"release/v90_60/output/actual_paper_runtime_certificate_v90_60.json"
if not p.is_file(): raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V90.61-V90.80 INSTALL CHECK PASS")
