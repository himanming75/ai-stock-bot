from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"alpaca_paper_operations/io.py","alpaca_paper_operations/config.py",
"alpaca_paper_operations/http_client.py","alpaca_paper_operations/client.py",
"alpaca_paper_operations/mock.py","alpaca_paper_operations/normalize.py",
"alpaca_paper_operations/order_gate.py","alpaca_paper_operations/qualification.py",
"alpaca_paper_operations/engine.py","alpaca_paper_operations/dashboard.py",
"tools/run_v121_01_to_v123_64.py","tools/test_v121_01_to_v123_64.py",
"tools/verify_v121_01_to_v123_64.py",
"release/v121_01_to_v123_64/input/alpaca_paper_policy.json",
"release/v121_01_to_v123_64/input/alpaca_mock_fixture.json",
"release/v121_01_to_v123_64/docs/ALPACA_PAPER_SETUP_GUIDE.md",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V121.01-V123.64 INSTALL CHECK PASS")
