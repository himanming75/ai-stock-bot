from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/live_broker_final_cert_v84_81_v85_00.py","tools/run_v84_81_to_v85_00_pipeline.py","tools/test_live_broker_final_cert_v84_81_to_v85_00.py","tools/verify_v84_81_to_v85_00_pipeline.py","release/v84_81/config/live_broker_final_cert_config_v84_81.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.live_broker_final_cert_v84_81_v85_00").LiveBrokerFinalCertificationConfig().validate()
print("V84.81-V85.00 INSTALL CHECK PASS")
