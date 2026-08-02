from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def _get_json(url: str, key: str, secret: str, timeout: int = 15) -> Any:
    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read().decode("utf-8")
        return json.loads(data) if data else {}


class AutomaticSnapshotCollector:
    def run(
        self,
        *,
        weekly_review_path: Path,
        collector_policy_path: Path,
        fixture_snapshot_path: Path,
        previous_snapshot_path: Path,
        current_snapshot_path: Path,
        history_dir: Path,
        rotation_report_path: Path,
        collector_token_path: Path,
        result_path: Path,
        base_url: str = PAPER_BASE_URL,
        enable_network: bool = False,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            weekly = _load(weekly_review_path)
        except Exception as exc:
            weekly = {}
            issues.append({"code":"INVALID_WEEKLY_REVIEW","blocking":True,"detail":str(exc)})

        if not weekly:
            issues.append({"code":"WEEKLY_REVIEW_NOT_FOUND","blocking":True,"detail":str(weekly_review_path)})

        status = str(weekly.get("status","")).upper()
        state = str(weekly.get("state","")).upper()
        safe = bool(weekly.get("safe_mode_engaged",False))
        weekly_ready = bool(weekly.get("weekly_review_ready",False))
        continuation_allowed = bool(weekly.get("pilot_continuation_allowed",False))
        pilot_id = str(weekly.get("pilot_id","")).strip()

        if status == "BLOCKED" or safe:
            issues.append({"code":"SOURCE_WEEKLY_REVIEW_SAFE_MODE","blocking":True,"detail":state})

        required = (
            (weekly_ready and continuation_allowed)
            or state == "WEEKLY_PILOT_REVIEW_READY"
        )

        try:
            policy = _load(collector_policy_path) if required else {}
        except Exception as exc:
            policy = {}
            issues.append({"code":"INVALID_COLLECTOR_POLICY","blocking":True,"detail":str(exc)})

        if required and not policy:
            issues.append({"code":"COLLECTOR_POLICY_NOT_FOUND","blocking":True,"detail":str(collector_policy_path)})

        endpoint_verified = base_url.rstrip("/") == PAPER_BASE_URL
        if required and not endpoint_verified:
            issues.append({"code":"NON_PAPER_ENDPOINT_BLOCKED","blocking":True,"detail":base_url})

        policy_ready = False
        collector_id = ""
        if policy:
            collector_id = str(policy.get("collector_id","")).strip()
            checks = [
                ("COLLECTOR_ID_MISSING", bool(collector_id)),
                ("READ_ONLY_REQUIRED", bool(policy.get("read_only",False))),
                ("ORDER_SUBMISSION_MUST_BE_DISABLED", not bool(policy.get("order_submission_enabled",True))),
                ("LIVE_TRADING_MUST_BE_DISABLED", not bool(policy.get("live_trading_enabled",True))),
                ("ROTATION_MUST_BE_ENABLED", bool(policy.get("rotation_enabled",False))),
                ("HISTORY_LIMIT_INVALID", 1 <= int(policy.get("history_limit",0)) <= 365),
                ("PAPER_ENDPOINT_POLICY_REQUIRED", str(policy.get("expected_base_url","")).rstrip("/") == PAPER_BASE_URL),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"collector policy gate failed"})
            policy_ready = all(passed for _,passed in checks)

        key = os.getenv("APCA_API_KEY_ID","")
        secret = os.getenv("APCA_API_SECRET_KEY","")
        credentials_present = bool(key and secret)
        credentials_used = False
        network_requests = 0
        snapshot: dict[str, Any] = {}

        if required and policy_ready and endpoint_verified and not any(i.get("blocking") for i in issues):
            if enable_network:
                if not credentials_present:
                    issues.append({"code":"PAPER_CREDENTIALS_MISSING","blocking":True,"detail":"APCA_API_KEY_ID and APCA_API_SECRET_KEY required"})
                else:
                    credentials_used = True
                    try:
                        account = _get_json(f"{PAPER_BASE_URL}/v2/account",key,secret); network_requests += 1
                        clock = _get_json(f"{PAPER_BASE_URL}/v2/clock",key,secret); network_requests += 1
                        orders = _get_json(f"{PAPER_BASE_URL}/v2/orders?status=open",key,secret); network_requests += 1
                        positions = _get_json(f"{PAPER_BASE_URL}/v2/positions",key,secret); network_requests += 1
                        snapshot = {
                            "account": dict(account) if isinstance(account,dict) else {},
                            "clock": dict(clock) if isinstance(clock,dict) else {},
                            "open_orders": list(orders) if isinstance(orders,list) else [],
                            "positions": list(positions) if isinstance(positions,list) else [],
                        }
                    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TypeError) as exc:
                        issues.append({"code":"PAPER_READ_FAILED","blocking":True,"detail":str(exc)})
            else:
                try:
                    snapshot = _load(fixture_snapshot_path)
                except Exception as exc:
                    issues.append({"code":"INVALID_FIXTURE_SNAPSHOT","blocking":True,"detail":str(exc)})
                if not snapshot:
                    issues.append({"code":"FIXTURE_SNAPSHOT_NOT_FOUND","blocking":True,"detail":str(fixture_snapshot_path)})

        snapshot_valid = False
        if snapshot:
            account = dict(snapshot.get("account",{}))
            checks = [
                ("ACCOUNT_NOT_ACTIVE", str(account.get("status","")).upper()=="ACTIVE"),
                ("ACCOUNT_BLOCKED", not bool(account.get("account_blocked",False))),
                ("TRADING_BLOCKED", not bool(account.get("trading_blocked",False))),
                ("NEGATIVE_EQUITY", float(account.get("equity",0))>=0),
                ("NEGATIVE_CASH", float(account.get("cash",0))>=0),
                ("OPEN_ORDERS_NOT_LIST", isinstance(snapshot.get("open_orders",[]),list)),
                ("POSITIONS_NOT_LIST", isinstance(snapshot.get("positions",[]),list)),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"snapshot validation failed"})
            snapshot_valid = all(passed for _,passed in checks)

        rotated = False
        current_written = False
        history_written = False
        history_pruned = 0
        history_path = ""
        now = datetime.now(timezone.utc)
        captured_at = now.isoformat()

        if snapshot_valid and not any(i.get("blocking") for i in issues):
            snapshot = dict(snapshot)
            snapshot["metadata"] = {
                "stage_range":"OP1.13-OP1.16",
                "collector_id":collector_id,
                "pilot_id":pilot_id,
                "captured_at":captured_at,
                "network_mode":enable_network,
                "read_only":True,
            }

            if current_snapshot_path.exists():
                previous_snapshot_path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(current_snapshot_path,previous_snapshot_path)
                rotated = True

            _write(current_snapshot_path,snapshot)
            current_written = True

            history_dir.mkdir(parents=True,exist_ok=True)
            stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
            history_file = history_dir/f"paper_snapshot_{stamp}.json"
            _write(history_file,snapshot)
            history_path = str(history_file.resolve())
            history_written = True

            limit = int(policy.get("history_limit",30))
            history_files = sorted(history_dir.glob("paper_snapshot_*.json"))
            while len(history_files) > limit:
                history_files[0].unlink()
                history_pruned += 1
                history_files.pop(0)

        blocking = sum(1 for i in issues if i.get("blocking"))
        collector_ready = bool(
            required and policy_ready and endpoint_verified and snapshot_valid
            and current_written and history_written and blocking == 0
        )

        _write(rotation_report_path,{
            "stage":"OP1.16",
            "pilot_id":pilot_id,
            "collector_id":collector_id,
            "previous_snapshot_rotated":rotated,
            "current_snapshot_written":current_written,
            "history_snapshot_written":history_written,
            "history_path":history_path,
            "history_pruned":history_pruned,
            "collector_ready":collector_ready,
            "created_at":captured_at,
        })

        token_written = False
        duplicate_token = False
        if collector_ready:
            token = {
                "stage_range":"OP1.13-OP1.16",
                "pilot_id":pilot_id,
                "collector_id":collector_id,
                "automatic_snapshot_collector_ready":True,
                "read_only":True,
                "order_submission_enabled":False,
                "live_trading_enabled":False,
                "network_reads_enabled":bool(enable_network),
                "created_at":captured_at,
            }
            if collector_token_path.exists():
                existing = _load(collector_token_path)
                if existing.get("collector_id")==collector_id:
                    duplicate_token = True
                else:
                    issues.append({"code":"COLLECTOR_TOKEN_CONFLICT","blocking":True,"detail":"another collector token exists"})
            else:
                _write(collector_token_path,token)
                token_written = True

        blocking = sum(1 for i in issues if i.get("blocking"))
        safe_mode = blocking > 0
        final_ready = bool(collector_ready and (token_written or duplicate_token) and not safe_mode)

        if safe_mode:
            out_state,out_status = "AUTOMATIC_SNAPSHOT_COLLECTOR_SAFE_MODE","BLOCKED"
        elif final_ready:
            out_state,out_status = "AUTOMATIC_SNAPSHOT_COLLECTION_READY","PASS"
        else:
            out_state,out_status = "WAIT_WEEKLY_PILOT_REVIEW","PASS"

        result = {
            "stage_range":"OP1.13-OP1.16",
            "implementation_type":"AUTOMATIC_READ_ONLY_SNAPSHOT_COLLECTOR",
            "status":out_status,
            "state":out_state,
            "pilot_id":pilot_id,
            "collector_id":collector_id,
            "endpoint_verified":endpoint_verified,
            "policy_ready":policy_ready,
            "credentials_present":credentials_present,
            "snapshot_valid":snapshot_valid,
            "previous_snapshot_rotated":rotated,
            "current_snapshot_written":current_written,
            "history_snapshot_written":history_written,
            "history_pruned":history_pruned,
            "automatic_snapshot_collector_ready":final_ready,
            "collector_token_written":token_written,
            "duplicate_collector_token":duplicate_token,
            "read_only":True,
            "order_submission_enabled":False,
            "live_trading_enabled":False,
            "actual_credentials_used":credentials_used,
            "actual_external_network_used":network_requests>0,
            "network_requests_executed":network_requests,
            "write_requests_executed":0,
            "actual_paper_orders_submitted":0,
            "live_orders_submitted":0,
            "safe_mode_engaged":safe_mode,
            "issue_count":len(issues),
            "blocking_issue_count":blocking,
            "issues":issues,
            "next_phase":"OP1_17_WINDOWS_SCHEDULED_READ_ONLY_COLLECTION" if final_ready else "OP1_13_TO_OP1_16_WAIT_WEEKLY_REVIEW",
            "validation_mode":"ACTUAL_PAPER_GET_ONLY" if enable_network else "LOCAL_FIXTURE_SNAPSHOT_ONLY",
            "observed_at":captured_at,
            "result_path":str(result_path.resolve()),
        }
        _write(result_path,result)
        return result
