from pathlib import Path
import sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from alpaca_market_data.order_lifecycle_v86_21_40 import LifecycleConfig
LifecycleConfig().validate();print("V86.21-V86.40 INSTALL CHECK PASS")
