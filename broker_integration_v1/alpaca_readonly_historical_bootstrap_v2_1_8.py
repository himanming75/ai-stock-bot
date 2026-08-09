from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from market_data_engine.models import Bar


class AlpacaReadOnlyHistoricalBootstrapV218:
    """
    Read-only Alpaca REST bootstrap for recent completed 1-minute bars.
    No trading endpoint is used.
    """

    BASE_URL="https://data.alpaca.markets/v2/stocks/bars"

    def __init__(self,feed="iex",timeout_seconds=30):
        self.feed=str(feed)
        self.timeout_seconds=int(timeout_seconds)

    def _credentials(self):
        key=os.environ.get("APCA_API_KEY_ID")
        secret=os.environ.get("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("Alpaca market-data credentials are required.")
        return key,secret

    @staticmethod
    def _parse_ts(value):
        text=str(value)
        dt=datetime.fromisoformat(text.replace("Z","+00:00"))
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def _to_bar(cls,symbol,row):
        return Bar(
            symbol=symbol,
            timestamp=cls._parse_ts(row["t"]),
            open=Decimal(str(row["o"])),
            high=Decimal(str(row["h"])),
            low=Decimal(str(row["l"])),
            close=Decimal(str(row["c"])),
            volume=int(row["v"]),
            trade_count=None if row.get("n") is None else int(row["n"]),
            vwap=None if row.get("vw") is None else Decimal(str(row["vw"])),
        )

    def fetch_recent_completed_bars(
        self,
        symbols,
        bars_per_symbol=3,
        lookback_days=7,
    ):
        symbols=sorted({str(x).upper().strip() for x in symbols if str(x).strip()})
        if not symbols:
            raise ValueError("At least one symbol is required.")
        if not 3 <= int(bars_per_symbol) <= 50:
            raise ValueError("bars_per_symbol must be between 3 and 50.")
        if not 1 <= int(lookback_days) <= 30:
            raise ValueError("lookback_days must be between 1 and 30.")

        key,secret=self._credentials()
        end=datetime.now(timezone.utc)-timedelta(minutes=2)
        start=end-timedelta(days=int(lookback_days))

        params={
            "symbols":",".join(symbols),
            "timeframe":"1Min",
            "start":start.isoformat().replace("+00:00","Z"),
            "end":end.isoformat().replace("+00:00","Z"),
            "limit":min(10000,max(100,int(bars_per_symbol)*len(symbols)*20)),
            "feed":self.feed,
            "sort":"desc",
        }

        req=Request(
            self.BASE_URL+"?"+urlencode(params),
            headers={
                "APCA-API-KEY-ID":key,
                "APCA-API-SECRET-KEY":secret,
                "Accept":"application/json",
                "User-Agent":"AI-Stock-Bot-V2.1.8-ReadOnlyBootstrap",
            },
            method="GET",
        )

        with urlopen(req,timeout=self.timeout_seconds) as response:
            payload=json.loads(response.read().decode("utf-8"))

        raw_bars=payload.get("bars") or {}
        result={}
        for symbol in symbols:
            rows=list(raw_bars.get(symbol) or [])
            rows.sort(key=lambda x:str(x["t"]))
            selected=rows[-int(bars_per_symbol):]
            result[symbol]=[self._to_bar(symbol,row) for row in selected]

        missing={
            s:len(result.get(s,[]))
            for s in symbols
            if len(result.get(s,[]))<int(bars_per_symbol)
        }
        if missing:
            raise RuntimeError(
                "Historical bootstrap did not return enough bars: "
                +str(missing)
            )

        return result


def flatten_bootstrap_map(bar_map):
    out=[]
    for symbol in sorted(bar_map):
        out.extend(sorted(bar_map[symbol],key=lambda x:x.timestamp))
    return out
