from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.p4_offline_cycle import OfflineCanonicalCycle
from broker_integration.p4_paths import P4Paths
from broker_integration.p4_runtime import AutonomousPaperRuntime
from broker_integration.p4_runtime_models import RuntimePolicy
from broker_integration.p4_state import write_json


paths = P4Paths(ROOT)
policy = RuntimePolicy(
    cycle_interval_seconds=1,
    maximum_cycles_per_session=3,
    require_market_open=True,
    require_p2_actual_validation=False,
    require_p3_actual_validation=False,
    fail_closed=True,
)

runtime = AutonomousPaperRuntime(
    root=ROOT,
    policy=policy,
    paths=paths.as_mapping(),
    market_clock_reader=lambda: {"is_open": True},
    kill_switch_reader=lambda: {"kill_switch_active": False},
    validation_reader=lambda: {
        "p2_actual_validated": False,
        "p3_actual_validated": False,
    },
    cycle_executor=OfflineCanonicalCycle(),
    sleeper=lambda _: None,
    runtime_id="p4-offline-qualification",
)
result = runtime.run()
write_json(paths.latest_result, result)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
