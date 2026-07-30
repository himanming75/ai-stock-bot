import hashlib,json,tempfile,unittest
from pathlib import Path
from tools.multi_strategy_tournament_v69_0 import *

def report(name,wr,pf,ex,pnl,gate="APPROVE",promotion="EXTENDED_PAPER_APPROVED",trades=100):
    return {"status":"PASS","pipeline_status":"PASS","network_used":False,"approved_for_live":False,
    "closed_trade_count":trades,"analytics":{"overall":{"trade_count":trades,"win_rate":str(wr),
    "profit_factor":str(pf),"expectancy":str(ex),"net_pnl":str(pnl)},
    "strategy_ranking":[{"strategy":name}]},"quality_gate":{"quality_gate":gate},
    "promotion":{"promotion_state":promotion},"pipeline_report_sha256":"a"*64,
    "schema_version":"v68.0.analytics_pipeline_orchestrator.1"}

def items():
    return [("m.json",report("momentum",".60","2.2","6.1","610"),None),
            ("r.json",report("mean_reversion",".55","1.7","3","300"),None),
            ("b.json",report("breakout",".48","1.1",".5","50","WATCH","WATCHLIST"),None)]

class T(unittest.TestCase):
    def test_version(self): self.assertEqual(VERSION,"69.0")
    def test_schema(self): self.assertEqual(SCHEMA_VERSION,"v69.0.multi_strategy_tournament.1")
    def test_pass(self): self.assertEqual(build_tournament(items())["status"],"PASS")
    def test_count(self): self.assertEqual(build_tournament(items())["candidate_count"],3)
    def test_champion(self): self.assertEqual(build_tournament(items())["champion_strategy"],"momentum")
    def test_runner_up(self): self.assertEqual(build_tournament(items())["runner_up_strategy"],"mean_reversion")
    def test_ranks(self): self.assertEqual([x["rank"] for x in build_tournament(items())["ranking"]],[1,2,3])
    def test_order(self): self.assertEqual([x["strategy"] for x in build_tournament(items())["ranking"]],["momentum","mean_reversion","breakout"])
    def test_live_false(self): self.assertFalse(build_tournament(items())["approved_for_live"])
    def test_network_false(self): self.assertFalse(build_tournament(items())["network_used"])
    def test_walk_forward(self): self.assertTrue(build_tournament(items())["requires_walk_forward_validation"])
    def test_no_eligible(self):
        x=[("a",report("a",".2",".5","-5","-50","REJECT","BLOCKED"),None),("b",report("b",".3",".7","-2","-20","REJECT","BLOCKED"),None)]
        self.assertIsNone(build_tournament(x)["champion_strategy"])
    def test_low_sample(self):
        x=items(); x[0]=("m",report("momentum",".6","2","5","500",trades=10),None)
        row=next(z for z in build_tournament(x)["ranking"] if z["strategy"]=="momentum")
        self.assertFalse(row["eligible"])
    def test_duplicate(self):
        x=[("a",report("same",".6","2","5","500"),None),("b",report("same",".5","1","1","100"),None)]
        with self.assertRaises(TournamentError): build_tournament(x)
    def test_minimum(self):
        with self.assertRaises(TournamentError): build_tournament(items()[:1])
    def test_bad_status(self):
        x=items(); x[0][1]["status"]="FAIL"
        with self.assertRaises(TournamentError): build_tournament(x)
    def test_bad_network(self):
        x=items(); x[0][1]["network_used"]=True
        with self.assertRaises(TournamentError): build_tournament(x)
    def test_bad_schema(self):
        x=items(); x[0][1]["schema_version"]="bad"
        with self.assertRaises(TournamentError): build_tournament(x)
    def test_hash(self):
        r=build_tournament(items()); c=dict(r); observed=c.pop("tournament_report_sha256")
        self.assertEqual(observed,hashlib.sha256(canonical_json(c).encode()).hexdigest())
    def test_deterministic(self): self.assertEqual(build_tournament(items()),build_tournament(items()))
    def test_run_and_main(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); args=[]
            for i,(_,r,_) in enumerate(items()):
                p=root/f"{i}.json"; p.write_text(json.dumps(r)); args+=["--input",str(p)]
            out=root/"out.json"
            self.assertEqual(main(args+["--output",str(out)]),0)
            self.assertTrue(out.exists())
    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.assertEqual(main(["--input",str(root/"a"),"--input",str(root/"b"),"--output",str(root/"o")]),1)

if __name__=="__main__": unittest.main()
