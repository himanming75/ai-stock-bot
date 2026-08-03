from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"ai_explainability_pro/io.py",
"ai_explainability_pro/features.py",
"ai_explainability_pro/reasons.py",
"ai_explainability_pro/confidence.py",
"ai_explainability_pro/narrative.py",
"ai_explainability_pro/engine.py",
"ai_explainability_pro/dashboard.py",
"tools/run_v92_01_to_v92_32.py",
"tools/test_v92_01_to_v92_32.py",
"tools/verify_v92_01_to_v92_32.py",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

if not (ROOT/"parameter_optimizer").exists():
    print("MISSING DEPENDENCY: parameter_optimizer")
    raise SystemExit(1)

print("V92.01-V92.32 INSTALL CHECK PASS")
