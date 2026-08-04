from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "final_release/io.py",
    "final_release/inventory.py",
    "final_release/readiness.py",
    "final_release/certificate.py",
    "final_release/manifest.py",
    "final_release/integrity.py",
    "final_release/acceptance.py",
    "final_release/bundle.py",
    "final_release/rollback.py",
    "final_release/engine.py",
    "final_release/dashboard.py",
    "tools/run_v105_33_to_v105_64.py",
    "tools/test_v105_33_to_v105_64.py",
    "tools/verify_v105_33_to_v105_64.py",
    "release/v105_33_to_v105_64/input/final_release_policy.json",
    "release/v105_33_to_v105_64/docs/OPERATOR_GUIDE.md",
    "release/v105_33_to_v105_64/docs/DISASTER_RECOVERY.md",
    "release/v105_33_to_v105_64/deploy/INSTALL_FINAL_RELEASE.ps1",
    "release/v105_33_to_v105_64/deploy/VERIFY_FINAL_RELEASE.ps1",
    "release/v105_33_to_v105_64/deploy/RUN_FINAL_RELEASE.ps1",
    "release/v105_33_to_v105_64/rollback/RESTORE_TO_V105_32.ps1",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)

print("V105.33-V105.64 INSTALL CHECK PASS")
