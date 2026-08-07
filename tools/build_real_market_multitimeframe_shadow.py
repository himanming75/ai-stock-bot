from __future__ import annotations

from pathlib import Path
from datetime import datetime, time, timezone
from collections import defaultdict, Counter
from zoneinfo import ZoneInfo
import argparse, json, statistics, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from multi_timeframe_ai.engine import analyze_symbol
from paper_autonomous_execution.signals import select_candidate

INTRADAY_TIMEFRAMES={
    "1m":1,
    "3m":3,
    "5m":5,
    "15m":15,
    "30m":30,
    "1h":60,
}
ALLOWED=("AAPL","MSFT","NVDA","SPY")
ET=ZoneInfo("America/New_York")
REGULAR_OPEN=time(9,30)
REGULAR_CLOSE=time(16,0)
MIN_CONFIDENCE=0.75
MIN_REWARD_RISK=1.0
ROLLING_STEP_MINUTES=30
FORWARD_HORIZONS=(15,30,60)

def ema(values,span):
    if not values:
        return 0.0
    alpha=2.0/(span+1.0)
    out=float(values[0])
    for v in values[1:]:
        out=alpha*float(v)+(1.0-alpha)*out
    return out

def rsi(values,period=14):
    if len(values)<period+1:
        return 50.0
    gains=[];losses=[]
    for a,b in zip(values[-period-1:-1],values[-period:]):
        d=float(b)-float(a)
        gains.append(max(d,0.0))
        losses.append(max(-d,0.0))
    ag=sum(gains)/period
    al=sum(losses)/period
    if al==0:
        return 100.0 if ag>0 else 50.0
    rs=ag/al
    return 100.0-(100.0/(1.0+rs))

def parse_timestamp(value):
    s=str(value).replace("Z","+00:00")
    dt=datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt

def regular_session_rows(rows):
    sessions=defaultdict(list)
    for row in rows:
        dt=parse_timestamp(row["timestamp"]).astimezone(ET)
        t=dt.time().replace(tzinfo=None)
        if REGULAR_OPEN <= t <= REGULAR_CLOSE:
            sessions[dt.date().isoformat()].append(row)
    for day in sessions:
        sessions[day].sort(key=lambda x:x["timestamp"])
    return dict(sorted(sessions.items()))

def aggregate_bucket(bucket):
    return {
        "timestamp":bucket[-1]["timestamp"],
        "open":float(bucket[0]["open"]),
        "high":max(float(x["high"]) for x in bucket),
        "low":min(float(x["low"]) for x in bucket),
        "close":float(bucket[-1]["close"]),
        "volume":sum(float(x["volume"]) for x in bucket),
    }

def aggregate_intraday_by_session(sessions,n):
    out=[]
    for _,rows in sessions.items():
        bucket=[]
        for row in rows:
            bucket.append(row)
            if len(bucket)==n:
                out.append(aggregate_bucket(bucket))
                bucket=[]
    return out

def aggregate_daily(sessions):
    return [aggregate_bucket(rows) for _,rows in sessions.items() if rows]

def feature_from_bars(bars,tf):
    min_required=15 if tf=="1d" else 30
    if len(bars)<min_required:
        return None

    closes=[float(x["close"]) for x in bars]
    highs=[float(x["high"]) for x in bars]
    lows=[float(x["low"]) for x in bars]
    vols=[float(x["volume"]) for x in bars]

    c=closes[-1]
    fast=ema(closes[-30:],8)
    slow=ema(closes[-60:],21)
    mom=(c/closes[-6]-1.0) if len(closes)>=6 and closes[-6] else 0.0
    avg_vol=sum(vols[-20:])/max(1,len(vols[-20:]))
    vr=(vols[-1]/avg_vol) if avg_vol else 1.0

    trs=[]
    for i in range(max(1,len(closes)-14),len(closes)):
        prev=closes[i-1]
        trs.append(max(highs[i]-lows[i],abs(highs[i]-prev),abs(lows[i]-prev)))
    atr=(sum(trs)/len(trs))/c if trs and c else 0.0

    day_gap=0.0
    if tf=="1d" and len(closes)>=2 and bars[-1]["open"]:
        day_gap=float(bars[-1]["open"])/float(closes[-2])-1.0

    rng=max(1e-12,highs[-1]-lows[-1])
    cvr=(c-lows[-1])/rng
    ft=(c/closes[-3]-1.0) if len(closes)>=3 and closes[-3] else 0.0

    return {
        "close":c,
        "ema_fast":fast,
        "ema_slow":slow,
        "momentum":mom,
        "rsi":rsi(closes),
        "volume_ratio":vr,
        "atr_percent":atr,
        "gap_percent":day_gap,
        "close_vs_range":cvr,
        "follow_through":ft,
    }

