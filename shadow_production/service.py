from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .approval import (
    ApprovalLedger,
    ApprovalQueue,
    DeploymentLock,
    EmergencyStop,
    RollbackApprovalPreview,
)
from .portfolio import ShadowPortfolio, ShadowRiskMetrics
from .shadow import FillSimulator, ShadowLedger, ShadowOrderIntake


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/shadow_trading_production_approval/actual"
    actual.mkdir(parents=True, exist_ok=True)

    feature_result = json.loads(
        (
            root / "release/feature_engine_auto_optimization/actual/"
                   "feature_engine_auto_optimization_result.json"
        ).read_text(encoding="utf-8-sig")
    )

    shadow_ledger_path = actual / "shadow_trade_ledger.jsonl"
    if shadow_ledger_path.exists():
        shadow_ledger_path.unlink()
    shadow_ledger = ShadowLedger(shadow_ledger_path)

    intake = ShadowOrderIntake()
    simulator = FillSimulator()
    portfolio = ShadowPortfolio(Decimal("100000"))

    orders = [
        intake.create(
            strategy_id="ensemble_v1",
            symbol="AAPL",
            side="buy",
            notional=Decimal("1000"),
            reference_price=Decimal("200"),
            latency_ms=125,
            slippage_bps=Decimal("2.5"),
        ),
        intake.create(
            strategy_id="ensemble_v1",
            symbol="MSFT",
            side="buy",
            notional=Decimal("1500"),
            reference_price=Decimal("500"),
            latency_ms=140,
            slippage_bps=Decimal("3.0"),
        ),
        intake.create(
            strategy_id="ensemble_v1",
            symbol="AAPL",
            side="sell",
            notional=Decimal("500"),
            reference_price=Decimal("205"),
            latency_ms=110,
            slippage_bps=Decimal("2.0"),
        ),
    ]

    fills = []
    snapshots = []
    for order in orders:
        order_json = {
            "record_type": "SHADOW_ORDER",
            **order.as_json(),
        }
        shadow_ledger.append(order_json)
        fill = simulator.simulate(order)
        fills.append(fill)
        shadow_ledger.append({
            "record_type": "SHADOW_FILL",
            **fill,
        })
        snapshots.append(portfolio.apply_fill(fill))

    final_snapshot = portfolio.snapshot(
        market_prices={
            "AAPL": Decimal("207"),
            "MSFT": Decimal("506"),
        }
    )

    equity_curve = [
        Decimal("100000"),
        Decimal("100010"),
        Decimal("100018"),
        Decimal("100015"),
        Decimal("100030"),
    ]
    returns = [
        Decimal("0.0001"),
        Decimal("0.00008"),
        Decimal("-0.00003"),
        Decimal("0.00015"),
    ]
    risk = ShadowRiskMetrics().calculate(
        equity_curve=equity_curve,
        returns=returns,
    )

    deployment_lock = DeploymentLock().evaluate(
        p2_validated=False,
        p3_validated=False,
        p4_validated=False,
        p5_validated=False,
        emergency_stop_active=False,
    )
    emergency = EmergencyStop().preview(requested=True)

    approval_ledger_path = actual / "approval_ledger.jsonl"
    if approval_ledger_path.exists():
        approval_ledger_path.unlink()
    approval_ledger = ApprovalLedger(approval_ledger_path)

    approval = ApprovalQueue().create(
        approval_type="PRODUCTION_RELEASE",
        subject="ensemble_v1.1",
        evidence={
            "feature_framework_status": feature_result.get("status"),
            "shadow_risk_state": risk["risk_state"],
            "p2_validated": False,
            "p3_validated": False,
            "p4_validated": False,
            "p5_validated": False,
        },
    )
    approval_ledger.append(approval)

    rollback = RollbackApprovalPreview().build(
        current_release="ensemble_v1.1",
        target_release="ensemble_v1.0",
        reason="SHADOW_REGRESSION_PREVIEW",
    )
    approval_ledger.append({
        "record_type": "ROLLBACK_PREVIEW",
        **rollback,
    })

    checks = {
        "feature_framework_pass": feature_result.get("status") == "PASS",
        "three_shadow_orders": len(orders) == 3,
        "three_shadow_fills": len(fills) == 3,
        "all_orders_preview_only": all(
            order.as_json()["actual_order_created"] is False
            for order in orders
        ),
        "all_fills_simulated": all(
            fill["actual_fill_received"] is False
            for fill in fills
        ),
        "shadow_portfolio_created": bool(final_snapshot["positions"]),
        "risk_metrics_created": risk["risk_state"] == "OK",
        "deployment_locked": (
            deployment_lock["production_release_allowed"] is False
        ),
        "emergency_stop_preview_only": (
            emergency["actual_emergency_stop_activated"] is False
        ),
        "approval_pending_preview": (
            approval["state"] == "PENDING_PREVIEW"
        ),
        "approval_not_granted": (
            approval["actual_approval_granted"] is False
        ),
        "rollback_preview_ready": (
            rollback["rollback_preview_allowed"] is True
        ),
        "rollback_not_performed": (
            rollback["actual_rollback_performed"] is False
        ),
    }

    result = {
        "stage": "SHADOW_TRADING_PRODUCTION_APPROVAL_FRAMEWORK",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "shadow_order_intake": "READY",
        "fill_simulation": "READY",
        "slippage_simulation": "READY",
        "latency_simulation": "READY",
        "shadow_portfolio": "READY",
        "shadow_pnl": "READY",
        "shadow_risk_metrics": "READY",
        "shadow_trade_ledger": "READY",
        "production_approval_queue": "READY_PREVIEW_ONLY",
        "deployment_lock": "READY",
        "emergency_stop": "READY_PREVIEW_ONLY",
        "approval_ledger": "READY",
        "rollback_approval": "READY_PREVIEW_ONLY",
        "release_gate": "LOCKED",
        "shadow_orders": [order.as_json() for order in orders],
        "shadow_fills": fills,
        "shadow_portfolio_snapshot": final_snapshot,
        "shadow_risk": risk,
        "deployment_lock_result": deployment_lock,
        "emergency_stop_preview": emergency,
        "approval_queue_record": approval,
        "rollback_approval_preview": rollback,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_fill_received": False,
        "actual_portfolio_modified": False,
        "actual_production_approval_granted": False,
        "actual_release_performed": False,
        "actual_emergency_stop_activated": False,
        "actual_rollback_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_development": "AI_MONITORING_DASHBOARD_AND_MULTI_WORKER_FRAMEWORK",
    }
    (actual / "shadow_trading_production_approval_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
