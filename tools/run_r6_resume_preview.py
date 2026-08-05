from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_session.service import resume_preview

result = resume_preview(ROOT)
print(json.dumps(result, indent=2, sort_keys=True))
