from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.strategy_execution_final_certification_v87_61_80 import StrategyExecutionFinalCertificationConfig
StrategyExecutionFinalCertificationConfig().validate()
for p in ["release/v87_20/output/strategy_execution_certificate_v87_20.json",
          "release/v87_40/output/strategy_execution_sim_certificate_v87_40.json",
          "release/v87_60/output/strategy_execution_recon_certificate_v87_60.json"]:
 if not (R/p).is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+p)
print("V87.61-V87.80 INSTALL CHECK PASS")
