from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "real_paper_micro_order/io.py",
    "real_paper_micro_order/config.py",
    "real_paper_micro_order/auth.py",
    "real_paper_micro_order/client.py",
    "real_paper_micro_order/token.py",
    "real_paper_micro_order/idempotency.py",
    "real_paper_micro_order/engine.py",
    "tools/run_v306_01_to_v310_64.py",
    "tools/test_v306_01_to_v310_64.py",
    "tools/verify_v306_01_to_v310_64.py",
    "release/v306_01_to_v310_64/config/real_paper_micro_order_policy.json",
    "release/v306_01_to_v310_64/docs/REAL_PAPER_MICRO_ORDER_VALIDATION_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    print("\n".join("MISSING: " + x for x in missing))
    raise SystemExit(1)
print("V306.01-V310.64 INSTALL CHECK PASS")
