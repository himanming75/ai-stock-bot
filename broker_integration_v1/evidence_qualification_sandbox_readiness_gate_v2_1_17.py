from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")
ALLOWED_SIDES = {"BUY", "SELL"}
CANONICAL_MIN_CONFIDENCE = Decimal("0.60")


def _as_decimal(value, field):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def qualify_evidence_row_v2_1_17(row):
    reasons = []
    signals = list(row.get("eligible_signals") or [])

    if row.get("observer_state") != "OBSERVED_FRESH":
        reasons.append("OBSERVER_NOT_FRESH")

    if row.get("canonical_gate_aligned") is not True:
        reasons.append("CANONICAL_GATE_NOT_ALIGNED")

    if row.get("signal_capture_allowed") is not True:
        reasons.append("SIGNAL_CAPTURE_NOT_ALLOWED")

    if row.get("all_fresh") is not True:
        reasons.append("BARS_NOT_ALL_FRESH")

    if row.get("freshness_status") != "PASS_REGULAR_WINDOW_FRESH_BARS":
        reasons.append("FRESHNESS_STATUS_NOT_PASS")

    expected_count = int(row.get("eligible_signal_count") or 0)
    if expected_count <= 0:
        reasons.append("NO_ELIGIBLE_SIGNALS")

    if expected_count != len(signals):
        reasons.append("ELIGIBLE_SIGNAL_COUNT_MISMATCH")

    if expected_count > 3:
        reasons.append("ELIGIBLE_SIGNAL_COUNT_EXCEEDS_3")

    if row.get("evidence_only") is not True:
        reasons.append("EVIDENCE_ONLY_FLAG_NOT_TRUE")

    if int(row.get("broker_orders_submitted") or 0) != 0:
        reasons.append("SOURCE_ALREADY_SUBMITTED_BROKER_ORDER")

    if row.get("production_order_submission") is not False:
        reasons.append("SOURCE_PROD_STATE_NOT_LOCKED")

    if row.get("live_trading") is not False:
        reasons.append("SOURCE_LIVE_STATE_NOT_LOCKED")

    if not row.get("evidence_key"):
        reasons.append("MISSING_EVIDENCE_KEY")

    normalized_signals = []
    seen_signal_keys = set()

    for idx, signal in enumerate(signals, 1):
        symbol = str(signal.get("symbol") or "").strip().upper()
        side = str(signal.get("side") or "").strip().upper()
        strategy_id = str(signal.get("strategy_id") or "").strip()

        if not SYMBOL_RE.fullmatch(symbol):
            reasons.append(f"SIGNAL_{idx}_INVALID_SYMBOL")

        if side not in ALLOWED_SIDES:
            reasons.append(f"SIGNAL_{idx}_INVALID_SIDE")

        try:
            quantity = _as_decimal(signal.get("quantity"), f"signal {idx} quantity")
            if quantity <= 0:
                reasons.append(f"SIGNAL_{idx}_NONPOSITIVE_QUANTITY")
        except ValueError:
            quantity = Decimal("0")
            reasons.append(f"SIGNAL_{idx}_INVALID_QUANTITY")

        try:
            confidence = _as_decimal(
                signal.get("source_confidence"),
                f"signal {idx} source_confidence",
            )
            if confidence < CANONICAL_MIN_CONFIDENCE:
                reasons.append(f"SIGNAL_{idx}_CONFIDENCE_BELOW_CANONICAL")
            if confidence > Decimal("1"):
                reasons.append(f"SIGNAL_{idx}_CONFIDENCE_ABOVE_1")
        except ValueError:
            confidence = None
            reasons.append(f"SIGNAL_{idx}_INVALID_CONFIDENCE")

        signal_key = (symbol, side, str(quantity), strategy_id)
        if signal_key in seen_signal_keys:
            reasons.append(f"SIGNAL_{idx}_DUPLICATE_SIGNAL")
        seen_signal_keys.add(signal_key)

        normalized_signals.append({
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "strategy_id": strategy_id,
            "source_confidence": (
                None if confidence is None else str(confidence)
            ),
        })

    ready = len(reasons) == 0

    return {
        "evidence_key": row.get("evidence_key"),
        "qualification_status": (
            "READY_FOR_MANUAL_SANDBOX_REVIEW"
            if ready
            else "NOT_READY"
        ),
        "ready": ready,
        "reasons": reasons,
        "eligible_signal_count": expected_count,
        "signals": normalized_signals,
        "canonical_min_confidence": str(CANONICAL_MIN_CONFIDENCE),
        "manual_review_required": True,
        "automatic_sandbox_execution_allowed": False,
        "etrade_oauth_started": False,
        "sandbox_preview_sent": False,
        "sandbox_place_sent": False,
        "broker_orders_submitted": 0,
        "production_order_submission": False,
        "live_trading": False,
    }


