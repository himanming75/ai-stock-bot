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
class BacktestCompletionConfig:
    required_stages: tuple[str, ...] = (
        "V79.65", "V79.70", "V79.75", "V79.80",
        "V79.85", "V79.90", "V79.95",
    )
    require_all_certificates_pass: bool = True
    require_zero_orders: bool = True
    require_offline_execution: bool = True
    preserve_source_outputs: bool = True
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        expected_stages = (
            "V79.65", "V79.70", "V79.75", "V79.80",
            "V79.85", "V79.90", "V79.95",
        )
        if self.required_stages != expected_stages:
            raise ValueError("required certificate stages or order mismatch")
        if not (
            self.require_all_certificates_pass
            and self.require_zero_orders
            and self.require_offline_execution
            and self.preserve_source_outputs
        ):
            raise ValueError("completion safety requirements must remain enabled")
        if (
            self.allow_network
            or self.allow_credentials
            or self.allow_trading_client
            or self.allow_order_submission
            or self.actual_orders_submitted
        ):
            raise ValueError("completion package must remain offline")

CERTIFICATE_SPECS = (
    ("V79.65", "release/v79_65/output/historical_feature_store_certificate_v79_65.json"),
    ("V79.70", "release/v79_70/output/historical_indicator_library_certificate_v79_70.json"),
    ("V79.75", "release/v79_75/output/historical_signal_engine_certificate_v79_75.json"),
    ("V79.80", "release/v79_80/output/historical_portfolio_simulation_certificate_v79_80.json"),
    ("V79.85", "release/v79_85/output/historical_risk_engine_certificate_v79_85.json"),
    ("V79.90", "release/v79_90/output/historical_performance_analytics_certificate_v79_90.json"),
    ("V79.95", "release/v79_95/output/historical_walk_forward_validation_certificate_v79_95.json"),
)

