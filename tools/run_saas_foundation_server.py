from __future__ import annotations
import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saas_foundation.control_plane import SaaSControlPlane
from saas_foundation.security import SessionSigner
from saas_foundation.store import SaaSStore
from saas_foundation.web import serve


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    store = SaaSStore(
        Path("runtime/saas_foundation/store.json")
    )
    control = SaaSControlPlane(
        store=store,
        signer=SessionSigner(secrets.token_bytes(32)),
    )
    serve(
        control,
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