def load_real_rows(root):
    path=root/"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl"
    if not path.exists():
        raise RuntimeError("Real historical dataset missing")
    by=defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r=json.loads(line)
        by[str(r["symbol"]).upper()].append(r)
    for sym in by:
        by[sym].sort(key=lambda x:x["timestamp"])
    return by

def build_features(rows):
    sessions=regular_session_rows(rows)
    features={}
    meta={}
    for tf,n in INTRADAY_TIMEFRAMES.items():
        bars=aggregate_intraday_by_session(sessions,n)
        feat=feature_from_bars(bars,tf)
        meta[tf]={"aggregated_bars":len(bars),"feature_ready":feat is not None}
        if feat is not None:
            features[tf]=feat

    daily=aggregate_daily(sessions)
    dfeat=feature_from_bars(daily,"1d")
    meta["1d"]={
        "aggregated_bars":len(daily),
        "trading_days":len(sessions),
        "feature_ready":dfeat is not None,
    }
    if dfeat is not None:
        features["1d"]=dfeat
    return features,meta,len(sessions)

def analyze_at_rows(by):
    analyses=[]
    audit={}
    rejected={}
    for symbol in ALLOWED:
        rows=by.get(symbol,[])
        features,meta,days=build_features(rows)
        audit[symbol]={
            "source_minute_rows":len(rows),
            "regular_session_days":days,
            "timeframes":meta,
            "ready_timeframe_count":len(features),
        }
        if len(features)!=7:
            rejected[symbol]={
                "reason":"INCOMPLETE_SEVEN_TIMEFRAME_FEATURE_SET",
                "ready_timeframes":sorted(features),
                "missing_timeframes":sorted(set((*INTRADAY_TIMEFRAMES.keys(),"1d"))-set(features)),
            }
            continue
        item=analyze_symbol(symbol,features)
        item["execution_mode"]="ANALYSIS_ONLY"
        analyses.append(item)

    analyses.sort(
        key=lambda x:(
            x.get("confidence_calibration",{}).get("calibrated_confidence",0.0),
            abs(float(x.get("consensus_score",0.0))),
        ),
        reverse=True,
    )
    selected=select_candidate(
        analyses,
        allowed_symbols=ALLOWED,
        min_confidence=MIN_CONFIDENCE,
        min_reward_risk=MIN_REWARD_RISK,
        excluded_symbols=(),
    )
    return analyses,audit,rejected,selected

def current_fixture_selection(root):
    current_path=root/"release/v11001_12000_multi_timeframe_ai/actual/multi_timeframe_ai_report_bilingual.json"
    current={}
    if current_path.exists():
        try:
            current=json.loads(current_path.read_text(encoding="utf-8-sig"))
        except Exception:
            current={}
    analyses=current.get("analyses",[]) if isinstance(current,dict) else []
    return select_candidate(
        analyses if isinstance(analyses,list) else [],
        allowed_symbols=ALLOWED,
        min_confidence=MIN_CONFIDENCE,
        min_reward_risk=MIN_REWARD_RISK,
        excluded_symbols=(),
    )

