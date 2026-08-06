from __future__ import annotations
from pathlib import Path


def production_checklist() -> dict:
    return {
        "environment_variables": "REQUIRED",
        "database_migration": "REQUIRED",
        "database_backup": "REQUIRED",
        "https": "REQUIRED",
        "reverse_proxy": "REQUIRED",
        "firewall": "REQUIRED",
        "health_check": "REQUIRED",
        "monitoring": "REQUIRED",
        "log_rotation": "REQUIRED",
        "secret_manager": "REQUIRED",
        "csrf_protection": "REQUIRED",
        "rate_limiting": "REQUIRED",
        "graceful_shutdown": "REQUIRED",
        "disaster_recovery_test": "REQUIRED",
        "broker_write_default": "OFF",
        "order_submission_default": "OFF",
    }


def validate_deployment_files(root: Path) -> dict:
    required = [
        "Dockerfile",
        "docker-compose.yml",
        "deploy/nginx.conf",
        "deploy/.env.production.example",
        "deploy/PRODUCTION_CHECKLIST.md",
    ]
    status = {
        item: (root / item).exists()
        for item in required
    }
    return {
        "files": status,
        "valid": all(status.values()),
    }
