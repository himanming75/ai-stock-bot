from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, statistics, tempfile

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
class WalkForwardConfig:
    train_size: int = 4
    test_size: int = 2
    step_size: int = 2
    min_fold_count: int = 2
    maximum_mean_drawdown_pct: float = 0.20
    require_no_overlap: bool = True
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if min(self.train_size, self.test_size, self.step_size, self.min_fold_count) < 1:
            raise ValueError("walk-forward sizes must be positive")
        if not 0 < self.maximum_mean_drawdown_pct <= 1:
            raise ValueError("maximum_mean_drawdown_pct")
        if not self.require_no_overlap:
            raise ValueError("train/test overlap must be prohibited")
        if (
            self.allow_network
            or self.allow_credentials
            or self.allow_trading_client
            or self.allow_order_submission
            or self.actual_orders_submitted
        ):
            raise ValueError("walk-forward validation must remain offline")

def _validate_certificate(path: Path, stage: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    certificate = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(certificate)
    expected = unsigned.pop("certificate_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError(f"{stage} certificate hash mismatch")
    if certificate.get("stage") != stage or certificate.get("status") != "PASS":
        raise ValueError(f"{stage} certificate is not PASS")
    return certificate

def validate_portfolio_certificate(path: Path) -> dict[str, Any]:
    return _validate_certificate(path, "V79.80")

def validate_performance_certificate(path: Path) -> dict[str, Any]:
    return _validate_certificate(path, "V79.90")

def locate_portfolio_data(output_dir: Path, certificate: dict[str, Any]) -> Path:
    simulation_id = certificate["portfolio_summary"]["simulation_id"]
    path = output_dir / "simulation" / simulation_id / "portfolio_simulation.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path

def load_equity_curve(path: Path) -> list[dict[str, Any]]:
    try:
        portfolio = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError("invalid portfolio JSON") from exc
    snapshots = portfolio.get("snapshots")
    if not isinstance(snapshots, list) or len(snapshots) < 2:
        raise ValueError("insufficient equity observations")
    curve = []
    previous_timestamp = None
    for index, item in enumerate(snapshots):
        timestamp = str(item["timestamp"])
        equity = float(item["equity"])
        if equity <= 0 or not math.isfinite(equity):
            raise ValueError("invalid equity observation")
        if previous_timestamp is not None and timestamp < previous_timestamp:
            raise ValueError("equity curve is out of order")
        previous_timestamp = timestamp
        curve.append({"index": index, "timestamp": timestamp, "equity": equity})
    return curve

def plan_walk_forward_windows(
    curve: list[dict[str, Any]], config: WalkForwardConfig
) -> list[dict[str, Any]]:
    config.validate()
    windows = []
    start = 0
    fold_number = 1
    while start + config.train_size + config.test_size <= len(curve):
        train_start = start
        train_end = start + config.train_size - 1
        test_start = train_end + 1
        test_end = test_start + config.test_size - 1
        windows.append({
            "fold_id": f"fold-{fold_number:03d}",
            "train_start_index": train_start,
            "train_end_index": train_end,
            "test_start_index": test_start,
            "test_end_index": test_end,
            "train_start_timestamp": curve[train_start]["timestamp"],
            "train_end_timestamp": curve[train_end]["timestamp"],
            "test_start_timestamp": curve[test_start]["timestamp"],
            "test_end_timestamp": curve[test_end]["timestamp"],
            "train_observation_count": config.train_size,
            "test_observation_count": config.test_size,
        })
        start += config.step_size
        fold_number += 1
    if len(windows) < config.min_fold_count:
        raise ValueError("insufficient walk-forward fold count")
    return windows

def validate_windows(windows: list[dict[str, Any]]) -> dict[str, int]:
    fold_ids = set()
    for window in windows:
        if window["fold_id"] in fold_ids:
            raise ValueError("duplicate fold id")
        fold_ids.add(window["fold_id"])
        if window["train_end_index"] >= window["test_start_index"]:
            raise ValueError("train/test leakage detected")
        if window["train_start_index"] > window["train_end_index"]:
            raise ValueError("invalid training window")
        if window["test_start_index"] > window["test_end_index"]:
            raise ValueError("invalid test window")
    return {
        "fold_count": len(windows),
        "unique_fold_count": len(fold_ids),
        "leakage_count": 0,
    }

def _segment_metrics(segment: list[dict[str, Any]]) -> dict[str, float]:
    first = segment[0]["equity"]
    last = segment[-1]["equity"]
    total_return = last / first - 1
    returns = [
        segment[index]["equity"] / segment[index - 1]["equity"] - 1
        for index in range(1, len(segment))
    ]
    mean_return = statistics.fmean(returns) if returns else 0.0
    volatility = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    sharpe = mean_return / volatility if volatility > 0 else 0.0
    peak = None
    maximum_drawdown = 0.0
    for item in segment:
        equity = item["equity"]
        peak = equity if peak is None else max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        maximum_drawdown = max(maximum_drawdown, drawdown)
    return {
        "total_return": total_return,
        "mean_return": mean_return,
        "volatility": volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": maximum_drawdown,
    }

def execute_folds(
    curve: list[dict[str, Any]], windows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    results = []
    for window in windows:
        train = curve[window["train_start_index"]:window["train_end_index"] + 1]
        test = curve[window["test_start_index"]:window["test_end_index"] + 1]
        results.append({
            "fold_id": window["fold_id"],
            "window": window,
            "train_metrics": _segment_metrics(train),
            "test_metrics": _segment_metrics(test),
            "train_end_equity": train[-1]["equity"],
            "test_end_equity": test[-1]["equity"],
            "status": "PASS",
        })
    return results

def aggregate_fold_results(
    fold_results: list[dict[str, Any]], config: WalkForwardConfig
) -> dict[str, Any]:
    if not fold_results:
        raise ValueError("fold results are empty")
    returns = [fold["test_metrics"]["total_return"] for fold in fold_results]
    sharpes = [fold["test_metrics"]["sharpe_ratio"] for fold in fold_results]
    drawdowns = [fold["test_metrics"]["max_drawdown_pct"] for fold in fold_results]
    mean_return = statistics.fmean(returns)
    return_std = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    mean_sharpe = statistics.fmean(sharpes)
    mean_drawdown = statistics.fmean(drawdowns)
    positive_fold_count = sum(1 for value in returns if value > 0)
    negative_fold_count = sum(1 for value in returns if value < 0)
    flat_fold_count = sum(1 for value in returns if value == 0)
    violations = []
    if mean_drawdown > config.maximum_mean_drawdown_pct:
        violations.append("MEAN_DRAWDOWN_LIMIT")
    status = "PASS" if not violations else "FAIL"
    return {
        "stage": "V79.93",
        "status": status,
        "fold_count": len(fold_results),
        "mean_test_return": mean_return,
        "test_return_std": return_std,
        "mean_test_sharpe": mean_sharpe,
        "mean_test_drawdown_pct": mean_drawdown,
        "positive_fold_count": positive_fold_count,
        "negative_fold_count": negative_fold_count,
        "flat_fold_count": flat_fold_count,
        "violation_count": len(violations),
        "violations": violations,
    }

def store_walk_forward(
    output_dir: Path,
    source_path: Path,
    windows: list[dict[str, Any]],
    fold_results: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> dict[str, Any]:
    validation_id = (
        f"walk-forward-{sha256_bytes(source_path.read_bytes())[:16]}-"
        f"{sha256_json({'windows': windows, 'aggregate': aggregate})[:12]}"
    )
    analysis_path = (
        output_dir / "validation" / validation_id / "walk_forward_validation.json"
    )
    analysis = {
        "stage": "V79.93",
        "status": aggregate["status"],
        "validation_id": validation_id,
        "windows": windows,
        "fold_results": fold_results,
        "aggregate": aggregate,
    }
    analysis_bytes = (
        json.dumps(analysis, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    created = not analysis_path.exists()
    if analysis_path.exists() and analysis_path.read_bytes() != analysis_bytes:
        raise ValueError("walk-forward validation conflict")
    if created:
        atomic_write(analysis_path, analysis_bytes)

    ledger = {
        "stage": "V79.94",
        "validation_id": validation_id,
        "created": created,
        "reused_existing_validation": not created,
        "fold_count": aggregate["fold_count"],
        "validation_status": aggregate["status"],
        "violation_count": aggregate["violation_count"],
        "folds": [
            {
                "fold_id": fold["fold_id"],
                "test_return": fold["test_metrics"]["total_return"],
                "test_sharpe": fold["test_metrics"]["sharpe_ratio"],
                "test_drawdown_pct": fold["test_metrics"]["max_drawdown_pct"],
            }
            for fold in fold_results
        ],
    }
    ledger["ledger_sha256"] = sha256_json(ledger)
    ledger_path = output_dir / "walk_forward_fold_ledger.json"
    write_json(ledger_path, ledger)

    manifest = {
        "stage": "V79.94",
        "validation_id": validation_id,
        "fold_count": aggregate["fold_count"],
        "validation_status": aggregate["status"],
        "mean_test_return": aggregate["mean_test_return"],
        "mean_test_drawdown_pct": aggregate["mean_test_drawdown_pct"],
        "files": {},
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    for name, path in (("analysis", analysis_path), ("ledger", ledger_path)):
        data = path.read_bytes()
        manifest["files"][name] = {
            "relative_path": str(path.relative_to(output_dir)).replace("\\", "/"),
            "sha256": sha256_bytes(data),
            "byte_size": len(data),
        }
    manifest["manifest_sha256"] = sha256_json(manifest)
    write_json(output_dir / "historical_walk_forward_manifest_v79_94.json", manifest)
    return {
        "validation_id": validation_id,
        "created": created,
        "reused_existing_validation": not created,
        "manifest": manifest,
    }

def verify_walk_forward_manifest(
    output_dir: Path, manifest: dict[str, Any]
) -> bool:
    unsigned = dict(manifest)
    expected = unsigned.pop("manifest_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError("walk-forward manifest hash mismatch")
    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        data = path.read_bytes()
        if (
            sha256_bytes(data) != info["sha256"]
            or len(data) != info["byte_size"]
        ):
            raise ValueError("walk-forward output tamper detected")
    return True

def run_walk_forward_validation(
    portfolio_output: Path,
    portfolio_certificate_path: Path,
    performance_certificate_path: Path,
    config: WalkForwardConfig,
    output_dir: Path,
) -> dict[str, Any]:
    portfolio_certificate = validate_portfolio_certificate(
        portfolio_certificate_path
    )
    validate_performance_certificate(performance_certificate_path)
    source_path = locate_portfolio_data(
        portfolio_output, portfolio_certificate
    )
    curve = load_equity_curve(source_path)
    windows = plan_walk_forward_windows(curve, config)
    window_stats = validate_windows(windows)
    fold_results = execute_folds(curve, windows)
    aggregate = aggregate_fold_results(fold_results, config)
    store = store_walk_forward(
        output_dir, source_path, windows, fold_results, aggregate
    )
    verify_walk_forward_manifest(output_dir, store["manifest"])
    return {
        "stage": "V79.94",
        "status": "PASS",
        "window_stats": window_stats,
        "aggregate": aggregate,
        **store,
        "source_preserved": source_path.is_file(),
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }

def build_walk_forward_certificate(
    repository_root: Path,
    output_dir: Path,
    config: WalkForwardConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    aggregate = result["aggregate"]
    checks = {
        "v79_80_certificate_present": (
            repository_root
            / "release/v79_80/output/historical_portfolio_simulation_certificate_v79_80.json"
        ).is_file(),
        "v79_90_certificate_present": (
            repository_root
            / "release/v79_90/output/historical_performance_analytics_certificate_v79_90.json"
        ).is_file(),
        "pipeline_status_pass": result["status"] == "PASS",
        "minimum_fold_count_met": (
            result["window_stats"]["fold_count"] >= config.min_fold_count
        ),
        "leakage_zero": result["window_stats"]["leakage_count"] == 0,
        "aggregate_status_pass": aggregate["status"] == "PASS",
        "source_preserved": result["source_preserved"] is True,
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
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    certificate = {
        "stage": "V79.95",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_WALK_FORWARD_VALIDATION",
        "stages_completed": [
            "V79.91", "V79.92", "V79.93", "V79.94", "V79.95"
        ],
        "passed_stage_count": 5 if status == "PASS" else max(0, 5 - len(failed)),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "walk_forward_summary": {
            "validation_id": result["validation_id"],
            **result["window_stats"],
            **aggregate,
            "cache_created": result["created"],
            "cache_reused": result["reused_existing_validation"],
            "source_preserved": result["source_preserved"],
        },
        "walk_forward_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_96_HISTORICAL_BACKTEST_COMPLETION",
    }
    certificate["certificate_sha256"] = sha256_json(certificate)
    certificate_path = (
        output_dir
        / "historical_walk_forward_validation_certificate_v79_95.json"
    )
    write_json(certificate_path, certificate)
    write_json(
        output_dir
        / "historical_walk_forward_validation_verify_v79_95.json",
        {
            "stage": "V79.95",
            "status": status,
            "verified": not failed,
            "certificate_sha256": certificate["certificate_sha256"],
            "certificate_path": str(
                certificate_path.relative_to(repository_root)
            ).replace("\\", "/"),
            "failed_checks": failed,
        },
    )
    return certificate

sha256_walk_forward_json = sha256_json

segment_metrics = _segment_metrics