def snapshot(root:Path):
    root=Path(root).resolve()
    by=load_real_rows(root)
    analyses,audit,rejected,selected=analyze_at_rows(by)
    current_selected=current_fixture_selection(root)

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    report={
        "stage":"REAL_MARKET_MULTI_TIMEFRAME_SHADOW_ADAPTER_V1_2",
        "status":"PASS" if len(analyses)==len(ALLOWED) else "PARTIAL",
        "mode":"SHADOW_ANALYSIS_ONLY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_dataset":"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "source_kind":"REAL_ALPACA_HISTORICAL_1MIN",
        "resampling_contract":{
            "timezone":"America/New_York",
            "regular_session_only":True,
            "regular_session":"09:30-16:00 ET",
            "intraday_buckets_never_cross_session_boundary":True,
            "daily_bar_is_one_regular_trading_session":True,
            "daily_feature_minimum_trading_days":15,
        },
        "canonical_engine":"multi_timeframe_ai.engine.analyze_symbol",
        "canonical_selector":"paper_autonomous_execution.signals.select_candidate",
        "allowed_symbols":list(ALLOWED),
        "thresholds":{"min_confidence":MIN_CONFIDENCE,"min_reward_risk":MIN_REWARD_RISK},
        "analyses":analyses,
        "feature_audit":audit,
        "rejected_symbols":rejected,
        "shadow_selected_candidate":selected,
        "current_fixture_selected_candidate":current_selected,
        "selection_matches":selected==current_selected,
        "strategy_equivalence":{
            "same_analyze_symbol_engine":True,
            "same_select_candidate_function":True,
            "same_thresholds":True,
            "same_allowed_symbols":True,
            "same_input_source":False,
            "current_input_source":"OFFLINE_MULTI_TIMEFRAME_FIXTURE",
            "shadow_input_source":"REAL_ALPACA_HISTORICAL_1MIN_SESSION_AWARE_RESAMPLED",
            "live_equivalence_asserted":False,
        },
        "contracts":base_contracts(),
    }
    (out/"latest_real_market_shadow.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    with (out/"real_market_shadow_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps(report,default=str)+"\n")
    return report

def base_contracts():
    return {
        "current_signal_report_modified":False,
        "paper_task_modified":False,
        "broker_write_performed":False,
        "order_submission_performed":False,
        "strategy_parameter_changed":False,
        "risk_parameter_changed":False,
        "live_auto_enable":False,
    }

def make_checkpoints(by):
    # Use SPY as the liquid market-clock reference. Only checkpoints at 30-minute
    # boundaries inside regular trading sessions are considered.
    sessions=regular_session_rows(by.get("SPY",[]))
    points=[]
    for day,rows in sessions.items():
        seen={}
        for row in rows:
            dt=parse_timestamp(row["timestamp"]).astimezone(ET)
            mins=(dt.hour*60+dt.minute)-(9*60+30)
            if mins < 0:
                continue
            if mins % ROLLING_STEP_MINUTES==0:
                seen[dt.replace(second=0,microsecond=0).isoformat()]=dt
        points.extend(seen.values())
    return sorted(points)

def truncate_by_checkpoint(by, checkpoint):
    out={}
    for symbol,rows in by.items():
        kept=[]
        for row in rows:
            if parse_timestamp(row["timestamp"]).astimezone(ET) <= checkpoint:
                kept.append(row)
            else:
                break
        out[symbol]=kept
    return out

def price_at_or_after(rows, target_dt):
    best=None
    for row in rows:
        dt=parse_timestamp(row["timestamp"]).astimezone(ET)
        if dt >= target_dt:
            best=(dt,float(row["close"]))
            break
    return best

