from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saas_persistence.control_plane import (
    PersistentSaaSControlPlane,
)
from saas_persistence.database import SQLiteDatabase
from saas_persistence.repository import SaaSRepository
from saas_persistence.security import SessionSigner
from saas_persistence.web import serve


def session_secret() -> bytes:
    configured = os.getenv("SAAS_SESSION_SECRET", "")
    if configured:
        value = configured.encode("utf-8")
        if len(value) < 32:
            raise ValueError(
                "SAAS_SESSION_SECRET must be at least 32 bytes"
            )
        return value
    return b"local-development-session-secret-2026"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--database",
        default="runtime/saas/saas.db",
    )
    args = parser.parse_args()

    database = SQLiteDatabase(Path(args.database))
    control = PersistentSaaSControlPlane(
        repository=SaaSRepository(database),
        signer=SessionSigner(session_secret()),
    )
    serve(
        control,
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
