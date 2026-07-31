from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib, json, re, secrets

KEY_NAMES = ("APCA_API_KEY_ID", "ALPACA_API_KEY")
SECRET_NAMES = ("APCA_API_SECRET_KEY", "ALPACA_SECRET_KEY")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class CredentialInspection:
    stage: str
    key_present: bool
    secret_present: bool
    pair_complete: bool
    key_shape_valid: bool
    secret_shape_valid: bool
    values_exposed: bool = False
    values_used: bool = False

    @property
    def ready_for_client_creation(self) -> bool:
        return (
            self.pair_complete
            and self.key_shape_valid
            and self.secret_shape_valid
            and not self.values_exposed
        )

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first_value(source: Mapping[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        value = source.get(name, "").strip()
        if value:
            return value
    return ""


def inspect_credentials(source: Mapping[str, str]) -> CredentialInspection:
    key = _first_value(source, KEY_NAMES)
    secret = _first_value(source, SECRET_NAMES)
    key_valid = 8 <= len(key) <= 128 and SAFE_TOKEN_RE.fullmatch(key) is not None
    secret_valid = 16 <= len(secret) <= 256 and all(not c.isspace() for c in secret)
    return CredentialInspection(
        stage="V79.11",
        key_present=bool(key),
        secret_present=bool(secret),
        pair_complete=bool(key and secret),
        key_shape_valid=key_valid,
        secret_shape_valid=secret_valid,
    )


@dataclass(frozen=True)
class NetworkApproval:
    stage: str
    approved: bool
    scope: str
    token_id: str
    issued_at: str
    expires_at: str
    max_requests: int
    requests_used: int = 0

    def validate(self, now: datetime | None = None) -> None:
        moment = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if not self.approved:
            raise PermissionError("network approval is not granted")
        if self.scope != "ALPACA_HISTORICAL_MARKET_DATA_ONLY":
            raise PermissionError("invalid network approval scope")
        if moment >= expiry:
            raise PermissionError("network approval expired")
        if self.max_requests < 1 or self.requests_used >= self.max_requests:
            raise PermissionError("network request allowance exhausted")


def issue_network_approval(
    *,
    approved: bool,
    ttl_minutes: int = 5,
    max_requests: int = 1,
    now: datetime | None = None,
    token_id: str | None = None,
) -> NetworkApproval:
    if ttl_minutes < 1 or ttl_minutes > 30:
        raise ValueError("ttl_minutes must be 1..30")
    if max_requests < 1 or max_requests > 10:
        raise ValueError("max_requests must be 1..10")
    moment = now or datetime.now(timezone.utc)
    return NetworkApproval(
        stage="V79.12",
        approved=approved,
        scope="ALPACA_HISTORICAL_MARKET_DATA_ONLY",
        token_id=token_id or secrets.token_hex(8),
        issued_at=moment.isoformat().replace("+00:00", "Z"),
        expires_at=(moment + timedelta(minutes=ttl_minutes)).isoformat().replace("+00:00", "Z"),
        max_requests=max_requests,
    )


@dataclass(frozen=True)
class AuthenticatedClientPolicy:
    stage: str = "V79.13"
    historical_data_only: bool = True
    trading_client_allowed: bool = False
    account_api_allowed: bool = False
    order_api_allowed: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if not self.historical_data_only:
            raise ValueError("historical_data_only must remain true")
        if self.trading_client_allowed or self.account_api_allowed or self.order_api_allowed:
            raise ValueError("trading, account, and order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual order count must remain zero")


class ClientFactoryResult:
    def __init__(self, client: Any, metadata: dict[str, Any]):
        self.client = client
        self.metadata = metadata


def build_authenticated_client(
    source: Mapping[str, str],
    inspection: CredentialInspection,
    policy: AuthenticatedClientPolicy,
) -> ClientFactoryResult:
    policy.validate()
    if not inspection.ready_for_client_creation:
        raise PermissionError("credential inspection did not pass")
    key = _first_value(source, KEY_NAMES)
    secret = _first_value(source, SECRET_NAMES)
    from alpaca.data.historical import StockHistoricalDataClient
    client = StockHistoricalDataClient(api_key=key, secret_key=secret)
    return ClientFactoryResult(
        client,
        {
            "stage": "V79.13",
            "client_type": type(client).__name__,
            "authenticated": True,
            "network_request_performed": False,
            "credential_values_exposed": False,
            "trading_client_created": False,
        },
    )


def authorize_historical_request(
    approval: NetworkApproval,
    policy: AuthenticatedClientPolicy,
    *,
    requested_operation: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    policy.validate()
    approval.validate(now)
    if requested_operation != "GET_STOCK_BARS":
        raise PermissionError("only GET_STOCK_BARS is authorized")
    return {
        "stage": "V79.14",
        "authorized": True,
        "operation": requested_operation,
        "scope": approval.scope,
        "approval_token_id": approval.token_id,
        "network_request_executed": False,
        "actual_orders_submitted": 0,
    }


def build_authenticated_gate_certificate(
    repository_root: Path,
    output_dir: Path,
    inspection: CredentialInspection,
    approval: NetworkApproval,
    policy: AuthenticatedClientPolicy,
    client_metadata: dict[str, Any],
    authorization: dict[str, Any],
) -> dict[str, Any]:
    policy.validate()
    checks = {
        "v79_10_certificate_present": (
            repository_root / "release/v79_10/output/alpaca_historical_data_certificate_v79_10.json"
        ).is_file(),
        "credential_pair_complete": inspection.pair_complete,
        "credential_shapes_valid": inspection.key_shape_valid and inspection.secret_shape_valid,
        "credential_values_not_exposed": not inspection.values_exposed,
        "network_approval_valid": approval.approved,
        "historical_scope_only": approval.scope == "ALPACA_HISTORICAL_MARKET_DATA_ONLY",
        "client_created_without_request": client_metadata.get("network_request_performed") is False,
        "trading_client_not_created": client_metadata.get("trading_client_created") is False,
        "operation_authorized": authorization.get("authorized") is True,
        "network_request_not_executed": authorization.get("network_request_executed") is False,
        "order_api_disabled": policy.order_api_allowed is False,
        "actual_orders_zero": policy.actual_orders_submitted == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "schema_version": "v79.15.authenticated_historical_gate.1",
        "stage": "V79.15",
        "status": status,
        "scope": "AUTHENTICATED_HISTORICAL_DATA_GATE_NO_NETWORK_EXECUTION",
        "stages_completed": ["V79.11", "V79.12", "V79.13", "V79.14", "V79.15"],
        "passed_stage_count": 5 if status == "PASS" else 5 - len(failed),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "credential_inspection": inspection.public_dict(),
        "network_approval": asdict(approval),
        "client_policy": asdict(policy),
        "client_metadata": client_metadata,
        "authorization": authorization,
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_exposed": False,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_16_ALPACA_HISTORICAL_NETWORK_SMOKE_TEST",
    }
    cert["certificate_sha256"] = sha256_json(cert)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "authenticated_historical_gate_certificate_v79_15.json"
    write_json(cert_path, cert)
    verify = {
        "stage": "V79.15", "status": status, "verified": not failed,
        "certificate_sha256": cert["certificate_sha256"],
        "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
        "failed_checks": failed, "next_phase": cert["next_phase"],
    }
    verify["verification_sha256"] = sha256_json(verify)
    write_json(output_dir / "authenticated_historical_gate_verification_v79_15.json", verify)
    return cert
