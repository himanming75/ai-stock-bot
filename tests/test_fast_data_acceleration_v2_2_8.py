from pathlib import Path
import json,tempfile,sys,unittest
from datetime import datetime,timezone,timedelta

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.fast_data_acceleration_v2_2_8 import FastDataAccelerationV228
from ai_engine_v2.fast_data_acceleration_status_v2_2_8 import build_v2_2_8_fast_status


def policy(root):
    p=Path(root)/"release"/"ai_trading_engine_v2_2_8_fast_data_acceleration"/"config"
    p.mkdir(parents=True,exist_ok=True)
    (p/"fast_data_policy.json").write_text(json.dumps({
        "symbols":["AAPL","MSFT","SPY"],
        "actual_paper_trading_symbols":["AAPL","MSFT","SPY"],
        "shadow_only_symbols":[],
        "timeframe":"1Min","feed":"iex",
        "historical_lookback_calendar_days":5,
        "historical_end_lag_minutes":20,
        "historical_page_limit":10000,
        "forward_horizons_minutes":[5,15,30,60],
        "live_poll_seconds":60,
        "live_max_runtime_seconds":3600
    }),encoding="utf-8")


def bars(symbol="AAPL",n=80,start=None):
    start=start or datetime(2026,8,10,14,30,tzinfo=timezone.utc)
    out=[]
    for i in range(n):
        price=100+i*.1
        out.append({
            "symbol":symbol,
            "timestamp":(start+timedelta(minutes=i)).isoformat().replace("+00:00","Z"),
            "open":price-.05,"high":price+.1,"low":price-.1,"close":price,
            "volume":1000+i,"trade_count":10,"vwap":price,"feed":"iex",
        })
    return out


class FakeClient:
    def __init__(self):
        self.requests_made=0
    def fetch_historical_bars(self,symbols,**kwargs):
        self.requests_made+=1
        yield {"bars":{s:[{
            "t":"2026-08-10T14:30:00Z","o":100,"h":101,"l":99,"c":100.5,
            "v":1000,"n":10,"vw":100.2
        }] for s in symbols},"next_page_token":None}
    def latest_bars(self,symbols,feed="iex"):
        self.requests_made+=1
        return {"bars":{s:{
            "t":"2026-08-10T17:00:00Z","o":100,"h":101,"l":99,"c":100.5,
            "v":1000,"n":10,"vw":100.2
        } for s in symbols}}


class Tests(unittest.TestCase):
    def test_forward_labels(self):
        with tempfile.TemporaryDirectory() as td:
            policy(td)
            c=FastDataAccelerationV228(td)
            with c.raw_bars.open("w",encoding="utf-8") as f:
                for r in bars():
                    f.write(json.dumps(r)+"\n")
            r=c.build_forward_labeled_dataset()
            self.assertEqual(r["labeled_rows"],80)
            self.assertGreater(r["fully_labeled_60m_rows"],0)
            rows=[json.loads(x) for x in c.dataset.read_text().splitlines()]
            self.assertIsNotNone(rows[0]["forward_labels"]["5m"])
            self.assertIsNotNone(rows[0]["forward_labels"]["60m"])
            self.assertIn("mfe_pct",rows[0]["forward_labels"]["15m"])
            self.assertIn("rsi_14",rows[20]["features"])

    def test_no_overnight_forward_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            policy(td)
            c=FastDataAccelerationV228(td)
            rs=bars(n=2,start=datetime(2026,8,10,19,59,tzinfo=timezone.utc))
            rs += bars(n=2,start=datetime(2026,8,11,13,30,tzinfo=timezone.utc))
            with c.raw_bars.open("w",encoding="utf-8") as f:
                for r in rs: f.write(json.dumps(r)+"\n")
            c.build_forward_labeled_dataset()
            rows=[json.loads(x) for x in c.dataset.read_text().splitlines()]
            self.assertIsNone(rows[1]["forward_labels"]["60m"])

    def test_fake_backfill_no_orders(self):
        with tempfile.TemporaryDirectory() as td:
            policy(td)
            c=FastDataAccelerationV228(td)
            r=c.historical_backfill(FakeClient(),lookback_days=2)
            self.assertEqual(r["status"],"PASS_FAST_HISTORICAL_BACKFILL")
            self.assertEqual(r["bar_rows"],3)
            self.assertEqual(r["orders_submitted"],0)
            self.assertFalse(r["broker_trading_api_used"])

    def test_live_once_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            policy(td)
            c=FastDataAccelerationV228(td)
            client=FakeClient()
            a=c.collect_live_once(client)
            b=c.collect_live_once(client)
            self.assertEqual(a["new_rows"],3)
            self.assertEqual(b["new_rows"],0)
            self.assertEqual(b["duplicates"],3)
            rows=[json.loads(x) for x in c.live_ledger.read_text().splitlines()]
            self.assertEqual(len(rows),3)
            self.assertTrue(all(r.get("bar_identity_sha256") for r in rows))
            self.assertEqual(b["orders_submitted"],0)

    def test_status_contract(self):
        s=build_v2_2_8_fast_status()
        self.assertTrue(s["historical_multi_symbol_backfill"])
        self.assertEqual(s["configured_symbol_count"],30)
        self.assertEqual(s["forward_horizons"],[5,15,30,60])
        self.assertTrue(s["mfe_mae_labels"])
        self.assertTrue(s["derived_ml_features"])
        self.assertTrue(s["live_30_symbol_shadow_collector"])
        self.assertFalse(s["broker_trading_api_used"])
        self.assertEqual(s["paper_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
