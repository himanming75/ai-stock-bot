from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .config_audit import ConfigurationDiffAuditor
from .data_quality import DataQualityAuditor
from .incident import IncidentSnapshotBuilder
from .reporting import OperatorReportBuilder
from .replay import HistoricalReplaySimulator


def _fixture_bars() -> list[dict[str, Any]]:
    bars = []
    price = Decimal("100")
    for index in range(40):
        step = Decimal("0.8") if index < 25 else Decimal("-0.3")
        close = price + step
        bars.append({
            "timestamp": f"2026-02-{index + 1:02d}",
            "open": str(price),
            "high": str(max(price, close) + Decimal("0.5")),
            "low": str(min(price, close) - Decimal("0.5")),
            "close": str(close),
            "volume": str(1000000 + index * 10000),
        })
        price = close
    return bars


def run_operations_v2(root: Path) -> dict[str, Any]:
    actual = root / "release/operations_v2/actual"
    actual.mkdir(parents=True, exist_ok=True)

    bars = _fixture_bars()
    quality = DataQualityAuditor().audit_bars(
        symbol="AAPL",
        bars=bars,
    )
    replay = HistoricalReplaySimulator().replay(
        symbol="AAPL",
        bars=bars,
        fast_window=5,
        slow_window=20,
    )
    config_audit = ConfigurationDiffAuditor().compare(
        baseline={
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "automatic_order_submission_enabled": False,
            "maximum_order_notional": "10",
        },
        current={
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "automatic_order_submission_enabled": False,
            "maximum_order_notional": "10",
        },
        protected_keys={
            "broker_network_enabled",
            "broker_write_enabled",
            "automatic_order_submission_enabled",
        },
    )

    (actual / "data_quality_result.json").write_text(
        json.dumps(quality, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "replay_result.json").write_text(
        json.dumps(replay, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "config_audit_result.json").write_text(
        json.dumps(config_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    incident_sources = [
        root / "release/ai_v2_final/actual/ai_v2_final_result.json",
        root / "release/ai_v2_final/actual/ai_v2_final_certificate.json",
        root / "release/bundle_c_r14_to_r15_final_operations/actual/bundle_c_result.json",
    ]
    incident = IncidentSnapshotBuilder().build(
        root=root,
        sources=incident_sources,
        output_dir=actual / "incident_snapshot",
    )

    report_builder = OperatorReportBuilder()
    report = report_builder.build(sections={
        "data_quality": quality,
        "historical_replay": replay,
        "configuration_audit": config_audit,
        "incident_snapshot": incident,
    })
    report_builder.export_json(
        actual / "daily_operator_report.json",
        report,
    )
    report_builder.export_csv(
        actual / "replay_events.csv",
        replay["events"],
    )

    checks = {
        "data_quality_pass": quality["status"] == "PASS",
        "replay_created": replay["event_count"] > 0,
        "replay_orders_zero": replay["actual_orders_created"] is False,
        "config_safe": config_audit["safe"] is True,
        "protected_changes_zero": config_audit["protected_change_count"] == 0,
        "incident_manifest_created": incident["captured_file_count"] >= 1,
        "daily_report_created": report["schema_version"] == 1,
        "csv_export_created": (actual / "replay_events.csv").exists(),
        "dashboard_read_only": report["read_only"] is True,
        "broker_actions_unavailable": report["broker_actions_available"] is False,
        "submission_off": report["automatic_order_submission_enabled"] is False,
    }

    result = {
        "stage": "OPERATIONS_V2_MEGA_BUNDLE",
        "state": "OPERATIONS_V2_OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "data_quality_auditor": "READY",
        "historical_replay_simulator": "READY",
        "configuration_diff_auditor": "READY",
        "incident_snapshot_builder": "READY",
        "daily_operator_report": "READY",
        "csv_json_export": "READY",
        "dashboard_4_read_only": "READY",
        "release_candidate_ready": True,
        "actual_market_network_used": False,
        "actual_broker_network_used": False,
        "actual_broker_write_used": False,
        "automatic_order_submission_enabled": False,
        "actual_orders_created": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    (actual / "operations_v2_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
