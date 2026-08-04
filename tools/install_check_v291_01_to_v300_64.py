from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "paper_qualification/io.py",
    "paper_qualification/config.py",
    "paper_qualification/reconciliation.py",
    "paper_qualification/order_states.py",
    "paper_qualification/recovery.py",
    "paper_qualification/metrics.py",
    "paper_qualification/engine.py",
    "paper_qualification/dashboard.py",
    "web_controller/paper_qualification_api.py",
    "tools/run_v291_01_to_v300_64.py",
    "tools/test_v291_01_to_v300_64.py",
    "tools/verify_v291_01_to_v300_64.py",
    "release/v291_01_to_v300_64/config/paper_qualification_policy.json",
    "release/v291_01_to_v300_64/docs/PAPER_QUALIFICATION_BROKER_RECONCILIATION_GUIDE.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)
print("V291.01-V300.64 INSTALL CHECK PASS")