class EvidenceQualificationSandboxReadinessGateV2117:
    def __init__(self, root):
        self.root = Path(root)
        self.source_ledger = (
            self.root
            / "runtime"
            / "fresh_eligible_signal_evidence_v2_1_16"
            / "eligible_signal_evidence.jsonl"
        )
        self.runtime_dir = (
            self.root
            / "runtime"
            / "sandbox_readiness_gate_v2_1_17"
        )
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.qualification_ledger = (
            self.runtime_dir / "qualification_ledger.jsonl"
        )
        self.latest_qualification = (
            self.runtime_dir / "latest_qualification.json"
        )

    def _existing_keys(self):
        keys = set()
        if not self.qualification_ledger.exists():
            return keys
        for line in self.qualification_ledger.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = row.get("evidence_key")
            if key:
                keys.add(key)
        return keys

    def evaluate(self):
        if not self.source_ledger.exists():
            return {
                "status": "WAITING_FOR_V2_1_16_EVIDENCE",
                "source_ledger": str(self.source_ledger),
                "source_rows": 0,
                "ready_rows": 0,
                "not_ready_rows": 0,
                "new_qualification_rows": 0,
                "duplicate_qualification_rows": 0,
                "qualification_ledger": str(self.qualification_ledger),
                "manual_review_required": True,
                "automatic_sandbox_execution_allowed": False,
                "etrade_oauth_started": False,
                "broker_orders_submitted": 0,
                "production_order_submission": False,
                "live_trading": False,
            }

        existing = self._existing_keys()
        source_rows = 0
        ready_rows = 0
        not_ready_rows = 0
        new_rows = 0
        duplicate_rows = 0
        latest = None

        with self.source_ledger.open("r", encoding="utf-8") as src:
            for line in src:
                if not line.strip():
                    continue

                source_rows += 1
                evidence = json.loads(line)
                result = qualify_evidence_row_v2_1_17(evidence)

                if result["ready"]:
                    ready_rows += 1
                else:
                    not_ready_rows += 1

                key = result.get("evidence_key")
                if key and key in existing:
                    duplicate_rows += 1
                    continue

                record = {
                    "stage": (
                        "BROKER_INTEGRATION_V2_1_17_"
                        "EVIDENCE_QUALIFICATION_SANDBOX_READINESS_GATE"
                    ),
                    "source_stage": evidence.get("stage"),
                    "source_observed_at_utc": evidence.get("observed_at_utc"),
                    **result,
                }

                with self.qualification_ledger.open(
                    "a", encoding="utf-8"
                ) as dst:
                    dst.write(
                        json.dumps(
                            record,
                            sort_keys=True,
                            ensure_ascii=False,
                        ) + "\n"
                    )

                self.latest_qualification.write_text(
                    json.dumps(
                        record,
                        indent=2,
                        sort_keys=True,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                if key:
                    existing.add(key)
                new_rows += 1
                latest = record

        return {
            "status": "PASS_EVIDENCE_QUALIFICATION_SANDBOX_READINESS",
            "source_ledger": str(self.source_ledger),
            "source_rows": source_rows,
            "ready_rows": ready_rows,
            "not_ready_rows": not_ready_rows,
            "new_qualification_rows": new_rows,
            "duplicate_qualification_rows": duplicate_rows,
            "qualification_ledger": str(self.qualification_ledger),
            "latest_qualification": (
                None if latest is None else str(self.latest_qualification)
            ),
            "manual_review_required": True,
            "automatic_sandbox_execution_allowed": False,
            "etrade_oauth_started": False,
            "sandbox_preview_sent": False,
            "sandbox_place_sent": False,
            "broker_orders_submitted": 0,
            "production_order_submission": False,
            "live_trading": False,
            "profitability_validated": False,
        }
