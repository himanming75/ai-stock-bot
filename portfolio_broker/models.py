from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any

@dataclass
class AccountSnapshot:
    broker_id:str
    account_id_masked:str
    mode:str
    status:str
    cash:float
    equity:float
    buying_power:float
    currency:str="USD"
    read_only:bool=True

@dataclass
class PositionSnapshot:
    broker_id:str
    account_id_masked:str
    symbol:str
    quantity:float
    market_value:float
    average_price:float
    current_price:float
    unrealized_pnl:float=0.0
    strategy_id:str="UNKNOWN"

def account_dict(value:AccountSnapshot)->dict[str,Any]:
    return asdict(value)

def position_dict(value:PositionSnapshot)->dict[str,Any]:
    return asdict(value)
