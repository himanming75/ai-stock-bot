from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from windows_autostart_recovery.supervisor import run

parser = argparse.ArgumentParser()
parser.add_argument("--execute-child", action="store_true")
args = parser.parse_args()
result = run(ROOT, execute_child=args.execute_child)
print(json.dumps(result, indent=2, sort_keys=True))
