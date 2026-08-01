from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_automation_rc2_v91_41_60 import AutomationRC2Config
AutomationRC2Config().validate()
required=[
ROOT/"release/v91_20/output/actual_paper_optin_certificate_v91_20.json",
ROOT/"release/v91_40/output/actual_paper_session_certificate_v91_40.json"]
missing=[str(p) for p in required if not p.is_file()]
if missing:raise SystemExit("MISSING SOURCE CERTIFICATES: "+", ".join(missing))
print("V91.41-V91.60 INSTALL CHECK PASS")
