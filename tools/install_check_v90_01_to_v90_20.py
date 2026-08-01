from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.actual_paper_automation_v90_01_20 import ActualPaperAutomationConfig
ActualPaperAutomationConfig().validate()
p=R/"release/v90_00/output/fast_track_certificate_v90_00.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V90.01-V90.20 INSTALL CHECK PASS")
