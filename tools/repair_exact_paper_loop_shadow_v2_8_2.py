from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse, json, shutil, py_compile

TARGET_REL=Path("paper_daily_session/runner.py")
BACKUP_REL=Path("runtime/regime_aware_buy_shadow_v2_8_1/runner.py.pre_v2_8_1.bak")
REPORT_REL=Path("runtime/regime_aware_buy_shadow_v2_8_2/latest_repair_v2_8_2.json")

METHOD_MARKER='    def _run_regime_shadow_cycle(self) -> dict[str, Any]:'
CALL_MARKER='                regime_shadow_v2_8_1 = self._run_regime_shadow_cycle()'

METHOD_BLOCK = '''
    def _run_regime_shadow_cycle(self) -> dict[str, Any]:
        script = self.root / "tools" / "run_regime_aware_shadow_v2_7.py"
        audit_dir = self.root / "runtime" / "regime_aware_buy_shadow_v2_8_1"
        audit_dir.mkdir(parents=True, exist_ok=True)
        ledger = audit_dir / "hook_ledger.jsonl"

        result: dict[str, Any] = {
            "stage": "V2.8.1_REGIME_SHADOW_HOOK",
            "timestamp_utc": utc_now(),
            "mode": "READ_ONLY_SHADOW",
            "script": str(script),
            "attempted": False,
            "exit_code": None,
            "status": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "broker_write_performed": False,
            "paper_order_submission_performed": False,
            "live_order_submission_performed": False,
            "primary_paper_flow_blocked": False,
        }

        try:
            if not script.exists():
                result["status"] = "SHADOW_SCRIPT_MISSING"
            else:
                result["attempted"] = True
                process = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "--root",
                        str(self.root),
                    ],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=45,
                    check=False,
                )
                result["exit_code"] = process.returncode
                result["stdout_tail"] = (process.stdout or "")[-4000:]
                result["stderr_tail"] = (process.stderr or "")[-4000:]
                result["status"] = (
                    "PASS"
                    if process.returncode == 0
                    else "SHADOW_NONZERO_ISOLATED"
                )
        except subprocess.TimeoutExpired as exc:
            result["status"] = "SHADOW_TIMEOUT_ISOLATED"
            result["stderr_tail"] = str(exc)
        except Exception as exc:
            result["status"] = "SHADOW_EXCEPTION_ISOLATED"
            result["stderr_tail"] = str(exc)

        append_jsonl(ledger, result)
        return result
'''

CALL_BLOCK = '''
                # V2.8.2: read-only regime-aware shadow hook.
                # Failure is intentionally isolated from primary Paper flow.
                regime_shadow_v2_8_1 = self._run_regime_shadow_cycle()
'''

def repair(root:Path) -> int:
    root=root.resolve()
    target=root/TARGET_REL
    backup=root/BACKUP_REL
    out=root/REPORT_REL.parent
    out.mkdir(parents=True,exist_ok=True)
    report_path=root/REPORT_REL

    report={
        "stage":"V2.8.2_REPAIR_EXACT_PAPER_LOOP_SHADOW_HOOK",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "target":str(TARGET_REL).replace("\\","/"),
        "backup":str(BACKUP_REL).replace("\\","/"),
        "status":None,
        "restored_from_backup":False,
        "literal_backslash_n_detected_before_repair":False,
        "compile_after_repair":False,
        "contracts":{
            "existing_poll_loop_reused":True,
            "shadow_failure_isolated":True,
            "broker_write_added":False,
            "paper_order_submission_added":False,
            "live_order_submission_added":False,
            "production_selector_changed":False,
            "production_strategy_parameter_changed":False,
            "automatic_promotion":False,
        },
    }

    if not target.exists():
        report["status"]="BLOCKED_TARGET_MISSING"
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))
        return 2

    broken_text=target.read_text(encoding="utf-8",errors="replace")
    report["literal_backslash_n_detected_before_repair"]='\\n    def run(self) -> dict[str, Any]:' in broken_text

    if not backup.exists():
        report["status"]="BLOCKED_BACKUP_MISSING"
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))
        return 3

    shutil.copy2(backup,target)
    report["restored_from_backup"]=True

    text=target.read_text(encoding="utf-8",errors="replace")
    method_anchor='    def run(self) -> dict[str, Any]:'
    call_anchor='                clock = self._clock_data(client)'

    if method_anchor not in text or call_anchor not in text:
        report["status"]="BLOCKED_ORIGINAL_ANCHOR_MISSING"
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))
        return 4

    if METHOD_MARKER in text or CALL_MARKER in text:
        report["status"]="BLOCKED_BACKUP_NOT_CLEAN"
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))
        return 5

    # IMPORTANT: concatenate with real newline characters, not literal backslash+n.
    text=text.replace(method_anchor, METHOD_BLOCK + "\n" + method_anchor, 1)
    text=text.replace(call_anchor, CALL_BLOCK + "\n" + call_anchor, 1)

    target.write_text(text,encoding="utf-8")

    repaired=target.read_text(encoding="utf-8",errors="replace")
    if '\\n    def run(self) -> dict[str, Any]:' in repaired:
        report["status"]="BLOCKED_LITERAL_BACKSLASH_N_REMAINS"
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))
        return 6

    try:
        py_compile.compile(str(target),doraise=True)
        report["compile_after_repair"]=True
    except Exception as exc:
        report["status"]="BLOCKED_COMPILE_FAILED"
        report["compile_error"]=str(exc)
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(json.dumps(report,indent=2))
        return 7

    report["status"]="PASS_REPAIRED_AND_INTEGRATED"
    report["method_marker_count"]=repaired.count(METHOD_MARKER)
    report["call_marker_count"]=repaired.count(CALL_MARKER)
    report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 0

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    return repair(Path(a.root))

if __name__=="__main__":
    raise SystemExit(main())
