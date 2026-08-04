from __future__ import annotations
from abc import ABC,abstractmethod
from portfolio_broker.models import AccountSnapshot,PositionSnapshot

class BrokerAdapter(ABC):
    broker_id="UNKNOWN"
    read_only=True
    supports_orders=False

    @abstractmethod
    def account(self)->AccountSnapshot: ...

    @abstractmethod
    def positions(self)->list[PositionSnapshot]: ...

    @abstractmethod
    def orders(self)->list[dict]: ...

    def submit_order(self,payload:dict)->dict:
        return {
            "ok":False,
            "error":"BROKER_WRITE_DISABLED",
            "broker_id":self.broker_id,
            "actual_live_orders_submitted":0,
        }
