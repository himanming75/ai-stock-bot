from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"multi_day_scheduler/io.py",
"multi_day_scheduler/calendar.py",
"multi_day_scheduler/session.py",
"multi_day_scheduler/queue.py",
"multi_day_scheduler/dedup.py",
"multi_day_scheduler/checkpoint.py",
"multi_day_scheduler/state.py",
"multi_day_scheduler/engine.py",
"multi_day_scheduler/dashboard.py",
"tools/run_v103_33_to_v103_64.py",
"tools/test_v103_33_to_v103_64.py",
"tools/verify_v103_33_to_v103_64.py",
"release/v103_33_to_v103_64/input/multi_day_scheduler_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

print("V103.33-V103.64 INSTALL CHECK PASS")
