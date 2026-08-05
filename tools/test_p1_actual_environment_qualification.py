from __future__ import annotations

import unittest

from actual_environment.certificate import build_certificate
from actual_environment.qualification import fingerprint


class Tests(unittest.TestCase):
    def test_fingerprint_is_not_plaintext(self):
        raw = "secret-value"
        value = fingerprint(raw)
        self.assertNotEqual(value, raw)
        self.assertEqual(len(value), 16)

    def test_empty_fingerprint(self):
        self.assertEqual(fingerprint(""), "")

    def test_pass_certificate_allows_only_p2_read(self):
        certificate = build_certificate({
            "qualified": True,
            "status": "PASS",
            "failed": [],
        })
        self.assertTrue(certificate["p2_actual_broker_read_allowed"])
        self.assertFalse(certificate["p3_actual_paper_order_allowed"])
        self.assertFalse(certificate["live_order_submission_allowed"])

    def test_fail_certificate_blocked(self):
        certificate = build_certificate({
            "qualified": False,
            "status": "FAIL",
            "failed": ["x"],
        })
        self.assertFalse(certificate["eligible"])
        self.assertEqual(certificate["status"], "BLOCKED")

    def test_p1_never_submits_orders(self):
        certificate = build_certificate({
            "qualified": True,
            "status": "PASS",
            "failed": [],
        })
        self.assertEqual(
            certificate["actual_orders_submitted_during_p1"], 0
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
