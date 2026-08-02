from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.final_production_release import FinalProductionRelease
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();r=Path(a.repository_root).resolve()
 out=FinalProductionRelease().run(
 scheduled_result_path=r/"release/v142_05_to_v142_08/actual/scheduled_runtime_bundle_result.json",
 scheduled_token_path=r/"release/v142_05_to_v142_08/actual/scheduled_runtime_token.json",
 deployment_snapshot_path=r/"release/v143_final/input/deployment_readiness_snapshot.json",
 rollback_snapshot_path=r/"release/v143_final/input/rollback_readiness_snapshot.json",
 installer_snapshot_path=r/"release/v143_final/input/installer_readiness_snapshot.json",
 production_certificate_path=r/"release/v143_final/actual/final_production_certificate.json",
 deployment_manifest_path=r/"release/v143_final/actual/final_deployment_manifest.json",
 rollback_manifest_path=r/"release/v143_final/actual/final_rollback_manifest.json",
 final_token_path=r/"release/v143_final/actual/final_production_release_token.json",
 result_path=r/"release/v143_final/actual/final_production_release_result.json")
 print(json.dumps(out,indent=2,sort_keys=True));print("RESULT_FILE="+out["result_path"]);return 0 if out["status"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
