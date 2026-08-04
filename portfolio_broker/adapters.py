from __future__ import annotations
from portfolio_broker.base import BrokerAdapter
from portfolio_broker.models import AccountSnapshot,PositionSnapshot

class FixtureBrokerAdapter(BrokerAdapter):
    def __init__(self,broker_id:str,fixture:dict):
        self.broker_id=broker_id
        self.fixture=fixture
        self.read_only=True
        self.supports_orders=False

    def account(self)->AccountSnapshot:
        a=self.fixture.get("account",{})
        return AccountSnapshot(
            broker_id=self.broker_id,
            account_id_masked=str(a.get("account_id_masked","NOT_AVAILABLE")),
            mode=str(a.get("mode","READ_ONLY")),
            status=str(a.get("status","UNKNOWN")),
            cash=float(a.get("cash",0) or 0),
            equity=float(a.get("equity",0) or 0),
            buying_power=float(a.get("buying_power",0) or 0),
            currency=str(a.get("currency","USD")),
            read_only=True,
        )

    def positions(self)->list[PositionSnapshot]:
        rows=[]
        account_id=self.account().account_id_masked
        for p in self.fixture.get("positions",[]):
            rows.append(PositionSnapshot(
                broker_id=self.broker_id,
                account_id_masked=account_id,
                symbol=str(p.get("symbol","")),
                quantity=float(p.get("quantity",0) or 0),
                market_value=float(p.get("market_value",0) or 0),
                average_price=float(p.get("average_price",0) or 0),
                current_price=float(p.get("current_price",0) or 0),
                unrealized_pnl=float(p.get("unrealized_pnl",0) or 0),
                strategy_id=str(p.get("strategy_id","UNKNOWN")),
            ))
        return rows

    def orders(self)->list[dict]:
        return list(self.fixture.get("orders",[]))
