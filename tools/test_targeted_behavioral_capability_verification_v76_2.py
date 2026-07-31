import json, tempfile, unittest
from pathlib import Path
from tools.targeted_behavioral_capability_verification_v76_2 import (
    VerificationError, digest, load_config, run_verification, validate_config
)

def config(commands):
    return {
        "verification_scope": "TARGETED_BEHAVIORAL_CAPABILITY_VERIFICATION",
        "capability_id": "FEATURE_PIPELINE",
        "offline_only": True,
        "preserve_repository": True,
        "require_zero_trading_side_effects": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "repository_mutation_allowed": False,
        "live_approval_allowed": False,
        "verification_commands": commands,
    }

class TestV762(unittest.TestCase):
    def make_script(self, root, name, body):
        path = Path(root)/name
        path.write_text(body, encoding="utf-8")
        return path

    def test_all_pass(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_script(d, "a.py", "print('ok')\n")
            result = run_verification(Path(d), config([{
                "verification_id":"A","script":"a.py","required":True,"timeout_seconds":10
            }]))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["capability_state"], "BEHAVIOR_VERIFIED")

    def test_failure_detected(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_script(d, "a.py", "raise SystemExit(4)\n")
            result = run_verification(Path(d), config([{
                "verification_id":"A","script":"a.py","required":True,"timeout_seconds":10
            }]))
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["failed_count"], 1)

    def test_missing_detected(self):
        with tempfile.TemporaryDirectory() as d:
            result = run_verification(Path(d), config([{
                "verification_id":"A","script":"missing.py","required":True,"timeout_seconds":10
            }]))
            self.assertEqual(result["missing_count"], 1)

    def test_optional_missing_does_not_fail(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_script(d, "a.py", "print('ok')\n")
            result = run_verification(Path(d), config([
                {"verification_id":"A","script":"a.py","required":True,"timeout_seconds":10},
                {"verification_id":"B","script":"missing.py","required":False,"timeout_seconds":10},
            ]))
            self.assertEqual(result["status"], "PASS")

    def test_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_script(d, "a.py", "import time; time.sleep(2)\n")
            result = run_verification(Path(d), config([{
                "verification_id":"A","script":"a.py","required":True,"timeout_seconds":1
            }]))
            self.assertTrue(result["records"][0]["timed_out"])

    def test_output_captured(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_script(d, "a.py", "print('hello')\n")
            result = run_verification(Path(d), config([{
                "verification_id":"A","script":"a.py","required":True,"timeout_seconds":10
            }]))
            self.assertIn("hello", result["records"][0]["stdout"])

    def test_script_hash_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_script(d, "a.py", "print('hello')\n")
            result = run_verification(Path(d), config([{
                "verification_id":"A","script":"a.py","required":True,"timeout_seconds":10
            }]))
            self.assertEqual(len(result["records"][0]["script_sha256"]), 64)

    def test_no_side_effect_claims(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_script(d, "a.py", "pass\n")
            result = run_verification(Path(d), config([{
                "verification_id":"A","script":"a.py","required":True,"timeout_seconds":10
            }]))
            self.assertEqual(result["orders_submitted"], 0)
            self.assertFalse(result["network_allowed"])
            self.assertFalse(result["approved_for_live"])

    def test_deterministic_digest(self):
        self.assertEqual(digest({"b":2,"a":1}), digest({"a":1,"b":2}))

    def test_wrong_capability_rejected(self):
        c = config([{"verification_id":"A","script":"a.py","timeout_seconds":10}])
        c["capability_id"] = "RISK_ENGINE"
        with self.assertRaises(VerificationError):
            validate_config(c)

    def test_unsafe_config_rejected(self):
        c = config([{"verification_id":"A","script":"a.py","timeout_seconds":10}])
        c["network_allowed"] = True
        with self.assertRaises(VerificationError):
            validate_config(c)

    def test_duplicate_id_rejected(self):
        c = config([
            {"verification_id":"A","script":"a.py","timeout_seconds":10},
            {"verification_id":"A","script":"b.py","timeout_seconds":10},
        ])
        with self.assertRaises(VerificationError):
            validate_config(c)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(VerificationError):
                run_verification(Path(d), config([{
                    "verification_id":"A","script":"../a.py","timeout_seconds":10
                }]))

    def test_config_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"c.json"
            expected=config([{"verification_id":"A","script":"a.py","timeout_seconds":10}])
            p.write_text(json.dumps(expected), encoding="utf-8")
            self.assertEqual(load_config(p), expected)

if __name__ == "__main__":
    unittest.main()
