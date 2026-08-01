from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Iterable, Mapping, Sequence

from .integrity import RuntimeIntegrityValidator
from .models import (
    CertificationCheck,
    CertificationStatus,
    RuntimeCertificate,
)
from .stress import RuntimeStressResult


class ContinuousRuntimeFinalCertifier:
    def __init__(self, *, validator: RuntimeIntegrityValidator) -> None:
        self.validator = validator

    def certify(
        self,
        *,
        available_components: Iterable[str],
        events: Sequence[str],
        runtime_state: Mapping[str, object],
        recovery_snapshot: Mapping[str, object],
        portfolio_state: Mapping[str, object],
        safety_counters: Mapping[str, int],
        stress: RuntimeStressResult,
    ) -> RuntimeCertificate:
        checks = (
            self.validator.validate_components(available_components),
            self.validator.validate_event_order(events),
            self.validator.validate_state_consistency(runtime_state),
            self.validator.validate_recovery(recovery_snapshot),
            self.validator.validate_portfolio(portfolio_state),
            self.validator.validate_safety(safety_counters),
            CertificationCheck(
                name="stress_cycles",
                passed=stress.cycles_completed == stress.cycles_requested
                and stress.failures == 0,
                detail=f"{stress.cycles_completed}/{stress.cycles_requested} cycles completed",
            ),
            CertificationCheck(
                name="restart_recovery",
                passed=stress.restart_count == stress.recovery_count
                and stress.restart_count >= 1,
                detail=f"restarts={stress.restart_count}, recoveries={stress.recovery_count}",
            ),
            CertificationCheck(
                name="final_runtime_state",
                passed=stress.final_state == "STOPPED",
                detail=f"final_state={stress.final_state}",
            ),
        )
        passed = all(item.passed for item in checks)
        generated_at = datetime.now(timezone.utc)
        payload = {
            "schema_version": 1,
            "generated_at": generated_at.isoformat(),
            "stage_range": "V118.01-V119.00",
            "release_candidate": "CONTINUOUS_PAPER_RUNTIME_RC1",
            "status": "PASS" if passed else "FAIL",
            "checks": [
                {"name": item.name, "passed": item.passed, "detail": item.detail}
                for item in checks
            ],
            "stress_cycles": stress.cycles_completed,
            "restart_count": stress.restart_count,
            "recovery_count": stress.recovery_count,
            "event_count": stress.event_count,
            "network_requests_executed": safety_counters["network_requests_executed"],
            "write_requests_executed": safety_counters["write_requests_executed"],
            "actual_paper_orders_submitted": safety_counters["actual_paper_orders_submitted"],
            "live_orders_submitted": safety_counters["live_orders_submitted"],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        certificate_id = f"continuous-paper-final-{digest[:24]}"

        return RuntimeCertificate(
            schema_version=1,
            certificate_id=certificate_id,
            generated_at=generated_at,
            stage_range="V118.01-V119.00",
            release_candidate="CONTINUOUS_PAPER_RUNTIME_RC1",
            certification_status=(
                CertificationStatus.PASS if passed else CertificationStatus.FAIL
            ),
            checks=checks,
            stress_cycles=stress.cycles_completed,
            restart_count=stress.restart_count,
            recovery_count=stress.recovery_count,
            event_count=stress.event_count,
            state_consistent=checks[2].passed,
            event_order_consistent=checks[1].passed,
            recovery_consistent=checks[3].passed,
            portfolio_consistent=checks[4].passed,
            network_requests_executed=safety_counters["network_requests_executed"],
            write_requests_executed=safety_counters["write_requests_executed"],
            actual_paper_orders_submitted=safety_counters["actual_paper_orders_submitted"],
            live_orders_submitted=safety_counters["live_orders_submitted"],
            certificate_sha256=digest,
        )
