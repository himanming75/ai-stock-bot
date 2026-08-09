from __future__ import annotations

import json
from pathlib import Path


class FreshEligibleSignalEvidenceCaptureV2116:
    """
    Thin evidence layer over the existing V2.1.15 observation ledger.

    It does not observe the market itself and does not submit orders.
    It only captures rows that V2.1.15 already marked as:
      OBSERVED_FRESH
      eligible_signal_captured == True
    """

    def __init__(self,root):
        self.root=Path(root)
        self.source_ledger=(
            self.root
            /"runtime"
            /"freshness_guarded_persistent_observer_v2_1_15"
            /"observation_ledger.jsonl"
        )
        self.runtime_dir=(
            self.root
            /"runtime"
            /"fresh_eligible_signal_evidence_v2_1_16"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.evidence_ledger=(
            self.runtime_dir/"eligible_signal_evidence.jsonl"
        )
        self.latest_evidence=(
            self.runtime_dir/"latest_eligible_signal_evidence.json"
        )

    def _existing_keys(self):
        keys=set()
        if not self.evidence_ledger.exists():
            return keys
        for line in self.evidence_ledger.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            key=row.get("evidence_key")
            if key:
                keys.add(key)
        return keys

    @staticmethod
    def _evidence_key(row):
        return str(row.get("snapshot_fingerprint") or "")

    @staticmethod
    def _eligible(row):
        return (
            row.get("observer_state")=="OBSERVED_FRESH"
            and row.get("eligible_signal_captured") is True
            and int(
                (row.get("snapshot") or {}).get(
                    "eligible_signal_count",0
                )
            ) > 0
        )

    def capture(self):
        if not self.source_ledger.exists():
            return {
                "status":"WAITING_FOR_V2_1_15_OBSERVATION_LEDGER",
                "source_ledger":str(self.source_ledger),
                "source_rows":0,
                "eligible_rows_found":0,
                "new_evidence_rows":0,
                "duplicate_evidence_rows":0,
                "evidence_ledger":str(self.evidence_ledger),
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        existing=self._existing_keys()
        source_rows=0
        eligible_rows=0
        new_rows=0
        duplicate_rows=0
        latest=None

        with self.source_ledger.open(
            "r",encoding="utf-8"
        ) as src:
            for line in src:
                if not line.strip():
                    continue
                source_rows+=1
                row=json.loads(line)

                if not self._eligible(row):
                    continue

                eligible_rows+=1
                key=self._evidence_key(row)
                if not key:
                    raise RuntimeError(
                        "Eligible observation missing snapshot_fingerprint"
                    )

                if key in existing:
                    duplicate_rows+=1
                    continue

                snapshot=row.get("snapshot") or {}
                evidence={
                    "stage":
                        "BROKER_INTEGRATION_V2_1_16_FRESH_ELIGIBLE_SIGNAL_EVIDENCE_CAPTURE",
                    "evidence_key":key,
                    "observed_at_utc":row.get("observed_at_utc"),
                    "source_iteration":row.get("iteration"),
                    "source_stage":row.get("stage"),
                    "observer_state":row.get("observer_state"),
                    "session_freshness_gate":
                        row.get("session_freshness_gate"),
                    "canonical_gate_aligned":
                        bool(snapshot.get("canonical_gate_aligned")),
                    "eligible_signal_count":
                        int(snapshot.get("eligible_signal_count",0)),
                    "eligible_signals":
                        list(snapshot.get("eligible_signals") or []),
                    "signal_capture_allowed":
                        bool(snapshot.get("signal_capture_allowed")),
                    "market_data_fetch_skipped":
                        bool(snapshot.get("market_data_fetch_skipped")),
                    "freshness_status":
                        snapshot.get("freshness_status"),
                    "all_fresh":
                        bool(snapshot.get("all_fresh")),
                    "evidence_only":True,
                    "etrade_oauth_started":False,
                    "sandbox_preview_sent":False,
                    "sandbox_place_sent":False,
                    "broker_orders_submitted":0,
                    "production_order_submission":False,
                    "live_trading":False,
                    "profitability_validated":False,
                }

                with self.evidence_ledger.open(
                    "a",encoding="utf-8"
                ) as dst:
                    dst.write(
                        json.dumps(
                            evidence,
                            sort_keys=True,
                            ensure_ascii=False,
                        )+"\n"
                    )

                self.latest_evidence.write_text(
                    json.dumps(
                        evidence,
                        indent=2,
                        sort_keys=True,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                existing.add(key)
                new_rows+=1
                latest=evidence

        return {
            "status":"PASS_FRESH_ELIGIBLE_SIGNAL_EVIDENCE_CAPTURE",
            "source_ledger":str(self.source_ledger),
            "source_rows":source_rows,
            "eligible_rows_found":eligible_rows,
            "new_evidence_rows":new_rows,
            "duplicate_evidence_rows":duplicate_rows,
            "evidence_ledger":str(self.evidence_ledger),
            "latest_evidence":
                None if latest is None else str(self.latest_evidence),
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
            "profitability_validated":False,
        }
