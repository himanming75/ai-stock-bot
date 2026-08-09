from __future__ import annotations

import json
from pathlib import Path


class ManualSandboxReviewPacketBuilderV2118:
    def __init__(self,root):
        self.root=Path(root)
        self.source_ledger=(
            self.root
            /"runtime"
            /"sandbox_readiness_gate_v2_1_17"
            /"qualification_ledger.jsonl"
        )
        self.runtime_dir=(
            self.root
            /"runtime"
            /"manual_sandbox_review_packets_v2_1_18"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.index_ledger=self.runtime_dir/"review_packet_index.jsonl"

    def _existing_keys(self):
        keys=set()
        if not self.index_ledger.exists():
            return keys
        for line in self.index_ledger.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            if row.get("evidence_key"):
                keys.add(row["evidence_key"])
        return keys

    @staticmethod
    def _ready(row):
        return (
            row.get("qualification_status")
                =="READY_FOR_MANUAL_SANDBOX_REVIEW"
            and row.get("ready") is True
            and row.get("manual_review_required") is True
            and row.get(
                "automatic_sandbox_execution_allowed"
            ) is False
            and int(row.get("broker_orders_submitted") or 0)==0
            and row.get("production_order_submission") is False
            and row.get("live_trading") is False
            and row.get("canonical_min_confidence")=="0.75"
            and row.get("canonical_min_reward_risk")=="1.0"
            and row.get("canonical_paper_gate_semantics")
                =="CORRECTED_V2_1_19_1"
        )

    def _packet(self,row):
        signals=list(row.get("signals") or [])
        return {
            "stage":
                "BROKER_INTEGRATION_V2_1_18_MANUAL_SANDBOX_REVIEW_PACKET",
            "packet_status":"AWAITING_MANUAL_REVIEW",
            "evidence_key":row.get("evidence_key"),
            "source_observed_at_utc":
                row.get("source_observed_at_utc"),
            "qualification_status":
                row.get("qualification_status"),
            "generic_etrade_bridge_min_confidence":
                row.get("generic_etrade_bridge_min_confidence"),
            "canonical_min_confidence":
                row.get("canonical_min_confidence"),
            "canonical_min_reward_risk":
                row.get("canonical_min_reward_risk"),
            "canonical_paper_gate_semantics":
                row.get("canonical_paper_gate_semantics"),
            "eligible_signal_count":
                int(row.get("eligible_signal_count") or 0),
            "signals":signals,
            "qualification_reasons":
                list(row.get("reasons") or []),
            "manual_review_required":True,
            "manual_approval_recorded":False,
            "automatic_sandbox_execution_allowed":False,
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
            "profitability_validated":False,
        }

    @staticmethod
    def _markdown(packet):
        lines=[
            "# V2.1.18 Manual Sandbox Review Packet",
            "",
            f"- Packet status: `{packet['packet_status']}`",
            f"- Evidence key: `{packet['evidence_key']}`",
            f"- Qualification: `{packet['qualification_status']}`",
            (
                "- Generic E*TRADE confidence: "
                f"`{packet.get('generic_etrade_bridge_min_confidence')}`"
            ),
            (
                "- Canonical Paper confidence: "
                f"`{packet.get('canonical_min_confidence')}`"
            ),
            (
                "- Canonical Paper minimum reward/risk: "
                f"`{packet.get('canonical_min_reward_risk')}`"
            ),
            (
                "- Canonical semantics: "
                f"`{packet.get('canonical_paper_gate_semantics')}`"
            ),
            "- Manual review required: `True`",
            "- Automatic Sandbox execution: `False`",
            "",
            "## Signals",
            "",
        ]
        for i,s in enumerate(packet["signals"],1):
            lines += [
                f"### Signal {i}",
                f"- Symbol: `{s.get('symbol')}`",
                f"- Side: `{s.get('side')}`",
                f"- Quantity: `{s.get('quantity')}`",
                f"- Strategy ID: `{s.get('strategy_id')}`",
                f"- Source confidence: `{s.get('source_confidence')}`",
                f"- Source reward/risk: `{s.get('source_reward_risk')}`",
                "",
            ]
        lines += [
            "## Manual Review Checklist",
            "",
            "- [ ] Confirm symbol",
            "- [ ] Confirm side",
            "- [ ] Confirm quantity",
            "- [ ] Confirm source confidence >= 0.75",
            "- [ ] Confirm source reward/risk >= 1.0",
            "- [ ] Confirm corrected canonical semantics marker",
            "- [ ] Confirm evidence key",
            "- [ ] Confirm Sandbox-only intent",
            "- [ ] Confirm PROD remains locked",
            "- [ ] Confirm live trading remains locked",
            "",
            (
                "**This packet is review evidence only. "
                "It does not authorize or execute an order.**"
            ),
            "",
        ]
        return "\n".join(lines)

    def build(self):
        if not self.source_ledger.exists():
            return {
                "status":"WAITING_FOR_V2_1_17_QUALIFICATION",
                "source_rows":0,
                "ready_rows":0,
                "legacy_or_not_ready_rows":0,
                "new_packets":0,
                "duplicate_packets":0,
                "source_ledger":str(self.source_ledger),
                "packet_directory":str(self.runtime_dir),
                "automatic_sandbox_execution_allowed":False,
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }

        existing=self._existing_keys()
        source_rows=ready_rows=legacy_or_not_ready_rows=0
        new_packets=duplicate_packets=0
        generated=[]

        for line in self.source_ledger.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            source_rows+=1
            row=json.loads(line)

            if not self._ready(row):
                legacy_or_not_ready_rows+=1
                continue

            ready_rows+=1
            key=str(row.get("evidence_key") or "").strip()
            if not key:
                continue
            if key in existing:
                duplicate_packets+=1
                continue

            packet=self._packet(row)
            safe="".join(
                c if c.isalnum() or c in "-_" else "_"
                for c in key
            )[:80]
            json_path=(
                self.runtime_dir/f"review_packet_{safe}.json"
            )
            md_path=(
                self.runtime_dir/f"review_packet_{safe}.md"
            )

            json_path.write_text(
                json.dumps(
                    packet,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            md_path.write_text(
                self._markdown(packet),
                encoding="utf-8",
            )

            index={
                "evidence_key":key,
                "packet_status":"AWAITING_MANUAL_REVIEW",
                "canonical_paper_gate_semantics":
                    "CORRECTED_V2_1_19_1",
                "json_path":str(json_path),
                "markdown_path":str(md_path),
                "manual_approval_recorded":False,
                "automatic_sandbox_execution_allowed":False,
                "broker_orders_submitted":0,
            }
            with self.index_ledger.open(
                "a",encoding="utf-8"
            ) as f:
                f.write(
                    json.dumps(
                        index,
                        sort_keys=True,
                    )+"\n"
                )

            existing.add(key)
            new_packets+=1
            generated.append(index)

        return {
            "status":"PASS_MANUAL_SANDBOX_REVIEW_PACKET_BUILD",
            "source_rows":source_rows,
            "ready_rows":ready_rows,
            "legacy_or_not_ready_rows":
                legacy_or_not_ready_rows,
            "new_packets":new_packets,
            "duplicate_packets":duplicate_packets,
            "source_ledger":str(self.source_ledger),
            "packet_directory":str(self.runtime_dir),
            "generated_packets":generated,
            "manual_review_required":True,
            "automatic_sandbox_execution_allowed":False,
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
            "profitability_validated":False,
        }
