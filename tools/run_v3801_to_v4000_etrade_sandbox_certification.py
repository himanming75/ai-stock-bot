from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from multi_broker_etrade_sandbox_cert.service import ETradeSandboxReadCertificationService
result=ETradeSandboxReadCertificationService().evaluate(output_dir=Path("release/v3801_4000_etrade_sandbox_certification/actual"))
print(json.dumps(result,indent=2,sort_keys=True))
raise SystemExit(0 if result["status"]=="PASS" else 2)
