from pathlib import Path
import sys
import json

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_readonly_adapter import ETradeReadOnlyAdapter
from broker_integration_v1.transport import FixtureTransport
from broker_integration_v1.integrated_status import build_broker_integration_v1_status

aid="SYNTHETIC1234"
paths={
    f"/accounts/{aid}/balance.json":{
        "BalanceResponse":{"Computed":{
            "cashAvailableForInvestment":"5000",
            "marginBuyingPower":"10000",
            "RealTimeValues":{"totalAccountValue":"7500"},
        }}
    },
    f"/accounts/{aid}/portfolio.json":{
        "PortfolioResponse":{"AccountPortfolio":[{
            "Position":[
                {"Product":{"symbol":"AAPL"},"quantity":"3","pricePaid":"200","marketValue":"630","totalGain":"30"},
                {"Product":{"symbol":"SPY"},"quantity":"1","pricePaid":"500","marketValue":"505","totalGain":"5"},
            ]
        }]}
    },
    f"/accounts/{aid}/orders.json":{"OrdersResponse":{"Order":[]}},
}

adapter=ETradeReadOnlyAdapter(FixtureTransport(paths))
snap=adapter.get_account_snapshot_from_fixture(aid)
status=build_broker_integration_v1_status()

summary={
    "account_id_masked":snap.account_id_masked,
    "equity":str(snap.equity),
    "position_count":len(snap.positions),
    "etrade_mode":status["etrade_readonly_status"],
    "network":status["network_status"],
    "live":status["live_trading_status"],
    "duplicate_contract":status["contracts"]["duplicate_broker_contract_created"],
}
print(json.dumps(summary,indent=2))

if summary["position_count"]!=2:
    raise SystemExit(2)
if summary["network"]!="LOCKED":
    raise SystemExit(3)
if summary["live"]!="LOCKED":
    raise SystemExit(4)
if summary["duplicate_contract"]:
    raise SystemExit(5)

print("BROKER V1 SYNTHETIC FIXTURE: PASS")
