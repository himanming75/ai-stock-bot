from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smart_safe_guard import SmartSafeTradingGuard


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--policy",
        default="release/smart_safe_trading_guard_1_0/config/guard_policy.json",
    )
    parser.add_argument(
        "--input",
        default="release/smart_safe_trading_guard_1_0/input/shadow_snapshot.json",
    )
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    payload = load(root / args.input)

    result = SmartSafeTradingGuard(root).evaluate(
        policy_path=root / args.policy,
        candidate=payload["candidate"],
        account=payload["account"],
        risk=payload["risk"],
        market=payload["market"],
        positions=payload["positions"],
        decision_path=(
            root
            / "release/smart_safe_trading_guard_1_0/actual/latest_guard_decision.json"
        ),
        ledger_path=(
            root
            / "release/smart_safe_trading_guard_1_0/actual/guard_ledger.jsonl"
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
