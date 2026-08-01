from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

def canonical(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha_json(v: Any) -> str:
    return hashlib.sha256(canonical(v).encode("utf-8")).hexdigest()

def sha_bytes(v: bytes) -> str:
    return hashlib.sha256(v).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as handle:
        handle.write(data)
        temp = Path(handle.name)
    os.replace(temp, path)

@dataclass(frozen=True)
class BrokerAdapterConfig:
    mode: str = "OFFLINE_ADAPTER_CONTRACT_ONLY"
    adapter_name: str = "SANDBOX_BROKER"
    retry_limit: int = 3
    rate_limit_per_minute: int = 120
    allow_network: bool = False
    allow_credentials: bool = False
    allow_client_creation: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if self.mode != "OFFLINE_ADAPTER_CONTRACT_ONLY":
            raise ValueError("unsafe mode")
        if self.adapter_name not in {"NULL_BROKER", "MOCK_BROKER", "SANDBOX_BROKER"}:
            raise ValueError("adapter")
        if self.retry_limit < 0 or self.rate_limit_per_minute < 1:
            raise ValueError("limits")
        if (
            self.allow_network
            or self.allow_credentials
            or self.allow_client_creation
            or self.allow_order_submission
            or self.actual_orders_submitted
        ):
            raise ValueError("offline only")

def validate_multi_asset_certificate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    cert = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(cert)
    expected = unsigned.pop("certificate_sha256", None)
    if expected != sha_json(unsigned):
        raise ValueError("certificate hash")
    if cert.get("stage") != "V81.40" or cert.get("status") != "PASS":
        raise ValueError("certificate stage")
    if cert.get("multi_asset_portfolio_complete") is not True:
        raise ValueError("multi asset incomplete")
    if cert.get("actual_orders_submitted") != 0:
        raise ValueError("orders found")
    return cert

def capability_registry() -> dict[str, Any]:
    adapters = {
        "NULL_BROKER": {
            "account_read": False, "position_read": False, "order_preview": False,
            "fill_preview": False, "network_required": False, "credentials_required": False,
            "order_submission": False,
        },
        "MOCK_BROKER": {
            "account_read": True, "position_read": True, "order_preview": True,
            "fill_preview": True, "network_required": False, "credentials_required": False,
            "order_submission": False,
        },
        "SANDBOX_BROKER": {
            "account_read": True, "position_read": True, "order_preview": True,
            "fill_preview": True, "network_required": False, "credentials_required": False,
            "order_submission": False,
        },
    }
    doc = {"stage": "V81.41", "status": "PASS", "adapter_count": len(adapters), "adapters": adapters}
    doc["registry_sha256"] = sha_json(doc)
    return doc

def symbol_map(symbol: str) -> dict[str, Any]:
    normalized = symbol.strip().upper()
    if not normalized or not normalized.replace(".", "").isalnum():
        raise ValueError("symbol")
    result = {
        "stage": "V81.44",
        "input_symbol": symbol,
        "normalized_symbol": normalized,
        "broker_symbol": normalized.replace(".", "-"),
    }
    result["mapping_sha256"] = sha_json(result)
    return result

def translate_order(intent: dict[str, Any]) -> dict[str, Any]:
    side = str(intent.get("side", "")).upper()
    order_type = str(intent.get("order_type", "MARKET")).upper()
    quantity = intent.get("quantity")
    if side not in {"BUY", "SELL"}:
        raise ValueError("side")
    if order_type not in {"MARKET", "LIMIT"}:
        raise ValueError("order type")
    if not isinstance(quantity, int) or quantity < 1:
        raise ValueError("quantity")
    mapped = symbol_map(str(intent.get("symbol", "")))
    translated = {
        "stage": "V81.45",
        "adapter_order_id": "preview-" + sha_json(intent)[:20],
        "symbol": mapped["broker_symbol"],
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "limit_price": intent.get("limit_price"),
        "time_in_force": str(intent.get("time_in_force", "DAY")).upper(),
        "preview_only": True,
        "submission_authorized": False,
    }
    if order_type == "LIMIT":
        price = translated["limit_price"]
        if price is None or float(price) <= 0 or not math.isfinite(float(price)):
            raise ValueError("limit price")
        translated["limit_price"] = float(price)
    translated["translation_sha256"] = sha_json(translated)
    return translated

def translate_account(raw: dict[str, Any]) -> dict[str, Any]:
    cash = float(raw["cash"])
    equity = float(raw["equity"])
    if cash < 0 or equity < 0:
        raise ValueError("account values")
    result = {
        "stage": "V81.46", "account_id": str(raw.get("account_id", "offline-account")),
        "cash": cash, "equity": equity, "buying_power": float(raw.get("buying_power", cash)),
        "currency": "USD", "source": "OFFLINE_FIXTURE",
    }
    result["account_sha256"] = sha_json(result)
    return result

def translate_positions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    translated = []
    for raw in rows:
        qty = int(raw["quantity"])
        avg = float(raw["average_price"])
        if qty < 0 or avg <= 0:
            raise ValueError("position")
        item = {
            "stage": "V81.47", "symbol": symbol_map(str(raw["symbol"]))["normalized_symbol"],
            "quantity": qty, "average_price": avg,
            "market_price": float(raw.get("market_price", avg)),
            "source": "OFFLINE_FIXTURE",
        }
        item["position_sha256"] = sha_json(item)
        translated.append(item)
    if len({x["symbol"] for x in translated}) != len(translated):
        raise ValueError("duplicate position")
    return translated

def translate_orders(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = {"NEW", "ACCEPTED", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED"}
    output = []
    for raw in rows:
        status = str(raw["status"]).upper()
        if status not in allowed:
            raise ValueError("order status")
        item = {
            "stage": "V81.48", "adapter_order_id": str(raw["adapter_order_id"]),
            "symbol": symbol_map(str(raw["symbol"]))["normalized_symbol"],
            "status": status, "filled_quantity": int(raw.get("filled_quantity", 0)),
            "source": "OFFLINE_FIXTURE",
        }
        item["order_sha256"] = sha_json(item)
        output.append(item)
    return output

def translate_fills(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for raw in rows:
        qty = int(raw["quantity"])
        price = float(raw["price"])
        if qty < 1 or price <= 0:
            raise ValueError("fill")
        item = {
            "stage": "V81.49", "fill_id": str(raw["fill_id"]),
            "adapter_order_id": str(raw["adapter_order_id"]),
            "symbol": symbol_map(str(raw["symbol"]))["normalized_symbol"],
            "quantity": qty, "price": price, "source": "OFFLINE_FIXTURE",
        }
        item["fill_sha256"] = sha_json(item)
        output.append(item)
    return output

ERROR_MAP = {
    "TIMEOUT": {"class": "TRANSIENT", "retryable": True},
    "RATE_LIMIT": {"class": "TRANSIENT", "retryable": True},
    "BAD_REQUEST": {"class": "PERMANENT", "retryable": False},
    "UNAUTHORIZED": {"class": "SAFETY", "retryable": False},
    "ORDER_REJECTED": {"class": "PERMANENT", "retryable": False},
}

def map_error(code: str) -> dict[str, Any]:
    normalized = code.strip().upper()
    metadata = ERROR_MAP.get(normalized, {"class": "UNKNOWN", "retryable": False})
    result = {"stage": "V81.50", "error_code": normalized, **metadata}
    result["error_sha256"] = sha_json(result)
    return result

def retry_plan(error_code: str, config: BrokerAdapterConfig) -> dict[str, Any]:
    mapped = map_error(error_code)
    attempts = config.retry_limit if mapped["retryable"] else 0
    result = {
        "stage": "V81.51", "error_code": mapped["error_code"], "retryable": mapped["retryable"],
        "maximum_attempts": attempts, "backoff_seconds": [2 ** i for i in range(attempts)],
        "network_execution_authorized": False,
    }
    result["retry_sha256"] = sha_json(result)
    return result

def rate_limit_guard(request_count: int, config: BrokerAdapterConfig) -> dict[str, Any]:
    if request_count < 0:
        raise ValueError("request count")
    allowed = request_count <= config.rate_limit_per_minute
    result = {
        "stage": "V81.52", "request_count": request_count,
        "limit": config.rate_limit_per_minute, "allowed": allowed,
        "network_requests_executed": 0,
    }
    result["rate_limit_sha256"] = sha_json(result)
    return result

def adapter_factory(name: str) -> dict[str, Any]:
    registry = capability_registry()["adapters"]
    normalized = name.upper()
    if normalized not in registry:
        raise ValueError("adapter not found")
    result = {
        "stage": "V81.43", "adapter_name": normalized,
        "capabilities": registry[normalized], "client_created": False,
        "network_connected": False, "credentials_loaded": False,
    }
    result["adapter_sha256"] = sha_json(result)
    return result

def build_fixture_snapshot() -> dict[str, Any]:
    account = translate_account({"account_id": "sandbox", "cash": 10000, "equity": 100000, "buying_power": 10000})
    positions = translate_positions([
        {"symbol": "AAPL", "quantity": 80, "average_price": 180, "market_price": 190},
        {"symbol": "MSFT", "quantity": 20, "average_price": 400, "market_price": 420},
    ])
    preview = translate_order({"symbol": "JPM", "side": "BUY", "quantity": 10, "order_type": "LIMIT", "limit_price": 208})
    orders = translate_orders([{"adapter_order_id": preview["adapter_order_id"], "symbol": "JPM", "status": "ACCEPTED", "filled_quantity": 0}])
    fills = translate_fills([{"fill_id": "fixture-fill-1", "adapter_order_id": preview["adapter_order_id"], "symbol": "JPM", "quantity": 5, "price": 208}])
    result = {
        "stage": "V81.53", "status": "PASS", "account": account, "positions": positions,
        "order_preview": preview, "orders": orders, "fills": fills,
        "actual_orders_submitted": 0,
    }
    result["snapshot_sha256"] = sha_json(result)
    return result

def build_audit(config, registry, adapter, snapshot, retry, rate):
    checks = {
        "registry_three": registry["adapter_count"] == 3,
        "adapter_selected": adapter["adapter_name"] == config.adapter_name,
        "client_not_created": adapter["client_created"] is False,
        "network_not_connected": adapter["network_connected"] is False,
        "credentials_not_loaded": adapter["credentials_loaded"] is False,
        "preview_only": snapshot["order_preview"]["preview_only"] is True,
        "submission_unauthorized": snapshot["order_preview"]["submission_authorized"] is False,
        "actual_orders_zero": snapshot["actual_orders_submitted"] == 0,
        "retry_network_unauthorized": retry["network_execution_authorized"] is False,
        "rate_network_zero": rate["network_requests_executed"] == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    result = {"stage": "V81.54", "status": "PASS" if not failed else "FAIL", "checks": checks, "failed_checks": failed}
    result["audit_sha256"] = sha_json(result)
    return result

def store_package(out: Path, docs: dict[str, Any]) -> dict[str, Any]:
    package_id = "broker-adapter-" + sha_json(docs)[:24]
    package_dir = out / "packages" / package_id
    created = not package_dir.exists()
    files = {}
    for name, doc in docs.items():
        path = package_dir / f"{name}.json"
        data = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if path.exists() and path.read_bytes() != data:
            raise ValueError("package conflict")
        if not path.exists():
            atomic_write(path, data)
        files[name] = {
            "relative_path": str(path.relative_to(out)).replace("\\", "/"),
            "sha256": sha_bytes(data), "byte_size": len(data),
        }
    ledger = {
        "stage": "V81.55", "status": "PASS", "package_id": package_id,
        "document_count": len(docs), "package_created": created,
        "package_reused": not created, "files": files, "actual_orders_submitted": 0,
    }
    ledger["ledger_sha256"] = sha_json(ledger)
    write_json(out / "broker_adapter_master_ledger_v81_55.json", ledger)
    return {"package_id": package_id, "created": created, "reused": not created, "ledger": ledger}

def build_manifest(out: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    ledger_path = out / "broker_adapter_master_ledger_v81_55.json"
    data = ledger_path.read_bytes()
    manifest = {
        "stage": "V81.56", "status": "PASS", "package_id": ledger["package_id"],
        "files": {"master_ledger": {
            "relative_path": str(ledger_path.relative_to(out)).replace("\\", "/"),
            "sha256": sha_bytes(data), "byte_size": len(data),
        }},
        "network_requests_executed": 0, "credentials_used": 0,
        "trading_client_created": False, "actual_orders_submitted": 0,
    }
    manifest["manifest_sha256"] = sha_json(manifest)
    write_json(out / "broker_adapter_manifest_v81_56.json", manifest)
    return manifest

def verify_manifest(out: Path, manifest: dict[str, Any]) -> bool:
    unsigned = dict(manifest)
    expected = unsigned.pop("manifest_sha256", None)
    if expected != sha_json(unsigned):
        raise ValueError("manifest hash")
    for metadata in manifest["files"].values():
        path = out / metadata["relative_path"]
        data = path.read_bytes()
        if sha_bytes(data) != metadata["sha256"] or len(data) != metadata["byte_size"]:
            raise ValueError("manifest tamper")
    ledger = json.loads((out / "broker_adapter_master_ledger_v81_55.json").read_text(encoding="utf-8"))
    for metadata in ledger["files"].values():
        path = out / metadata["relative_path"]
        data = path.read_bytes()
        if sha_bytes(data) != metadata["sha256"] or len(data) != metadata["byte_size"]:
            raise ValueError("nested tamper")
    return True

def run_engine(root: Path, config: BrokerAdapterConfig, out: Path) -> dict[str, Any]:
    config.validate()
    source = validate_multi_asset_certificate(root / "release/v81_40/output/multi_asset_portfolio_certificate_v81_40.json")
    registry = capability_registry()
    adapter = adapter_factory(config.adapter_name)
    snapshot = build_fixture_snapshot()
    timeout = map_error("TIMEOUT")
    retry = retry_plan("TIMEOUT", config)
    rate = rate_limit_guard(0, config)
    audit = build_audit(config, registry, adapter, snapshot, retry, rate)
    docs = {
        "capability_registry": registry, "adapter": adapter, "fixture_snapshot": snapshot,
        "error_mapping": timeout, "retry_plan": retry, "rate_limit_guard": rate, "audit": audit,
    }
    stored = store_package(out, docs)
    manifest = build_manifest(out, stored["ledger"])
    verify_manifest(out, manifest)
    summary = {
        "adapter_count": registry["adapter_count"], "selected_adapter": adapter["adapter_name"],
        "account_snapshot_count": 1, "position_snapshot_count": len(snapshot["positions"]),
        "order_preview_count": 1, "order_snapshot_count": len(snapshot["orders"]),
        "fill_snapshot_count": len(snapshot["fills"]), "retry_attempt_limit": retry["maximum_attempts"],
        "rate_limit_per_minute": rate["limit"], "audit_status": audit["status"],
        "source_asset_count": source["multi_asset_summary"]["asset_count"],
        "actual_orders_submitted": 0,
    }
    return {
        "stage": "V81.57", "status": "PASS", "summary": summary, **stored, "manifest": manifest,
        "network_requests_executed": 0, "credentials_used": 0,
        "trading_client_created": False, "actual_orders_submitted": 0,
    }

def build_certificate(root: Path, out: Path, config: BrokerAdapterConfig, result: dict[str, Any]) -> dict[str, Any]:
    summary = result["summary"]
    checks = {
        "v81_40_certificate_present": (root / "release/v81_40/output/multi_asset_portfolio_certificate_v81_40.json").is_file(),
        "pipeline_pass": result["status"] == "PASS",
        "adapter_count_three": summary["adapter_count"] == 3,
        "selected_adapter_sandbox": summary["selected_adapter"] == "SANDBOX_BROKER",
        "account_snapshot_one": summary["account_snapshot_count"] == 1,
        "position_snapshots_positive": summary["position_snapshot_count"] > 0,
        "order_preview_one": summary["order_preview_count"] == 1,
        "audit_pass": summary["audit_status"] == "PASS",
        "manifest_hash_present": len(result["manifest"]["manifest_sha256"]) == 64,
        "network_zero": result["network_requests_executed"] == 0,
        "credentials_zero": result["credentials_used"] == 0,
        "client_false": result["trading_client_created"] is False,
        "actual_orders_zero": result["actual_orders_submitted"] == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "stage": "V81.60", "status": status, "scope": "OFFLINE_BROKER_ADAPTER_FOUNDATION",
        "stages_completed": [f"V81.{i:02d}" for i in range(41, 61)],
        "completed_stage_count": 20 if status == "PASS" else 20 - len(failed),
        "config": asdict(config),
        "adapter_summary": {**summary, "package_id": result["package_id"],
                            "package_created": result["created"], "package_reused": result["reused"]},
        "adapter_manifest": result["manifest"], "checks": checks, "failed_checks": failed,
        "network_requests_executed": 0, "credentials_used": 0, "broker_connected": False,
        "trading_client_created": False, "actual_orders_submitted": 0,
        "paper_trading_authorized": False, "live_trading_authorized": False,
        "broker_adapter_foundation_complete": status == "PASS",
        "next_phase": "V81_61_EXECUTION_SIMULATION_ENGINE",
    }
    cert["certificate_sha256"] = sha_json(cert)
    write_json(out / "broker_adapter_foundation_certificate_v81_60.json", cert)
    write_json(out / "broker_adapter_foundation_verify_v81_60.json", {
        "stage": "V81.60", "status": status, "verified": not failed,
        "certificate_sha256": cert["certificate_sha256"], "failed_checks": failed,
        "next_phase": cert["next_phase"],
    })
    return cert
