from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_automation_session_v91_21_40 import SessionValidationConfig
SessionValidationConfig().validate()
p=ROOT/"release/v91_20/output/actual_paper_optin_certificate_v91_20.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V91.21-V91.40 INSTALL CHECK PASS")
