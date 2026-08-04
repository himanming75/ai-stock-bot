from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "release/v321_01_to_v330_64/config/real_paper_long_run_policy.json"

if not POLICY.exists():
    raise SystemExit(f"Policy file not found: {POLICY}")

try:
    policy = json.loads(POLICY.read_text(encoding="utf-8-sig"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Unable to read policy: {exc}")

policy.update({
    "stage": "V330.64",
    "paper_base_url": "https://paper-api.alpaca.markets",
    "qualification_enabled": True,
    "maximum_new_orders_per_day": 0,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False,
    "monitor_only": True,
})

POLICY.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("V321.01A policy repaired and saved as UTF-8 without BOM.")
print("Paper submission: OFF")
print("Live submission: OFF")
print("Broker write: OFF")
print("Monitor only: ON")
