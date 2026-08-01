from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_order_submission_optin_v91_81_v92_00 import OrderSubmissionOptInConfig
OrderSubmissionOptInConfig().validate()
p=ROOT/"release/v91_80/output/actual_paper_rc2_certification_v91_80.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V91.81-V92.00 INSTALL CHECK PASS")
