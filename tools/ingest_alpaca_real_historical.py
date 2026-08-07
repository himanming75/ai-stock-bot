from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse, hashlib, json, os, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

DEFAULT_SYMBOLS=("AAPL","SPY","QQQ","MSFT","NVDA","AMZN","META","TSLA")

def digest_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def normalized_bar(symbol, timestamp, bar):
    return {
        "symbol":str(symbol).upper(),
        "timestamp":timestamp.isoformat() if hasattr(timestamp,"isoformat") else str(timestamp),
        "open":float(bar.open),
        "high":float(bar.high),
        "low":float(bar.low),
        "close":float(bar.close),
        "volume":float(bar.volume),
        "trade_count":int(bar.trade_count) if getattr(bar,"trade_count",None) is not None else None,
        "vwap":float(bar.vwap) if getattr(bar,"vwap",None) is not None else None,
    }

def fetch_real_history(root:Path, symbols, lookback_days:int=30):
    # Import only at runtime so unit tests do not need network.
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import DataFeed

    key=os.environ.get("APCA_API_KEY_ID","").strip()
    secret=os.environ.get("APCA_API_SECRET_KEY","").strip()
    if not key or not secret:
        raise RuntimeError("Alpaca market-data credentials are missing")

    end=datetime.now(timezone.utc)-timedelta(minutes=20)
    start=end-timedelta(days=lookback_days)

    client=StockHistoricalDataClient(key,secret)
    request=StockBarsRequest(
        symbol_or_symbols=list(symbols),
        timeframe=TimeFrame.Minute,
        start=start,
        end=end,
        feed=DataFeed.IEX,
    )

    bars=client.get_stock_bars(request)
    data=getattr(bars,"data",bars)

    rows=[]
    if isinstance(data,dict):
        for symbol,items in data.items():
            for bar in items:
                ts=getattr(bar,"timestamp",None)
                rows.append(normalized_bar(symbol,ts,bar))
    else:
        # DataFrame fallback if SDK representation changes.
        df=getattr(bars,"df",None)
        if df is None:
            raise RuntimeError("Unsupported Alpaca bars response")
        reset=df.reset_index()
        for _,r in reset.iterrows():
            rows.append({
                "symbol":str(r.get("symbol","")).upper(),
                "timestamp":str(r.get("timestamp","")),
                "open":float(r["open"]),
                "high":float(r["high"]),
                "low":float(r["low"]),
                "close":float(r["close"]),
                "volume":float(r["volume"]),
                "trade_count":int(r["trade_count"]) if "trade_count" in r and r["trade_count"]==r["trade_count"] else None,
                "vwap":float(r["vwap"]) if "vwap" in r and r["vwap"]==r["vwap"] else None,
            })

    rows.sort(key=lambda x:(x["timestamp"],x["symbol"]))
    if len(rows)<200:
        raise RuntimeError(f"Insufficient real historical rows: {len(rows)}")

    out=root/"runtime/real_historical_ingestion"
    out.mkdir(parents=True,exist_ok=True)
    data_path=out/"alpaca_real_historical_1min.jsonl"
    with data_path.open("w",encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r,separators=(",",":"))+"\n")

    manifest={
        "stage":"ALPACA_REAL_HISTORICAL_INGESTION_V1",
        "status":"PASS",
        "mode":"MARKET_DATA_READ_ONLY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":"ALPACA_STOCK_HISTORICAL_DATA_API",
        "feed":"IEX",
        "timeframe":"1Min",
        "symbols":sorted({r["symbol"] for r in rows}),
        "requested_symbols":list(symbols),
        "lookback_days":lookback_days,
        "start_utc":start.isoformat(),
        "end_utc":end.isoformat(),
        "row_count":len(rows),
        "timestamp_count":len({r["timestamp"] for r in rows}),
        "dataset_path":"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "dataset_sha256":digest_file(data_path),
        "provenance":{
            "actual_external_network_used":True,
            "network_requests_executed":1,
            "credentials_used":True,
            "broker_trading_client_created":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "paper_order_submission_performed":False,
            "live_order_submission_performed":False,
        },
    }
    (out/"alpaca_real_historical_manifest.json").write_text(
        json.dumps(manifest,indent=2),encoding="utf-8"
    )
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--symbols",default=",".join(DEFAULT_SYMBOLS))
    p.add_argument("--lookback-days",type=int,default=30)
    a=p.parse_args()
    syms=tuple(s.strip().upper() for s in a.symbols.split(",") if s.strip())
    print(json.dumps(fetch_real_history(Path(a.root),syms,a.lookback_days),indent=2))
