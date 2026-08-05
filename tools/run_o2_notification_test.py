from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.notifications import (
    NotificationCenter,
    load_notification_config,
)

result = NotificationCenter(load_notification_config()).send(
    "AI Stock Bot Test",
    "Notification Center installation test.",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] in {"DISABLED", "PASS"} else 1)
