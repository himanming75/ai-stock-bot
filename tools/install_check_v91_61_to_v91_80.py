from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_automation_rc2_certification_v91_61_80 import RC2CertificationConfig
RC2CertificationConfig().validate()
p=ROOT/"release/v91_60/output/actual_paper_rc2_certificate_v91_60.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V91.61-V91.80 INSTALL CHECK PASS")
