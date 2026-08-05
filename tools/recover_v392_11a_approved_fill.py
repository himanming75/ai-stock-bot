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
        if record.get("stage") == "V392.11A"
        and record.get("status") == "PASS"
        and record.get("state") == "PAPER_EXECUTION_SIMULATOR_READY"
        and record.get("simulated_fill_created") is True
        and record.get("fill_accounting_allowed") is True
        and isinstance(record.get("evaluation", {}).get("fill_event"), dict)
        and bool(record.get("evaluation", {}).get("fill_event"))
    ]
    if not approved:
        raise ValueError("NO_APPROVED_V392_11A_FILL_RECORD")
    return approved[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        default="release/v392_11a/actual/paper_execution_simulator_ledger.jsonl",
    )
    parser.add_argument(
        "--snapshot-result",
        default=(
            "release/v392_11a/actual/"
            "paper_execution_simulator_approved_snapshot.json"
        ),
    )
    parser.add_argument(
        "--snapshot-fill",
        default="release/v392_11a/actual/fill_event_approved_snapshot.json",
    )
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    ledger_path = root / args.ledger
    result_path = root / args.snapshot_result
    fill_path = root / args.snapshot_fill

    if not ledger_path.exists():
        raise FileNotFoundError(f"LEDGER_NOT_FOUND:{ledger_path}")

    approved = select_latest_approved(load_jsonl(ledger_path))
    fill_event = approved["evaluation"]["fill_event"]

    snapshot = {
        **approved,
        "snapshot_metadata": {
            "source": str(ledger_path),
            "selection": "LATEST_APPROVED_V392_11A_FILL_RECORD",
            "replay_registry_preserved": True,
            "current_blocked_result_preserved": True,
        },
    }

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fill_path.write_text(
        json.dumps(fill_event, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "stage": "V392.12A1",
        "status": "PASS",
        "recovery_state": "APPROVED_FILL_SNAPSHOT_RECOVERED",
        "fill_event_id": fill_event.get("fill_event_id"),
        "result_snapshot_path": str(result_path),
        "fill_snapshot_path": str(fill_path),
        "replay_registry_modified": False,
        "current_result_overwritten": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
