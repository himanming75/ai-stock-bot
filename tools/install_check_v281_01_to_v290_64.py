from pathlib import Path
R=Path(__file__).resolve().parents[1]
req=["multi_account_engine/engine.py","multi_account_engine/config.py","web_controller/multi_account_engine_api.py","tools/run_v281_01_to_v290_64.py","tools/test_v281_01_to_v290_64.py","tools/verify_v281_01_to_v290_64.py","release/v281_01_to_v290_64/config/multi_account_policy.json","release/v281_01_to_v290_64/docs/MULTI_ACCOUNT_ENGINE_GUIDE.md"]
m=[x for x in req if not (R/x).exists()]
[print("MISSING:",x) for x in m]
if m: raise SystemExit(1)
print("V281.01-V290.64 INSTALL CHECK PASS")
