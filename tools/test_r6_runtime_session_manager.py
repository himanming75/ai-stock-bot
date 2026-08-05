from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from runtime_session.lock import SessionAlreadyActive, SessionLock
from runtime_session.models import SessionPolicy
from runtime_session.service import resume_preview


class Tests(unittest.TestCase):
    def test_policy(self):
        self.assertTrue(SessionPolicy().validate()["valid"])

    def test_single_instance_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = SessionLock(Path(directory) / "lock.json")
            lock.acquire("a")
            with self.assertRaises(SessionAlreadyActive):
                lock.acquire("b")
            lock.release("a")

    def test_owner_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = SessionLock(Path(directory) / "lock.json")
            lock.acquire("a")
            with self.assertRaises(RuntimeError):
                lock.release("b")

    def test_resume_never_auto_replays(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual = root / "release/r6_runtime_session_manager/actual"
            actual.mkdir(parents=True)
            (actual / "session_checkpoint.json").write_text(
                json.dumps({
                    "session_id": "x",
                    "automatic_order_replay_enabled": False,
                }),
                encoding="utf-8",
            )
            (actual / "heartbeat.json").write_text(
                json.dumps({"session_id": "x"}),
                encoding="utf-8",
            )
            result = resume_preview(root)
        self.assertFalse(result["safe_to_auto_resume"])
        self.assertFalse(result["automatic_order_replay_enabled"])

    def test_missing_checkpoint_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            result = resume_preview(Path(directory))
        self.assertTrue(result["operator_review_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
