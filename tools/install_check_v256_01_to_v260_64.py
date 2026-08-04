from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "autonomous_paper_trading/io.py",
    "autonomous_paper_trading/config.py",
    "autonomous_paper_trading/auth.py",
    "autonomous_paper_trading/alpaca_paper.py",
    "autonomous_paper_trading/idempotency.py",
    "autonomous_paper_trading/report.py",
    "autonomous_paper_trading/engine.py",
    "autonomous_paper_trading/dashboard.py",
    "web_controller/autonomous_paper_api.py",
    "tools/run_v256_01_to_v260_64.py",
    "tools/test_v256_01_to_v260_64.py",
    "tools/verify_v256_01_to_v260_64.py",
    "release/v256_01_to_v260_64/config/autonomous_paper_policy.json",
    "release/v256_01_to_v260_64/docs/AUTONOMOUS_PAPER_TRADING_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for x in missing:
    print("MISSING:", x)
if missing:
    raise SystemExit(1)
print("V256.01-V260.64 INSTALL CHECK PASS")
