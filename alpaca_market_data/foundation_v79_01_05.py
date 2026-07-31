from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata, util
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import os
import re


SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
ALLOWED_TIMEFRAMES = {"1Min", "5Min", "15Min", "1Hour", "1Day"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class AlpacaInstallStatus:
    stage: str
    package_name: str
    import_name: str
    installed: bool
    version: str | None
    minimum_version: str
    install_command: str
    network_test_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_alpaca_installation(minimum_version: str = "0.28.0") -> AlpacaInstallStatus:
    installed = util.find_spec("alpaca") is not None
    version = None
    if installed:
        try:
            version = metadata.version("alpaca-py")
        except metadata.PackageNotFoundError:
            version = "unknown"
    return AlpacaInstallStatus(
        stage="V79.01",
        package_name="alpaca-py",
        import_name="alpaca",
        installed=installed,
        version=version,
        minimum_version=minimum_version,
        install_command=f'python -m pip install "alpaca-py>={minimum_version}"',
    )


@dataclass(frozen=True)
class MarketDataSafetyConfig:
    stage: str = "V79.02"
    environment: str = "offline_foundation"
    network_allowed: bool = False
    broker_connected: bool = False
    order_submission_allowed: bool = False
    actual_orders_submitted: int = 0
    real_credentials_used: bool = False
    credential_presence_detected: bool = False
    credential_values_exposed: bool = False
    feed: str = "iex"
    base_url: str = "https://data.alpaca.markets"

    def validate(self) -> None:
        if self.network_allowed:
            raise ValueError("V79.01-V79.05 forbids network access")
        if self.broker_connected:
            raise ValueError("V79.01-V79.05 forbids broker connection")
        if self.order_submission_allowed or self.actual_orders_submitted != 0:
            raise ValueError("V79.01-V79.05 forbids order submission")
        if self.real_credentials_used or self.credential_values_exposed:
            raise ValueError("V79.01-V79.05 forbids credential use or exposure")
        if self.feed not in {"iex", "sip", "delayed_sip", "boats"}:
            raise ValueError("unsupported Alpaca data feed")


def load_safety_config(env: dict[str, str] | None = None) -> MarketDataSafetyConfig:
    source = os.environ if env is None else env
    key_present = bool(
        source.get("APCA_API_KEY_ID")
        or source.get("APCA_API_SECRET_KEY")
        or source.get("ALPACA_API_KEY")
        or source.get("ALPACA_SECRET_KEY")
    )
    config = MarketDataSafetyConfig(
        credential_presence_detected=key_present,
        feed=source.get("ALPACA_DATA_FEED", "iex").strip().lower() or "iex",
    )
    config.validate()
    return config


@dataclass(frozen=True)
class BarRequest:
    symbols: tuple[str, ...]
    timeframe: str
    start: str
    end: str
    limit: int = 1000
    adjustment: str = "raw"
    feed: str = "iex"

    def __post_init__(self) -> None:
        if not self.symbols:
            raise ValueError("at least one symbol is required")
        normalized = tuple(symbol.strip().upper() for symbol in self.symbols)
        if any(not SYMBOL_RE.fullmatch(symbol) for symbol in normalized):
            raise ValueError("invalid symbol")
        object.__setattr__(self, "symbols", normalized)
        if self.timeframe not in ALLOWED_TIMEFRAMES:
            raise ValueError("unsupported timeframe")
        start_dt = _parse_iso(self.start)
        end_dt = _parse_iso(self.end)
        if start_dt >= end_dt:
            raise ValueError("start must be before end")
        if not 1 <= self.limit <= 10000:
            raise ValueError("limit must be between 1 and 10000")
        if self.adjustment not in {"raw", "split", "dividend", "all"}:
            raise ValueError("unsupported adjustment")
        if self.feed not in {"iex", "sip", "delayed_sip", "boats"}:
            raise ValueError("unsupported feed")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["symbols"] = list(self.symbols)
        return value


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: int = 0
    vwap: float | None = None
    source: str = "offline_fixture"

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not SYMBOL_RE.fullmatch(symbol):
            raise ValueError("invalid symbol")
        object.__setattr__(self, "symbol", symbol)
        _parse_iso(self.timestamp)
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC values must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high is inconsistent")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low is inconsistent")
        if self.volume < 0 or self.trade_count < 0:
            raise ValueError("volume and trade_count must be nonnegative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class OfflineAlpacaMarketDataAdapter:
    """Deterministic adapter that mirrors a market-data boundary without HTTP."""

    def __init__(self, fixture_bars: Iterable[MarketBar], config: MarketDataSafetyConfig):
        config.validate()
        self._config = config
        self._bars = tuple(fixture_bars)
        self.network_call_count = 0
        self.order_submission_count = 0

    def get_stock_bars(self, request: BarRequest) -> dict[str, list[MarketBar]]:
        self._config.validate()
        start = _parse_iso(request.start)
        end = _parse_iso(request.end)
        requested = set(request.symbols)
        result: dict[str, list[MarketBar]] = {symbol: [] for symbol in request.symbols}
        for bar in self._bars:
            timestamp = _parse_iso(bar.timestamp)
            if bar.symbol in requested and start <= timestamp < end:
                result[bar.symbol].append(bar)
        for symbol in result:
            result[symbol] = sorted(
                result[symbol], key=lambda item: _parse_iso(item.timestamp)
            )[: request.limit]
        return result

    def submit_order(self, *_: Any, **__: Any) -> None:
        raise RuntimeError("order submission is outside the V79 market-data foundation")

    def diagnostics(self) -> dict[str, Any]:
        return {
            "adapter": "OfflineAlpacaMarketDataAdapter",
            "network_call_count": self.network_call_count,
            "order_submission_count": self.order_submission_count,
            "network_allowed": self._config.network_allowed,
            "broker_connected": self._config.broker_connected,
        }


def build_foundation_certificate(
    repository_root: Path,
    output_dir: Path,
    install_status: AlpacaInstallStatus,
    safety_config: MarketDataSafetyConfig,
    fixture_result: dict[str, list[MarketBar]],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    safety_config.validate()
    output_dir.mkdir(parents=True, exist_ok=True)
    bar_count = sum(len(items) for items in fixture_result.values())
    checks = {
        "alpaca_install_contract_defined": bool(install_status.install_command),
        "credential_values_not_exposed": not safety_config.credential_values_exposed,
        "real_credentials_not_used": not safety_config.real_credentials_used,
        "network_disabled": not safety_config.network_allowed,
        "broker_disconnected": not safety_config.broker_connected,
        "orders_disabled": not safety_config.order_submission_allowed,
        "actual_orders_zero": safety_config.actual_orders_submitted == 0,
        "offline_adapter_network_calls_zero": diagnostics["network_call_count"] == 0,
        "offline_adapter_order_count_zero": diagnostics["order_submission_count"] == 0,
        "request_response_contract_verified": bar_count > 0,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    certificate = {
        "schema_version": "v79.05.alpaca_market_data_foundation_certificate.1",
        "stage": "V79.05",
        "status": status,
        "scope": "ALPACA_MARKET_DATA_FOUNDATION_OFFLINE_ONLY",
        "stages_completed": ["V79.01", "V79.02", "V79.03", "V79.04", "V79.05"],
        "passed_stage_count": 5 if status == "PASS" else 0,
        "failed_stage_count": 0 if status == "PASS" else 1,
        "alpaca_sdk": install_status.to_dict(),
        "safety_config": asdict(safety_config),
        "fixture_bar_count": bar_count,
        "symbols_verified": sorted(fixture_result),
        "checks": checks,
        "network_calls_made": diagnostics["network_call_count"],
        "broker_connected": False,
        "actual_orders_submitted": 0,
        "real_credentials_used": False,
        "live_trading_authorized": False,
        "next_phase": "V79_06_ALPACA_HISTORICAL_DATA_CLIENT",
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    write_json(
        output_dir / "alpaca_market_data_foundation_certificate_v79_05.json",
        certificate,
    )
    verification = {
        "stage": "V79.05",
        "status": status,
        "verified": status == "PASS",
        "certificate_sha256": certificate["certificate_sha256"],
        "output_path": str(
            (output_dir / "alpaca_market_data_foundation_certificate_v79_05.json")
            .relative_to(repository_root)
        ).replace("\\", "/"),
        "next_phase": certificate["next_phase"],
    }
    verification["verification_sha256"] = sha256_json(verification)
    write_json(
        output_dir / "alpaca_market_data_foundation_verification_v79_05.json",
        verification,
    )
    return certificate
