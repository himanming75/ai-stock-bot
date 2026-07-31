import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_release_candidate_evidence_seal_v76_6 import (
    digest,
    verify_ledger,
)


class TestVerifyReleaseCandidateEvidenceSealV766(unittest.TestCase):
    def test_valid_single_entry_ledger(self):
        entry = {
            "sequence": 1,
            "evidence_id": "X",
            "path": "x.json",
            "file_sha256": "a" * 64,
            "record_sha256": "b" * 64,
            "previous_entry_sha256": "0" * 64,
        }
        entry["entry_sha256"] = digest(entry)
        ledger = {
            "entries": [entry],
            "ledger_head_sha256": entry["entry_sha256"],
        }
        self.assertEqual(verify_ledger(ledger), [])

    def test_tampered_entry_detected(self):
        entry = {
            "sequence": 1,
            "evidence_id": "X",
            "path": "x.json",
            "file_sha256": "a" * 64,
            "record_sha256": "b" * 64,
            "previous_entry_sha256": "0" * 64,
        }
        entry["entry_sha256"] = digest(entry)
        entry["path"] = "changed.json"
        ledger = {
            "entries": [entry],
            "ledger_head_sha256": entry["entry_sha256"],
        }
        self.assertTrue(verify_ledger(ledger))


if __name__ == "__main__":
    unittest.main()
