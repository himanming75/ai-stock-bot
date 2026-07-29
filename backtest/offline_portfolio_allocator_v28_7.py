from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json

VERSION = "28.7"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class AllocationError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise AllocationError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise AllocationError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AllocationCandidate:
    symbol: str
    sector: str
    confidence: Decimal
    risk_score: Decimal
    volatility: Decimal
    kelly_fraction: Decimal
    approved_fraction: Decimal
    decision_hash: str
    risk_hash: str


@dataclass(frozen=True)
class AllocationPolicy:
    method: str = "CONFIDENCE_WEIGHTED"
    cash_reserve_fraction: Decimal = Decimal("0.20")
    max_position_fraction: Decimal = Decimal("0.15")
    min_position_fraction: Decimal = Decimal("0.01")
    max_sector_fraction: Decimal = Decimal("0.40")
    max_total_invested_fraction: Decimal = Decimal("0.80")

    def __post_init__(self) -> None:
        if self.method.upper() not in {
            "EQUAL", "CONFIDENCE_WEIGHTED", "RISK_PARITY", "KELLY_WEIGHTED"
        }:
            raise AllocationError("unsupported allocation method")
        for name in (
            "cash_reserve_fraction",
            "max_position_fraction",
            "min_position_fraction",
            "max_sector_fraction",
            "max_total_invested_fraction",
        ):
            value = _d(getattr(self, name))
            if value < ZERO or value > ONE:
                raise AllocationError(f"{name} must be between 0 and 1")
        if self.min_position_fraction > self.max_position_fraction:
            raise AllocationError("min_position_fraction cannot exceed max_position_fraction")
        if self.max_total_invested_fraction > ONE - self.cash_reserve_fraction:
            raise AllocationError("invested fraction exceeds cash reserve rule")


@dataclass(frozen=True)
class AllocationLine:
    symbol: str
    sector: str
    raw_weight: Decimal
    normalized_weight: Decimal
    capped_weight: Decimal


@dataclass(frozen=True)
class AllocationResult:
    version: str
    allocation_id: str
    method: str
    lines: tuple[AllocationLine, ...]
    invested_fraction: Decimal
    cash_fraction: Decimal
    input_hash: str
    result_hash: str


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise AllocationError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _line_payload(line: AllocationLine) -> dict[str, Any]:
    return {
        "symbol": line.symbol,
        "sector": line.sector,
        "raw_weight": str(line.raw_weight),
        "normalized_weight": str(line.normalized_weight),
        "capped_weight": str(line.capped_weight),
    }


