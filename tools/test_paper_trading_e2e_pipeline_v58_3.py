import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace

from tools.paper_trading_e2e_pipeline_v58_3 import *

class FakeAdapter:
    def transform(self, handoff_type, source, template):
        out=dict(template)
        out["handoff"]={
            "handoff_type":handoff_type,
            "source_sha256":"a"*64,
            "generated_input_sha256":"b"*64,
            "handoff_sha256":"c"*64,
            "network_used":False,
        }
        return out
    def export(self,path,payload):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(payload))

class Tests(unittest.TestCase):
    def case(self, fail_stage=None, network_stage=None, missing_output=None):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        stage_names=["v54_signal","v55_sizing","v56_risk","v57_execution"]
        stage_files={}
        for name in stage_names:
            script=root/f"{name}.py";script.write_text("# mock")
            inp=root/f"{name}.in.json";inp.write_text("{}")
            out=root/f"{name}.out.json"
            stage_files[name]=(script,inp,out)
        handoff_defs=[
            ("v54_to_v55","v54_to_v55","v54_signal","v55_sizing"),
            ("v55_to_v56","v55_to_v56","v55_sizing","v56_risk"),
            ("v56_to_v57","v56_to_v57","v56_risk","v57_execution"),
        ]
        handoffs=[]
        for name,kind,source,next_stage in handoff_defs:
            template=root/f"{name}.template.json";template.write_text("{}")
            output=stage_files[next_stage][1]
            handoffs.append(HandoffCommand(name,kind,source,str(template),str(output)))
        stages=[StageCommand(n,str(stage_files[n][0]),str(stage_files[n][1]),str(stage_files[n][2])) for n in stage_names]
        cfg=PipelineConfig("pipe-v583","python","paper",stages,handoffs)

        def runner(cmd,capture_output,text):
            stage=Path(cmd[1]).stem
            output=Path(cmd[-1])
            if stage != missing_output:
                status="FAIL" if stage==fail_stage else "PASS"
                result={"status":status,"network_used":stage==network_stage,"stage":stage}
                if stage=="v57_execution":
                    result.update({"final_state":"FILLED","filled_quantity":"100.000000","average_fill_price":"200.20"})
                output.write_text(json.dumps(result))
            return SimpleNamespace(returncode=1 if stage==fail_stage else 0,stdout="ok",stderr="")
        return td,cfg,runner

    def test_pass(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("PASS",x["status"]);td.cleanup()
    def test_seven_components(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual(7,x["completed_component_count"]);td.cleanup()
    def test_final_state(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("FILLED",x["final_execution_state"]);td.cleanup()
    def test_final_quantity(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("100.000000",x["final_filled_quantity"]);td.cleanup()
    def test_final_price(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("200.20",x["final_average_fill_price"]);td.cleanup()
    def test_stage_failure(self):
        td,c,r=self.case(fail_stage="v56_risk");x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("FAIL",x["status"]);td.cleanup()
    def test_fail_fast_position(self):
        td,c,r=self.case(fail_stage="v55_sizing");x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("v55_sizing",x["stopped_at"]);td.cleanup()
    def test_network_rejected(self):
        td,c,r=self.case(network_stage="v56_risk");x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("FAIL",x["status"]);td.cleanup()
    def test_missing_output(self):
        td,c,r=self.case(missing_output="v54_signal");x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("FAIL",x["status"]);td.cleanup()
    def test_pipeline_hash(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual(64,len(x["pipeline_sha256"]));td.cleanup()
    def test_ledger_genesis(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("GENESIS",x["ledger"][0]["previous_entry_sha256"]);td.cleanup()
    def test_ledger_chain(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual(x["ledger"][0]["entry_sha256"],x["ledger"][1]["previous_entry_sha256"]);td.cleanup()
    def test_live_blocked(self):
        td,c,r=self.case();c=PipelineConfig(c.pipeline_id,c.python_executable,"live",c.stages,c.handoffs)
        with self.assertRaises(PermissionError):EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run()
        td.cleanup()
    def test_live_unimplemented(self):
        td,c,r=self.case();c=PipelineConfig(c.pipeline_id,c.python_executable,"live",c.stages,c.handoffs)
        with self.assertRaises(NotImplementedError):EndToEndPipelineV583(c,enable_live=True,runner=r,adapter=FakeAdapter()).run()
        td.cleanup()
    def test_bad_mode(self):
        td,c,r=self.case()
        with self.assertRaises(ValueError):EndToEndPipelineV583(PipelineConfig("x","python","bad",c.stages,c.handoffs),runner=r,adapter=FakeAdapter())
        td.cleanup()
    def test_missing_id(self):
        td,c,r=self.case()
        with self.assertRaises(ValueError):EndToEndPipelineV583(PipelineConfig("","python","paper",c.stages,c.handoffs),runner=r,adapter=FakeAdapter())
        td.cleanup()
    def test_bad_stage_order(self):
        td,c,r=self.case()
        with self.assertRaises(ValueError):EndToEndPipelineV583(PipelineConfig("x","python","paper",list(reversed(c.stages)),c.handoffs),runner=r,adapter=FakeAdapter())
        td.cleanup()
    def test_bad_handoff_order(self):
        td,c,r=self.case()
        with self.assertRaises(ValueError):EndToEndPipelineV583(PipelineConfig("x","python","paper",c.stages,list(reversed(c.handoffs))),runner=r,adapter=FakeAdapter())
        td.cleanup()
    def test_missing_script(self):
        td,c,r=self.case();Path(c.stages[0].script).unlink();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("FAIL",x["status"]);td.cleanup()
    def test_missing_template(self):
        td,c,r=self.case();Path(c.handoffs[0].template).unlink();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();self.assertEqual("FAIL",x["status"]);td.cleanup()
    def test_input_output_mismatch(self):
        td,c,r=self.case();h=list(c.handoffs);h[0]=HandoffCommand(h[0].name,h[0].handoff_type,h[0].source_stage,h[0].template,str(Path(td.name)/"other.json"))
        x=EndToEndPipelineV583(PipelineConfig(c.pipeline_id,c.python_executable,c.mode,c.stages,h),runner=r,adapter=FakeAdapter()).run()
        self.assertEqual("FAIL",x["status"]);td.cleanup()
    def test_export(self):
        td,c,r=self.case();x=EndToEndPipelineV583(c,runner=r,adapter=FakeAdapter()).run();p=Path(td.name)/"final.json";EndToEndPipelineV583.export(p,x);self.assertTrue(p.exists());td.cleanup()
    def test_load_json_object(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.json";p.write_text('{"a":1}');self.assertEqual(1,load_json(p)["a"])
    def test_hash_deterministic(self):
        self.assertEqual(canonical_hash({"a":1,"b":2}),canonical_hash({"b":2,"a":1}))

if __name__=="__main__":unittest.main()
