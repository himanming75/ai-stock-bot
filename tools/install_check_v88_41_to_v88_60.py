from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.market_data_operations_v88_41_60 import MarketDataOperationsConfig
MarketDataOperationsConfig().validate()
p=R/"release/v88_40/output/runtime_loop_certificate_v88_40.json"
if not p.is_file():raise SystemExit("MISSING SOURCE CERTIFICATE: "+str(p))
print("V88.41-V88.60 INSTALL CHECK PASS")
