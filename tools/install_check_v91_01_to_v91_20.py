from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_automation_optin_v91_01_20 import ActualPaperAutomationOptInConfig
ActualPaperAutomationOptInConfig().validate()
p=ROOT/"release/v91_00/output/final_paper_automation_certificate_v91_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V91.01-V91.20 INSTALL CHECK PASS")
