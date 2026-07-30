import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.strategy_extended_paper_promotion_v66_0 import (
    PromotionError, VERSION, SCHEMA_VERSION, build_report, main, run
)


def v64():
    return {
        "closed_trade_count": 0, "open_trade_count": 1,
        "decision": "strategy_analytics_built", "network_used": False,
        "overall": {"win_rate": "0", "profit_factor": "0", "expectancy": "0", "net_pnl": "0"},
        "schema_version": "v64.0.strategy_analytics.1", "status": "PASS",
        "strategy_report_sha256": "9" * 64, "version": "64.0"
    }


def v65(gate="INSUFFICIENT_DATA", approved=False):
    return {
        "approved_for_extended_paper": approved, "approved_for_live": False,
        "decision": "strategy_quality_evaluated", "network_used": False,
        "quality_gate": gate, "quality_gate_sha256": "e" * 64,
        "schema_version": "v65.0.strategy_quality_gate.1",
        "source_v64_strategy_report_sha256": "9" * 64,
        "status": "PASS", "version": "65.0"
    }


class TestV66(unittest.TestCase):
    def test_version(self): self.assertEqual(VERSION, "66.0")
    def test_schema(self): self.assertEqual(SCHEMA_VERSION, "v66.0.extended_paper_promotion.1")
    def test_hold_state(self): self.assertEqual(build_report(v65(), v64())["promotion_state"], "HOLD_INSUFFICIENT_DATA")
    def test_hold_not_eligible(self): self.assertFalse(build_report(v65(), v64())["eligible_for_extended_paper"])
    def test_watch(self): self.assertEqual(build_report(v65("WATCH"), v64())["promotion_state"], "WATCHLIST")
    def test_reject(self): self.assertEqual(build_report(v65("REJECT"), v64())["promotion_state"], "BLOCKED")
    def test_approve(self): self.assertEqual(build_report(v65("APPROVE", True), v64())["promotion_state"], "EXTENDED_PAPER_APPROVED")
    def test_approve_starts(self): self.assertTrue(build_report(v65("APPROVE", True), v64())["start_extended_paper"])
    def test_never_live(self): self.assertFalse(build_report(v65("APPROVE", True), v64())["approved_for_live"])
    def test_network_false(self): self.assertFalse(build_report(v65(), v64())["network_used"])
    def test_safety_disabled(self):
        s = build_report(v65(), v64())["safety"]
        self.assertFalse(s["live_trading_enabled"])
        self.assertFalse(s["broker_connection_enabled"])
        self.assertFalse(s["external_order_submission_enabled"])
    def test_observed(self):
        o = build_report(v65(), v64())["observed"]
        self.assertEqual(o["closed_trade_count"], 0)
        self.assertEqual(o["open_trade_count"], 1)
    def test_hash_length(self): self.assertEqual(len(build_report(v65(), v64())["promotion_report_sha256"]), 64)
    def test_hash_deterministic(self): self.assertEqual(build_report(v65(), v64()), build_report(v65(), v64()))
    def test_hash_matches(self):
        r = build_report(v65(), v64()); observed = r.pop("promotion_report_sha256")
        expected = hashlib.sha256(json.dumps(r, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(observed, expected)
    def test_bad_v65_status(self):
        x=v65(); x["status"]="FAIL"
        with self.assertRaises(PromotionError): build_report(x,v64())
    def test_bad_v65_network(self):
        x=v65(); x["network_used"]=True
        with self.assertRaises(PromotionError): build_report(x,v64())
    def test_bad_v65_hash(self):
        x=v65(); x["quality_gate_sha256"]="bad"
        with self.assertRaises(PromotionError): build_report(x,v64())
    def test_bad_gate(self):
        with self.assertRaises(PromotionError): build_report(v65("BAD"),v64())
    def test_approve_requires_flag(self):
        with self.assertRaises(PromotionError): build_report(v65("APPROVE",False),v64())
    def test_nonapprove_forbids_flag(self):
        with self.assertRaises(PromotionError): build_report(v65("WATCH",True),v64())
    def test_v65_live_forbidden(self):
        x=v65(); x["approved_for_live"]=True
        with self.assertRaises(PromotionError): build_report(x,v64())
    def test_bad_v64_status(self):
        x=v64(); x["status"]="FAIL"
        with self.assertRaises(PromotionError): build_report(v65(),x)
    def test_bad_v64_network(self):
        x=v64(); x["network_used"]=True
        with self.assertRaises(PromotionError): build_report(v65(),x)
    def test_source_mismatch(self):
        x=v65(); x["source_v64_strategy_report_sha256"]="1"*64
        with self.assertRaises(PromotionError): build_report(x,v64())
    def test_bad_overall(self):
        x=v64(); x["overall"]=[]
        with self.assertRaises(PromotionError): build_report(v65(),x)
    def test_run_writes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); a=p/"65.json"; b=p/"64.json"; out=p/"out.json"
            a.write_text(json.dumps(v65())); b.write_text(json.dumps(v64()))
            result=run(a,b,out)
            self.assertEqual(json.loads(out.read_text()), result)
    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); a=p/"65.json"; b=p/"64.json"; out=p/"out.json"
            a.write_text(json.dumps(v65())); b.write_text(json.dumps(v64()))
            self.assertEqual(main(["--quality-gate",str(a),"--strategy-analytics",str(b),"--output",str(out)]),0)
    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            self.assertEqual(main(["--quality-gate",str(p/"x"),"--strategy-analytics",str(p/"y"),"--output",str(p/"z")]),1)


if __name__ == "__main__": unittest.main()