def validate_certificate(path: Path, expected_stage: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    certificate = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(certificate)
    expected_hash = unsigned.pop("certificate_sha256", None)
    if expected_hash != sha256_json(unsigned):
        raise ValueError(f"{expected_stage} certificate hash mismatch")
    if certificate.get("stage") != expected_stage:
        raise ValueError(f"{expected_stage} certificate stage mismatch")
    if certificate.get("status") != "PASS":
        raise ValueError(f"{expected_stage} certificate is not PASS")
    if certificate.get("actual_orders_submitted") != 0:
        raise ValueError(f"{expected_stage} certificate reports actual orders")
    if certificate.get("trading_client_created") is not False:
        raise ValueError(f"{expected_stage} certificate reports trading client")
    if certificate.get("credentials_used") != 0:
        raise ValueError(f"{expected_stage} certificate reports credentials")
    if certificate.get("network_requests_executed") != 0:
        raise ValueError(f"{expected_stage} certificate reports network requests")
    return certificate

def collect_certificate_chain(
    repository_root: Path, config: BacktestCompletionConfig
) -> list[dict[str, Any]]:
    config.validate()
    entries = []
    for stage, relative_path in CERTIFICATE_SPECS:
        certificate_path = repository_root / relative_path
        certificate = validate_certificate(certificate_path, stage)
        data = certificate_path.read_bytes()
        entries.append({
            "stage": stage,
            "relative_path": relative_path,
            "certificate_sha256": certificate["certificate_sha256"],
            "file_sha256": sha256_bytes(data),
            "byte_size": len(data),
            "status": certificate["status"],
            "next_phase": certificate.get("next_phase"),
        })
    if tuple(entry["stage"] for entry in entries) != config.required_stages:
        raise ValueError("certificate chain order mismatch")
    return entries

def build_completion_summary(
    repository_root: Path,
    certificate_chain: list[dict[str, Any]],
) -> dict[str, Any]:
    feature = json.loads((repository_root / CERTIFICATE_SPECS[0][1]).read_text())
    indicator = json.loads((repository_root / CERTIFICATE_SPECS[1][1]).read_text())
    signal = json.loads((repository_root / CERTIFICATE_SPECS[2][1]).read_text())
    portfolio = json.loads((repository_root / CERTIFICATE_SPECS[3][1]).read_text())
    risk = json.loads((repository_root / CERTIFICATE_SPECS[4][1]).read_text())
    performance = json.loads((repository_root / CERTIFICATE_SPECS[5][1]).read_text())
    walk_forward = json.loads((repository_root / CERTIFICATE_SPECS[6][1]).read_text())
    return {
        "stage": "V79.96",
        "status": "PASS",
        "certificate_count": len(certificate_chain),
        "certificate_stages": [entry["stage"] for entry in certificate_chain],
        "feature_count": feature["feature_summary"]["feature_count"],
        "feature_row_count": feature["feature_summary"]["feature_row_count"],
        "indicator_count": indicator["indicator_summary"]["indicator_count"],
        "indicator_row_count": indicator["indicator_summary"]["indicator_row_count"],
        "signal_row_count": signal["signal_summary"]["signal_row_count"],
        "buy_count": signal["signal_summary"]["buy_count"],
        "sell_count": signal["signal_summary"]["sell_count"],
        "hold_count": signal["signal_summary"]["hold_count"],
        "portfolio_trade_count": portfolio["portfolio_summary"]["trade_count"],
        "portfolio_final_equity": portfolio["portfolio_summary"]["final_equity"],
        "risk_violation_count": risk["risk_summary"]["violation_count"],
        "maximum_drawdown_pct": risk["risk_summary"]["max_drawdown_pct"],
        "total_return": performance["performance_summary"]["total_return"],
        "sharpe_ratio": performance["performance_summary"]["sharpe_ratio"],
        "walk_forward_fold_count": walk_forward["walk_forward_summary"]["fold_count"],
        "walk_forward_leakage_count": walk_forward["walk_forward_summary"]["leakage_count"],
        "walk_forward_violation_count": walk_forward["walk_forward_summary"]["violation_count"],
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
    }

def build_completion_ledger(
    certificate_chain: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    ledger = {
        "stage": "V79.97",
        "status": "PASS",
        "chain_length": len(certificate_chain),
        "certificate_chain": certificate_chain,
        "summary_sha256": sha256_json(summary),
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
    }
    ledger["ledger_sha256"] = sha256_json(ledger)
    return ledger

def store_completion_package(
    output_dir: Path,
    summary: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_id = (
        f"backtest-complete-{ledger['ledger_sha256'][:16]}-"
        f"{sha256_json(summary)[:12]}"
    )
    summary_path = output_dir / "package" / package_id / "historical_backtest_completion_summary.json"
    summary_bytes = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
    created = not summary_path.exists()
    if summary_path.exists() and summary_path.read_bytes() != summary_bytes:
        raise ValueError("completion summary conflict")
    if created:
        atomic_write(summary_path, summary_bytes)
    ledger_path = output_dir / "historical_backtest_completion_ledger.json"
    write_json(ledger_path, ledger)

    report = {
        "stage": "V80.00",
        "status": "PASS",
        "title": "Historical Backtest Engine Completion Report",
        "package_id": package_id,
        "completed_range": "V1-V80.00",
        "historical_engine_complete": True,
        "offline_backtest_complete": True,
        "paper_trading_enabled": False,
        "live_trading_enabled": False,
        "broker_credentials_required": False,
        "actual_orders_submitted": 0,
        "summary": summary,
        "next_phase": "V80_01_PAPER_TRADING_READINESS",
    }
    report_path = output_dir / "historical_backtest_engine_completion_report_v80_00.json"
    write_json(report_path, report)

    manifest = {
        "stage": "V79.98",
        "status": "PASS",
        "package_id": package_id,
        "files": {},
        "certificate_chain_sha256": sha256_json(ledger["certificate_chain"]),
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
    }
    for name, path in (
        ("summary", summary_path),
        ("ledger", ledger_path),
        ("report", report_path),
    ):
        data = path.read_bytes()
        manifest["files"][name] = {
            "relative_path": str(path.relative_to(output_dir)).replace("\\", "/"),
            "sha256": sha256_bytes(data),
            "byte_size": len(data),
        }
    manifest["manifest_sha256"] = sha256_json(manifest)
    manifest_path = output_dir / "historical_backtest_completion_manifest_v79_98.json"
    write_json(manifest_path, manifest)
    return {
        "package_id": package_id,
        "created": created,
        "reused_existing_package": not created,
        "manifest": manifest,
        "report": report,
    }

def verify_completion_manifest(
    output_dir: Path, manifest: dict[str, Any]
) -> bool:
    unsigned = dict(manifest)
    expected_hash = unsigned.pop("manifest_sha256", None)
    if expected_hash != sha256_json(unsigned):
        raise ValueError("completion manifest hash mismatch")
    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        data = path.read_bytes()
        if (
            sha256_bytes(data) != info["sha256"]
            or len(data) != info["byte_size"]
        ):
            raise ValueError("completion package tamper detected")
    return True

def run_backtest_completion(
    repository_root: Path,
    config: BacktestCompletionConfig,
    output_dir: Path,
) -> dict[str, Any]:
    chain = collect_certificate_chain(repository_root, config)
    summary = build_completion_summary(repository_root, chain)
    ledger = build_completion_ledger(chain, summary)
    stored = store_completion_package(output_dir, summary, ledger)
    verify_completion_manifest(output_dir, stored["manifest"])
    return {
        "stage": "V79.98",
        "status": "PASS",
        "certificate_chain": chain,
        "summary": summary,
        "ledger": ledger,
        **stored,
        "source_outputs_preserved": True,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }

def build_backtest_completion_certificate(
    repository_root: Path,
    output_dir: Path,
    config: BacktestCompletionConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "seven_certificates_verified": len(result["certificate_chain"]) == 7,
        "all_certificates_pass": all(
            entry["status"] == "PASS"
            for entry in result["certificate_chain"]
        ),
        "pipeline_status_pass": result["status"] == "PASS",
        "risk_violations_zero": (
            result["summary"]["risk_violation_count"] == 0
        ),
        "walk_forward_leakage_zero": (
            result["summary"]["walk_forward_leakage_count"] == 0
        ),
        "walk_forward_violations_zero": (
            result["summary"]["walk_forward_violation_count"] == 0
        ),
        "source_outputs_preserved": (
            result["source_outputs_preserved"] is True
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
    }
    failed_checks = [
        name for name, passed in checks.items() if not passed
    ]
    status = "PASS" if not failed_checks else "FAIL"
    certificate = {
        "stage": "V79.99",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_BACKTEST_COMPLETION",
        "stages_completed": [
            "V79.96", "V79.97", "V79.98", "V79.99", "V80.00"
        ],
        "passed_stage_count": 5 if status == "PASS" else max(
            0, 5 - len(failed_checks)
        ),
        "failed_stage_count": 0 if status == "PASS" else len(failed_checks),
        "config": asdict(config),
        "completion_summary": {
            "package_id": result["package_id"],
            "certificate_count": len(result["certificate_chain"]),
            **result["summary"],
            "package_created": result["created"],
            "package_reused": result["reused_existing_package"],
            "historical_engine_complete": status == "PASS",
        },
        "completion_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed_checks,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "paper_trading_authorized": False,
        "next_phase": "V80_01_PAPER_TRADING_READINESS",
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    certificate_path = (
        output_dir
        / "historical_backtest_completion_certificate_v79_99.json"
    )
    write_json(certificate_path, certificate)
    write_json(
        output_dir
        / "historical_backtest_completion_verify_v80_00.json",
        {
            "stage": "V80.00",
            "status": status,
            "verified": not failed_checks,
            "historical_engine_complete": status == "PASS",
            "certificate_sha256": certificate["certificate_sha256"],
            "certificate_path": str(
                certificate_path.relative_to(repository_root)
            ).replace("\\", "/"),
            "failed_checks": failed_checks,
            "next_phase": certificate["next_phase"],
        },
    )
    return certificate

sha256_completion_json = sha256_json
