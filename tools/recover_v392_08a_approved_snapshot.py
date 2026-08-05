from __future__ import annotations
import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"INVALID_JSONL_RECORD:{line_number}:{exc.msg}"
                ) from exc
            if isinstance(value, dict):
                records.append(value)
    return records


def select_latest_approved(records: list[dict]) -> dict:
    approved = [
        record
        for record in records
        if record.get("stage") == "V392.08A"
        and record.get("status") == "PASS"
        and record.get("state") == "LOCAL_DISPATCH_RELEASE_GATE_READY"
        and record.get("local_dispatch_release_approved") is True
        and record.get("local_dispatch_engine_preparation_allowed") is True
    ]
    if not approved:
        raise ValueError("NO_APPROVED_V392_08A_LEDGER_RECORD")
    return approved[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        default="release/v392_08a/actual/local_dispatch_release_ledger.jsonl",
    )
    parser.add_argument(
        "--snapshot",
        default=(
            "release/v392_08a/actual/"
            "local_dispatch_release_gate_approved_snapshot.json"
        ),
    )
    parser.add_argument(
        "--project-root",
        default=".",
    )
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    ledger_path = root / args.ledger
    snapshot_path = root / args.snapshot

    if not ledger_path.exists():
        raise FileNotFoundError(f"LEDGER_NOT_FOUND:{ledger_path}")

    records = load_jsonl(ledger_path)
    approved = select_latest_approved(records)

    snapshot = {
        **approved,
        "snapshot_metadata": {
            "source": str(ledger_path),
            "selection": "LATEST_APPROVED_V392_08A_RECORD",
            "immutable_replay_registry_preserved": True,
            "current_blocked_result_not_overwritten": True,
        },
    }

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "stage": "V392.09A1",
        "status": "PASS",
        "recovery_state": "APPROVED_SNAPSHOT_RECOVERED",
        "snapshot_path": str(snapshot_path),
        "dispatch_id": (
            snapshot.get("evaluation", {})
            .get("release_record", {})
            .get("dispatch_id")
        ),
        "current_result_overwritten": False,
        "replay_registry_modified": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
