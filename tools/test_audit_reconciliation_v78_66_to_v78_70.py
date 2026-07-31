import tempfile,unittest
from pathlib import Path
from audit_reconciliation.audit_reconciliation_pipeline_v78_66_70 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        self.normalization=self.r/"normalization.json"
        self.reconciliation=self.r/"reconciliation.json"

        write_json(self.cert,{
            "stage":"V78.65","status":"PASS",
            "certification_scope":"OFFLINE_AUDIT_RECONCILIATION_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "audit_reconciliation":{
                "starting_cash":100000.0,
                "cash_tolerance":0.000001,
                "pnl_tolerance":0.000001,
                "position_tolerance":0,
                "allow_real_broker_sources":False
            }
        })

        fills=[
            {"normalized_fill_id":"nf1","source_fill_id":"f1","broker_order_id":"b1","order_intent_id":"i1",
             "symbol":"AAPL","side":"buy","quantity":1,"price":100.0,"gross_notional":100.0,
             "commission":0.25,"slippage_cost":0.05,"remaining_quantity":0,"fill_status":"FILLED",
             "normalized_sha256":"sha1"},
            {"normalized_fill_id":"nf2","source_fill_id":"f2","broker_order_id":"b2","order_intent_id":"i2",
             "symbol":"AAPL","side":"sell","quantity":1,"price":99.9,"gross_notional":99.9,
             "commission":0.25,"slippage_cost":0.1,"remaining_quantity":0,"fill_status":"FILLED",
             "normalized_sha256":"sha2"}
        ]
        write_json(self.normalization,{"stage":"V78.62","status":"PASS","normalized_fills":fills})

        events=[
            {"sequence":1,"normalized_fill_id":"nf1","symbol":"AAPL","side":"buy","quantity":1,
             "price":100.0,"commission":0.25,"cash_delta":-100.25,"realized_pnl_delta":0.0},
            {"sequence":2,"normalized_fill_id":"nf2","symbol":"AAPL","side":"sell","quantity":1,
             "price":99.9,"commission":0.25,"cash_delta":99.65,"realized_pnl_delta":-0.6}
        ]
        for e in events:
            e["event_sha256"]=digest_json({k:e[k] for k in (
                "sequence","normalized_fill_id","symbol","side","quantity","price","commission",
                "cash_delta","realized_pnl_delta"
            )})
        write_json(self.reconciliation,{
            "stage":"V78.63","status":"PASS",
            "portfolio_fill_events":events,
            "portfolio_snapshot":{
                "cash":99999.4,"market_value":0.0,"equity":99999.4,
                "realized_pnl":-0.6,"unrealized_pnl":0.0,"total_pnl":-0.6,
                "positions":[],"event_count":2,"last_sequence":2
            },
            "replay_state":{"cash":99999.4,"realized_pnl":-0.6,"last_sequence":2},
            "total_commission":0.5
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o66=self.r/"o66"
        a=build_audit_reconciliation_foundation(self.cert,self.cfg,o66)
        o67=self.r/"o67"
        b=run_cash_position_fill_cross_check(
            o66/"audit_reconciliation_foundation_v78_66.json",
            self.normalization,self.reconciliation,o67)
        o68=self.r/"o68"
        c=run_ledger_integrity_replay_audit(self.normalization,self.reconciliation,o68)
        o69=self.r/"o69"
        d=run_audit_reconciliation_safety_gate(
            o66/"audit_reconciliation_foundation_v78_66.json",
            o67/"cash_position_fill_cross_check_v78_67.json",
            o68/"ledger_integrity_replay_audit_v78_68.json",o69)
        o70=self.r/"o70"
        e=issue_audit_reconciliation_certificate(
            o66/"audit_reconciliation_foundation_verification_v78_66.json",
            o67/"cash_position_fill_cross_check_verification_v78_67.json",
            o68/"ledger_integrity_replay_audit_verification_v78_68.json",
            o69/"audit_reconciliation_safety_gate_verification_v78_69.json",
            o66/"audit_reconciliation_foundation_v78_66.json",o70)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_audit_chain_tamper_blocked(self):
        r1=build_audit_record(1,"A","1","sha","")
        r2=build_audit_record(2,"B","2","sha2",r1.record_sha256)
        bad=AuditRecord(**{**asdict(r2),"source_sha256":"tampered"})
        with self.assertRaises(ValueError):
            verify_audit_chain([r1,bad])

    def test_sequence_gap_blocked(self):
        r=build_audit_record(2,"A","1","sha","")
        with self.assertRaises(ValueError):
            verify_audit_chain([r])

    def test_duplicate_source_blocked(self):
        r1=build_audit_record(1,"A","same","sha","")
        r2=build_audit_record(2,"B","same","sha2",r1.record_sha256)
        with self.assertRaises(ValueError):
            verify_audit_chain([r1,r2])

    def test_reconstruct_round_trip(self):
        state=reconstruct_expected_state(100000.0,load_json(self.normalization)["normalized_fills"])
        self.assertEqual(state["cash"],99999.4)
        self.assertEqual(state["positions"],[])

    def test_cash_mismatch_detected(self):
        doc=load_json(self.reconciliation)
        doc["portfolio_snapshot"]["cash"]=99998.0
        write_json(self.reconciliation,doc)
        o66=self.r/"o66b"
        build_audit_reconciliation_foundation(self.cert,self.cfg,o66)
        result=run_cash_position_fill_cross_check(
            o66/"audit_reconciliation_foundation_v78_66.json",
            self.normalization,self.reconciliation,self.r/"bad")
        self.assertEqual(result["status"],"FAIL")

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_PERFORMANCE_ACCOUNTING_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.65","status":"FAIL"})
        self.assertEqual(
            build_audit_reconciliation_foundation(self.cert,self.cfg,self.r/"badcert")["status"],
            "FAIL"
        )

    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
            self.assertFalse(x["broker_connected"])

    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))

if __name__=="__main__":
    unittest.main()
