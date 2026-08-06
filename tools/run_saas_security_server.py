from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saas_security.control_plane import (
    SaaSSecurityControlPlane,
)
from saas_security.database import SecurityDatabase
from saas_security.repository import SecurityRepository
from saas_security.web import serve


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--database",
        default="runtime/saas/security.db",
    )
    args = parser.parse_args()

    database = SecurityDatabase(
        Path(args.database)
    )
    control = SaaSSecurityControlPlane(
        SecurityRepository(database)
    )
    serve(
        control,
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
