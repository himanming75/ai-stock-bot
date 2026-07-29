import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from tools.paper_trading_pipeline_v58_1 import *

class PipelineTests(unittest.TestCase):
    def case(self,statuses=None,network=None,fail_fast=True):
        td=tempfile.TemporaryDirectory();root=Path(td.name);statuses=statuses or {};network=network or {};stages=[]
        for name in STAGES:
            s=root/f"{name}.py";s.write_text("# mock")
            i=root/f"{name}.json";i.write_text("{}")
            stages.append(StageSpec(name,str(s),str(i),str(root/f"{name}.out.json")))
        cfg=PipelineConfig("pipe-1","python","paper",fail_fast,stages)
        def runner(cmd,capture_output,text):
            stage=Path(cmd[1]).stem
            name=next(x for x in STAGES if x in stage)
            result={"status":statuses.get(name,"PASS"),"network_used":network.get(name,False),"stage":name}
            Path(cmd[-1]).write_text(json.dumps(result))
            return SimpleNamespace(returncode=0 if result["status"]=="PASS" else 1,stdout="ok",stderr="")
        return td,cfg,runner
    def test_pass(self):
        td,c,r=self.case();self.assertEqual("PASS",PaperTradingPipelineV581(c,runner=r).run()["status"]);td.cleanup()
    def test_four(self):
        td,c,r=self.case();self.assertEqual(4,PaperTradingPipelineV581(c,runner=r).run()["completed_stage_count"]);td.cleanup()
    def test_fail_fast(self):
        td,c,r=self.case({"v55_sizing":"FAIL"});self.assertEqual(2,PaperTradingPipelineV581(c,runner=r).run()["completed_stage_count"]);td.cleanup()
    def test_no_fail_fast(self):
        td,c,r=self.case({"v55_sizing":"FAIL"},fail_fast=False);self.assertEqual(4,PaperTradingPipelineV581(c,runner=r).run()["completed_stage_count"]);td.cleanup()
    def test_network(self):
        td,c,r=self.case(network={"v56_risk":True});self.assertEqual("FAIL",PaperTradingPipelineV581(c,runner=r).run()["status"]);td.cleanup()
    def test_hash(self):
        td,c,r=self.case();self.assertEqual(64,len(PaperTradingPipelineV581(c,runner=r).run()["pipeline_sha256"]));td.cleanup()
    def test_genesis(self):
        td,c,r=self.case();self.assertEqual("GENESIS",PaperTradingPipelineV581(c,runner=r).run()["ledger"][0]["previous_entry_sha256"]);td.cleanup()
    def test_chain(self):
        td,c,r=self.case();x=PaperTradingPipelineV581(c,runner=r).run();self.assertEqual(x["ledger"][0]["entry_sha256"],x["ledger"][1]["previous_entry_sha256"]);td.cleanup()
    def test_live_blocked(self):
        td,c,r=self.case();c=PipelineConfig(c.pipeline_id,c.python_executable,"live",True,c.stages)
        with self.assertRaises(PermissionError):PaperTradingPipelineV581(c,runner=r).run()
        td.cleanup()
    def test_live_unimplemented(self):
        td,c,r=self.case();c=PipelineConfig(c.pipeline_id,c.python_executable,"live",True,c.stages)
        with self.assertRaises(NotImplementedError):PaperTradingPipelineV581(c,enable_live=True,runner=r).run()
        td.cleanup()
    def test_bad_order(self):
        td,c,r=self.case()
        with self.assertRaises(ValueError):PaperTradingPipelineV581(PipelineConfig("x","python","paper",True,list(reversed(c.stages))),runner=r)
        td.cleanup()
    def test_bad_mode(self):
        td,c,r=self.case()
        with self.assertRaises(ValueError):PaperTradingPipelineV581(PipelineConfig("x","python","bad",True,c.stages),runner=r)
        td.cleanup()
    def test_missing_id(self):
        td,c,r=self.case()
        with self.assertRaises(ValueError):PaperTradingPipelineV581(PipelineConfig("","python","paper",True,c.stages),runner=r)
        td.cleanup()
    def test_missing_script(self):
        td,c,r=self.case();Path(c.stages[0].script).unlink()
        with self.assertRaises(FileNotFoundError):PaperTradingPipelineV581(c,runner=r).run()
        td.cleanup()
    def test_missing_input(self):
        td,c,r=self.case();Path(c.stages[0].input).unlink()
        with self.assertRaises(FileNotFoundError):PaperTradingPipelineV581(c,runner=r).run()
        td.cleanup()
    def test_export(self):
        td,c,r=self.case();p=Path(td.name)/"x.json";x=PaperTradingPipelineV581(c,runner=r).run();PaperTradingPipelineV581.export(p,x);self.assertTrue(p.exists());td.cleanup()
if __name__=="__main__":unittest.main()
