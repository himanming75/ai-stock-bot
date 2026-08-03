from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
required=[
"dashboard_analytics_v3/io.py","dashboard_analytics_v3/analytics.py",
"dashboard_analytics_v3/render.py","dashboard_analytics_v3/app.py",
"tools/export_dashboard_analytics_v3.py","tools/test_v90_01_to_v90_32.py",
"tools/verify_v90_01_to_v90_32.py","RUN_V90_01_TO_V90_32_DASHBOARD_V3.ps1"
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V90.01-V90.32 INSTALL CHECK PASS")
