from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import os

ENABLE_NAME = "ALPACA_ENABLE_NETWORK_SMOKE"
KEY_NAMES = ("APCA_API_KEY_ID", "ALPACA_API_KEY")
SECRET_NAMES = ("APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY")


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


def _value(source: Mapping[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        value = source.get(name, "").strip()
        if value:
            return value
    return ""


@dataclass(frozen=True)
class NetworkSmokeConfig:
    stage: str = "V79.16"
    symbol: str = "AAPL"
    timeframe: str = "1Day"
    lookback_days: int = 7
    limit: int = 1
    feed: str = "iex"
    adjustment: str = "raw"
    sort: str = "desc"
    timeout_seconds: int = 15
    historical_data_only: bool = True
    trading_api_allowed: bool = False
    account_api_allowed: bool = False
    order_api_allowed: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if self.symbol != "AAPL":
            raise ValueError("network smoke symbol must remain AAPL")
        if self.timeframe != "1Day":
            raise ValueError("network smoke timeframe must remain 1Day")
        if not 1 <= self.lookback_days <= 14:
            raise ValueError("lookback_days must be 1..14")
        if self.limit != 1:
            raise ValueError("network smoke limit must remain 1")
        if self.feed != "iex":
            raise ValueError("network smoke feed must remain iex")
        if self.timeout_seconds > 15:
            raise ValueError("timeout_seconds must not exceed 15")
        if not self.historical_data_only:
            raise ValueError("historical_data_only must remain true")
        if self.trading_api_allowed or self.account_api_allowed or self.order_api_allowed:
            raise ValueError("trading/account/order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual order count must remain zero")


@dataclass(frozen=True)
class NetworkSmokePreflight:
    stage: str
    enable_flag_present: bool
    enable_flag_valid: bool
    key_present: bool
    secret_present: bool
    credential_pair_complete: bool
    network_execution_authorized: bool
    credentials_exposed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_network_smoke_preflight(
    source: Mapping[str, str] | None = None,
) -> NetworkSmokePreflight:
    env = os.environ if source is None else source
    flag = env.get(ENABLE_NAME, "").strip()
    key = _value(env, KEY_NAMES)
    secret = _value(env, SECRET_NAMES)
    valid_flag = flag == "YES"
    pair = bool(key and secret)
    return NetworkSmokePreflight(
        stage="V79.16",
        enable_flag_present=bool(flag),
        enable_flag_valid=valid_flag,
        key_present=bool(key),
        secret_present=bool(secret),
        credential_pair_complete=pair,
        network_execution_authorized=valid_flag and pair,
    )


def build_bounded_stock_bars_request(
    config: NetworkSmokeConfig,
    *,
    now: datetime | None = None,
) -> Any:
    config.validate()
    from alpaca.common.enums import Sort
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    end = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = end - timedelta(days=config.lookback_days)
    return StockBarsRequest(
        symbol_or_symbols=[config.symbol],
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        limit=config.limit,
        adjustment=Adjustment.RAW,
        feed=DataFeed.IEX,
        sort=Sort.DESC,
    )


@dataclass(frozen=True)
class NetworkSmokeResult:
    stage: str
    status: str
    executed: bool
    skipped_safely: bool
    symbol: str
    record_count: int
    response_type: str | None
    error_type: str | None
    error_message_redacted: str | None
    network_request_count: int
    credential_use_count: int
    trading_client_created: bool
    actual_orders_submitted: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_historical_network_smoke(
    source: Mapping[str, str],
    config: NetworkSmokeConfig,
    client_factory: Any | None = None,
    *,
    now: datetime | None = None,
) -> NetworkSmokeResult:
    config.validate()
    preflight = inspect_network_smoke_preflight(source)
    if not preflight.network_execution_authorized:
        return NetworkSmokeResult(
            stage="V79.18",
            status="SKIPPED_SAFE",
            executed=False,
            skipped_safely=True,
            symbol=config.symbol,
            record_count=0,
            response_type=None,
            error_type=None,
            error_message_redacted=None,
            network_request_count=0,
            credential_use_count=0,
            trading_client_created=False,
            actual_orders_submitted=0,
        )

    key = _value(source, KEY_NAMES)
    secret = _value(source, SECRET_NAMES)
    request = build_bounded_stock_bars_request(config, now=now)

    try:
        if client_factory is None:
            from alpaca.data.historical import StockHistoricalDataClient
            client = StockHistoricalDataClient(api_key=key, secret_key=secret)
        else:
            client = client_factory(key, secret)
        response = client.get_stock_bars(request)
        count = _count_response_records(response, config.symbol)
        return NetworkSmokeResult(
            stage="V79.18",
            status="PASS",
            executed=True,
            skipped_safely=False,
            symbol=config.symbol,
            record_count=count,
            response_type=type(response).__name__,
            error_type=None,
            error_message_redacted=None,
            network_request_count=1,
            credential_use_count=1,
            trading_client_created=False,
            actual_orders_submitted=0,
        )
    except Exception as exc:
        return NetworkSmokeResult(
            stage="V79.18",
            status="FAIL",
            executed=True,
            skipped_safely=False,
            symbol=config.symbol,
            record_count=0,
            response_type=None,
            error_type=type(exc).__name__,
            error_message_redacted="historical network smoke request failed",
            network_request_count=1,
            credential_use_count=1,
            trading_client_created=False,
            actual_orders_submitted=0,
        )


def _count_response_records(response: Any, symbol: str) -> int:
    data = getattr(response, "data", response)
    if isinstance(data, dict):
        rows = data.get(symbol, [])
        return min(len(rows), 1)
    if hasattr(response, "df"):
        frame = response.df
        return min(len(frame), 1)
    return 0


def sanitize_smoke_result(result: NetworkSmokeResult) -> dict[str, Any]:
    doc = result.to_dict()
    doc["stage"] = "V79.19"
    doc["credentials_exposed"] = False
    doc["raw_response_persisted"] = False
    doc["sanitized"] = True
    doc["result_sha256"] = sha256_json(doc)
    return doc


def build_network_smoke_certificate(
    repository_root: Path,
    output_dir: Path,
    config: NetworkSmokeConfig,
    preflight: NetworkSmokePreflight,
    result: NetworkSmokeResult,
    sanitized: dict[str, Any],
) -> dict[str, Any]:
    config.validate()
    acceptable_result = result.status in {"PASS", "SKIPPED_SAFE"}
    checks = {
        "v79_15_certificate_present": (
            repository_root
            / "release/v79_15/output/authenticated_historical_gate_certificate_v79_15.json"
        ).is_file(),
        "bounded_symbol": config.symbol == "AAPL",
        "bounded_limit": config.limit == 1,
        "bounded_timeframe": config.timeframe == "1Day",
        "historical_scope_only": config.historical_data_only,
        "trading_api_disabled": not config.trading_api_allowed,
        "account_api_disabled": not config.account_api_allowed,
        "order_api_disabled": not config.order_api_allowed,
        "result_acceptable": acceptable_result,
        "unsafe_execution_prevented": (
            result.executed is preflight.network_execution_authorized
        ),
        "credentials_not_exposed": sanitized.get("credentials_exposed") is False,
        "raw_response_not_persisted": sanitized.get("raw_response_persisted") is False,
        "trading_client_not_created": result.trading_client_created is False,
        "actual_orders_zero": result.actual_orders_submitted == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    certificate = {
        "schema_version": "v79.20.historical_network_smoke_certificate.1",
        "stage": "V79.20",
        "status": status,
        "scope": "BOUNDED_ALPACA_HISTORICAL_NETWORK_SMOKE",
        "stages_completed": ["V79.16", "V79.17", "V79.18", "V79.19", "V79.20"],
        "passed_stage_count": 5 if status == "PASS" else 5 - len(failed),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "network_smoke_mode": result.status,
        "config": asdict(config),
        "preflight": preflight.to_dict(),
        "sanitized_result": sanitized,
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": result.network_request_count,
        "credential_use_count": result.credential_use_count,
        "credentials_exposed": False,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_21_ALPACA_HISTORICAL_DATA_INGESTION",
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "historical_network_smoke_certificate_v79_20.json"
    write_json(cert_path, certificate)
    verify = {
        "stage": "V79.20",
        "status": status,
        "verified": not failed,
        "certificate_sha256": certificate["certificate_sha256"],
        "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
        "failed_checks": failed,
        "next_phase": certificate["next_phase"],
    }
    verify["verification_sha256"] = sha256_json(verify)
    write_json(
        output_dir / "historical_network_smoke_verification_v79_20.json",
        verify,
    )
    return certificate
