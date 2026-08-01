from pathlib import Path
import json,hashlib
o=Path("release/v86_40/output");c=json.loads((o/"lifecycle_certificate_v86_40.json").read_text());u=dict(c);e=u.pop("certificate_sha256")
checks={"certificate_hash_valid":e==hashlib.sha256(json.dumps(u,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest(),"status_pass":c["status"]=="PASS","validation_complete":c["paper_order_lifecycle_validation_complete"] is True,"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,v in checks.items() if not v];print(json.dumps({"stage_range":"V86.21-V86.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
