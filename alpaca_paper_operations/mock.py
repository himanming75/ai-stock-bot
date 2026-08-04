from __future__ import annotations
from typing import Any
from alpaca_paper_operations.http_client import HttpResult

class MockAlpacaPaperClient:
    def __init__(self,fixture:dict[str,Any]) -> None:
        self.fixture=fixture
        self.submitted=[]

    def _r(self,key:str):
        return HttpResult(200,self.fixture.get(key,{}),{"X-Request-ID":"mock"})

    def account(self): return self._r("account")
    def positions(self): return self._r("positions")
    def orders(self,status="all",limit=100): return self._r("orders")
    def clock(self): return self._r("clock")
    def snapshots(self,symbols,feed="iex"): return self._r("snapshots")
    def submit_order(self,payload):
        order={
            "id":"mock-paper-order-1",
            "client_order_id":payload.get("client_order_id"),
            "symbol":payload.get("symbol"),
            "qty":payload.get("qty"),
            "side":payload.get("side"),
            "type":payload.get("type"),
            "time_in_force":payload.get("time_in_force"),
            "status":"accepted",
        }
        self.submitted.append(order)
        return HttpResult(200,order,{"X-Request-ID":"mock-submit"})
    def cancel_order(self,order_id):
        return HttpResult(204,{},{"X-Request-ID":"mock-cancel"})
