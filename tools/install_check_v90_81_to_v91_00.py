from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.final_paper_automation_certification_v90_81_v91_00 import FinalPaperAutomationCertificationConfig
FinalPaperAutomationCertificationConfig().validate()
required=[
ROOT/"release/v90_20/output/actual_paper_automation_certificate_v90_20.json",
ROOT/"release/v90_40/output/read_only_runtime_certificate_v90_40.json",
ROOT/"release/v90_60/output/actual_paper_runtime_certificate_v90_60.json",
ROOT/"release/v90_80/output/actual_paper_release_candidate_certificate_v90_80.json"]
missing=[str(p) for p in required if not p.is_file()]
if missing:raise SystemExit("MISSING SOURCE CERTIFICATES: "+", ".join(missing))
print("V90.81-V91.00 INSTALL CHECK PASS")
