from pathlib import Path
import argparse,json
def main():
 p=argparse.ArgumentParser();p.add_argument("--output-dir",required=True);a=p.parse_args()
 d=json.loads((Path(a.output_dir)/"automatic_restart_recovery_verification_v77_18.json").read_text(encoding="utf-8"))
 errors=[] if d.get("status")=="PASS" and d.get("verified") is True and d.get("error_count")==0 else ["stage_verification"]
 r={"verified":not errors,"status":"PASS" if not errors else "FAIL","error_count":len(errors),"errors":errors,"next_phase":d.get("next_phase")}
 print(json.dumps(r,indent=2));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
