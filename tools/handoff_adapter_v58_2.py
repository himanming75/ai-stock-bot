#!/usr/bin/env python3
"""V58.2 Handoff Adapter Foundation.

Transforms actual stage results into the next stage's input:
V54 result -> V55 input
V55 result -> V56 input
V56 result -> V57 input

The adapter preserves account/state/config/event template sections while
replacing transaction fields with values and integrity hashes produced by
the preceding stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

VERSION = "58.2"
VALID_HANDOFFS = {"v54_to_v55", "v55_to_v56", "v56_to_v57"}

def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value

def unwrap_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result", payload)
    if not isinstance(result, dict):
        raise ValueError("result must be a JSON object")
    return result

def require_pass(result: dict[str, Any], stage: str) -> None:
    if str(result.get("status", "")).upper() != "PASS":
        raise ValueError(f"{stage} result status must be PASS")
    if bool(result.get("network_used", False)):
        raise ValueError(f"{stage} result indicates network use")

def require_text(value: Any, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text

def require_hash(value: Any, field: str) -> str:
    text = require_text(value, field)
    if len(text) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
        raise ValueError(f"{field} must be a 64-character SHA-256")
    return text.lower()

def normalize_number(value: Any, field: str) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{field} must be finite")
    return format(number, "f")

class HandoffAdapterV582:
    def v54_to_v55(self, source_payload: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
        source = unwrap_result(source_payload)
        require_pass(source, "V54")
        selected = source.get("selected_signals")
        if not isinstance(selected, list) or not selected:
            raise ValueError("V54 selected_signals cannot be empty")

        orderable = [x for x in selected if str(x.get("selected_action", "")).upper() in {"BUY", "SELL"}]
        if not orderable:
            raise ValueError("V54 has no orderable BUY or SELL signal")
        signal = sorted(
            orderable,
            key=lambda x: (
                -int(x.get("selected_priority", 0)),
                -Decimal(str(x.get("selected_weighted_confidence", "0"))),
                str(x.get("symbol", "")),
            ),
        )[0]

        output = deepcopy(template)
        request = output.setdefault("request", {})
        request["request_id"] = f"v58-v55-{require_text(signal.get('symbol'), 'symbol').lower()}"
        request["symbol"] = require_text(signal.get("symbol"), "symbol").upper()
        request["action"] = require_text(signal.get("selected_action"), "selected_action").upper()
        request["signal_sha256"] = require_hash(signal.get("selected_signal_sha256"), "selected_signal_sha256")
        request.setdefault("metadata", {})
        request["metadata"].update({
            "handoff": "v54_to_v55",
            "source_version": source.get("version"),
            "selection_sha256": signal.get("selection_sha256"),
        })
        output["handoff"] = self._audit("v54_to_v55", source, output)
        return output

    def v55_to_v56(self, source_payload: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
        source = unwrap_result(source_payload)
        require_pass(source, "V55")
        if source.get("decision") != "size_approved":
            raise ValueError("V55 decision must be size_approved")

        output = deepcopy(template)
        request = output.setdefault("request", {})
        symbol = require_text(source.get("symbol"), "symbol").upper()
        action = require_text(source.get("action"), "action").upper()
        quantity = normalize_number(source.get("shares"), "shares")
        entry_price = normalize_number(source.get("entry_price"), "entry_price")

        request.update({
            "request_id": f"v58-v56-{symbol.lower()}",
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "entry_price": entry_price,
            "estimated_risk_amount": normalize_number(source.get("estimated_risk_amount"), "estimated_risk_amount"),
            "position_sizing_sha256": require_hash(source.get("sizing_sha256"), "sizing_sha256"),
            "order_key": f"{symbol}-{action}-{quantity.rstrip('0').rstrip('.')}-{entry_price.rstrip('0').rstrip('.')}",
        })
        request.setdefault("metadata", {})
        request["metadata"].update({"handoff": "v55_to_v56", "source_request_id": source.get("request_id")})
        output["handoff"] = self._audit("v55_to_v56", source, output)
        return output

    def v56_to_v57(self, source_payload: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
        source = unwrap_result(source_payload)
        require_pass(source, "V56")
        if source.get("decision") != "risk_approved":
            raise ValueError("V56 decision must be risk_approved")

        output = deepcopy(template)
        request = output.setdefault("request", {})
        symbol = require_text(source.get("symbol"), "symbol").upper()
        action = require_text(source.get("action"), "action").upper()
        quantity = normalize_number(source.get("quantity"), "quantity")
        limit_price = normalize_number(source.get("entry_price"), "entry_price")

        request.update({
            "request_id": f"v58-v57-{symbol.lower()}",
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "limit_price": limit_price,
            "risk_approval_sha256": require_hash(source.get("risk_sha256"), "risk_sha256"),
            "execution_key": f"{symbol}-{action}-{quantity.rstrip('0').rstrip('.')}-{limit_price.rstrip('0').rstrip('.')}",
        })
        request.setdefault("metadata", {})
        request["metadata"].update({
            "handoff": "v56_to_v57",
            "source_request_id": source.get("request_id"),
            "risk_reward_ratio": source.get("risk_reward_ratio"),
        })
        output["handoff"] = self._audit("v56_to_v57", source, output)
        return output

    @staticmethod
    def _audit(handoff_type: str, source: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
        core = {
            "schema_version": "v58.2.handoff.1",
            "version": VERSION,
            "handoff_type": handoff_type,
            "source_sha256": canonical_hash(source),
            "generated_input_sha256": canonical_hash({k: v for k, v in output.items() if k != "handoff"}),
            "network_used": False,
        }
        return {**core, "handoff_sha256": canonical_hash(core)}

    def transform(self, handoff_type: str, source: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
        if handoff_type not in VALID_HANDOFFS:
            raise ValueError("unsupported handoff type")
        return getattr(self, handoff_type)(source, template)

    @staticmethod
    def export(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V58.2 Handoff Adapter Foundation")
    parser.add_argument("--handoff", required=True, choices=sorted(VALID_HANDOFFS))
    parser.add_argument("--source", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        adapter = HandoffAdapterV582()
        result = adapter.transform(args.handoff, load_json(Path(args.source)), load_json(Path(args.template)))
        adapter.export(output, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        error = {
            "schema_version": "v58.2.handoff_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(error, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
