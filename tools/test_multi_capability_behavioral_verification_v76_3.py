import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.multi_capability_behavioral_verification_v76_3 import (
    VerificationError,
    digest,
    load_config,
    run_verification,
    validate_config,
    write_outputs,
    safety_environment,
)


def make_config(capabilities):
    return {
        "verification_scope": "MULTI_CAPABILITY_BEHAVIORAL_VERIFICATION",
        "offline_only": True,
        "preserve_repository": True,
        "require_zero_trading_side_effects": True,
        "require_all_capabilities_pass": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "repository_mutation_allowed": False,
        "live_approval_allowed": False,
        "capabilities": capabilities,
    }


def capability(capability_id, script, required=True, timeout=10):
    return {
        "capability_id": capability_id,
        "name": capability_id.replace("_", " ").title(),
        "verification_commands": [{
            "verification_id": f"{capability_id}_TEST",
            "script": script,
            "required": required,
            "timeout_seconds": timeout,
        }],
    }


class TestV763(unittest.TestCase):
    def write_script(self, root, name, body):
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_all_capabilities_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(directory, "a.py", "print('a')\n")
            self.write_script(directory, "b.py", "print('b')\n")
            result = run_verification(
                Path(directory),
                make_config([
                    capability("A", "a.py"),
                    capability("B", "b.py"),
                ]),
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["passed_capability_count"], 2)

    def test_one_capability_failure_fails_overall(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(directory, "a.py", "print('a')\n")
            self.write_script(directory, "b.py", "raise SystemExit(3)\n")
            result = run_verification(
                Path(directory),
                make_config([
                    capability("A", "a.py"),
                    capability("B", "b.py"),
                ]),
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["failed_capability_ids"], ["B"])

    def test_missing_required_script(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_verification(
                Path(directory),
                make_config([capability("A", "missing.py")]),
            )
            self.assertEqual(result["capability_results"][0]["missing_count"], 1)

    def test_optional_missing_does_not_fail_capability(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(directory, "a.py", "print('a')\n")
            config = make_config([{
                "capability_id": "A",
                "name": "A",
                "verification_commands": [
                    {
                        "verification_id": "A_REQUIRED",
                        "script": "a.py",
                        "required": True,
                        "timeout_seconds": 10,
                    },
                    {
                        "verification_id": "A_OPTIONAL",
                        "script": "missing.py",
                        "required": False,
                        "timeout_seconds": 10,
                    },
                ],
            }])
            result = run_verification(Path(directory), config)
            self.assertEqual(result["status"], "PASS")

    def test_timeout_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(
                directory, "slow.py", "import time; time.sleep(2)\n"
            )
            result = run_verification(
                Path(directory),
                make_config([capability("A", "slow.py", timeout=1)]),
            )
            record = result["capability_results"][0]["records"][0]
            self.assertTrue(record["timed_out"])

    def test_output_captured(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(directory, "a.py", "print('hello')\n")
            result = run_verification(
                Path(directory),
                make_config([capability("A", "a.py")]),
            )
            record = result["capability_results"][0]["records"][0]
            self.assertIn("hello", record["stdout"])

    def test_script_hash_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(directory, "a.py", "print('hello')\n")
            result = run_verification(
                Path(directory),
                make_config([capability("A", "a.py")]),
            )
            record = result["capability_results"][0]["records"][0]
            self.assertEqual(len(record["script_sha256"]), 64)

    def test_input_config_not_mutated(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(directory, "a.py", "pass\n")
            config = make_config([capability("A", "a.py")])
            before = copy.deepcopy(config)
            run_verification(Path(directory), config)
            self.assertEqual(config, before)

    def test_zero_side_effect_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_script(directory, "a.py", "pass\n")
            result = run_verification(
                Path(directory),
                make_config([capability("A", "a.py")]),
            )
            self.assertEqual(result["orders_submitted"], 0)
            self.assertEqual(result["repository_mutations_by_verifier"], 0)
            self.assertFalse(result["network_allowed"])
            self.assertFalse(result["approved_for_live"])

    def test_duplicate_capability_rejected(self):
        config = make_config([
            capability("A", "a.py"),
            capability("A", "b.py"),
        ])
        with self.assertRaises(VerificationError):
            validate_config(config)

    def test_duplicate_verification_id_rejected(self):
        config = make_config([
            {
                "capability_id": "A",
                "name": "A",
                "verification_commands": [{
                    "verification_id": "SAME",
                    "script": "a.py",
                    "timeout_seconds": 10,
                }],
            },
            {
                "capability_id": "B",
                "name": "B",
                "verification_commands": [{
                    "verification_id": "SAME",
                    "script": "b.py",
                    "timeout_seconds": 10,
                }],
            },
        ])
        with self.assertRaises(VerificationError):
            validate_config(config)

    def test_unsafe_config_rejected(self):
        config = make_config([capability("A", "a.py")])
        config["order_submission_allowed"] = True
        with self.assertRaises(VerificationError):
            validate_config(config)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(VerificationError):
                run_verification(
                    Path(directory),
                    make_config([capability("A", "../a.py")]),
                )

    def test_config_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            expected = make_config([capability("A", "a.py")])
            path.write_text(json.dumps(expected), encoding="utf-8")
            self.assertEqual(load_config(path), expected)

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_script(root, "a.py", "pass\n")
            result = run_verification(
                root, make_config([capability("A", "a.py")])
            )
            outputs = write_outputs(result, root / "output")
            self.assertEqual(len(outputs), 2)
            self.assertTrue(all(path.exists() for path in outputs))

    def test_deterministic_digest(self):
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )

    def test_repository_root_is_added_to_pythonpath(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = safety_environment(Path(directory))
            first = environment["PYTHONPATH"].split(__import__("os").pathsep)[0]
            self.assertEqual(Path(first).resolve(), Path(directory).resolve())

    def test_tools_package_import_works_from_direct_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tools" / "helper.py").write_text(
                "VALUE = 123\n", encoding="utf-8"
            )
            (root / "tools" / "runner.py").write_text(
                "from tools.helper import VALUE\n"
                "print(VALUE)\n",
                encoding="utf-8",
            )
            result = run_verification(
                root,
                make_config([capability("TOOLS_IMPORT", "tools/runner.py")]),
            )
            self.assertEqual(result["status"], "PASS")
            record = result["capability_results"][0]["records"][0]
            self.assertIn("123", record["stdout"])


if __name__ == "__main__":
    unittest.main()
