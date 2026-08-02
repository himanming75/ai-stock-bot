from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.terminal_commit import (
    JsonlLedger,
    TerminalCommitState,
    TerminalCompletionCommitter,
)


def result(**overrides):
    value = {
        "client_order_id": "single-legacy",
        "broker_order_id": "broker-1",
        "symbol": "AAPL",
        "side": "BUY",
        "final_status": "ACCEPTED",
        "quantity": "1",
        "filled_quantity": "0",
        "remaining_quantity": "1",
        "average_fill_price": "0",
        "position_quantity": "0",
        "cash": "100000",
        "equity": "100000",
    }
    value.update(overrides)
    return value


class TerminalCommitTests(unittest.TestCase):
    def make(self):
        temp = tempfile.TemporaryDirectory()
        base = Path(temp.name)
        committer = TerminalCompletionCommitter(
            completion_ledger=JsonlLedger(base/"completion.jsonl"),
            audit_ledger=JsonlLedger(base/"audit.jsonl"),
            unlock_ledger=JsonlLedger(base/"unlock.jsonl"),
            recovery_snapshot_path=base/"recovery.json",
        )
        return temp, base, committer

    def test_active_continue_tracking(self):
        temp, base, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(),
                source_result_path="source.json",
                completed_at="",
            )
            self.assertEqual(r.state,TerminalCommitState.CONTINUE_TRACKING)
            self.assertFalse(r.committed)
            self.assertFalse((base/"completion.jsonl").exists())
        finally:
            temp.cleanup()

    def test_filled_commit(self):
        temp, base, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(
                    final_status="FILLED",
                    filled_quantity="1",
                    remaining_quantity="0",
                    average_fill_price="50",
                    position_quantity="1",
                    cash="99950",
                ),
                source_result_path="source.json",
                completed_at="2026-08-02T10:00:00+00:00",
            )
            self.assertEqual(r.state,TerminalCommitState.COMMITTED_FILLED)
            self.assertTrue(r.committed)
            self.assertTrue(r.next_order_allowed)
            self.assertTrue((base/"recovery.json").exists())
        finally:
            temp.cleanup()

    def test_canceled_commit(self):
        temp, _, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(final_status="CANCELED"),
                source_result_path="source.json",
                completed_at="now",
            )
            self.assertEqual(r.state,TerminalCommitState.COMMITTED_TERMINAL_NO_FILL)
        finally:
            temp.cleanup()

    def test_expired_commit(self):
        temp, _, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(final_status="EXPIRED"),
                source_result_path="source.json",
                completed_at="now",
            )
            self.assertTrue(r.committed)
        finally:
            temp.cleanup()

    def test_rejected_commit(self):
        temp, _, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(final_status="REJECTED"),
                source_result_path="source.json",
                completed_at="now",
            )
            self.assertTrue(r.committed)
        finally:
            temp.cleanup()

    def test_duplicate_commit_blocked(self):
        temp, _, c = self.make()
        try:
            payload=result(final_status="CANCELED")
            one=c.commit(
                terminal_result=payload,
                source_result_path="source.json",
                completed_at="now",
            )
            two=c.commit(
                terminal_result=payload,
                source_result_path="source.json",
                completed_at="later",
            )
            self.assertTrue(one.committed)
            self.assertEqual(two.state,TerminalCommitState.DUPLICATE_COMMIT)
            self.assertFalse(two.committed)
            self.assertTrue(two.duplicate_commit)
        finally:
            temp.cleanup()

    def test_missing_identity_safe_mode(self):
        temp, _, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(
                    client_order_id="",
                    final_status="FILLED",
                    filled_quantity="1",
                    remaining_quantity="0",
                ),
                source_result_path="source.json",
                completed_at="now",
            )
            self.assertEqual(r.state,TerminalCommitState.SAFE_MODE)
        finally:
            temp.cleanup()

    def test_unknown_status_safe_mode(self):
        temp, _, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(final_status="MYSTERY"),
                source_result_path="source.json",
                completed_at="now",
            )
            self.assertTrue(r.safe_mode_engaged)
        finally:
            temp.cleanup()

    def test_all_ledgers_written(self):
        temp, base, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(final_status="CANCELED"),
                source_result_path="source.json",
                completed_at="now",
            )
            self.assertTrue(r.completion_ledger_written)
            self.assertTrue(r.audit_ledger_written)
            self.assertTrue(r.unlock_ledger_written)
            self.assertEqual(len(JsonlLedger(base/"completion.jsonl").read_all()),1)
            self.assertEqual(len(JsonlLedger(base/"audit.jsonl").read_all()),1)
            self.assertEqual(len(JsonlLedger(base/"unlock.jsonl").read_all()),1)
        finally:
            temp.cleanup()

    def test_commit_id_deterministic(self):
        temp, _, c = self.make()
        try:
            payload=result(final_status="CANCELED")
            one=c.commit(
                terminal_result=payload,
                source_result_path="one.json",
                completed_at="one",
            )
            two=c.commit(
                terminal_result=payload,
                source_result_path="two.json",
                completed_at="two",
            )
            self.assertEqual(one.commit_id,two.commit_id)
        finally:
            temp.cleanup()

    def test_zero_broker_writes(self):
        temp, _, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(),
                source_result_path="source.json",
                completed_at="",
                network_requests_executed=9,
            )
            self.assertEqual(r.network_requests_executed,9)
            self.assertEqual(r.write_requests_executed,0)
            self.assertEqual(r.actual_paper_orders_submitted,0)
            self.assertEqual(r.live_orders_submitted,0)
        finally:
            temp.cleanup()

    def test_json(self):
        temp, _, c = self.make()
        try:
            r=c.commit(
                terminal_result=result(),
                source_result_path="source.json",
                completed_at="",
            )
            self.assertEqual(r.to_json_dict()["state"],"CONTINUE_TRACKING")
        finally:
            temp.cleanup()


if __name__=="__main__":
    unittest.main()
