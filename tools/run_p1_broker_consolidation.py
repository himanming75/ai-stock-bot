from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from broker_integration.inspection import inspect_repository
from broker_integration.registry import consolidation_manifest
from broker_integration.paths import BrokerStatePaths
from broker_integration.io import write_json,append_jsonl
inspection=inspect_repository(ROOT);manifest=consolidation_manifest();paths=BrokerStatePaths(ROOT)
core={"stage":"P1","state":"BROKER_CONSOLIDATION_CANONICAL_PATH_READY" if inspection["consolidation_valid"] else "BROKER_CONSOLIDATION_BLOCKED","status":"PASS" if inspection["consolidation_valid"] else "FAIL","observed_at":datetime.now(timezone.utc).isoformat(),"inspection":inspection,"legacy_files_deleted":[],"canonical_state_root":str(paths.canonical_root),"idempotency_registry_path":str(paths.order_registry),"order_ledger_path":str(paths.order_ledger),"fill_ledger_path":str(paths.fill_ledger),"portfolio_state_path":str(paths.portfolio_state),"checkpoint_path":str(paths.checkpoint),"kill_switch_path":str(paths.kill_switch),"broker_write_enabled":False,"paper_submission_enabled":False,"live_submission_enabled":False,"actual_paper_orders_submitted":0,"actual_live_orders_submitted":0,"next_fixed_stage":"P2_ACTUAL_ALPACA_PAPER_EXECUTION"}
core["consolidation_hash"]=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
write_json(paths.component_registry,manifest["canonical"]);write_json(paths.compatibility_map,manifest["compatibility"]);write_json(paths.deprecation_manifest,manifest["deprecated"]);write_json(paths.order_registry,{"client_order_ids":[]});write_json(paths.kill_switch,{"kill_switch_active":True,"reason":"P1_ONLY"});write_json(paths.consolidation_result,core);append_jsonl(paths.canonical_root/'consolidation_audit_ledger.jsonl',core)
print(json.dumps({"stage":"P1","state":core["state"],"status":core["status"],"missing_required_roles":inspection["missing_required_roles"],"legacy_files_deleted":[],"next_fixed_stage":core["next_fixed_stage"]},indent=2));raise SystemExit(0 if core["status"]=="PASS" else 1)
