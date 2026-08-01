from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime import EndToEndPaperRuntime, PaperRuntimeRecoveryManager

assert EndToEndPaperRuntime
assert PaperRuntimeRecoveryManager

source = ROOT / "release" / "v108_00" / "output" / "runtime_risk_manager_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V108 RISK RESULT: {source}")

print("V108.01-V109.00 END-TO-END PAPER RUNTIME INSTALL CHECK PASS")
