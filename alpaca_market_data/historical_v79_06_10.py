from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata, util
from pathlib import Path
from typing import Any, Protocol
import hashlib
import json
import re

SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
TIMEFRAME_NAMES = {"1Min", "5Min", "15Min", "1Hour", "1Day"}
FEEDS = {"iex", "sip", "delayed_sip", "boats"}
ADJUSTMENTS = {"raw", "split", "dividend", "all"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_text(value: str | datetime) -> str:
    return parse_utc(value).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class HistoricalClientConfig:
    stage: str = "V79.06"
    mode: str = "offline_fixture"
    network_allowed: bool = False
    credentials_allowed: bool = False
    credentials_used: bool = False
    broker_connected: bool = False
    trading_client_created: bool = False
    order_submission_allowed: bool = False
    actual_orders_submitted: int = 0
    default_feed: str = "iex"
    cache_enabled: bool = True

    def validate(self) -> None:
        if self.mode != "offline_fixture":
            raise ValueError("V79.06-V79.10 supports offline_fixture mode only")
        if self.network_allowed:
            raise ValueError("network access is prohibited")
        if self.credentials_allowed or self.credentials_used:
            raise ValueError("credential use is prohibited")
        if self.broker_connected or self.trading_client_created:
            raise ValueError("broker/trading clients are prohibited")
        if self.order_submission_allowed or self.actual_orders_submitted != 0:
            raise ValueError("order submission is prohibited")
        if self.default_feed not in FEEDS:
            raise ValueError("unsupported data feed")


@dataclass(frozen=True)
class HistoricalBarsQuery:
    symbols: tuple[str, ...]
    timeframe: str
    start: str
    end: str
    limit: int = 1000
    adjustment: str = "raw"
    feed: str = "iex"
    sort: str = "asc"

    def __post_init__(self) -> None:
        normalized = tuple(item.strip().upper() for item in self.symbols)
        if not normalized or any(not SYMBOL_RE.fullmatch(item) for item in normalized):
            raise ValueError("invalid symbols")
        object.__setattr__(self, "symbols", normalized)
        object.__setattr__(self, "start", utc_text(self.start))
        object.__setattr__(self, "end", utc_text(self.end))
        if parse_utc(self.start) >= parse_utc(self.end):
            raise ValueError("start must be before end")
        if self.timeframe not in TIMEFRAME_NAMES:
            raise ValueError("unsupported timeframe")
        if not 1 <= self.limit <= 10000:
            raise ValueError("limit must be between 1 and 10000")
        if self.adjustment not in ADJUSTMENTS:
            raise ValueError("unsupported adjustment")
        if self.feed not in FEEDS:
            raise ValueError("unsupported feed")
        if self.sort not in {"asc", "desc"}:
            raise ValueError("sort must be asc or desc")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["symbols"] = list(self.symbols)
        return value

    @property
    def cache_key(self) -> str:
        return sha256_json(self.to_dict())


@dataclass(frozen=True)
class HistoricalBarRecord:
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: int = 0
    vwap: float | None = None
    source: str = "alpaca_fixture"

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not SYMBOL_RE.fullmatch(symbol):
            raise ValueError("invalid symbol")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timestamp", utc_text(self.timestamp))
        values = (self.open, self.high, self.low, self.close)
        if min(values) <= 0:
            raise ValueError("OHLC must be positive")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high is inconsistent")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low is inconsistent")
        if self.volume < 0 or self.trade_count < 0:
            raise ValueError("volume and trade_count must be nonnegative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HistoricalInstallStatus:
    stage: str
    alpaca_py_installed: bool
    alpaca_py_version: str | None
    stock_historical_client_importable: bool
    stock_bars_request_importable: bool
    dataframe_support_available: bool
    network_test_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_historical_installation() -> HistoricalInstallStatus:
    installed = util.find_spec("alpaca") is not None
    version = None
    client_ok = request_ok = False
    if installed:
        try:
            version = metadata.version("alpaca-py")
        except metadata.PackageNotFoundError:
            version = "unknown"
        try:
            from alpaca.data.historical import StockHistoricalDataClient  # noqa: F401
            client_ok = True
        except Exception:
            client_ok = False
        try:
            from alpaca.data.requests import StockBarsRequest  # noqa: F401
            request_ok = True
        except Exception:
            request_ok = False
    return HistoricalInstallStatus(
        stage="V79.06",
        alpaca_py_installed=installed,
        alpaca_py_version=version,
        stock_historical_client_importable=client_ok,
        stock_bars_request_importable=request_ok,
        dataframe_support_available=util.find_spec("pandas") is not None,
    )


class AlpacaRequestFactory:
    """Builds official alpaca-py request objects without sending them."""

    @staticmethod
    def build_stock_bars_request(query: HistoricalBarsQuery) -> Any:
        try:
            from alpaca.common.enums import Sort
            from alpaca.data.enums import Adjustment, DataFeed
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        except ImportError as exc:
            raise RuntimeError("alpaca-py is required to build an SDK request") from exc

        timeframe_map = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day,
        }
        feed_map = {
            "iex": DataFeed.IEX,
            "sip": DataFeed.SIP,
            "delayed_sip": DataFeed.DELAYED_SIP,
            "boats": DataFeed.BOATS,
        }
        adjustment_map = {
            "raw": Adjustment.RAW,
            "split": Adjustment.SPLIT,
            "dividend": Adjustment.DIVIDEND,
            "all": Adjustment.ALL,
        }
        sort_map = {"asc": Sort.ASC, "desc": Sort.DESC}
        return StockBarsRequest(
            symbol_or_symbols=list(query.symbols),
            timeframe=timeframe_map[query.timeframe],
            start=parse_utc(query.start),
            end=parse_utc(query.end),
            limit=query.limit,
            adjustment=adjustment_map[query.adjustment],
            feed=feed_map[query.feed],
            sort=sort_map[query.sort],
        )


