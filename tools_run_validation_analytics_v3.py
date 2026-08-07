from pathlib import Path
import json,sys
ROOT=Path(r"C:\stock-bot")
sys.path.insert(0,str(ROOT))
from validation_analytics_v3 import main_report
print(json.dumps(main_report(ROOT),indent=2,default=str))
