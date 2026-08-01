from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_submission_release_candidate_v92_81_v93_00 import SubmissionReleaseCandidateConfig
SubmissionReleaseCandidateConfig().validate()
p=ROOT/"release/v92_80/output/actual_paper_e2e_certificate_v92_80.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V92.81-V93.00 INSTALL CHECK PASS")
