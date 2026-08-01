from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_order_submission_dryrun_v92_01_20 import DryRunConfig
DryRunConfig().validate()
p=ROOT/"release/v92_00/output/actual_paper_order_optin_certificate_v92_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V92.01-V92.20 INSTALL CHECK PASS")
