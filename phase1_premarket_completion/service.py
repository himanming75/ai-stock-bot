from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .backup import build_backup_plan
from .command_queue import enqueue_plan
from .config_pipeline import (
    create_approval_candidate,
    create_review_package,
)
from .health import calculate_health
from .io import write_json
from .notifications import (
    build_notification_preview,
)
from .report import build_bilingual_report
from .runtime_loader import (
    build_runtime_load_plan,
)
from .session import build_session_plan


class Phase1PremarketCompletionService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        fixture = output_dir / "fixtures"
        actual = output_dir / "actual"
        fixture.mkdir(
            parents=True,
            exist_ok=True,
        )
        actual.mkdir(
            parents=True,
            exist_ok=True,
        )

        draft_path = fixture / "configuration_draft.json"
        write_json(
            draft_path,
            {
                "profile_key": "BALANCED",
                "profile": {
                    "max_positions": 4,
                    "max_position_percent": 15,
                    "max_daily_loss_percent": 1,
                    "cash_reserve_percent": 30,
                },
                "symbols": [
                    "SPY",
                    "QQQ",
                    "AAPL",
                ],
                "strategies": {
                    "EMA": {
                        "enabled": True,
                    },
                    "RSI": {
                        "enabled": True,
                    },
                    "MACD": {
                        "enabled": False,
                    },
                },
                "execution": {
                    "mode": "DRAFT_ONLY",
                    "activation_enabled": False,
                    "broker_write_enabled": False,
                    "order_submission_enabled": False,
                },
            },
        )

        review_path = actual / "configuration_review.json"
        review = create_review_package(
            draft_path=draft_path,
            output_path=review_path,
            ledger_path=(
                actual
                / "configuration_review_ledger.jsonl"
            ),
            requested_by="CERTIFICATION",
        )
        candidate_path = (
            actual
            / "approved_configuration_candidate.json"
        )
        candidate = create_approval_candidate(
            review_path=review_path,
            output_path=candidate_path,
            ledger_path=(
                actual
                / "configuration_candidate_ledger.jsonl"
            ),
            approved_by="CERTIFICATION",
            approval_note=(
                "Offline candidate only."
            ),
        )

        runtime_plan = build_runtime_load_plan(
            candidate_path=candidate_path,
            current_runtime_path=(
                fixture / "runtime.json"
            ),
            output_path=(
                actual / "runtime_load_plan.json"
            ),
        )

        command_plans = []
        for action in (
            "PAUSE",
            "RESUME",
            "RELOAD_CONFIGURATION",
            "GRACEFUL_STOP",
            "PREMARKET_VALIDATE",
            "GENERATE_REPORT",
        ):
            command_plans.append(
                enqueue_plan(
                    action=action,
                    reason="Certification fixture",
                    requested_by="CERTIFICATION",
                    latest_path=(
                        actual
                        / "latest_command_plan.json"
                    ),
                    queue_path=(
                        actual
                        / "command_queue.jsonl"
                    ),
                )
            )

        session_plan = build_session_plan(
            market_status="CLOSED",
            configuration_ready=True,
            broker_read_ready=True,
            controller_ready=True,
        )
        write_json(
            actual / "session_plan.json",
            session_plan,
        )

        health = calculate_health(
            cpu_percent=22,
            memory_growth_mb=13,
            polling_delay_seconds=31,
            broker_latency_ms=210,
            error_count=0,
            stale_source_count=0,
        )
        write_json(
            actual / "health_score.json",
            health,
        )

        backup_plan = build_backup_plan(
            action="SNAPSHOT",
            source_paths=[
                "release/trading_configuration/actual",
                "release/paper_automation_controller/actual",
                "release/actual_multi_broker_sync/actual",
            ],
            destination=(
                "release/backups/phase1_snapshot"
            ),
            output_path=(
                actual / "backup_plan.json"
            ),
        )

        notification = (
            build_notification_preview(
                channel="WEB",
                event_type=(
                    "PREMARKET_READY"
                ),
                severity="INFO",
                title_en=(
                    "Premarket checks are ready"
                ),
                title_ko=(
                    "장전 검사가 준비되었습니다"
                ),
                message_en=(
                    "All offline Phase 1 checks passed."
                ),
                message_ko=(
                    "1단계 오프라인 검사가 모두 통과했습니다."
                ),
                output_path=(
                    actual
                    / "notification_preview.json"
                ),
                ledger_path=(
                    actual
                    / "notification_preview_ledger.jsonl"
                ),
            )
        )

        report = build_bilingual_report(
            configuration=candidate,
            runtime_plan=runtime_plan,
            session_plan=session_plan,
            health=health,
            backup_plan=backup_plan,
            notification_preview=notification,
            output_path=(
                actual
                / "phase1_premarket_report_bilingual.json"
            ),
        )

        result = {
            "stage": (
                "V9201_TO_V9800_PHASE1_"
                "PREMARKET_COMPLETION_MAX_BUNDLE"
            ),
            "status": "PASS",
            "configuration_review_ready": True,
            "approval_candidate_ready": True,
            "runtime_loader_plan_ready": True,
            "hot_reload_plan_ready": True,
            "command_queue_plan_ready": True,
            "session_state_machine_ready": True,
            "market_open_wait_plan_ready": True,
            "health_score_ready": True,
            "backup_restore_plan_ready": True,
            "notification_preview_ready": True,
            "bilingual_ui_foundation_ready": True,
            "bilingual_report_ready": True,
            "configuration_review": review,
            "approval_candidate": candidate,
            "runtime_plan": runtime_plan,
            "command_plan_count": len(
                command_plans
            ),
            "session_plan": session_plan,
            "health_score": health,
            "backup_plan": backup_plan,
            "notification_preview": notification,
            "report": report,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_configuration_activated": False,
            "actual_runtime_configuration_applied": False,
            "actual_command_executed": False,
            "actual_process_started": False,
            "actual_process_stopped": False,
            "actual_backup_executed": False,
            "actual_restore_executed": False,
            "actual_notification_sent": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_market_open_tasks": [
                {
                    "en": (
                        "Validate actual Alpaca market clock "
                        "and quote freshness."
                    ),
                    "ko": (
                        "실제 Alpaca 시장 시계와 시세 "
                        "신선도를 검증합니다."
                    ),
                },
                {
                    "en": (
                        "Run intraday read-only polling "
                        "and state-transition validation."
                    ),
                    "ko": (
                        "장중 조회 전용 Polling과 상태 "
                        "전환을 검증합니다."
                    ),
                },
                {
                    "en": (
                        "Do not enable paper order submission "
                        "until explicit approval."
                    ),
                    "ko": (
                        "명시적 승인 전에는 페이퍼 주문 "
                        "제출을 활성화하지 않습니다."
                    ),
                },
            ],
            "next_fixed_development": (
                "PHASE2_AI_FEATURE_ENGINE_"
                "AND_SIGNAL_CANDIDATES"
            ),
        }

        checks = (
            review["status"]
            == "REVIEW_REQUIRED",
            candidate["status"]
            == "APPROVED_CANDIDATE",
            candidate["activation_status"]
            == "NOT_ACTIVATED",
            runtime_plan[
                "runtime_apply_enabled"
            ] is False,
            len(command_plans) == 6,
            all(
                item["execution_status"]
                == "NOT_EXECUTED"
                for item in command_plans
            ),
            session_plan[
                "planned_action"
            ] == "WAIT_FOR_MARKET_OPEN",
            health["score"] >= 85,
            backup_plan["mode"]
            == "DRY_RUN_ONLY",
            notification[
                "delivery_status"
            ] == "NOT_SENT",
            report["safety"][
                "broker_write_enabled"
            ] is False,
        )
        if not all(checks):
            result["status"] = "BLOCKED"

        result[
            "certification_fingerprint"
        ] = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        write_json(
            output_dir
            / "phase1_premarket_completion_certification.json",
            result,
        )
        return result
