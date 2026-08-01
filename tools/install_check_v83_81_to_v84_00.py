from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_broker_final_cert_v83_81_v84_00.py","tools/run_v83_81_to_v84_00_pipeline.py","tools/test_paper_broker_final_cert_v83_81_to_v84_00.py","tools/verify_v83_81_to_v84_00_pipeline.py","release/v83_81/config/paper_broker_final_cert_config_v83_81.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_broker_final_cert_v83_81_v84_00").PaperBrokerFinalCertificationConfig().validate()
print("V83.81-V84.00 INSTALL CHECK PASS")
