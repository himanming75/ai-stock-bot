from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_e2e_submission_certification_v92_61_80 import E2ECertificationConfig
E2ECertificationConfig().validate()
required=[
ROOT/"release/v92_00/output/actual_paper_order_optin_certificate_v92_00.json",
ROOT/"release/v92_20/output/actual_paper_dryrun_certificate_v92_20.json",
ROOT/"release/v92_40/output/actual_paper_gate_certificate_v92_40.json",
ROOT/"release/v92_60/output/actual_paper_final_submission_certificate_v92_60.json"]
missing=[str(p) for p in required if not p.is_file()]
if missing:raise SystemExit("MISSING SOURCE CERTIFICATES: "+", ".join(missing))
print("V92.61-V92.80 INSTALL CHECK PASS")
