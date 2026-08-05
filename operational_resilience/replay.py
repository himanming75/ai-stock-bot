from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


class DeterministicReplayManifest:
    def build(
        self,
        *,
        dataset_fingerprint: str,
        strategy_versions: dict[str, str],
        configuration_fingerprint: str,
        random_seed: int,
    ) -> dict[str, Any]:
        core = {
            "dataset_fingerprint": dataset_fingerprint,
            "strategy_versions": strategy_versions,
            "configuration_fingerprint": configuration_fingerprint,
            "random_seed": random_seed,
        }
        raw = json.dumps(core, sort_keys=True, separators=(",", ":"))
        return {
            **core,
            "replay_id": hashlib.sha256(
                raw.encode("utf-8")
            ).hexdigest(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "actual_replay_started": False,
            "actual_order_submission_performed": False,
        }
