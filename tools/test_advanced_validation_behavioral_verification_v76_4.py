import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.advanced_validation_behavioral_verification_v76_4 import (
    VerificationError,
    digest,
    load_config,
    normalize_output,
    run_verification,
    safety_environment,
    tracked_snapshot,
    validate_config,
    write_outputs,
)


def config(scenarios, repeat_count=2):
    return {
        "verification_scope": "ADVANCED_VALIDATION_BEHAVIORAL_VERIFICATION",
        "offline_only": True,
        "preserve_repository": True,
        "require_zero_trading_side_effects": True,
        "require_all_scenarios_pass": True,
        "require_repeatability": True,
        "verify_tracked_file_immutability": True,
        "repeat_count": repeat_count,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "repository_mutation_allowed": False,
        "live_approval_allowed": False,
        "scenarios": scenarios,
    }


def scenario(identifier, script, timeout=10):
    return {
        "scenario_id": identifier,
        "name": identifier,
        "script": script,
        "timeout_seconds": timeout,
    }


class TestV764(unittest.TestCase):
    def init_repo(self, root):
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=root, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=root, check=True
        )

    def add_and_commit(self, root):
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=root, check=True, capture_output=True
        )

    def write(self, root, name, body):
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_repeatable_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            self.init_repo(directory)
            self.write(directory, "a.py", "print('stable')\n")
            self.add_and_commit(directory)
            result = run_verification(
                Path(directory), config([scenario("A", "a.py")])
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["all_outputs_repeatable"])

    def test_nonrepeatable_output_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            self.init_repo(directory)
            self.write(
                directory, "a.py",
                "import uuid; print(uuid.uuid4())\n"
            )
            self.add_and_commit(directory)
            result = run_verification(
                Path(directory), config([scenario("A", "a.py")])
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["all_outputs_repeatable"])

    def test_failure_exit_code_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            self.init_repo(directory)
            self.write(directory, "a.py", "raise SystemExit(2)\n")
            self.add_and_commit(directory)
            result = run_verification(
                Path(directory), config([scenario("A", "a.py")])
            )
            self.assertEqual(result["status"], "FAIL")

    def test_tracked_mutation_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.init_repo(directory)
            self.write(directory, "data.txt", "before\n")
            self.write(
                directory, "a.py",
                "from pathlib import Path\n"
                "Path('data.txt').write_text('after\\n')\n"
                "print('done')\n"
            )
            self.add_and_commit(directory)
            result = run_verification(
                Path(directory), config([scenario("A", "a.py")])
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("data.txt", result["changed_tracked_files"])

    def test_untracked_output_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.init_repo(directory)
            self.write(
                directory, "a.py",
                "from pathlib import Path\n"
                "Path('output.tmp').write_text('x')\n"
                "print('done')\n"
            )
            self.add_and_commit(directory)
            result = run_verification(
                Path(directory), config([scenario("A", "a.py")])
            )
            self.assertTrue(result["tracked_file_immutability_verified"])

    def test_missing_script_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            self.init_repo(directory)
            self.write(directory, "tracked.txt", "x\n")
            self.add_and_commit(directory)
            result = run_verification(
                Path(directory), config([scenario("A", "missing.py")])
            )
            self.assertEqual(result["status"], "FAIL")

    def test_output_normalizes_test_duration(self):
        first = "Ran 10 tests in 1.234s\nOK"
        second = "Ran 10 tests in 9.876s\nOK"
        self.assertEqual(normalize_output(first), normalize_output(second))

    def test_pythonpath_added(self):
        with tempfile.TemporaryDirectory() as directory:
            env = safety_environment(Path(directory))
            first = env["PYTHONPATH"].split(os.pathsep)[0]
            self.assertEqual(Path(first).resolve(), Path(directory).resolve())

    def test_duplicate_scenario_rejected(self):
        value = config([
            scenario("A", "a.py"),
            scenario("A", "b.py"),
        ])
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_repeat_count_rejected(self):
        value = config([scenario("A", "a.py")], repeat_count=1)
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_unsafe_flag_rejected(self):
        value = config([scenario("A", "a.py")])
        value["network_allowed"] = True
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.init_repo(directory)
            self.write(directory, "tracked.txt", "x\n")
            self.add_and_commit(directory)
            with self.assertRaises(VerificationError):
                run_verification(
                    Path(directory),
                    config([scenario("A", "../outside.py")])
                )

    def test_config_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            expected = config([scenario("A", "a.py")])
            path.write_text(json.dumps(expected), encoding="utf-8")
            self.assertEqual(load_config(path), expected)

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_repo(root)
            self.write(root, "a.py", "print('stable')\n")
            self.add_and_commit(root)
            result = run_verification(
                root, config([scenario("A", "a.py")])
            )
            outputs = write_outputs(result, root / "output")
            self.assertEqual(len(outputs), 2)
            self.assertTrue(all(path.exists() for path in outputs))

    def test_snapshot_hashes_tracked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_repo(root)
            self.write(root, "a.txt", "alpha\n")
            self.add_and_commit(root)
            snapshot = tracked_snapshot(root)
            self.assertIn("a.txt", snapshot)
            self.assertEqual(len(snapshot["a.txt"]), 64)

    def test_zero_side_effect_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_repo(root)
            self.write(root, "a.py", "print('stable')\n")
            self.add_and_commit(root)
            result = run_verification(
                root, config([scenario("A", "a.py")])
            )
            self.assertEqual(result["orders_submitted"], 0)
            self.assertFalse(result["network_allowed"])
            self.assertFalse(result["approved_for_live"])

    def test_deterministic_digest(self):
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )


if __name__ == "__main__":
    unittest.main()
