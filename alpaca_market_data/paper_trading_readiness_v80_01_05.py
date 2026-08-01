from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as handle:
        handle.write(data)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)

@dataclass(frozen=True)
class PaperReadinessConfig:
    mode: str = "DRY_RUN_NO_NETWORK"
    broker_name: str = "ALPACA"
    paper_environment_required: bool = True
    historical_completion_required: bool = True
    credentials_required: bool = False
    network_probe_enabled: bool = False
    trading_client_enabled: bool = False
    order_submission_enabled: bool = False
    account_query_enabled: bool = False
    positions_query_enabled: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if self.mode != "DRY_RUN_NO_NETWORK":
            raise ValueError("paper readiness must use DRY_RUN_NO_NETWORK")
        if self.broker_name != "ALPACA":
            raise ValueError("unsupported broker")
        if not self.paper_environment_required or not self.historical_completion_required:
            raise ValueError("paper and historical completion requirements must remain enabled")
        if (
            self.credentials_required
            or self.network_probe_enabled
            or self.trading_client_enabled
            or self.order_submission_enabled
            or self.account_query_enabled
            or self.positions_query_enabled
            or self.actual_orders_submitted
        ):
            raise ValueError("readiness foundation must not access broker services")

def validate_historical_completion_certificate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    certificate = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(certificate)
    expected = unsigned.pop("certificate_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError("historical completion certificate hash mismatch")
    if certificate.get("stage") != "V79.99" or certificate.get("status") != "PASS":
        raise ValueError("historical completion certificate is not PASS")
    summary = certificate.get("completion_summary", {})
    if summary.get("historical_engine_complete") is not True:
        raise ValueError("historical engine is not complete")
    if certificate.get("actual_orders_submitted") != 0:
        raise ValueError("historical completion reports actual orders")
    return certificate

def build_paper_policy(config: PaperReadinessConfig) -> dict[str, Any]:
    config.validate()
    policy = {
        "stage": "V80.01",
        "status": "PASS",
        "mode": config.mode,
        "broker_name": config.broker_name,
        "environment": "PAPER_ONLY",
        "capabilities": {
            "historical_data_read": True,
            "offline_signal_read": True,
            "offline_order_intent_build": True,
            "broker_network_connect": False,
            "credential_load": False,
            "account_query": False,
            "positions_query": False,
            "order_submit": False,
            "order_cancel": False,
            "live_trading": False,
        },
        "actual_orders_submitted": 0,
    }
    policy["policy_sha256"] = sha256_json(policy)
    return policy

def build_capability_probe(policy: dict[str, Any]) -> dict[str, Any]:
    capabilities = policy["capabilities"]
    forbidden = [
        name for name, enabled in capabilities.items()
        if name in {
            "broker_network_connect", "credential_load", "account_query",
            "positions_query", "order_submit", "order_cancel", "live_trading",
        } and enabled
    ]
    result = {
        "stage": "V80.02",
        "status": "PASS" if not forbidden else "FAIL",
        "adapter_kind": "NO_NETWORK_PAPER_CAPABILITY_PROBE",
        "broker_name": policy["broker_name"],
        "forbidden_capability_count": len(forbidden),
        "forbidden_capabilities": forbidden,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    result["probe_sha256"] = sha256_json(result)
    return result

def build_order_intent(
    symbol: str,
    side: str,
    quantity: int,
    reference_price: float,
) -> dict[str, Any]:
    normalized_symbol = symbol.strip().upper()
    normalized_side = side.strip().upper()
    if not normalized_symbol or not normalized_symbol.replace(".", "").isalnum():
        raise ValueError("invalid symbol")
    if normalized_side not in {"BUY", "SELL"}:
        raise ValueError("invalid side")
    if quantity < 1:
        raise ValueError("quantity must be positive")
    if reference_price <= 0:
        raise ValueError("reference price must be positive")
    intent = {
        "schema_version": "v80.03.paper_order_intent.1",
        "stage": "V80.03",
        "symbol": normalized_symbol,
        "side": normalized_side,
        "quantity": quantity,
        "reference_price": float(reference_price),
        "time_in_force": "DAY",
        "order_type": "MARKET",
        "execution_mode": "DRY_RUN_NO_NETWORK",
        "broker_submission_authorized": False,
        "status": "VALIDATED_NOT_SUBMITTED",
        "actual_orders_submitted": 0,
    }
    intent["intent_sha256"] = sha256_json(intent)
    return intent

class NoNetworkPaperAdapter:
    adapter_kind = "NO_NETWORK_PAPER_ADAPTER"

    def __init__(self, policy: dict[str, Any]) -> None:
        if policy.get("mode") != "DRY_RUN_NO_NETWORK":
            raise ValueError("invalid policy mode")
        self.policy = policy
        self.network_requests_executed = 0
        self.credentials_used = 0
        self.trading_client_created = False
        self.actual_orders_submitted = 0

    def validate_intent(self, intent: dict[str, Any]) -> dict[str, Any]:
        unsigned = dict(intent)
        expected = unsigned.pop("intent_sha256", None)
        if expected != sha256_json(unsigned):
            raise ValueError("order intent hash mismatch")
        if intent.get("broker_submission_authorized") is not False:
            raise ValueError("broker submission must remain unauthorized")
        if intent.get("execution_mode") != "DRY_RUN_NO_NETWORK":
            raise ValueError("invalid execution mode")
        receipt = {
            "stage": "V80.03",
            "status": "ACCEPTED_DRY_RUN",
            "adapter_kind": self.adapter_kind,
            "intent_sha256": intent["intent_sha256"],
            "symbol": intent["symbol"],
            "side": intent["side"],
            "quantity": intent["quantity"],
            "broker_order_id": None,
            "network_requests_executed": self.network_requests_executed,
            "credentials_used": self.credentials_used,
            "trading_client_created": self.trading_client_created,
            "actual_orders_submitted": self.actual_orders_submitted,
        }
        receipt["receipt_sha256"] = sha256_json(receipt)
        return receipt

def build_readiness_assessment(
    historical_certificate: dict[str, Any],
    policy: dict[str, Any],
    probe: dict[str, Any],
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    checks = {
        "historical_engine_complete": historical_certificate[
            "completion_summary"
        ]["historical_engine_complete"] is True,
        "paper_only_environment": policy["environment"] == "PAPER_ONLY",
        "dry_run_mode": policy["mode"] == "DRY_RUN_NO_NETWORK",
        "capability_probe_pass": probe["status"] == "PASS",
        "forbidden_capabilities_zero": probe["forbidden_capability_count"] == 0,
        "receipt_count_positive": len(receipts) > 0,
        "all_receipts_dry_run": all(
            receipt["status"] == "ACCEPTED_DRY_RUN" for receipt in receipts
        ),
        "network_requests_zero": probe["network_requests_executed"] == 0,
        "credentials_unused": probe["credentials_used"] == 0,
        "trading_client_not_created": probe["trading_client_created"] is False,
        "actual_orders_zero": probe["actual_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    assessment = {
        "stage": "V80.04",
        "status": "PASS" if not failed else "FAIL",
        "readiness_level": "FOUNDATION_READY_NO_BROKER_CONNECTION",
        "checks": checks,
        "failed_checks": failed,
        "intent_receipt_count": len(receipts),
        "paper_trading_authorized": False,
        "broker_connection_authorized": False,
        "live_trading_authorized": False,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    assessment["assessment_sha256"] = sha256_json(assessment)
    return assessment

def store_readiness_package(
    output_dir: Path,
    policy: dict[str, Any],
    probe: dict[str, Any],
    receipts: list[dict[str, Any]],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    package_seed = {
        "policy_sha256": policy["policy_sha256"],
        "probe_sha256": probe["probe_sha256"],
        "assessment_sha256": assessment["assessment_sha256"],
    }
    package_id = f"paper-readiness-{sha256_json(package_seed)[:20]}"
    package_dir = output_dir / "package" / package_id
    policy_path = output_dir / "paper_trading_readiness_policy_v80_01.json"
    probe_path = output_dir / "paper_trading_capability_probe_v80_02.json"
    receipts_path = package_dir / "dry_run_order_intent_receipts.json"
    assessment_path = package_dir / "paper_trading_readiness_assessment.json"

    write_json(policy_path, policy)
    write_json(probe_path, probe)
    receipts_document = {
        "stage": "V80.03",
        "status": "PASS",
        "receipt_count": len(receipts),
        "receipts": receipts,
    }
    receipts_document["receipts_sha256"] = sha256_json(receipts_document)
    receipts_bytes = (
        json.dumps(receipts_document, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    created = not receipts_path.exists()
    if receipts_path.exists() and receipts_path.read_bytes() != receipts_bytes:
        raise ValueError("readiness package conflict")
    if created:
        atomic_write(receipts_path, receipts_bytes)
    write_json(assessment_path, assessment)

    ledger = {
        "stage": "V80.04",
        "status": assessment["status"],
        "package_id": package_id,
        "package_created": created,
        "package_reused": not created,
        "policy_sha256": policy["policy_sha256"],
        "probe_sha256": probe["probe_sha256"],
        "assessment_sha256": assessment["assessment_sha256"],
        "receipt_count": len(receipts),
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    ledger["ledger_sha256"] = sha256_json(ledger)
    ledger_path = output_dir / "paper_trading_readiness_ledger_v80_04.json"
    write_json(ledger_path, ledger)

    manifest = {
        "stage": "V80.04",
        "status": assessment["status"],
        "package_id": package_id,
        "files": {},
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    for name, path in (
        ("policy", policy_path),
        ("probe", probe_path),
        ("receipts", receipts_path),
        ("assessment", assessment_path),
        ("ledger", ledger_path),
    ):
        data = path.read_bytes()
        manifest["files"][name] = {
            "relative_path": str(path.relative_to(output_dir)).replace("\\", "/"),
            "sha256": sha256_bytes(data),
            "byte_size": len(data),
        }
    manifest["manifest_sha256"] = sha256_json(manifest)
    write_json(output_dir / "paper_trading_readiness_manifest_v80_04.json", manifest)
    return {
        "package_id": package_id,
        "created": created,
        "reused_existing_package": not created,
        "ledger": ledger,
        "manifest": manifest,
    }

def verify_readiness_manifest(output_dir: Path, manifest: dict[str, Any]) -> bool:
    unsigned = dict(manifest)
    expected = unsigned.pop("manifest_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError("readiness manifest hash mismatch")
    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        data = path.read_bytes()
        if (
            sha256_bytes(data) != info["sha256"]
            or len(data) != info["byte_size"]
        ):
            raise ValueError("readiness output tamper detected")
    return True

def run_paper_readiness(
    repository_root: Path,
    config: PaperReadinessConfig,
    output_dir: Path,
) -> dict[str, Any]:
    historical_path = (
        repository_root
        / "release/v80_00/output/historical_backtest_completion_certificate_v79_99.json"
    )
    historical_certificate = validate_historical_completion_certificate(
        historical_path
    )
    policy = build_paper_policy(config)
    probe = build_capability_probe(policy)
    adapter = NoNetworkPaperAdapter(policy)
    intents = [
        build_order_intent("AAPL", "BUY", 1, 100.0),
        build_order_intent("AAPL", "SELL", 1, 101.0),
    ]
    receipts = [adapter.validate_intent(intent) for intent in intents]
    assessment = build_readiness_assessment(
        historical_certificate, policy, probe, receipts
    )
    stored = store_readiness_package(
        output_dir, policy, probe, receipts, assessment
    )
    verify_readiness_manifest(output_dir, stored["manifest"])
    return {
        "stage": "V80.04",
        "status": "PASS",
        "policy": policy,
        "probe": probe,
        "assessment": assessment,
        "receipts": receipts,
        **stored,
        "historical_certificate_preserved": historical_path.is_file(),
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }

def build_paper_readiness_certificate(
    repository_root: Path,
    output_dir: Path,
    config: PaperReadinessConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "historical_completion_present": (
            repository_root
            / "release/v80_00/output/historical_backtest_completion_certificate_v79_99.json"
        ).is_file(),
        "pipeline_status_pass": result["status"] == "PASS",
        "assessment_status_pass": result["assessment"]["status"] == "PASS",
        "dry_run_mode": result["policy"]["mode"] == "DRY_RUN_NO_NETWORK",
        "forbidden_capabilities_zero": (
            result["probe"]["forbidden_capability_count"] == 0
        ),
        "historical_certificate_preserved": (
            result["historical_certificate_preserved"] is True
        ),
        "manifest_hash_present": len(
            result["manifest"].get("manifest_sha256", "")
        ) == 64,
        "network_requests_zero": result["network_requests_executed"] == 0,
        "credentials_unused": result["credentials_used"] == 0,
        "trading_client_not_created": (
            result["trading_client_created"] is False
        ),
        "actual_orders_zero": result["actual_orders_submitted"] == 0,
        "paper_trading_not_authorized": (
            result["assessment"]["paper_trading_authorized"] is False
        ),
        "live_trading_not_authorized": (
            result["assessment"]["live_trading_authorized"] is False
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    certificate = {
        "stage": "V80.05",
        "status": status,
        "scope": "PAPER_TRADING_READINESS_FOUNDATION_NO_NETWORK",
        "stages_completed": [
            "V80.01", "V80.02", "V80.03", "V80.04", "V80.05"
        ],
        "passed_stage_count": 5 if status == "PASS" else max(0, 5 - len(failed)),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "readiness_summary": {
            "package_id": result["package_id"],
            "readiness_level": result["assessment"]["readiness_level"],
            "intent_receipt_count": result["assessment"]["intent_receipt_count"],
            "forbidden_capability_count": result["probe"][
                "forbidden_capability_count"
            ],
            "package_created": result["created"],
            "package_reused": result["reused_existing_package"],
            "historical_certificate_preserved": result[
                "historical_certificate_preserved"
            ],
        },
        "readiness_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "next_phase": "V80_06_PAPER_SESSION_CONFIGURATION",
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    certificate_path = (
        output_dir / "paper_trading_readiness_certificate_v80_05.json"
    )
    write_json(certificate_path, certificate)
    write_json(
        output_dir / "paper_trading_readiness_verify_v80_05.json",
        {
            "stage": "V80.05",
            "status": status,
            "verified": not failed,
            "certificate_sha256": certificate["certificate_sha256"],
            "certificate_path": str(
                certificate_path.relative_to(repository_root)
            ).replace("\\", "/"),
            "failed_checks": failed,
            "next_phase": certificate["next_phase"],
        },
    )
    return certificate

sha256_paper_readiness_json = sha256_json
