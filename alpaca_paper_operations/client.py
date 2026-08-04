from __future__ import annotations
from typing import Any
from urllib.parse import urlencode

from alpaca_paper_operations.config import (
    PAPER_TRADING_BASE_URL,MARKET_DATA_BASE_URL
)
from alpaca_paper_operations.http_client import request_json

class AlpacaPaperClient:
    def __init__(self,headers:dict[str,str]) -> None:
        self.headers=headers

    def account(self):
        return request_json(
            "GET",f"{PAPER_TRADING_BASE_URL}/v2/account",self.headers
        )

    def positions(self):
        return request_json(
            "GET",f"{PAPER_TRADING_BASE_URL}/v2/positions",self.headers
        )

    def orders(self,status:str="all",limit:int=100):
        query=urlencode({"status":status,"limit":limit,"direction":"desc"})
        return request_json(
            "GET",f"{PAPER_TRADING_BASE_URL}/v2/orders?{query}",self.headers
        )

    def clock(self):
        return request_json(
            "GET",f"{PAPER_TRADING_BASE_URL}/v2/clock",self.headers
        )

    def snapshots(self,symbols:list[str],feed:str="iex"):
        query=urlencode({"symbols":",".join(symbols),"feed":feed})
        return request_json(
            "GET",f"{MARKET_DATA_BASE_URL}/v2/stocks/snapshots?{query}",
            self.headers,
        )

    def submit_order(self,payload:dict[str,Any]):
        return request_json(
            "POST",f"{PAPER_TRADING_BASE_URL}/v2/orders",
            self.headers,payload=payload,
        )

    def cancel_order(self,order_id:str):
        return request_json(
            "DELETE",f"{PAPER_TRADING_BASE_URL}/v2/orders/{order_id}",
            self.headers,
        )
