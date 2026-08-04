from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "real_paper_data_collection/io.py",
    "real_paper_data_collection/config.py",
    "real_paper_data_collection/auth.py",
    "real_paper_data_collection/client.py",
    "real_paper_data_collection/normalize.py",
    "real_paper_data_collection/metrics.py",
    "real_paper_data_collection/reconcile.py",
    "real_paper_data_collection/collector.py",
    "real_paper_data_collection/session.py",
    "web_controller/real_paper_data_collection_api.py",
    "tools/run_v311_01_to_v320_64.py",
    "tools/test_v311_01_to_v320_64.py",
    "tools/verify_v311_01_to_v320_64.py",
    "release/v311_01_to_v320_64/config/real_paper_data_collection_policy.json",
    "release/v311_01_to_v320_64/docs/REAL_PAPER_AUTONOMOUS_DATA_COLLECTION_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    print("\n".join("MISSING: " + x for x in missing))
    raise SystemExit(1)
print("V311.01-V320.64 INSTALL CHECK PASS")
