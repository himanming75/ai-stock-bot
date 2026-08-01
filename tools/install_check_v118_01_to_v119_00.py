from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_certification import (
    ContinuousRuntimeFinalCertifier,
    RuntimeIntegrityValidator,
    RuntimeStressRunner,
)

assert ContinuousRuntimeFinalCertifier
assert RuntimeIntegrityValidator
assert RuntimeStressRunner

source = (
    ROOT / "release" / "v118_00" / "output"
    / "continuous_paper_runtime_release_candidate_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V118 RELEASE CANDIDATE RESULT: {source}")

print("V118.01-V119.00 CONTINUOUS PAPER RUNTIME FINAL CERTIFICATION INSTALL CHECK PASS")