def _result_payload(result: AllocationResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "allocation_id": result.allocation_id,
        "method": result.method,
        "lines": [_line_payload(line) for line in result.lines],
        "invested_fraction": str(result.invested_fraction),
        "cash_fraction": str(result.cash_fraction),
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _raw_weight(candidate: AllocationCandidate, method: str) -> Decimal:
    if method == "EQUAL":
        return ONE
    if method == "CONFIDENCE_WEIGHTED":
        return max(ZERO, _d(candidate.confidence))
    if method == "RISK_PARITY":
        volatility = _d(candidate.volatility)
        if volatility <= ZERO:
            raise AllocationError("volatility must be positive for risk parity")
        return ONE / volatility
    if method == "KELLY_WEIGHTED":
        return max(ZERO, min(_d(candidate.kelly_fraction), _d(candidate.approved_fraction)))
    raise AllocationError("unsupported allocation method")


def allocate_portfolio(
    candidates: Iterable[AllocationCandidate],
    policy: AllocationPolicy | None = None,
) -> AllocationResult:
    selected = policy or AllocationPolicy()
    items = tuple(candidates)
    if not items:
        raise AllocationError("at least one candidate is required")

    normalized = []
    seen = set()
    for item in items:
        symbol = item.symbol.strip().upper()
        sector = item.sector.strip().upper()
        if not symbol or not sector:
            raise AllocationError("symbol and sector are required")
        if symbol in seen:
            raise AllocationError("duplicate symbol detected")
        seen.add(symbol)
        _validate_sha256(item.decision_hash, "decision_hash")
        _validate_sha256(item.risk_hash, "risk_hash")
        for name, value in (
            ("confidence", item.confidence),
            ("risk_score", item.risk_score),
            ("volatility", item.volatility),
            ("kelly_fraction", item.kelly_fraction),
            ("approved_fraction", item.approved_fraction),
        ):
            val = _d(value)
            if val < ZERO or val > ONE:
                raise AllocationError(f"{name} must be between 0 and 1")
        normalized.append(replace(item, symbol=symbol, sector=sector))

    method = selected.method.upper()
    raw = [_raw_weight(item, method) for item in normalized]
    total_raw = sum(raw, ZERO)
    if total_raw <= ZERO:
        raise AllocationError("allocation weights sum to zero")

    target_invested = min(
        _d(selected.max_total_invested_fraction),
        ONE - _d(selected.cash_reserve_fraction),
    )

    preliminary = [
        min(
            _d(selected.max_position_fraction),
            target_invested * weight / total_raw,
            _d(item.approved_fraction),
        )
        for item, weight in zip(normalized, raw)
    ]

    sector_totals: dict[str, Decimal] = {}
    final = list(preliminary)
    for sector in sorted({item.sector for item in normalized}):
        indices = [i for i, item in enumerate(normalized) if item.sector == sector]
        sector_sum = sum((final[i] for i in indices), ZERO)
        cap = _d(selected.max_sector_fraction)
        if sector_sum > cap:
            factor = cap / sector_sum
            for i in indices:
                final[i] = final[i] * factor
        sector_totals[sector] = sum((final[i] for i in indices), ZERO)

    invested = sum(final, ZERO)
    if invested > target_invested:
        factor = target_invested / invested
        final = [value * factor for value in final]
        invested = sum(final, ZERO)

    lines = []
    for item, raw_weight, allocated in zip(normalized, raw, final):
        capped = _q(allocated if allocated >= _d(selected.min_position_fraction) else ZERO)
        lines.append(AllocationLine(
            symbol=item.symbol,
            sector=item.sector,
            raw_weight=_q(raw_weight),
            normalized_weight=_q(raw_weight / total_raw),
            capped_weight=capped,
        ))

    invested = _q(sum((line.capped_weight for line in lines), ZERO))
    cash = _q(ONE - invested)

    input_hash = _hash({
        "candidates": [
            {
                "symbol": item.symbol,
                "sector": item.sector,
                "confidence": str(item.confidence),
                "risk_score": str(item.risk_score),
                "volatility": str(item.volatility),
                "kelly_fraction": str(item.kelly_fraction),
                "approved_fraction": str(item.approved_fraction),
                "decision_hash": item.decision_hash,
                "risk_hash": item.risk_hash,
            }
            for item in normalized
        ],
        "policy": {key: str(value) for key, value in selected.__dict__.items()},
    })
    result = AllocationResult(
        version=VERSION,
        allocation_id=f"ALLOC-{input_hash[:16].upper()}",
        method=method,
        lines=tuple(sorted(lines, key=lambda line: line.symbol)),
        invested_fraction=invested,
        cash_fraction=cash,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: AllocationResult) -> bool:
    if result.version != VERSION:
        raise AllocationError("unsupported allocation version")
    if not result.allocation_id.startswith("ALLOC-"):
        raise AllocationError("invalid allocation ID")
    if len({line.symbol for line in result.lines}) != len(result.lines):
        raise AllocationError("duplicate allocation symbol")
    if any(line.capped_weight < ZERO or line.capped_weight > ONE for line in result.lines):
        raise AllocationError("allocation weight out of range")
    if sum((line.capped_weight for line in result.lines), ZERO) != result.invested_fraction:
        raise AllocationError("invested fraction mismatch")
    if result.invested_fraction + result.cash_fraction != Decimal("1.000000"):
        raise AllocationError("portfolio fractions must sum to one")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise AllocationError("allocation result hash mismatch")
    return True


def save_result(result: AllocationResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> AllocationResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    result = AllocationResult(
        version=payload["version"],
        allocation_id=payload["allocation_id"],
        method=payload["method"],
        lines=tuple(
            AllocationLine(
                symbol=item["symbol"],
                sector=item["sector"],
                raw_weight=_d(item["raw_weight"]),
                normalized_weight=_d(item["normalized_weight"]),
                capped_weight=_d(item["capped_weight"]),
            )
            for item in payload["lines"]
        ),
        invested_fraction=_d(payload["invested_fraction"]),
        cash_fraction=_d(payload["cash_fraction"]),
        input_hash=payload["input_hash"],
        result_hash=payload["result_hash"],
    )
    verify_result(result)
    return result


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
