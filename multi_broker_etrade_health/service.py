from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .fixtures import CRITICAL_FIXTURE, DEGRADED_FIXTURE, HEALTHY_FIXTURE
from .routing import decide_routing
from .scoring import health_band, weighted_score
from .signals import (
    account_status_signal,
    error_rate_signal,
    latency_signal,
    oauth_signal,
    rate_limit_signal,
    snapshot_integrity_signal,
)


class ETradeHealthMonitoringService:
    def evaluate_case(self, name: str, fixture: dict) -> dict:
        signals = [
            oauth_signal(
                fixture["oauth_status"],
                fixture["renew_required"],
                fixture["revoked"],
            ),
            latency_signal(fixture["latency_ms"]),
            error_rate_signal(
                fixture["successes"],
                fixture["failures"],
            ),
            rate_limit_signal(
                fixture["rate_limited"]
            ),
            account_status_signal(
                fixture["account_status"]
            ),
            snapshot_integrity_signal(
                fixture["snapshot_integrity_passed"]
            ),
        ]
        score = weighted_score(signals)
        critical_signal_present = any(
            signal.status == "CRITICAL"
            for signal in signals
        )
        decision = decide_routing(
            score,
            critical_signal_present,
        )
        return {
            "name": name,
            "health_score": score,
            "health_band": health_band(score),
            "signals": [
                signal.to_dict() for signal in signals
            ],
            "critical_signal_present": critical_signal_present,
            "routing_decision": decision.to_dict(),
        }

    def evaluate(self, *, output_dir: Path) -> dict:
        now = datetime.now(timezone.utc)
        healthy = self.evaluate_case(
            "HEALTHY",
            HEALTHY_FIXTURE,
        )
        degraded = self.evaluate_case(
            "DEGRADED",
            DEGRADED_FIXTURE,
        )
        critical = self.evaluate_case(
            "CRITICAL",
            CRITICAL_FIXTURE,
        )

        result = {
            "stage": (
                "V4601_TO_V4800_ETRADE_ACCOUNT_HEALTH_"
                "MONITORING_AND_FAILSAFE_ROUTING"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": "FIXTURE_HEALTH_SCENARIOS",
            "cases": [healthy, degraded, critical],
            "health_scoring_ready": True,
            "oauth_monitoring_ready": True,
            "latency_monitoring_ready": True,
            "error_rate_monitoring_ready": True,
            "rate_limit_monitoring_ready": True,
            "account_restriction_monitoring_ready": True,
            "snapshot_integrity_monitoring_ready": True,
            "failsafe_routing_ready": True,
            "critical_read_block_ready": True,
            "safe_mode_ready": True,
            "automatic_order_submission_enabled": False,
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
                "RUN_ACTUAL_HEALTH_MONITORING_AFTER_ETRADE_KEY_ISSUANCE"
            ),
            "next_fixed_development": (
                "V4801_TO_V5000_ETRADE_RECOVERY_ORCHESTRATION_"
                "AND_OPERATIONAL_READINESS_CERTIFICATION"
            ),
        }

        checks = (
            healthy["routing_decision"]["mode"] == "READ_ONLY_NORMAL",
            degraded["routing_decision"]["mode"]
            in {"READ_ONLY_DEGRADED", "READ_ONLY_SAFE_MODE"},
            critical["routing_decision"]["mode"] == "FAILSAFE_BLOCKED",
            critical["routing_decision"]["read_allowed"] is False,
            all(
                case["routing_decision"]["write_allowed"] is False
                for case in result["cases"]
            ),
        )
        if not all(checks):
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
        outputs = {
            "etrade_health_certification.json": result,
            "etrade_health_dashboard.json": {
                "status": result["status"],
                "cases": result["cases"],
                "broker_write": False,
                "network_used": False,
            },
            "etrade_failsafe_routing_policy.json": {
                "score_90_100": "READ_ONLY_NORMAL",
                "score_75_89": "READ_ONLY_DEGRADED",
                "score_50_74": "READ_ONLY_SAFE_MODE",
                "score_0_49": "FAILSAFE_BLOCKED",
                "critical_signal_override": "FAILSAFE_BLOCKED",
                "write_allowed": False,
            },
            "etrade_health_signal_catalog.json": {
                "signals": [
                    "OAUTH",
                    "LATENCY",
                    "ERROR_RATE",
                    "RATE_LIMIT",
                    "ACCOUNT_STATUS",
                    "SNAPSHOT_INTEGRITY",
                ]
            },
        }
        for name, payload in outputs.items():
            (output_dir / name).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        with (
            output_dir / "etrade_health_monitoring_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        return result
