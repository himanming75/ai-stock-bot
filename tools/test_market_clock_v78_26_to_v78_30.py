import tempfile,unittest
from datetime import date,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from market_clock.market_clock_pipeline_v78_26_30 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V78.25","status":"PASS",
          "certification_scope":"OFFLINE_MARKET_CLOCK_DEVELOPMENT_ONLY",
          "champion_candidate":{"candidate_id":"abc"}})
        write_json(self.cfg,{"market_clock":{"timezone":"America/New_York",
          "holidays":["2026-07-03"],"early_closes":{"2026-11-27":"13:00"},
          "session_times":{"premarket_open":"04:00","regular_open":"09:30","regular_close":"16:00","aftermarket_close":"20:00"}}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o26=self.r/"o26";a=build_market_clock_foundation(self.cert,self.cfg,o26)
        o27=self.r/"o27";b=build_trading_session_calendar(o26/"market_clock_foundation_v78_26.json",o27)
        o28=self.r/"o28";c=run_market_transition_engine(o26/"market_clock_foundation_v78_26.json",o28)
        o29=self.r/"o29";d=run_market_clock_safety_gate(
          o26/"market_clock_foundation_v78_26.json",
          o27/"trading_session_calendar_v78_27.json",
          o28/"market_open_close_transition_engine_v78_28.json",o29)
        o30=self.r/"o30";e=issue_market_clock_certificate(
          o26/"market_clock_foundation_verification_v78_26.json",
          o27/"trading_session_calendar_verification_v78_27.json",
          o28/"market_open_close_transition_engine_verification_v78_28.json",
          o29/"market_clock_safety_gate_verification_v78_29.json",
          o26/"market_clock_foundation_v78_26.json",o30)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_weekend_closed(self):
        c=DeterministicTradingCalendar("America/New_York",[],{})
        self.assertFalse(c.is_trading_day(date(2026,7,4)))
    def test_holiday_closed(self):
        c=DeterministicTradingCalendar("America/New_York",["2026-07-03"],{})
        self.assertEqual(c.session_for(date(2026,7,3)).session_type,"CLOSED")
    def test_early_close(self):
        c=DeterministicTradingCalendar("America/New_York",[],{"2026-11-27":"13:00"})
        self.assertEqual(c.session_for(date(2026,11,27)).regular_close,"13:00")
    def test_state_boundaries(self):
        tz=ZoneInfo("America/New_York");c=DeterministicTradingCalendar("America/New_York",[],{})
        clock=DeterministicMarketClock(c)
        self.assertEqual(clock.state_at(datetime(2026,7,6,4,0,tzinfo=tz)),"PREMARKET")
        self.assertEqual(clock.state_at(datetime(2026,7,6,9,30,tzinfo=tz)),"REGULAR")
        self.assertEqual(clock.state_at(datetime(2026,7,6,16,0,tzinfo=tz)),"AFTERMARKET")
        self.assertEqual(clock.state_at(datetime(2026,7,6,20,0,tzinfo=tz)),"CLOSED")
    def test_naive_datetime_blocked(self):
        c=DeterministicTradingCalendar("America/New_York",[],{})
        with self.assertRaises(ValueError):DeterministicMarketClock(c).state_at(datetime(2026,7,6,10,0))
    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_MARKET_DATA_ADAPTER_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.25","status":"FAIL"})
        self.assertEqual(build_market_clock_foundation(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
