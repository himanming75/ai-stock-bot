from __future__ import annotations

TEXT = {
    "READY": {
        "en": "Ready",
        "ko": "준비 완료",
    },
    "DEGRADED": {
        "en": "Degraded",
        "ko": "주의 필요",
    },
    "BLOCKED": {
        "en": "Blocked",
        "ko": "차단됨",
    },
    "DRAFT": {
        "en": "Draft",
        "ko": "초안",
    },
    "REVIEW_REQUIRED": {
        "en": "Review Required",
        "ko": "검토 필요",
    },
    "APPROVED_CANDIDATE": {
        "en": "Approved Candidate",
        "ko": "승인 후보",
    },
    "NOT_ACTIVATED": {
        "en": "Not Activated",
        "ko": "활성화되지 않음",
    },
    "READ_ONLY": {
        "en": "Read Only",
        "ko": "조회 전용",
    },
    "COMMAND_QUEUE": {
        "en": "Command Queue",
        "ko": "명령 대기열",
    },
    "HEALTH_SCORE": {
        "en": "Health Score",
        "ko": "시스템 상태 점수",
    },
    "BACKUP_RESTORE": {
        "en": "Backup and Restore",
        "ko": "백업 및 복원",
    },
    "NOTIFICATION_CENTER": {
        "en": "Notification Center",
        "ko": "알림 센터",
    },
    "SESSION_AUTOMATION": {
        "en": "Session Automation",
        "ko": "거래 세션 자동화",
    },
    "CONFIGURATION": {
        "en": "Configuration",
        "ko": "설정",
    },
    "PAPER_ORDER": {
        "en": "Paper Order",
        "ko": "페이퍼 주문",
    },
}


def bilingual(key: str) -> dict[str, str]:
    return dict(
        TEXT.get(
            key,
            {
                "en": key,
                "ko": key,
            },
        )
    )


def label(key: str) -> str:
    value = bilingual(key)
    return f'{value["en"]} / {value["ko"]}'
