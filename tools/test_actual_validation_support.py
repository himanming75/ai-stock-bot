from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from broker_integration.actual_validation import validation_status


class Tests(unittest.TestCase):
    def test_missing_records_are_false(self):
        with tempfile.TemporaryDirectory() as directory:
            result = validation_status(Path(directory))
        self.assertFalse(result["p2_actual_validated"])
        self.assertFalse(result["p3_actual_validated"])
        self.assertFalse(result["p4_actual_validated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
