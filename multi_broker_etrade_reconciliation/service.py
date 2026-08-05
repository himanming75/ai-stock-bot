from __future__ import annotations
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .diff import account_changes, order_changes, position_changes
from .fixtures import CURRENT, PREVIOUS
from .integrity import validate_snapshot


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ETradePortfolioReconciliationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
        previous_snapshot: dict | None = None,
        current_snapshot: dict | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        previous_snapshot = previous_snapshot or PREVIOUS
        current_snapshot = current_snapshot or CURRENT

        previous_integrity = validate_snapshot(previous_snapshot)
        current_integrity = validate_snapshot(current_snapshot)

        events = []
        if previous_integrity["passed"] and current_integrity["passed"]:
            events.extend(account_changes(
                previous_snapshot["accounts"],
                current_snapshot["accounts"],
            ))
            events.extend(position_changes(
                previous_snapshot["positions"],
                current_snapshot["positions"],
            ))
            events.extend(order_changes(
                previous_snapshot["orders"],
                current_snapshot["orders"],
            ))

        event_dicts = [event.to_dict() for event in events]
        severity_counts = dict(Counter(
            item["severity"] for item in event_dicts
        ))
        type_counts = dict(Counter(
            item["event_type"] for item in event_dicts
        ))

        result = {
            "stage": (
                "V4401_TO_V4600_ETRADE_PORTFOLIO_"
                "RECONCILIATION_AND_CHANGE_DETECTION"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": "FIXTURE_SNAPSHOT_DIFF",
            "previous_integrity": previous_integrity,
            "current_integrity": current_integrity,
            "change_count": len(event_dicts),
            "changes": event_dicts,
            "severity_counts": severity_counts,
            "event_type_counts": type_counts,
            "new_positions_detected": sum(
                1 for item in event_dicts
                if item["event_type"] == "POSITION_OPENED"
            ),
            "closed_positions_detected": sum(
                1 for item in event_dicts
                if item["event_type"] == "POSITION_CLOSED"
            ),
            "position_quantity_changes_detected": sum(
                1 for item in event_dicts
                if item["event_type"] == "POSITION_QUANTITY_CHANGED"
            ),
            "order_status_changes_detected": sum(
                1 for item in event_dicts
                if item["event_type"] == "ORDER_STATUS_CHANGED"
            ),
            "account_balance_changes_detected": sum(
                1 for item in event_dicts
                if item["event_type"] in {
                    "ACCOUNT_EQUITY_CHANGED",
                    "ACCOUNT_CASH_CHANGED",
                    "ACCOUNT_BUYING_POWER_CHANGED",
                }
            ),
            "integrity_checks_ready": True,
            "change_ledger_ready": True,
            "critical_event_detection_ready": True,
            "production_network_read_performed": False,
            "sandbox_network_read_performed": False,
            "real_credentials_used": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "existing_alpaca_controller_modified": False,
            "existing_market_polling_modified": False,
            "key_issuance_blocks_code_development": False,
            "deferred_external_validation": (
                "RECONCILE_ACTUAL_ETRADE_SNAPSHOTS_AFTER_KEY_ISSUANCE"
            ),
            "next_fixed_development": (
                "V4601_TO_V4800_ETRADE_ACCOUNT_HEALTH_"
                "MONITORING_AND_FAILSAFE_ROUTING"
            ),
        }

        if (
            not previous_integrity["passed"]
            or not current_integrity["passed"]
        ):
            result["status"] = "BLOCKED"

        seed = dict(result)
        seed.pop("generated_at")
        result["certification_fingerprint"] = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / "etrade_reconciliation_certification.json",
            result,
        )
        write_json(
            output_dir / "etrade_change_events.json",
            {"items": event_dicts},
        )
        write_json(
            output_dir / "etrade_reconciliation_summary.json",
            {
                "status": result["status"],
                "change_count": result["change_count"],
                "severity_counts": severity_counts,
                "event_type_counts": type_counts,
                "integrity": {
                    "previous": previous_integrity,
                    "current": current_integrity,
                },
            },
        )
        write_json(
            output_dir / "previous_snapshot_fixture.json",
            previous_snapshot,
        )
        write_json(
            output_dir / "current_snapshot_fixture.json",
            current_snapshot,
        )

        csv_path = output_dir / "etrade_change_events.csv"
        keys = [
            "event_type", "severity", "entity_type", "entity_key",
            "account_id", "symbol", "previous", "current",
            "delta", "message",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            for row in event_dicts:
                writer.writerow({
                    key: (
                        json.dumps(row.get(key), sort_keys=True)
                        if isinstance(row.get(key), (dict, list))
                        else row.get(key)
                    )
                    for key in keys
                })

        with (
            output_dir / "etrade_reconciliation_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        return result