class HistoricalTransport(Protocol):
    network_call_count: int
    credential_use_count: int
    order_submission_count: int

    def fetch_bars(self, query: HistoricalBarsQuery) -> Any:
        ...


class FixtureHistoricalTransport:
    """Offline transport used by tests and V79.10 certification."""

    def __init__(self, raw_payload: dict[str, list[dict[str, Any]]]):
        self._payload = raw_payload
        self.network_call_count = 0
        self.credential_use_count = 0
        self.order_submission_count = 0
        self.fixture_fetch_count = 0

    def fetch_bars(self, query: HistoricalBarsQuery) -> dict[str, list[dict[str, Any]]]:
        self.fixture_fetch_count += 1
        start, end = parse_utc(query.start), parse_utc(query.end)
        result: dict[str, list[dict[str, Any]]] = {}
        for symbol in query.symbols:
            rows = []
            for item in self._payload.get(symbol, []):
                timestamp = parse_utc(item["timestamp"])
                if start <= timestamp < end:
                    rows.append(dict(item))
            rows.sort(key=lambda item: parse_utc(item["timestamp"]), reverse=query.sort == "desc")
            result[symbol] = rows[: query.limit]
        return result


class HistoricalDataNormalizer:
    @staticmethod
    def normalize(payload: Any) -> list[HistoricalBarRecord]:
        if hasattr(payload, "data"):
            payload = payload.data
        if hasattr(payload, "df"):
            return HistoricalDataNormalizer.from_dataframe(payload.df)
        if not isinstance(payload, dict):
            raise ValueError("unsupported historical payload")

        records: list[HistoricalBarRecord] = []
        for symbol, rows in payload.items():
            for row in rows:
                if isinstance(row, HistoricalBarRecord):
                    records.append(row)
                    continue
                getter = row.get if isinstance(row, dict) else lambda key, default=None: getattr(row, key, default)
                records.append(HistoricalBarRecord(
                    symbol=getter("symbol", symbol),
                    timestamp=getter("timestamp"),
                    open=float(getter("open")),
                    high=float(getter("high")),
                    low=float(getter("low")),
                    close=float(getter("close")),
                    volume=int(getter("volume")),
                    trade_count=int(getter("trade_count", 0) or 0),
                    vwap=None if getter("vwap") is None else float(getter("vwap")),
                    source="alpaca_fixture",
                ))
        return sorted(records, key=lambda item: (item.symbol, parse_utc(item.timestamp)))

    @staticmethod
    def from_dataframe(frame: Any) -> list[HistoricalBarRecord]:
        if not hasattr(frame, "reset_index"):
            raise ValueError("dataframe-like object required")
        rows = frame.reset_index().to_dict(orient="records")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            symbol = str(row.get("symbol", "")).upper()
            grouped.setdefault(symbol, []).append(row)
        return HistoricalDataNormalizer.normalize(grouped)

    @staticmethod
    def to_rows(records: list[HistoricalBarRecord]) -> list[dict[str, Any]]:
        return [record.to_dict() for record in records]


class HistoricalDataCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    def _data_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _manifest_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.manifest.json"

    def put(self, query: HistoricalBarsQuery, records: list[HistoricalBarRecord]) -> dict[str, Any]:
        key = query.cache_key
        rows = HistoricalDataNormalizer.to_rows(records)
        payload = {
            "schema_version": "v79.09.historical_cache.1",
            "query": query.to_dict(),
            "records": rows,
        }
        data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        data_path = self._data_path(key)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_bytes(data)
        manifest = {
            "stage": "V79.09",
            "cache_key": key,
            "relative_data_file": data_path.name,
            "sha256": sha256_bytes(data),
            "byte_size": len(data),
            "record_count": len(records),
        }
        manifest["manifest_sha256"] = sha256_json(manifest)
        write_json(self._manifest_path(key), manifest)
        return manifest

    def get(self, query: HistoricalBarsQuery) -> list[HistoricalBarRecord] | None:
        key = query.cache_key
        data_path, manifest_path = self._data_path(key), self._manifest_path(key)
        if not data_path.is_file() or not manifest_path.is_file():
            return None
        data = data_path.read_bytes()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("cache_key") != key:
            raise ValueError("cache key mismatch")
        if manifest.get("sha256") != sha256_bytes(data):
            raise ValueError("cache content hash mismatch")
        if manifest.get("byte_size") != len(data):
            raise ValueError("cache byte size mismatch")
        payload = json.loads(data.decode("utf-8"))
        if payload.get("query") != query.to_dict():
            raise ValueError("cache query mismatch")
        records = [HistoricalBarRecord(**item) for item in payload.get("records", [])]
        if manifest.get("record_count") != len(records):
            raise ValueError("cache record count mismatch")
        return records


