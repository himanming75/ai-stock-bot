#!/usr/bin/env python3
"""
V54.0 Strategy Signal Engine Foundation

Deterministic, offline strategy-signal normalization and selection layer.

Capabilities:
- BUY / SELL / HOLD validation
- strategy registry
- confidence and priority validation
- signal expiration validation
- duplicate signal removal
- deterministic sorting
- per-symbol conflict resolution
- signal SHA-256
- audit ledger hash chain
- offline-only safety gate
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any, Iterable, Sequence

getcontext().prec = 40

VERSION = "54.0"
RATIO_Q = Decimal("0.000001")
VALID_ACTIONS = {"BUY", "SELL", "HOLD"}
VALID_MODES = {"replay", "paper", "live"}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def dec(value: Any, *, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def q_ratio(value: Decimal) -> str:
    return format(value.quantize(RATIO_Q, rounding=ROUND_HALF_UP), "f")


@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    strategy_name: str
    strategy_version: str
    enabled: bool
    weight: str
    allowed_actions: list[str]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RawSignal:
    strategy_id: str
    symbol: str
    action: str
    confidence: str
    priority: int
    created_at: str
    expires_at: str
    rationale: str
    source_sha256: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class NormalizedSignal:
    sequence: int
    strategy_id: str
    strategy_name: str
    strategy_version: str
    symbol: str
    action: str
    confidence: str
    weighted_confidence: str
    priority: int
    created_at: str
    expires_at: str
    rationale: str
    source_sha256: str
    metadata: dict[str, Any]
    duplicate_key: str
    signal_sha256: str


@dataclass(frozen=True)
class SelectedSignal:
    symbol: str
    selected_action: str
    selected_strategy_id: str
    selected_signal_sha256: str
    selected_priority: int
    selected_weighted_confidence: str
    conflict_detected: bool
    candidate_count: int
    selection_sha256: str


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    event_type: str
    strategy_count: int
    raw_signal_count: int
    normalized_signal_count: int
    selected_signal_count: int
    rejected_signal_count: int
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class SignalEngineResult:
    schema_version: str
    version: str
    status: str
    decision: str
    strategy_count: int
    raw_signal_count: int
    normalized_signal_count: int
    selected_signal_count: int
    rejected_signal_count: int
    duplicate_signal_count: int
    expired_signal_count: int
    disabled_strategy_signal_count: int
    conflict_symbol_count: int
    normalized_signals: list[dict[str, Any]]
    selected_signals: list[dict[str, Any]]
    rejected_signals: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    result_sha256: str


class StrategySignalEngine:
    def __init__(self, *, mode: str = "paper", enable_live: bool = False) -> None:
        if mode not in VALID_MODES:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.registry: dict[str, StrategyDefinition] = {}
        self.ledger: list[LedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError("live strategy-signal transport is intentionally not implemented in V54.0")

    def register_strategy(self, strategy: StrategyDefinition) -> None:
        sid = strategy.strategy_id.strip()
        if not sid:
            raise ValueError("strategy_id is required")
        if sid in self.registry:
            raise ValueError(f"duplicate strategy_id: {sid}")
        if not strategy.strategy_name.strip():
            raise ValueError("strategy_name is required")
        if not strategy.strategy_version.strip():
            raise ValueError("strategy_version is required")
        weight = dec(strategy.weight, field="weight")
        if weight < 0 or weight > 1:
            raise ValueError("weight must be between 0 and 1")
        actions = [a.upper().strip() for a in strategy.allowed_actions]
        if not actions:
            raise ValueError("allowed_actions cannot be empty")
        if any(a not in VALID_ACTIONS for a in actions):
            raise ValueError("allowed_actions contains an invalid action")
        normalized = StrategyDefinition(
            strategy_id=sid,
            strategy_name=strategy.strategy_name.strip(),
            strategy_version=strategy.strategy_version.strip(),
            enabled=bool(strategy.enabled),
            weight=q_ratio(weight),
            allowed_actions=sorted(set(actions)),
            metadata=dict(strategy.metadata),
        )
        self.registry[sid] = normalized

    def register_many(self, strategies: Iterable[StrategyDefinition]) -> None:
        for strategy in strategies:
            self.register_strategy(strategy)

    @staticmethod
    def _signal_duplicate_key(signal: RawSignal) -> str:
        payload = {
            "strategy_id": signal.strategy_id.strip(),
            "symbol": signal.symbol.upper().strip(),
            "action": signal.action.upper().strip(),
            "created_at": signal.created_at.strip(),
        }
        return canonical_hash(payload)

    @staticmethod
    def _validate_iso_order(created_at: str, expires_at: str) -> bool:
        # ISO-8601 UTC strings in this project are lexicographically sortable.
        return bool(created_at and expires_at and expires_at > created_at)

    def _normalize_one(self, signal: RawSignal, sequence: int, as_of: str) -> tuple[NormalizedSignal | None, dict[str, Any] | None]:
        reasons: list[str] = []
        strategy = self.registry.get(signal.strategy_id.strip())
        symbol = signal.symbol.upper().strip()
        action = signal.action.upper().strip()

        if strategy is None:
            reasons.append("strategy_not_registered")
        elif not strategy.enabled:
            reasons.append("strategy_disabled")

        if not symbol:
            reasons.append("symbol_required")
        if action not in VALID_ACTIONS:
            reasons.append("invalid_action")
        elif strategy is not None and action not in strategy.allowed_actions:
            reasons.append("action_not_allowed_for_strategy")

        try:
            confidence = dec(signal.confidence, field="confidence")
            if confidence < 0 or confidence > 1:
                reasons.append("confidence_out_of_range")
        except ValueError:
            confidence = Decimal("0")
            reasons.append("confidence_invalid")

        if not isinstance(signal.priority, int) or isinstance(signal.priority, bool):
            reasons.append("priority_must_be_integer")
        elif signal.priority < 0 or signal.priority > 100:
            reasons.append("priority_out_of_range")

        if not signal.created_at.strip():
            reasons.append("created_at_required")
        if not signal.expires_at.strip():
            reasons.append("expires_at_required")
        elif signal.created_at.strip() and not self._validate_iso_order(signal.created_at.strip(), signal.expires_at.strip()):
            reasons.append("expires_at_must_be_after_created_at")

        if signal.expires_at.strip() and signal.expires_at.strip() <= as_of:
            reasons.append("signal_expired")

        if not signal.source_sha256 or len(signal.source_sha256) != 64:
            reasons.append("source_sha256_invalid")

        if reasons:
            return None, {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "action": signal.action,
                "created_at": signal.created_at,
                "expires_at": signal.expires_at,
                "reasons": reasons,
                "rejection_sha256": canonical_hash({
                    "strategy_id": signal.strategy_id,
                    "symbol": signal.symbol,
                    "action": signal.action,
                    "created_at": signal.created_at,
                    "expires_at": signal.expires_at,
                    "reasons": reasons,
                }),
            }

        assert strategy is not None
        weighted = confidence * dec(strategy.weight, field="weight")
        duplicate_key = self._signal_duplicate_key(signal)
        core = {
            "sequence": sequence,
            "strategy_id": strategy.strategy_id,
            "strategy_name": strategy.strategy_name,
            "strategy_version": strategy.strategy_version,
            "symbol": symbol,
            "action": action,
            "confidence": q_ratio(confidence),
            "weighted_confidence": q_ratio(weighted),
            "priority": signal.priority,
            "created_at": signal.created_at.strip(),
            "expires_at": signal.expires_at.strip(),
            "rationale": signal.rationale.strip(),
            "source_sha256": signal.source_sha256,
            "metadata": dict(signal.metadata),
            "duplicate_key": duplicate_key,
        }
        return NormalizedSignal(**core, signal_sha256=canonical_hash(core)), None

    @staticmethod
    def _selection_sort_key(signal: NormalizedSignal) -> tuple[Any, ...]:
        action_rank = {"BUY": 2, "SELL": 2, "HOLD": 1}[signal.action]
        return (
            -signal.priority,
            -Decimal(signal.weighted_confidence),
            -Decimal(signal.confidence),
            -action_rank,
            signal.strategy_id,
            signal.signal_sha256,
        )

    def _select_by_symbol(self, signals: list[NormalizedSignal]) -> list[SelectedSignal]:
        grouped: dict[str, list[NormalizedSignal]] = {}
        for signal in signals:
            grouped.setdefault(signal.symbol, []).append(signal)

        selected: list[SelectedSignal] = []
        for symbol in sorted(grouped):
            candidates = sorted(grouped[symbol], key=self._selection_sort_key)
            winner = candidates[0]
            actions = {candidate.action for candidate in candidates}
            core = {
                "symbol": symbol,
                "selected_action": winner.action,
                "selected_strategy_id": winner.strategy_id,
                "selected_signal_sha256": winner.signal_sha256,
                "selected_priority": winner.priority,
                "selected_weighted_confidence": winner.weighted_confidence,
                "conflict_detected": len(actions) > 1,
                "candidate_count": len(candidates),
            }
            selected.append(SelectedSignal(**core, selection_sha256=canonical_hash(core)))
        return selected

    def _append_ledger(self, raw_count: int, norm_count: int, selected_count: int, rejected_count: int) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": "STRATEGY_SIGNALS_PROCESSED",
            "strategy_count": len(self.registry),
            "raw_signal_count": raw_count,
            "normalized_signal_count": norm_count,
            "selected_signal_count": selected_count,
            "rejected_signal_count": rejected_count,
        }
        payload_sha = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_sha,
        }
        self.ledger.append(LedgerEntry(**core, entry_sha256=canonical_hash(core)))

    def process(self, signals: Sequence[RawSignal], *, as_of: str) -> SignalEngineResult:
        self._live_gate()
        global_reasons: list[str] = []
        if not self.registry:
            global_reasons.append("at least one strategy must be registered")
        if not as_of.strip():
            global_reasons.append("as_of is required")

        normalized: list[NormalizedSignal] = []
        rejected: list[dict[str, Any]] = []
        duplicate_count = 0
        expired_count = 0
        disabled_count = 0
        seen: set[str] = set()

        for raw in signals:
            duplicate_key = self._signal_duplicate_key(raw)
            if duplicate_key in seen:
                duplicate_count += 1
                rejected.append({
                    "strategy_id": raw.strategy_id,
                    "symbol": raw.symbol,
                    "action": raw.action,
                    "created_at": raw.created_at,
                    "expires_at": raw.expires_at,
                    "reasons": ["duplicate_signal"],
                    "rejection_sha256": canonical_hash({
                        "strategy_id": raw.strategy_id,
                        "symbol": raw.symbol,
                        "action": raw.action,
                        "created_at": raw.created_at,
                        "expires_at": raw.expires_at,
                        "reasons": ["duplicate_signal"],
                    }),
                })
                continue
            seen.add(duplicate_key)
            item, rejection = self._normalize_one(raw, len(normalized) + 1, as_of)
            if rejection is not None:
                if "signal_expired" in rejection["reasons"]:
                    expired_count += 1
                if "strategy_disabled" in rejection["reasons"]:
                    disabled_count += 1
                rejected.append(rejection)
            elif item is not None:
                normalized.append(item)

        normalized = sorted(normalized, key=lambda s: (s.symbol, *self._selection_sort_key(s)))
        normalized = [
            NormalizedSignal(**{**asdict(signal), "sequence": i})
            for i, signal in enumerate(normalized, start=1)
        ]
        # Recalculate signal hash after final deterministic sequence assignment.
        normalized = [
            NormalizedSignal(
                **{k: v for k, v in asdict(signal).items() if k != "signal_sha256"},
                signal_sha256=canonical_hash({k: v for k, v in asdict(signal).items() if k != "signal_sha256"}),
            )
            for signal in normalized
        ]

        selected = self._select_by_symbol(normalized)
        if not global_reasons:
            self._append_ledger(len(signals), len(normalized), len(selected), len(rejected))

        conflict_count = sum(1 for item in selected if item.conflict_detected)
        core = {
            "schema_version": "v54.0.strategy_signal_engine.1",
            "version": VERSION,
            "status": "PASS" if not global_reasons else "FAIL",
            "decision": "signals_selected" if not global_reasons else "reject",
            "strategy_count": len(self.registry),
            "raw_signal_count": len(signals),
            "normalized_signal_count": len(normalized),
            "selected_signal_count": len(selected),
            "rejected_signal_count": len(rejected),
            "duplicate_signal_count": duplicate_count,
            "expired_signal_count": expired_count,
            "disabled_strategy_signal_count": disabled_count,
            "conflict_symbol_count": conflict_count,
            "normalized_signals": [asdict(x) for x in normalized],
            "selected_signals": [asdict(x) for x in selected],
            "rejected_signals": rejected,
            "ledger": [asdict(x) for x in self.ledger],
            "rejection_reasons": global_reasons,
            "network_used": False,
        }
        return SignalEngineResult(**core, result_sha256=canonical_hash(core))

    @staticmethod
    def export(path: Path, result: SignalEngineResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v54.0.strategy_signal_engine_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_payload(path: Path) -> tuple[list[StrategyDefinition], list[RawSignal], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    strategies = [StrategyDefinition(**item) for item in payload.get("strategies", [])]
    signals = [RawSignal(**item) for item in payload.get("signals", [])]
    as_of = str(payload.get("as_of", ""))
    return strategies, signals, as_of


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V54.0 Strategy Signal Engine Foundation")
    parser.add_argument("--input", required=True)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--output", default="release/v54/audit/strategy_signal_engine_result_v54_0.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        strategies, signals, as_of = load_payload(Path(args.input))
        engine = StrategySignalEngine(mode=args.mode, enable_live=args.enable_live)
        engine.register_many(strategies)
        result = engine.process(signals, as_of=as_of)
        engine.export(output, result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (TypeError, ValueError, PermissionError, NotImplementedError, json.JSONDecodeError, OSError) as exc:
        error = {
            "schema_version": "v54.0.strategy_signal_engine_error.1",
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
