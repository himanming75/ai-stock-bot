from __future__ import annotations
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .ledger import append_jsonl
from .loader import load_json_snapshot
from .normalization import normalize_snapshot
from .portal import build_portal_snapshot
from .reconciliation import (
    reconcile_accounts,
    reconcile_orders,
    reconcile_positions,
)


class BrokerSyncEngine:
    def run(
        self,
        *,
        alpaca_path: Path,
        etrade_path: Path,
        output_dir: Path,
        stale_after_seconds: float = 900,
    ) -> dict:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        run_id = f"sync_{secrets.token_hex(8)}"
        generated_at = datetime.now(
            timezone.utc
        ).isoformat()

        alpaca_raw, alpaca_health = load_json_snapshot(
            alpaca_path,
            broker="ALPACA",
            stale_after_seconds=stale_after_seconds,
        )
        etrade_raw, etrade_health = load_json_snapshot(
            etrade_path,
            broker="ETRADE",
            stale_after_seconds=stale_after_seconds,
        )

        snapshots = {}
        errors = []
        if alpaca_health.available:
            snapshots["ALPACA"] = normalize_snapshot(
                alpaca_raw
            )
        else:
            errors.append({
                "broker": "ALPACA",
                "error": alpaca_health.error,
            })

        if etrade_health.available:
            snapshots["ETRADE"] = normalize_snapshot(
                etrade_raw
            )
        else:
            errors.append({
                "broker": "ETRADE",
                "error": etrade_health.error,
            })

        issues = []
        if (
            "ALPACA" in snapshots
            and "ETRADE" in snapshots
        ):
            issues.extend(
                reconcile_accounts(
                    snapshots["ALPACA"],
                    snapshots["ETRADE"],
                    left_name="ALPACA",
                    right_name="ETRADE",
                )
            )
            issues.extend(
                reconcile_positions(
                    snapshots["ALPACA"],
                    snapshots["ETRADE"],
                    left_name="ALPACA",
                    right_name="ETRADE",
                )
            )
            issues.extend(
                reconcile_orders(
                    snapshots["ALPACA"],
                    snapshots["ETRADE"],
                    left_name="ALPACA",
                    right_name="ETRADE",
                )
            )

        sources = [
            alpaca_health.to_dict(),
            etrade_health.to_dict(),
        ]
        portal = build_portal_snapshot(
            run_id=run_id,
            generated_at=generated_at,
            sources=sources,
            snapshots=snapshots,
            issues=issues,
            errors=errors,
        )

        result = {
            "run_id": run_id,
            "generated_at": generated_at,
            "status": (
                "PASS"
                if snapshots
                else "BLOCKED"
            ),
            "partial_success": (
                bool(snapshots) and bool(errors)
            ),
            "sources": sources,
            "snapshots": snapshots,
            "issues": issues,
            "errors": errors,
            "portal_snapshot": portal,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
        }

        (output_dir / "broker_sync_result.json").write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        (output_dir / "multi_broker_portal_snapshot.json").write_text(
            json.dumps(
                portal,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        append_jsonl(
            output_dir / "broker_reconciliation_ledger.jsonl",
            {
                "run_id": run_id,
                "generated_at": generated_at,
                "status": result["status"],
                "partial_success": result[
                    "partial_success"
                ],
                "source_status": {
                    item["broker"]: item["freshness"]
                    for item in sources
                },
                "issue_count": len(issues),
                "error_count": len(errors),
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "order_cancel_enabled": False,
            },
        )
        return result

    def submit_order(self, *args, **kwargs):
        raise PermissionError("BROKER_WRITE_DISABLED")

    def cancel_order(self, *args, **kwargs):
        raise PermissionError("BROKER_WRITE_DISABLED")
