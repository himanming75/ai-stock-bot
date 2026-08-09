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
        "content-type",
        "date",
        "server",
        "x-request-id",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
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

    def _request_page(self,key,secret,params):
        url=self.BASE_URL+"?"+urlencode(params)
        req=Request(
            url,
            headers={
                "APCA-API-KEY-ID":key,
                "APCA-API-SECRET-KEY":secret,
                "Accept":"application/json",
                "User-Agent":"AI-Stock-Bot-V2.1.8.1-ReadOnlyBootstrap",
            },
            method="GET",
        )
        try:
            with urlopen(req,timeout=self.timeout_seconds) as response:
                return (
                    response.getcode(),
                    json.loads(response.read().decode("utf-8")),
                    _safe_headers(response.headers),
                    url,
                )
        except HTTPError as exc:
            try:
                body=exc.read().decode("utf-8","replace")
            except Exception:
                body="<unable to read response body>"
            raise AlpacaHistoricalBootstrapHTTPError(
                exc.code,url,body,_safe_headers(exc.headers)
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"Alpaca historical bootstrap transport error: {exc.reason}") from exc

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

        all_rows={s:[] for s in symbols}
        page_count=0
        next_page_token=None
        first_status=None
        first_headers={}

        while True:
            page_params=dict(params)
            if next_page_token:
                page_params["page_token"]=next_page_token

            status,payload,headers,url=self._request_page(
                key,secret,page_params
            )
            page_count+=1
            if first_status is None:
                first_status=status
                first_headers=headers

            raw_bars=payload.get("bars") or {}
            for symbol in symbols:
                rows=list(raw_bars.get(symbol) or [])
                all_rows[symbol].extend(rows)

            next_page_token=payload.get("next_page_token")
            if not next_page_token:
                break

            if all(len(all_rows[s])>=int(bars_per_symbol) for s in symbols):
                break

            if page_count>=20:
                break

        result={}
        symbol_diagnostics={}

        for symbol in symbols:
            rows=all_rows[symbol]
            rows.sort(key=lambda x:str(x["t"]))
            selected=rows[-int(bars_per_symbol):]
            result[symbol]=[self._to_bar(symbol,row) for row in selected]

            symbol_diagnostics[symbol]={
                "raw_bar_count":len(rows),
                "selected_bar_count":len(selected),
                "first_timestamp":None if not rows else str(rows[0]["t"]),
                "last_timestamp":None if not rows else str(rows[-1]["t"]),
            }

        self.last_diagnostics={
            "http_status":first_status,
            "safe_headers":first_headers,
            "page_count":page_count,
            "final_next_page_token_present":bool(next_page_token),
            "feed":self.feed,
            "symbols":symbols,
            "requested_bars_per_symbol":int(bars_per_symbol),
            "lookback_days":int(lookback_days),
            "symbol_diagnostics":symbol_diagnostics,
        }

        print("ALPACA REST HTTP STATUS:",first_status)
        print("ALPACA REST FEED:",self.feed)
        print("ALPACA REST PAGE COUNT:",page_count)
        print("NEXT PAGE TOKEN REMAINING:",bool(next_page_token))
        for symbol in symbols:
            d=symbol_diagnostics[symbol]
            print(
                f"{symbol}: raw={d['raw_bar_count']} "
                f"selected={d['selected_bar_count']} "
                f"first={d['first_timestamp']} "
                f"last={d['last_timestamp']}"
            )

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
