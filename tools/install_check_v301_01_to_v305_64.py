from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "real_paper_validation/io.py",
    "real_paper_validation/config.py",
    "real_paper_validation/auth.py",
    "real_paper_validation/client.py",
    "real_paper_validation/engine.py",
    "tools/run_v301_01_to_v305_64.py",
    "tools/test_v301_01_to_v305_64.py",
    "tools/verify_v301_01_to_v305_64.py",
    "release/v301_01_to_v305_64/config/real_paper_validation_policy.json",
    "release/v301_01_to_v305_64/docs/REAL_PAPER_VALIDATION_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    print("\n".join("MISSING: " + x for x in missing))
    raise SystemExit(1)
print("V301.01-V305.64 INSTALL CHECK PASS")
