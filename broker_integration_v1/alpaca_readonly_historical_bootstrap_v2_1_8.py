from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from market_data_engine.models import Bar


class AlpacaHistoricalBootstrapHTTPError(RuntimeError):
    def __init__(self,status,url,body,safe_headers=None):
        self.status=int(status)
        self.url=str(url)
        self.body=str(body)
        self.safe_headers=dict(safe_headers or {})
        super().__init__(f"Alpaca historical bootstrap HTTP {self.status}")


def _safe_headers(headers):
    if headers is None:
        return {}
    allowed={
        "content-type","date","server","x-request-id",
        "x-ratelimit-limit","x-ratelimit-remaining","x-ratelimit-reset",
    }
    out={}
    for k,v in headers.items():
        if str(k).lower() in allowed:
            out[str(k)]=str(v)
    return out


class AlpacaReadOnlyHistoricalBootstrapV218:
    BASE_URL="https://data.alpaca.markets/v2/stocks/bars"

    def __init__(self,feed="iex",timeout_seconds=30):
        self.feed=str(feed)
        self.timeout_seconds=int(timeout_seconds)
        self.last_diagnostics={}

    def _credentials(self):
        key=os.environ.get("APCA_API_KEY_ID")
        secret=os.environ.get("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("Alpaca market-data credentials are required.")
        return key,secret

    @staticmethod
    def _parse_ts(value):
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
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

    def _request_page(self,key,secret,params):
        url=self.BASE_URL+"?"+urlencode(params)
        req=Request(
            url,
            headers={
                "APCA-API-KEY-ID":key,
                "APCA-API-SECRET-KEY":secret,
                "Accept":"application/json",
                "User-Agent":"AI-Stock-Bot-V2.1.8.2-ReadOnlyBootstrap",
            },
            method="GET",
        )
        try:
            with urlopen(req,timeout=self.timeout_seconds) as response:
                return (
                    response.getcode(),
                    json.loads(response.read().decode("utf-8")),
                    _safe_headers(response.headers),
                )
        except HTTPError as exc:
            body=exc.read().decode("utf-8","replace")
            raise AlpacaHistoricalBootstrapHTTPError(
                exc.code,url,body,_safe_headers(exc.headers)
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Alpaca historical bootstrap transport error: {exc.reason}"
            ) from exc

    def _fetch_symbol(
        self,
        key,
        secret,
        symbol,
        bars_per_symbol,
        start,
        end,
        max_pages=20,
    ):
        params={
            "symbols":symbol,
            "timeframe":"1Min",
            "start":start.isoformat().replace("+00:00","Z"),
            "end":end.isoformat().replace("+00:00","Z"),
            "limit":1000,
            "feed":self.feed,
            "sort":"desc",
        }

        rows=[]
        page_count=0
        next_page_token=None
        status=None
        headers={}

        while True:
            page_params=dict(params)
            if next_page_token:
                page_params["page_token"]=next_page_token

            status,payload,headers=self._request_page(
                key,secret,page_params
            )
            page_count+=1

            raw_bars=payload.get("bars") or {}
            rows.extend(list(raw_bars.get(symbol) or []))

            next_page_token=payload.get("next_page_token")

            if len(rows)>=int(bars_per_symbol):
                break
            if not next_page_token:
                break
            if page_count>=int(max_pages):
                break

        rows.sort(key=lambda x:str(x["t"]))
        selected=rows[-int(bars_per_symbol):]

        return {
            "bars":[self._to_bar(symbol,row) for row in selected],
            "diagnostics":{
                "http_status":status,
                "safe_headers":headers,
                "page_count":page_count,
                "next_page_token_remaining":bool(next_page_token),
                "raw_bar_count":len(rows),
                "selected_bar_count":len(selected),
                "first_timestamp":None if not rows else str(rows[0]["t"]),
                "last_timestamp":None if not rows else str(rows[-1]["t"]),
            },
        }

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

        result={}
        symbol_diagnostics={}

        print("ALPACA REST MODE: SYMBOL-SCOPED")
        print("ALPACA REST FEED:",self.feed)

        for symbol in symbols:
            fetched=self._fetch_symbol(
                key,
                secret,
                symbol,
                int(bars_per_symbol),
                start,
                end,
            )
            result[symbol]=fetched["bars"]
            symbol_diagnostics[symbol]=fetched["diagnostics"]

            d=fetched["diagnostics"]
            print(
                f"{symbol}: "
                f"http={d['http_status']} "
                f"pages={d['page_count']} "
                f"raw={d['raw_bar_count']} "
                f"selected={d['selected_bar_count']} "
                f"next={d['next_page_token_remaining']} "
                f"first={d['first_timestamp']} "
                f"last={d['last_timestamp']}"
            )

        self.last_diagnostics={
            "mode":"SYMBOL_SCOPED",
            "feed":self.feed,
            "symbols":symbols,
            "requested_bars_per_symbol":int(bars_per_symbol),
            "lookback_days":int(lookback_days),
            "symbol_diagnostics":symbol_diagnostics,
        }

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
