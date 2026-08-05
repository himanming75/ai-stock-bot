from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_read.adapter import AlpacaLiveReadAdapter
from live_read.config import LiveReadConfig
from live_read.gates import evaluate_l2_gates
from live_read.http_guard import GetOnlyHttpGuard
from live_read.service import run_snapshot

fixture = json.loads(
    (
        ROOT / "release/l2_live_read_only_preparation/fixtures/"
               "live_read_fixture.json"
    ).read_text(encoding="utf-8-sig")
)

def transport(method: str, path: str):
    if path == "/v2/account":
        return fixture["account"]
    if path == "/v2/positions":
        return fixture["positions"]
    if path.startswith("/v2/orders"):
        return fixture["orders"]
    if path == "/v2/clock":
        return fixture["clock"]
    if path.startswith("/v2/assets/"):
        symbol = path.rsplit("/", 1)[-1]
        return fixture["assets"][symbol]
    raise KeyError(path)

config = LiveReadConfig.from_env()
config_result = config.evaluate()
gates = evaluate_l2_gates(ROOT)

adapter = AlpacaLiveReadAdapter(
    GetOnlyHttpGuard(
        network_enabled=False,
        transport=transport,
    )
)
result = run_snapshot(
    adapter,
    ["SPY"],
    mode="OFFLINE_FIXTURE_LIVE_READ_ONLY_PREPARATION",
)
result["config"] = config_result
result["gates"] = gates
result["actual_live_read_allowed"] = False

path = (
    ROOT / "release/l2_live_read_only_preparation/actual/"
           "l2_offline_qualification.json"
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(
    0 if result["status"] == "PASS" and config_result["valid"] else 1
)
