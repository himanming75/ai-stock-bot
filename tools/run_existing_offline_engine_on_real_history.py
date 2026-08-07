from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from backtest.offline_multi_asset_v26_1 import AssetBar, MultiAssetPolicy, run_multi_asset_backtest

def build(root:Path):
    src=root/"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl"
    manifest_path=root/"runtime/real_historical_ingestion/alpaca_real_historical_manifest.json"
    if not src.exists() or not manifest_path.exists():
        raise RuntimeError("Real historical dataset or manifest missing")

    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    prov=manifest.get("provenance",{})
    if manifest.get("source")!="ALPACA_STOCK_HISTORICAL_DATA_API":
        raise RuntimeError("Historical source is not Alpaca real historical API")
    if prov.get("actual_external_network_used") is not True:
        raise RuntimeError("Positive network provenance missing")
    if prov.get("order_submission_performed") is not False:
        raise RuntimeError("Order-write safety contract failed")

    bars=[]
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        bars.append(AssetBar(
            symbol=r["symbol"],
            timestamp=r["timestamp"],
            open=r["open"],high=r["high"],low=r["low"],
            close=r["close"],volume=r["volume"],
        ))

    if len(bars)<200:
        raise RuntimeError("Insufficient real bars for replay")

    result=run_multi_asset_backtest(bars,MultiAssetPolicy())

    # Convert SELL trades into closed-trade rows for research feeds.
    buys={}
    closed=[]
    for t in result.trades:
        if t.side=="BUY":
            buys[t.symbol]=t
        elif t.side=="SELL":
            entry=buys.pop(t.symbol,None)
            if entry is None:
                continue
            closed.append({
                "symbol":t.symbol,
                "entry_time":entry.timestamp,
                "exit_time":t.timestamp,
                "side":"LONG",
                "entry_price":float(entry.price),
                "exit_price":float(t.price),
                "quantity":float(t.quantity),
                "realized_pl":float(t.realized_pnl),
                "exit_reason":t.reason,
                "strategy":"OFFLINE_MULTI_ASSET_V26_1_EMA",
                "_canonical_source":"runtime/real_historical_replay/real_historical_closed_trades.jsonl",
                "_provenance_class":"REAL_HISTORICAL_BACKTEST",
            })

    out=root/"runtime/real_historical_replay"
    out.mkdir(parents=True,exist_ok=True)
    with (out/"real_historical_closed_trades.jsonl").open("w",encoding="utf-8") as h:
        for r in closed:
            h.write(json.dumps(r,separators=(",",":"))+"\n")

    report={
        "stage":"REAL_HISTORICAL_OFFLINE_MULTI_ASSET_REPLAY_V1",
        "status":"PASS",
        "mode":"OFFLINE_BACKTEST_ON_REAL_ALPACA_HISTORY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_dataset":manifest["dataset_path"],
        "source_dataset_sha256":manifest["dataset_sha256"],
        "source":"ALPACA_STOCK_HISTORICAL_DATA_API",
        "input_bar_count":len(bars),
        "symbols":list(result.symbols),
        "engine":"backtest.offline_multi_asset_v26_1",
        "engine_strategy":"EMA_FAST_SLOW_V26_1",
        "strategy_equivalence_to_current_paper":"NOT_ASSERTED",
        "total_order_events":result.total_trades,
        "closed_trade_count":len(closed),
        "starting_cash":float(result.starting_cash),
        "ending_equity":float(result.ending_equity),
        "total_return_pct":float(result.total_return_pct),
        "max_drawdown_pct":float(result.max_drawdown_pct),
        "closed_trade_feed":"runtime/real_historical_replay/real_historical_closed_trades.jsonl",
        "contracts":{
            "network_used_by_replay":False,
            "broker_connected_by_replay":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "paper_task_modified":False,
            "new_backtest_engine_created":False,
            "current_paper_strategy_modified":False,
            "live_auto_enable":False,
        },
    }
    (out/"latest_real_historical_replay.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    print(json.dumps(build(Path(a.root)),indent=2))