def rolling(root:Path):
    root=Path(root).resolve()
    by=load_real_rows(root)
    checkpoints=make_checkpoints(by)
    records=[]
    eligible_checkpoints=0

    for cp in checkpoints:
        truncated=truncate_by_checkpoint(by,cp)
        analyses,_,rejected,selected=analyze_at_rows(truncated)
        if len(analyses)!=len(ALLOWED):
            continue
        eligible_checkpoints+=1

        rec={
            "checkpoint_et":cp.isoformat(),
            "analysis_count":len(analyses),
            "selected_candidate":selected,
            "decision":"NO_ACTION" if selected is None else str(selected.get("side","")).upper(),
            "symbol":None if selected is None else selected.get("symbol"),
            "confidence":None if selected is None else selected.get("confidence"),
            "reward_risk":None if selected is None else selected.get("reward_risk"),
            "forward_outcomes":{},
        }

        if selected:
            symbol=str(selected["symbol"]).upper()
            side=str(selected["side"]).upper()
            entry_data=price_at_or_after(by[symbol],cp)
            if entry_data:
                _,entry=entry_data
                for horizon in FORWARD_HORIZONS:
                    target=cp.replace(second=0,microsecond=0)
                    from datetime import timedelta
                    target=target+timedelta(minutes=horizon)
                    future=price_at_or_after(by[symbol],target)
                    if future:
                        fdt,fprice=future
                        raw=(fprice/entry)-1.0 if entry else 0.0
                        signed=raw if side=="BUY" else -raw
                        rec["forward_outcomes"][str(horizon)]={
                            "entry_price":entry,
                            "future_timestamp_et":fdt.isoformat(),
                            "future_price":fprice,
                            "raw_return":raw,
                            "directional_return":signed,
                            "directional_win":signed>0,
                        }
        records.append(rec)

    decisions=Counter(r["decision"] for r in records)
    selected_records=[r for r in records if r["selected_candidate"] is not None]

    horizon_stats={}
    for horizon in FORWARD_HORIZONS:
        vals=[]
        wins=0
        for r in selected_records:
            o=r["forward_outcomes"].get(str(horizon))
            if not o:
                continue
            vals.append(float(o["directional_return"]))
            wins+=1 if o["directional_win"] else 0
        horizon_stats[str(horizon)]={
            "sample_count":len(vals),
            "win_count":wins,
            "win_rate":(wins/len(vals)) if vals else None,
            "average_directional_return":statistics.mean(vals) if vals else None,
            "median_directional_return":statistics.median(vals) if vals else None,
            "sum_equal_weight_directional_returns":sum(vals) if vals else None,
            "pnl_equivalence_to_paper_lifecycle":"NOT_ASSERTED",
        }

    dates=sorted({r["checkpoint_et"][:10] for r in records})
    report={
        "stage":"REAL_MARKET_MULTI_TIMEFRAME_ROLLING_REPLAY_V1_2",
        "status":"PASS",
        "mode":"ROLLING_SHADOW_FORWARD_OUTCOME_DIAGNOSTIC",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_dataset":"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "no_lookahead_contract":True,
        "checkpoint_step_minutes":ROLLING_STEP_MINUTES,
        "forward_horizons_minutes":list(FORWARD_HORIZONS),
        "thresholds":{"min_confidence":MIN_CONFIDENCE,"min_reward_risk":MIN_REWARD_RISK},
        "total_market_checkpoints":len(checkpoints),
        "eligible_checkpoints":eligible_checkpoints,
        "evaluated_checkpoints":len(records),
        "trading_dates_evaluated":dates,
        "decision_counts":dict(decisions),
        "selected_signal_count":len(selected_records),
        "no_action_count":decisions.get("NO_ACTION",0),
        "signal_rate":(len(selected_records)/len(records)) if records else 0.0,
        "signals_per_evaluated_day":(len(selected_records)/len(dates)) if dates else 0.0,
        "projected_signals_per_10_days":((len(selected_records)/len(dates))*10.0) if dates else 0.0,
        "horizon_stats":horizon_stats,
        "records":records,
        "interpretation_contract":{
            "candidate_selection_equivalent_to_current_selector":True,
            "analysis_engine_equivalent_to_current_engine":True,
            "input_source_equivalent_to_current_production":False,
            "paper_exit_lifecycle_replayed":False,
            "paper_strategy_pnl_asserted":False,
            "forward_outcomes_are_diagnostic_only":True,
        },
        "contracts":base_contracts(),
    }

    out=root/"runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_rolling_replay.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    with (out/"rolling_replay_ledger.jsonl").open("a",encoding="utf-8") as h:
        h.write(json.dumps({k:v for k,v in report.items() if k!="records"},default=str)+"\n")
    return report

