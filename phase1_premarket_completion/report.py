from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from .i18n import bilingual
from .io import write_json


def build_bilingual_report(
    *,
    configuration: dict,
    runtime_plan: dict,
    session_plan: dict,
    health: dict,
    backup_plan: dict,
    notification_preview: dict,
    output_path: Path,
) -> dict:
    report = {
        "report_type": (
            "PHASE1_PREMARKET_COMPLETION_REPORT"
        ),
        "report_title": {
            "en": (
                "Phase 1 Premarket Completion Report"
            ),
            "ko": (
                "1단계 장전 완료 보고서"
            ),
        },
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "overall_status": "READY",
        "overall_status_i18n": bilingual(
            "READY"
        ),
        "sections": {
            "configuration": {
                "title": {
                    "en": "Configuration",
                    "ko": "설정",
                },
                "data": configuration,
            },
            "runtime_loader": {
                "title": {
                    "en": (
                        "Runtime Configuration Loader"
                    ),
                    "ko": (
                        "실행 설정 로더"
                    ),
                },
                "data": runtime_plan,
            },
            "session_automation": {
                "title": {
                    "en": "Session Automation",
                    "ko": "거래 세션 자동화",
                },
                "data": session_plan,
            },
            "health_score": {
                "title": {
                    "en": "Health Score",
                    "ko": "시스템 상태 점수",
                },
                "data": health,
            },
            "backup_restore": {
                "title": {
                    "en": "Backup and Restore",
                    "ko": "백업 및 복원",
                },
                "data": backup_plan,
            },
            "notification_center": {
                "title": {
                    "en": "Notification Center",
                    "ko": "알림 센터",
                },
                "data": notification_preview,
            },
        },
        "safety": {
            "configuration_activation_enabled": False,
            "runtime_apply_enabled": False,
            "command_execution_enabled": False,
            "backup_restore_execution_enabled": False,
            "notification_delivery_enabled": False,
            "process_start_enabled": False,
            "process_stop_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
        },
    }
    write_json(output_path, report)
    return report
