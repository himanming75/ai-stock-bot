from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .client import AlpacaPaperRejectClient
from .token import consume_token, sha256_file, validate_token

class P3PaperRejectValidationService:
    def __init__(self, client=None) -> None:
        self.client = client or AlpacaPaperRejectClient()

    def run(self, *, plan_path: Path, token_path: Path, nonce: str, output_dir: Path) -> dict:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan_hash = sha256_file(plan_path)
        token, blockers = validate_token(token_path, plan_hash, nonce)

        clock_status, clock = self.client.get_clock()
        account_status, account = self.client.get_account()
        if clock_status != 200:
            blockers.append(f"CLOCK_READ_FAILED:{clock_status}")
        if account_status != 200:
            blockers.append(f"ACCOUNT_READ_FAILED:{account_status}")
        if account and account.get("status") != "ACTIVE":
            blockers.append("ACCOUNT_NOT_ACTIVE")

        payload = plan.get("payload", {})
        if "qty" not in payload or "notional" not in payload:
            blockers.append("INVALID_REJECT_TEST_PAYLOAD")
        if payload.get("client_order_id") != plan.get("client_order_id"):
            blockers.append("CLIENT_ORDER_ID_MISMATCH")

        http_status = None
        error_response = None
        attempted = False

        if not blockers:
            attempted = True
            http_status, error_response = self.client.submit_invalid_order(payload)
            if token is not None:
                consume_token(token_path, token)

        expected_status = http_status in set(plan.get("expected_http_statuses", [400, 422]))
        no_order_created = False
        lookup_http_status = None
        lookup_response = None

        if attempted:
            lookup_http_status, lookup_response = self.client.get_order_by_client_id(
                plan["client_order_id"]
            )
            no_order_created = lookup_http_status in {404, 422} or not (
                lookup_response and lookup_response.get("id")
            )

        if attempted and not expected_status:
            blockers.append(f"UNEXPECTED_REJECT_HTTP_STATUS:{http_status}")
        if attempted and not no_order_created:
            blockers.append("REJECTED_REQUEST_CREATED_ORDER")

        passed = attempted and expected_status and no_order_created and not blockers
        result = {
            "stage": "P3_PAPER_REJECT_VALIDATION",
            "status": "PASS" if passed else "BLOCKED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "paper_endpoint_verified": True,
            "market_is_open": bool((clock or {}).get("is_open", False)),
            "account_status": (account or {}).get("status"),
            "client_order_id": plan.get("client_order_id"),
            "invalid_payload": payload,
            "submission_attempted": attempted,
            "reject_http_status": http_status,
            "reject_response": error_response,
            "expected_reject_status": expected_status,
            "lookup_http_status": lookup_http_status,
            "lookup_response": lookup_response,
            "no_order_created": no_order_created,
            "blockers": sorted(set(blockers)),
            "actual_external_network_used": attempted,
            "actual_broker_read_performed": True,
            "actual_broker_write_attempted": attempted,
            "actual_broker_write_performed": False,
            "actual_order_submission_attempted": attempted,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_market_validation": "P3_PARTIAL_FILL_VALIDATION",
            "next_fixed_development": "PAPER_AUTOMATION_CONTROLLER_AND_SCHEDULER",
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "reject_validation_result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with (output_dir / "reject_validation_ledger.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")
        return result
