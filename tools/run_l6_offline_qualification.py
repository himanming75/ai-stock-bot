from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_qualification.certificate import write_preparation_certificate
from live_qualification.gates import evaluate_l6_gates
from live_qualification.policy import LiveLongRunPolicy
from live_qualification.service import qualify_offline

policy = LiveLongRunPolicy(
    required_cycles=3,
    maximum_failed_cycles=0,
    maximum_heartbeat_gap_seconds=300,
    require_zero_duplicate_cycles=True,
    require_zero_unresolved_drift=True,
    require_kill_switch_response=True,
    require_crash_resume_test=True,
    fail_closed=True,
)

result = qualify_offline(
    root=ROOT,
    policy=policy,
    successful_cycles=3,
    failed_cycles=0,
)
result["gates"] = evaluate_l6_gates(ROOT)
result["actual_live_long_run_allowed"] = False

actual = (
    ROOT / "release/l6_live_long_run_qualification_preparation/actual"
)
actual.mkdir(parents=True, exist_ok=True)
(actual / "l6_offline_qualification.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

certificate = write_preparation_certificate(
    actual / "l6_preparation_certificate.json",
    qualification_result=result,
)
result["certificate"] = certificate

print(json.dumps(result, indent=2, sort_keys=True))
