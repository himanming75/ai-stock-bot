import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.promotion_approval import PromotionApprovalLedger


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        policy = {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "explicit_approval_required": True,
            "block_duplicate_approval": True,
        }
        promotion = {
            "promotion_ready": True,
            "state": "PROMOTION_READY",
        }
        certificate = {
            "certificate_verified": True,
            "certificate_id": "VAL-1",
            "certificate_sha256": "a" * 64,
        }
        return policy, promotion, certificate

    def run_case(
        self,
        values,
        *,
        approve=False,
        approver="",
        reason="",
    ):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["policy", "promotion", "certificate"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            self.write(paths[name], value)

        result = PromotionApprovalLedger().run(
            policy_path=paths["policy"],
            promotion_gate_result_path=paths["promotion"],
            certificate_result_path=paths["certificate"],
            approval_ledger_path=root/"ledger.jsonl",
            approval_record_path=root/"record.json",
            approval_manifest_path=root/"manifest.json",
            certification_gate_path=root/"gate.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            approve=approve,
            approver=approver,
            approval_reason=reason,
        )
        return result, root

    def test_wait_promotion_ready(self):
        values = list(self.data())
        values[1] = {
            "promotion_ready": False,
            "state": "WAIT_VALIDATION_COMPLETE",
        }
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_PROMOTION_READY")

    def test_wait_explicit_approval(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["state"], "WAIT_EXPLICIT_APPROVAL")

    def test_approval_requires_identity(self):
        result, _ = self.run_case(
            self.data(),
            approve=True,
            approver="",
            reason="approved",
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_approval_written(self):
        result, root = self.run_case(
            self.data(),
            approve=True,
            approver="James Park",
            reason="Paper validation approved",
        )
        self.assertTrue(result["approval_written"])
        self.assertTrue(result["certification_gate_clear"])
        self.assertTrue((root/"ledger.jsonl").exists())

    def test_duplicate_approval_blocks(self):
        values = self.data()
        result, root = self.run_case(
            values,
            approve=True,
            approver="James Park",
            reason="Approved",
        )
        self.assertTrue(result["approval_written"])
        second = PromotionApprovalLedger().run(
            policy_path=root/"policy.json",
            promotion_gate_result_path=root/"promotion.json",
            certificate_result_path=root/"certificate.json",
            approval_ledger_path=root/"ledger.jsonl",
            approval_record_path=root/"record2.json",
            approval_manifest_path=root/"manifest2.json",
            certification_gate_path=root/"gate2.json",
            dashboard_state_path=root/"dashboard2.json",
            result_path=root/"result2.json",
            approve=True,
            approver="James Park",
            approval_reason="Approved again",
        )
        self.assertEqual(second["status"], "BLOCKED")
        self.assertTrue(second["duplicate_approval"])

    def test_read_only_contract(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertFalse(result["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main()
