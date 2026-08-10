from __future__ import annotations

import json
import math
import os
import time
import hashlib
import urllib.parse
import urllib.request
import urllib.error
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA_BASE="https://data.alpaca.markets"
DEFAULT_HORIZONS=(5,15,30,60)


def _utcnow():
    return datetime.now(timezone.utc)


def _parse_dt(value):
    if isinstance(value,datetime):
        dt=value
    else:
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt):
    return _parse_dt(dt).isoformat().replace("+00:00","Z")


def _f(v,default=0.0):
    try:
        return float(v)
    except (TypeError,ValueError):
        return default


def _sha(obj):
    return hashlib.sha256(
        json.dumps(obj,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    ).hexdigest()


def _atomic_json(path: Path, value: Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(temp,path)


def _append_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")


def _read_jsonl(path: Path):
    if not path.exists():
        return []
    out=[]
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


class AlpacaMarketDataReadClientV228:
    """Market-data-only HTTP client. No trading/broker endpoints exist here."""

    def __init__(self, *, key=None, secret=None, timeout=30, sleep_fn=time.sleep):
        self.key=key or os.getenv("APCA_API_KEY_ID","")
        self.secret=secret or os.getenv("APCA_API_SECRET_KEY","")
        if not self.key or not self.secret:
            raise RuntimeError("ALPACA_MARKET_DATA_CREDENTIALS_MISSING")
        self.timeout=int(timeout)
        self.sleep_fn=sleep_fn
        self.requests_made=0

    def _request(self,path,params,max_attempts=5):
        url=DATA_BASE+path
        if params:
            url+="?"+urllib.parse.urlencode(params)
        headers={
            "APCA-API-KEY-ID":self.key,
            "APCA-API-SECRET-KEY":self.secret,
            "Accept":"application/json",
        }
        errors=[]
        for attempt in range(1,max_attempts+1):
            try:
                self.requests_made+=1
                req=urllib.request.Request(url,headers=headers,method="GET")
                with urllib.request.urlopen(req,timeout=self.timeout) as resp:
                    data=resp.read()
                    return json.loads(data.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body=""
                try:
                    body=exc.read().decode("utf-8","replace")[:500]
                except Exception:
                    pass
                errors.append(f"HTTP_{exc.code}:{body}")
                if exc.code==429:
                    retry=exc.headers.get("Retry-After")
                    wait=max(1,int(retry)) if retry and retry.isdigit() else min(10,attempt*2)
                    self.sleep_fn(wait)
                    continue
                if 500 <= exc.code <= 599:
                    self.sleep_fn(min(10,attempt*2))
                    continue
                raise RuntimeError(errors[-1]) from exc
            except Exception as exc:
                errors.append(f"{type(exc).__name__}:{exc}")
                if attempt==max_attempts:
                    break
                self.sleep_fn(min(10,attempt*2))
        raise RuntimeError("ALPACA_MARKET_DATA_REQUEST_FAILED|"+"|".join(errors[-5:]))

    def fetch_historical_bars(
        self, symbols, *, start, end, timeframe="1Min", feed="iex", limit=10000
    ):
        token=None
        pages=0
        while True:
            params={
                "symbols":",".join(symbols),
                "timeframe":timeframe,
                "start":_iso(start),
                "end":_iso(end),
                "limit":int(limit),
                "adjustment":"raw",
                "feed":feed,
                "sort":"asc",
            }
            if token:
                params["page_token"]=token
            payload=self._request("/v2/stocks/bars",params)
            pages+=1
            yield payload
            token=payload.get("next_page_token")
            if not token:
                break

    def latest_bars(self,symbols,feed="iex"):
        return self._request(
            "/v2/stocks/bars/latest",
            {"symbols":",".join(symbols),"feed":feed}
        )


class FastDataAccelerationV228:
    def __init__(self,root):
        self.root=Path(root)
        self.policy_path=(
            self.root/"release"/
            "ai_trading_engine_v2_2_8_fast_data_acceleration"/
            "config"/"fast_data_policy.json"
        )
        self.runtime=(
            self.root/"runtime"/"ai_fast_data_acceleration_v2_2_8"
        )
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.raw_bars=self.runtime/"historical_1m_bars.jsonl"
        self.dataset=self.runtime/"training_forward_labels.jsonl"
        self.backfill_state=self.runtime/"historical_backfill_state.json"
        self.live_ledger=self.runtime/"live_30_symbol_shadow.jsonl"
        self.live_stop=self.runtime/"STOP_LIVE_COLLECTOR"
        self.latest_status=self.runtime/"latest_status.json"

    def policy(self):
        if not self.policy_path.exists():
            raise RuntimeError("FAST_DATA_POLICY_MISSING")
        p=json.loads(self.policy_path.read_text(encoding="utf-8-sig"))
        symbols=[str(s).upper() for s in p.get("symbols",[])]
        if not 3 <= len(symbols) <= 30 or len(symbols)!=len(set(symbols)):
            raise RuntimeError("INVALID_FAST_DATA_SYMBOLS")
        if p.get("timeframe")!="1Min":
            raise RuntimeError("ONLY_1MIN_SUPPORTED")
        return p

    @staticmethod
    def _normalize_bar(symbol,bar,feed="iex"):
        ts=bar.get("t")
        return {
            "symbol":symbol,
            "timestamp":ts,
            "open":_f(bar.get("o")),
            "high":_f(bar.get("h")),
            "low":_f(bar.get("l")),
            "close":_f(bar.get("c")),
            "volume":_f(bar.get("v")),
            "trade_count":int(bar.get("n") or 0),
            "vwap":_f(bar.get("vw")),
            "feed":feed,
        }

    def historical_backfill(self,client,*,lookback_days=None,end=None):
        p=self.policy()
        end_dt=_parse_dt(end or (_utcnow()-timedelta(minutes=int(p["historical_end_lag_minutes"]))))
        days=int(lookback_days or p["historical_lookback_calendar_days"])
        if days<1 or days>730:
            raise ValueError("INVALID_LOOKBACK_DAYS")
        start_dt=end_dt-timedelta(days=days)

        # Rebuild deterministic raw dataset for this requested range.
        temp=self.raw_bars.with_suffix(".jsonl.tmp")
        if temp.exists():
            temp.unlink()
        total=0
        pages=0
        counts=defaultdict(int)
        seen=set()

        with temp.open("w",encoding="utf-8") as f:
            for payload in client.fetch_historical_bars(
                p["symbols"],
                start=start_dt,end=end_dt,
                timeframe=p["timeframe"],feed=p["feed"],
                limit=int(p["historical_page_limit"]),
            ):
                pages+=1
                bars_by_symbol=payload.get("bars") or {}
                for symbol, bars in bars_by_symbol.items():
                    symbol=symbol.upper()
                    for bar in bars or []:
                        row=self._normalize_bar(symbol,bar,p["feed"])
                        key=(symbol,row["timestamp"])
                        if key in seen:
                            continue
                        seen.add(key)
                        f.write(json.dumps(row,sort_keys=True)+"\n")
                        total+=1
                        counts[symbol]+=1
        os.replace(temp,self.raw_bars)

        labels=self.build_forward_labeled_dataset()
        state={
            "status":"PASS_FAST_HISTORICAL_BACKFILL",
            "symbols_requested":len(p["symbols"]),
            "symbols_with_bars":sum(1 for s in p["symbols"] if counts.get(s,0)>0),
            "bar_rows":total,
            "page_count":pages,
            "http_requests":client.requests_made,
            "start":_iso(start_dt),
            "end":_iso(end_dt),
            "feed":p["feed"],
            "timeframe":p["timeframe"],
            "per_symbol_rows":dict(sorted(counts.items())),
            "labeled_rows":labels["labeled_rows"],
            "fully_labeled_60m_rows":labels["fully_labeled_60m_rows"],
            "broker_trading_api_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        state["dataset_sha256"]=hashlib.sha256(self.dataset.read_bytes()).hexdigest() if self.dataset.exists() else None
        _atomic_json(self.backfill_state,state)
        _atomic_json(self.latest_status,state)
        return state

    @staticmethod
    def _rsi(closes,period=14):
        if len(closes)<period+1:
            return None
        gains=0.0
        losses=0.0
        for a,b in zip(closes[-period-1:-1],closes[-period:]):
            d=b-a
            if d>=0:
                gains+=d
            else:
                losses+=-d
        avg_gain=gains/period
        avg_loss=losses/period
        if avg_loss==0:
            return 100.0
        rs=avg_gain/avg_loss
        return 100-(100/(1+rs))

    @staticmethod
    def _mean(values):
        return sum(values)/len(values) if values else None

    @staticmethod
    def _std(values):
        if len(values)<2:
            return None
        m=sum(values)/len(values)
        return math.sqrt(sum((x-m)**2 for x in values)/len(values))

    def _feature_rows_for_symbol(self,rows,horizons):
        rows=sorted(rows,key=lambda r:r["timestamp"])
        by_time={_parse_dt(r["timestamp"]):i for i,r in enumerate(rows)}
        times=[_parse_dt(r["timestamp"]) for r in rows]
        out=[]

        closes=[]
        volumes=[]
        one_min_returns=[]
        for i,row in enumerate(rows):
            close=row["close"]
            closes.append(close)
            volumes.append(row["volume"])
            r1=None
            if i>=1 and rows[i-1]["close"]>0:
                r1=(close/rows[i-1]["close"]-1)*100
                one_min_returns.append(r1)
            else:
                one_min_returns.append(0.0)

            def ret_back(n):
                if i<n or rows[i-n]["close"]<=0:
                    return None
                # Never bridge across overnight/session gaps.
                if (times[i]-times[i-n]).total_seconds() > (n+2)*60:
                    return None
                return (close/rows[i-n]["close"]-1)*100

            sma5=self._mean(closes[-5:]) if len(closes)>=5 else None
            sma20=self._mean(closes[-20:]) if len(closes)>=20 else None
            vol20=self._std(one_min_returns[-20:]) if len(one_min_returns)>=20 else None
            vol_avg20=self._mean(volumes[-20:]) if len(volumes)>=20 else None
            volume_ratio=(row["volume"]/vol_avg20) if vol_avg20 and vol_avg20>0 else None
            range_pct=((row["high"]-row["low"])/close*100) if close>0 else None

            labels={}
            full60=False
            for h in horizons:
                target=times[i]+timedelta(minutes=h)
                j=by_time.get(target)
                label=None
                if j is not None and j>i and close>0:
                    future=rows[j]
                    # Confirm no overnight bridge by exact target already.
                    window=rows[i+1:j+1]
                    highs=[x["high"] for x in window if x["high"]>0]
                    lows=[x["low"] for x in window if x["low"]>0]
                    fwd=(future["close"]/close-1)*100
                    mfe=((max(highs)/close)-1)*100 if highs else None
                    mae=((min(lows)/close)-1)*100 if lows else None
                    label={
                        "forward_return_pct":round(fwd,6),
                        "mfe_pct":None if mfe is None else round(mfe,6),
                        "mae_pct":None if mae is None else round(mae,6),
                        "target_timestamp":future["timestamp"],
                        "direction":"UP" if fwd>0 else ("DOWN" if fwd<0 else "FLAT"),
                    }
                labels[f"{h}m"]=label
                if h==60 and label is not None:
                    full60=True

            out.append({
                **row,
                "features":{
                    "return_1m_pct":None if r1 is None else round(r1,6),
                    "return_5m_pct":None if ret_back(5) is None else round(ret_back(5),6),
                    "return_15m_pct":None if ret_back(15) is None else round(ret_back(15),6),
                    "sma_5":None if sma5 is None else round(sma5,8),
                    "sma_20":None if sma20 is None else round(sma20,8),
                    "close_vs_sma20_pct":(
                        None if not sma20 or sma20==0 else round((close/sma20-1)*100,6)
                    ),
                    "rolling_volatility_20":None if vol20 is None else round(vol20,6),
                    "volume_ratio_20":None if volume_ratio is None else round(volume_ratio,6),
                    "range_pct":None if range_pct is None else round(range_pct,6),
                    "rsi_14":self._rsi(closes,14),
                },
                "forward_labels":labels,
                "has_60m_label":full60,
                "data_role":"AI_TRAINING_SHADOW_ONLY",
            })
        return out

    def build_forward_labeled_dataset(self):
        p=self.policy()
        rows=_read_jsonl(self.raw_bars)
        grouped=defaultdict(list)
        for row in rows:
            grouped[row["symbol"]].append(row)

        horizons=tuple(int(x) for x in p["forward_horizons_minutes"])
        temp=self.dataset.with_suffix(".jsonl.tmp")
        if temp.exists():
            temp.unlink()
        total=0
        full60=0
        per_symbol={}
        with temp.open("w",encoding="utf-8") as f:
            for symbol in p["symbols"]:
                feat=self._feature_rows_for_symbol(grouped.get(symbol,[]),horizons)
                per_symbol[symbol]=len(feat)
                for row in feat:
                    f.write(json.dumps(row,sort_keys=True)+"\n")
                    total+=1
                    if row["has_60m_label"]:
                        full60+=1
        os.replace(temp,self.dataset)
        return {
            "status":"PASS_FORWARD_LABEL_BUILD",
            "labeled_rows":total,
            "fully_labeled_60m_rows":full60,
            "per_symbol_rows":per_symbol,
            "horizons_minutes":list(horizons),
            "orders_submitted":0,
        }

    def collect_live_once(self,client):
        p=self.policy()
        payload=client.latest_bars(p["symbols"],p["feed"])
        bars=payload.get("bars") or {}
        observed=_iso(_utcnow())
        rows=[]
        for symbol in p["symbols"]:
            bar=bars.get(symbol)
            if not bar:
                continue
            row=self._normalize_bar(symbol,bar,p["feed"])
            identity_payload={
                "symbol":row["symbol"],
                "timestamp":row["timestamp"],
                "open":row["open"],
                "high":row["high"],
                "low":row["low"],
                "close":row["close"],
                "volume":row["volume"],
                "trade_count":row["trade_count"],
                "vwap":row["vwap"],
                "feed":row["feed"],
            }
            row.update({
                "observed_at_utc":observed,
                "data_role":"AI_LIVE_SHADOW_ONLY",
                "broker_trading_api_used":False,
                "orders_submitted":0,
                "bar_identity_sha256":_sha(identity_payload),
            })
            # Deduplicate by immutable market-bar identity, not collection time.
            row["row_sha256"]=row["bar_identity_sha256"]
            rows.append(row)

        existing=set()
        if self.live_ledger.exists():
            # only keep hashes for modest live collector ledger
            for r in _read_jsonl(self.live_ledger):
                if r.get("row_sha256"):
                    existing.add(r["row_sha256"])
        new=[r for r in rows if r["row_sha256"] not in existing]
        if new:
            _append_jsonl(self.live_ledger,new)
        result={
            "status":"PASS_LIVE_30_SYMBOL_SHADOW_COLLECTION",
            "symbols_requested":len(p["symbols"]),
            "symbols_received":len(rows),
            "new_rows":len(new),
            "duplicates":len(rows)-len(new),
            "feed":p["feed"],
            "http_requests":client.requests_made,
            "broker_trading_api_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic_json(self.latest_status,result)
        return result

    def collect_live_continuous(self,client,*,poll_seconds=None,max_runtime_seconds=None,sleep_fn=time.sleep):
        p=self.policy()
        poll=int(poll_seconds or p["live_poll_seconds"])
        runtime=int(max_runtime_seconds or p["live_max_runtime_seconds"])
        if poll<30 or poll>3600:
            raise ValueError("INVALID_LIVE_POLL_SECONDS")
        if runtime<60 or runtime>172800:
            raise ValueError("INVALID_LIVE_MAX_RUNTIME_SECONDS")
        if self.live_stop.exists():
            self.live_stop.unlink()

        start=time.monotonic()
        polls=0
        total_new=0
        last=None
        reason=None
        while True:
            if self.live_stop.exists():
                reason="STOP_FILE"
                break
            if time.monotonic()-start>=runtime:
                reason="MAX_RUNTIME"
                break
            last=self.collect_live_once(client)
            polls+=1
            total_new+=last["new_rows"]
            sleep_fn(poll)

        return {
            "status":"PASS_LIVE_30_SYMBOL_SHADOW_SUPERVISOR",
            "polls":polls,
            "total_new_rows":total_new,
            "stop_reason":reason,
            "last_collection":last,
            "broker_trading_api_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }

    def local_status(self):
        p=self.policy()
        state=json.loads(self.backfill_state.read_text(encoding="utf-8")) if self.backfill_state.exists() else {}
        return {
            "status":"PASS_FAST_DATA_LOCAL_STATUS",
            "configured_symbols":len(p["symbols"]),
            "actual_trading_symbols":p["actual_paper_trading_symbols"],
            "shadow_only_symbols":len(p["shadow_only_symbols"]),
            "historical_raw_exists":self.raw_bars.exists(),
            "training_dataset_exists":self.dataset.exists(),
            "historical_bar_rows":state.get("bar_rows",0),
            "labeled_rows":state.get("labeled_rows",0),
            "fully_labeled_60m_rows":state.get("fully_labeled_60m_rows",0),
            "live_shadow_rows":len(_read_jsonl(self.live_ledger)),
            "market_data_network_in_local_status":False,
            "broker_trading_api_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