class SafeHistoricalDataService:
    def __init__(
        self,
        config: HistoricalClientConfig,
        transport: HistoricalTransport,
        cache: HistoricalDataCache | None = None,
    ):
        config.validate()
        self.config = config
        self.transport = transport
        self.cache = cache
        self.cache_hit_count = 0
        self.cache_miss_count = 0

    def get_bars(self, query: HistoricalBarsQuery) -> list[HistoricalBarRecord]:
        self.config.validate()
        if self.cache and self.config.cache_enabled:
            cached = self.cache.get(query)
            if cached is not None:
                self.cache_hit_count += 1
                return cached
            self.cache_miss_count += 1
        payload = self.transport.fetch_bars(query)
        records = HistoricalDataNormalizer.normalize(payload)
        if self.cache and self.config.cache_enabled:
            self.cache.put(query, records)
        return records

    def diagnostics(self) -> dict[str, Any]:
        return {
            "mode": self.config.mode,
            "network_call_count": self.transport.network_call_count,
            "credential_use_count": self.transport.credential_use_count,
            "order_submission_count": self.transport.order_submission_count,
            "cache_hit_count": self.cache_hit_count,
            "cache_miss_count": self.cache_miss_count,
        }


def build_historical_certificate(
    repository_root: Path,
    output_dir: Path,
    install_status: HistoricalInstallStatus,
    config: HistoricalClientConfig,
    query: HistoricalBarsQuery,
    records: list[HistoricalBarRecord],
    diagnostics: dict[str, Any],
    cache_manifest: dict[str, Any],
) -> dict[str, Any]:
    config.validate()
    timestamps = [parse_utc(item.timestamp) for item in records]
    checks = {
        "foundation_certificate_present": (
            repository_root / "release/v79_05/output/alpaca_market_data_foundation_certificate_v79_05.json"
        ).is_file(),
        "alpaca_sdk_installed": install_status.alpaca_py_installed,
        "stock_historical_client_importable": install_status.stock_historical_client_importable,
        "stock_bars_request_importable": install_status.stock_bars_request_importable,
        "dataframe_support_available": install_status.dataframe_support_available,
        "query_contract_valid": bool(query.symbols),
        "normalized_records_nonempty": len(records) > 0,
        "records_sorted_by_symbol_and_time": records == sorted(
            records, key=lambda item: (item.symbol, parse_utc(item.timestamp))
        ),
        "timestamps_are_utc": all(item.utcoffset().total_seconds() == 0 for item in timestamps),
        "cache_manifest_hash_present": len(cache_manifest.get("sha256", "")) == 64,
        "network_calls_zero": diagnostics["network_call_count"] == 0,
        "credential_use_zero": diagnostics["credential_use_count"] == 0,
        "order_submission_zero": diagnostics["order_submission_count"] == 0,
        "broker_disconnected": config.broker_connected is False,
        "trading_client_not_created": config.trading_client_created is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    certificate = {
        "schema_version": "v79.10.alpaca_historical_data_certificate.1",
        "stage": "V79.10",
        "status": status,
        "scope": "ALPACA_HISTORICAL_MARKET_DATA_OFFLINE_CERTIFICATION",
        "stages_completed": ["V79.06", "V79.07", "V79.08", "V79.09", "V79.10"],
        "passed_stage_count": 5 if status == "PASS" else 5 - len(failed),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "install_status": install_status.to_dict(),
        "client_config": asdict(config),
        "query": query.to_dict(),
        "record_count": len(records),
        "symbols": sorted({item.symbol for item in records}),
        "first_timestamp": min(item.timestamp for item in records),
        "last_timestamp": max(item.timestamp for item in records),
        "cache_manifest": cache_manifest,
        "diagnostics": diagnostics,
        "checks": checks,
        "failed_checks": failed,
        "network_calls_made": diagnostics["network_call_count"],
        "credentials_used": diagnostics["credential_use_count"],
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": diagnostics["order_submission_count"],
        "live_trading_authorized": False,
        "next_phase": "V79_11_ALPACA_AUTHENTICATED_HISTORICAL_DATA_GATE",
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "alpaca_historical_data_certificate_v79_10.json"
    write_json(cert_path, certificate)
    verification = {
        "stage": "V79.10",
        "status": status,
        "verified": not failed,
        "certificate_sha256": certificate["certificate_sha256"],
        "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
        "failed_checks": failed,
        "next_phase": certificate["next_phase"],
    }
    verification["verification_sha256"] = sha256_json(verification)
    write_json(output_dir / "alpaca_historical_data_verification_v79_10.json", verification)
    return certificate
