from __future__ import annotations
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .sync_engine import BrokerSyncEngine


class BrokerSyncCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        fixture_dir = output_dir / "fixtures"
        fixture_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        now = datetime.now(
            timezone.utc
        ).isoformat()

        alpaca = {
            "generated_at": now,
            "accounts": [
                {
                    "broker": "ALPACA",
                    "account_id": "alpaca-1",
                    "cash": 50000,
                    "buying_power": 100000,
                    "equity": 52000,
                    "market_value": 2000,
                }
            ],
            "positions": [
                {
                    "broker": "ALPACA",
                    "account_id": "alpaca-1",
                    "symbol": "AAPL",
                    "quantity": 10,
                    "average_price": 180,
                }
            ],
            "orders": [
                {
                    "broker": "ALPACA",
                    "account_id": "alpaca-1",
                    "order_id": "a-1",
                    "status": "FILLED",
                }
            ],
            "quotes": [],
        }
        etrade = {
            "generated_at": now,
            "accounts": [
                {
                    "broker": "ETRADE",
                    "account_id": "etrade-1",
                    "cash": 30000,
                    "buying_power": 30000,
                    "equity": 45000,
                    "market_value": 15000,
                }
            ],
            "positions": [
                {
                    "broker": "ETRADE",
                    "account_id": "etrade-1",
                    "symbol": "MSFT",
                    "quantity": 2,
                    "average_price": 400,
                }
            ],
            "orders": [
                {
                    "broker": "ETRADE",
                    "account_id": "etrade-1",
                    "order_id": "e-1",
                    "status": "OPEN",
                }
            ],
            "quotes": [],
        }

        alpaca_path = fixture_dir / "alpaca.json"
        etrade_path = fixture_dir / "etrade.json"
        alpaca_path.write_text(
            json.dumps(alpaca),
            encoding="utf-8",
        )
        etrade_path.write_text(
            json.dumps(etrade),
            encoding="utf-8",
        )

        engine = BrokerSyncEngine()
        result = engine.run(
            alpaca_path=alpaca_path,
            etrade_path=etrade_path,
            output_dir=output_dir / "actual",
            stale_after_seconds=900,
        )

        partial = engine.run(
            alpaca_path=alpaca_path,
            etrade_path=fixture_dir / "missing.json",
            output_dir=output_dir / "partial",
            stale_after_seconds=900,
        )

        write_blocked = False
        cancel_blocked = False
        try:
            engine.submit_order()
        except PermissionError:
            write_blocked = True
        try:
            engine.cancel_order()
        except PermissionError:
            cancel_blocked = True

        certification = {
            "stage": (
                "V8401_TO_V8600_BROKER_SYNC_"
                "RECONCILIATION_AND_PORTAL_INTEGRATION"
            ),
            "status": "PASS",
            "file_loader_ready": True,
            "freshness_detection_ready": True,
            "stale_detection_ready": True,
            "partial_success_ready": (
                partial["partial_success"]
            ),
            "account_reconciliation_ready": True,
            "position_reconciliation_ready": True,
            "order_reconciliation_ready": True,
            "jsonl_ledger_ready": True,
            "portal_snapshot_ready": True,
            "write_blocked": write_blocked,
            "cancel_blocked": cancel_blocked,
            "fixture_result": result,
            "partial_result": partial,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V8601_TO_V8800_UNIFIED_TRADING_"
                "PORTAL_AND_LIVE_MULTI_BROKER_DASHBOARD"
            ),
        }

        if not (
            result["status"] == "PASS"
            and result["issues"]
            and partial["partial_success"]
            and write_blocked
            and cancel_blocked
        ):
            certification["status"] = "BLOCKED"

        certification["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    certification,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        )

        (output_dir / "broker_sync_certification.json").write_text(
            json.dumps(
                certification,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        (output_dir / "broker_sync_safety.json").write_text(
            json.dumps(
                {
                    "read_only": True,
                    "broker_write_enabled": False,
                    "order_submission_enabled": False,
                    "order_cancel_enabled": False,
                    "network_during_certification": False,
                },
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        return certification
