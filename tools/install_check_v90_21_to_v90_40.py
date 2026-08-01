from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.actual_paper_read_runtime_v90_21_40 import ReadOnlyRuntimeConfig
ReadOnlyRuntimeConfig().validate()
p=R/"release/v90_20/output/actual_paper_automation_certificate_v90_20.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V90.21-V90.40 INSTALL CHECK PASS")