def build(root:Path,mode="snapshot"):
    return rolling(root) if mode=="rolling" else snapshot(root)

# === V1.3.1 PAPER LIFECYCLE HISTORICAL REPLAY EXTENSION ===

PAPER_LIFECYCLE_DEFAULTS = {
    "take_profit_pct": 0.008,
    "stop_loss_pct": 0.005,
    "max_hold_minutes": 30,
    "force_flat_before_close": True,
    "market_close_buffer_minutes": 15,
    "maximum_open_positions": 4,
    "maximum_daily_entries": 15,
}

def load_paper_lifecycle_contract(root):
    cfg_path = root / "config/paper_full_auto_lifecycle.json"
    cfg = dict(PAPER_LIFECYCLE_DEFAULTS)
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            for k in ("take_profit_pct","stop_loss_pct","max_hold_minutes","force_flat_before_close"):
                if k in raw:
                    cfg[k] = raw[k]
        except Exception:
            pass

    guard_path = root / "config/smart_safe_guard_policy.json"
    if guard_path.exists():
        try:
            raw = json.loads(guard_path.read_text(encoding="utf-8-sig"))
            if "maximum_open_positions" in raw:
                cfg["maximum_open_positions"] = int(raw["maximum_open_positions"])
        except Exception:
            pass
    return cfg

def _regular_rows_by_symbol(by):
    result = {}
    for symbol, rows in by.items():
        kept = []
        for row in rows:
            dt = parse_timestamp(row["timestamp"]).astimezone(ET)
            local_t = dt.time().replace(tzinfo=None)
            if REGULAR_OPEN <= local_t <= REGULAR_CLOSE:
                kept.append(row)
        result[symbol] = kept
    return result

def _row_strictly_after(rows, checkpoint):
    for row in rows:
        if parse_timestamp(row["timestamp"]).astimezone(ET) > checkpoint:
            return row
    return None

def _minutes_to_regular_close(dt_et):
    close_dt = dt_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return max(0.0, (close_dt - dt_et).total_seconds() / 60.0)

def _equity_mark(starting_equity, realized_pl, positions, latest_price, now_et):
    unrealized = 0.0
    for sym, pos in positions.items():
        if now_et < pos["entry_time_et"]:
            continue
        px = latest_price.get(sym, pos["entry_price"])
        unrealized += (px - pos["entry_price"]) * pos["quantity"]
    return starting_equity + realized_pl + unrealized

