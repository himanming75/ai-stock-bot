from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_final_submission_certification_v92_41_60 import FinalSubmissionCertificationConfig
FinalSubmissionCertificationConfig().validate()
p=ROOT/"release/v92_40/output/actual_paper_gate_certificate_v92_40.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V92.41-V92.60 INSTALL CHECK PASS")
