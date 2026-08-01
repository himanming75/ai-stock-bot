from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_order_submission_gate_v92_21_40 import SubmissionGateConfig
SubmissionGateConfig().validate()
p=ROOT/"release/v92_20/output/actual_paper_dryrun_certificate_v92_20.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V92.21-V92.40 INSTALL CHECK PASS")