def rolling_lifecycle(root: Path):
    root = Path(root).resolve()
    by_all = load_real_rows(root)
    by = _regular_rows_by_symbol(by_all)
    checkpoints = make_checkpoints(by_all)
    lifecycle = load_paper_lifecycle_contract(root)

    decisions = {}
    eligible = 0
    for cp in checkpoints:
        truncated = truncate_by_checkpoint(by_all, cp)
        analyses, _, _, selected = analyze_at_rows(truncated)
        if len(analyses) != len(ALLOWED):
            continue
        eligible += 1
        decisions[cp.isoformat()] = {
            "analysis_count": len(analyses),
            "selected_candidate": selected,
        }

    spy_rows = by.get("SPY", [])
    if not spy_rows:
        raise RuntimeError("SPY REGULAR SESSION TIMELINE MISSING")

    symbol_rows_by_ts = {}
    for symbol in ALLOWED:
        symbol_rows_by_ts[symbol] = {
            parse_timestamp(r["timestamp"]).astimezone(ET).replace(second=0, microsecond=0): r
            for r in by.get(symbol, [])
        }

    starting_equity = 100000.0
    positions = {}
    closed = []
    realized_pl = 0.0
    latest_price = {}
    equity_curve = []
    daily_entries = defaultdict(int)
    skipped_entries = Counter()
    raw_signal_counts = Counter()
    accepted_buy_entries = 0
    sell_signals_observed = 0

    def close_position(symbol, dt_et, price, reason):
        nonlocal realized_pl
        pos = positions.pop(symbol)
        qty = pos["quantity"]
        pl = (price - pos["entry_price"]) * qty
        ret = (price - pos["entry_price"]) / pos["entry_price"] if pos["entry_price"] else 0.0
        realized_pl += pl
        hold = max(0.0, (dt_et - pos["entry_time_et"]).total_seconds() / 60.0)
        trade = {
            "trade_id": f"hist-paper-{symbol}-{len(closed)+1}",
            "symbol": symbol,
            "side": "LONG",
            "entry_signal_time_et": pos["signal_time_et"].isoformat(),
            "entry_time_et": pos["entry_time_et"].isoformat(),
            "entry_price": pos["entry_price"],
            "exit_time_et": dt_et.isoformat(),
            "exit_price": price,
            "quantity": qty,
            "notional": pos["notional"],
            "realized_pl": pl,
            "realized_return": ret,
            "hold_minutes": hold,
            "exit_reason": reason,
            "entry_confidence": pos.get("confidence"),
            "entry_reward_risk": pos.get("reward_risk"),
            "fill_model": "NEXT_AVAILABLE_1MIN_CLOSE_AFTER_SIGNAL",
            "lifecycle_price_model": "1MIN_CLOSE_POLLING_APPROXIMATION",
        }
        closed.append(trade)

    for spy in spy_rows:
        dt_et = parse_timestamp(spy["timestamp"]).astimezone(ET).replace(second=0, microsecond=0)
        day = dt_et.date().isoformat()

        for symbol in ALLOWED:
            row = symbol_rows_by_ts[symbol].get(dt_et)
            if row is not None:
                latest_price[symbol] = float(row["close"])

        # Production runner evaluates lifecycle before opening a new entry.
        for symbol in list(positions):
            pos = positions[symbol]
            if dt_et < pos["entry_time_et"]:
                continue
            if symbol not in latest_price:
                continue

            px = latest_price[symbol]
            ret = (px - pos["entry_price"]) / pos["entry_price"]
            hold = max(0.0, (dt_et - pos["entry_time_et"]).total_seconds() / 60.0)
            minutes_to_close = _minutes_to_regular_close(dt_et)

            reason = None
            if ret >= float(lifecycle["take_profit_pct"]):
                reason = "TAKE_PROFIT"
            elif ret <= -float(lifecycle["stop_loss_pct"]):
                reason = "STOP_LOSS"
            elif hold >= int(lifecycle["max_hold_minutes"]):
                reason = "TIME_EXIT"
            elif (
                bool(lifecycle["force_flat_before_close"])
                and minutes_to_close <= int(lifecycle["market_close_buffer_minutes"])
            ):
                reason = "MARKET_CLOSE_FLATTEN"

            if reason:
                close_position(symbol, dt_et, px, reason)

        decision = decisions.get(dt_et.isoformat())
        if decision:
            selected = decision["selected_candidate"]
            if selected is None:
                raw_signal_counts["NO_ACTION"] += 1
            else:
                side = str(selected.get("side","")).upper()
                raw_signal_counts[side] += 1

                if side == "SELL":
                    sell_signals_observed += 1
                    skipped_entries["SELL_DELEGATED_TO_POSITION_LIFECYCLE"] += 1
                elif side == "BUY":
                    symbol = str(selected.get("symbol","")).upper()
                    if symbol in positions:
                        skipped_entries["DUPLICATE_SYMBOL_OPEN_POSITION"] += 1
                    elif len(positions) >= int(lifecycle["maximum_open_positions"]):
                        skipped_entries["MAX_OPEN_POSITIONS"] += 1
                    elif daily_entries[day] >= int(lifecycle["maximum_daily_entries"]):
                        skipped_entries["DAILY_ENTRY_LIMIT"] += 1
                    else:
                        next_row = _row_strictly_after(by.get(symbol, []), dt_et)
                        if next_row is None:
                            skipped_entries["NO_NEXT_FILL_BAR"] += 1
                        else:
                            entry_dt = parse_timestamp(next_row["timestamp"]).astimezone(ET).replace(second=0, microsecond=0)
                            if entry_dt.date() != dt_et.date():
                                skipped_entries["NEXT_FILL_OUTSIDE_SIGNAL_DAY"] += 1
                            else:
                                entry_price = float(next_row["close"])
                                notional = 100.0
                                qty = notional / entry_price if entry_price > 0 else 0.0
                                if qty <= 0:
                                    skipped_entries["INVALID_ENTRY_PRICE"] += 1
                                else:
                                    positions[symbol] = {
                                        "symbol": symbol,
                                        "signal_time_et": dt_et,
                                        "entry_time_et": entry_dt,
                                        "entry_price": entry_price,
                                        "quantity": qty,
                                        "notional": notional,
                                        "confidence": selected.get("confidence"),
                                        "reward_risk": selected.get("reward_risk"),
                                    }
                                    daily_entries[day] += 1
                                    accepted_buy_entries += 1

        equity_curve.append({
            "timestamp_et": dt_et.isoformat(),
            "equity": _equity_mark(
                starting_equity, realized_pl, positions, latest_price, dt_et
            ),
        })

    # Diagnostic flatten only if the source ends with an unclosed position.
    if spy_rows:
        final_dt = parse_timestamp(spy_rows[-1]["timestamp"]).astimezone(ET).replace(second=0, microsecond=0)
        for symbol in list(positions):
            if symbol in latest_price:
                close_position(symbol, final_dt, latest_price[symbol], "DATA_END_FLATTEN")

    wins = [t for t in closed if t["realized_pl"] > 0]
    losses = [t for t in closed if t["realized_pl"] < 0]
    gross_profit = sum(t["realized_pl"] for t in wins)
    gross_loss_abs = abs(sum(t["realized_pl"] for t in losses))
    profit_factor = (gross_profit / gross_loss_abs) if gross_loss_abs > 0 else None

    running_peak = None
    max_dd = 0.0
    for p in equity_curve:
        eq = float(p["equity"])
        running_peak = eq if running_peak is None else max(running_peak, eq)
        if running_peak > 0:
            max_dd = min(max_dd, (eq - running_peak) / running_peak)

    max_consecutive_losses = 0
    streak = 0
    for t in closed:
        if t["realized_pl"] < 0:
            streak += 1
            max_consecutive_losses = max(max_consecutive_losses, streak)
        else:
            streak = 0

    dates = sorted({
        parse_timestamp(x["timestamp"]).astimezone(ET).date().isoformat()
        for x in spy_rows
    })
    exit_counts = Counter(t["exit_reason"] for t in closed)

    ending_equity = starting_equity + sum(t["realized_pl"] for t in closed)
    total_pl = ending_equity - starting_equity
    closed_count = len(closed)
    avg_win = (sum(t["realized_pl"] for t in wins)/len(wins)) if wins else None
    avg_loss = (sum(t["realized_pl"] for t in losses)/len(losses)) if losses else None
    expectancy = (total_pl/closed_count) if closed_count else None
    win_rate = (len(wins)/closed_count) if closed_count else None
    avg_hold = (sum(t["hold_minutes"] for t in closed)/closed_count) if closed_count else None
    trades_per_day = (closed_count/len(dates)) if dates else 0.0
    projected_10 = trades_per_day*10.0
    projected_days_300 = (300.0/trades_per_day) if trades_per_day > 0 else None

    report = {
        "stage": "REAL_MARKET_PAPER_LIFECYCLE_ROLLING_REPLAY_V1_3_1",
        "status": "PASS",
        "mode": "HISTORICAL_PAPER_LIFECYCLE_APPROXIMATION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": "runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "no_lookahead_signal_contract": True,
        "canonical_reuse": {
            "analyze_symbol": "multi_timeframe_ai.engine.analyze_symbol",
            "select_candidate": "paper_autonomous_execution.signals.select_candidate",
            "paper_lifecycle_source": "paper_autonomous_execution.lifecycle.PaperLifecycleConfig/_exit_reason",
            "paper_entry_contract": "BUY_ONLY_NEW_ENTRY",
            "sell_signal_contract": "DELEGATED_TO_POSITION_LIFECYCLE_NOT_SHORT_ENTRY",
        },
        "lifecycle_parameters": lifecycle,
        "execution_approximation": {
            "entry_fill": "NEXT_AVAILABLE_1MIN_CLOSE_AFTER_SIGNAL",
            "lifecycle_polling": "1MIN_CLOSE",
            "commission": 0.0,
            "slippage": 0.0,
            "exact_broker_fill_equivalence_asserted": False,
            "exact_live_equivalence_asserted": False,
        },
        "checkpoint_summary": {
            "total_market_checkpoints": len(checkpoints),
            "eligible_checkpoints": eligible,
            "raw_decision_counts": dict(raw_signal_counts),
            "sell_signals_observed_not_entered": sell_signals_observed,
        },
        "entry_summary": {
            "accepted_buy_entries": accepted_buy_entries,
            "skipped_entries": dict(skipped_entries),
        },
        "portfolio": {
            "starting_equity": starting_equity,
            "ending_equity": ending_equity,
            "total_pl": total_pl,
            "total_return_pct": (total_pl / starting_equity) if starting_equity else 0.0,
            "closed_trades": closed_count,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "profit_factor": profit_factor,
            "expectancy_per_trade": expectancy,
            "average_hold_minutes": avg_hold,
            "max_drawdown_pct": max_dd,
            "max_consecutive_losses": max_consecutive_losses,
            "exit_reason_counts": dict(exit_counts),
        },
        "validation_feasibility": {
            "trading_days_evaluated": len(dates),
            "closed_trades_per_day": trades_per_day,
            "projected_closed_trades_10_days": projected_10,
            "projected_trading_days_for_300_closed_trades": projected_days_300,
            "original_target_closed_trades": 300,
            "original_target_trading_days": 10,
            "original_300_in_10_days_feasible_at_observed_rate": projected_10 >= 300.0,
        },
        "closed_trades": closed,
        "interpretation_contract": {
            "current_paper_fixture_input_replaced": False,
            "production_paper_strategy_modified": False,
            "exact_broker_fill_equivalence_asserted": False,
            "historical_lifecycle_rules_replayed": True,
            "sell_signals_open_short_positions": False,
            "parameter_optimization_performed": False,
        },
        "contracts": base_contracts(),
    }

    out = root / "runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest_paper_lifecycle_replay.json").write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
    with (out / "paper_lifecycle_replay_ledger.jsonl").open("a", encoding="utf-8") as h:
        h.write(json.dumps(
            {k:v for k,v in report.items() if k != "closed_trades"},
            default=str,
        ) + "\n")
    with (out / "paper_lifecycle_closed_trades.jsonl").open("w", encoding="utf-8") as h:
        for trade in closed:
            h.write(json.dumps(trade, default=str) + "\n")
    return report

# === END V1.3.1 EXTENSION ===

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("snapshot","rolling","lifecycle"),default="snapshot")
    a=p.parse_args()
    result = rolling_lifecycle(Path(a.root)) if a.mode=="lifecycle" else build(Path(a.root),a.mode)
    print(json.dumps(result,indent=2,default=str))
