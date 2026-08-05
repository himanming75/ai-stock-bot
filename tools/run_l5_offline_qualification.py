from pathlib import Path
import json
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_runtime.gates import evaluate_l5_gates
from live_runtime.models import LiveRuntimePolicy
from live_runtime.runtime import run_offline_live_runtime

policy = LiveRuntimePolicy(
    cycle_interval_seconds=60,
    maximum_cycles_per_session=390,
    require_market_open=True,
    fail_closed=True,
    require_l1=True,
    require_l2_actual=True,
    require_l3_actual=True,
    require_l4_actual=True,
    require_p5_actual=True,
)
policy_result = policy.evaluate()

runtime_id = f"l5-offline-{uuid.uuid4().hex[:12]}"
result = run_offline_live_runtime(
    root=ROOT,
    runtime_id=runtime_id,
    cycles=3,
    market_open=True,
)
result["policy"] = policy_result
result["gates"] = evaluate_l5_gates(ROOT)
result["actual_live_runtime_allowed"] = False

path = (
    ROOT / "release/l5_live_autonomous_runtime_preparation/actual/"
           "l5_offline_qualification.json"
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
