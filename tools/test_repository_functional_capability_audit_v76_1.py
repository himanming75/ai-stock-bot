import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.repository_functional_capability_audit_v76_1 import (
    RepositoryAuditError,
    audit_repository,
    main,
    normalize_path,
    read_path_list,
    sha256_of,
)


def make_config():
    return {
        "audit_scope": "REPOSITORY_FUNCTIONAL_CAPABILITY_AUDIT",
        "offline_only": True,
        "filename_evidence_only": True,
        "preserve_repository": True,
        "require_tracked_file_evidence": True,
        "require_test_evidence": True,
        "require_release_evidence": True,
        "require_conservative_classification": True,
        "require_zero_trading_side_effects": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "repository_mutation_allowed": False,
        "live_approval_allowed": False,
        "capabilities": [
            {
                "capability_id": "MARKET_DATA_PIPELINE",
                "name": "Market Data Pipeline",
                "category": "DATA",
                "evidence_rules": {
                    "implementation": ["data/*market*.py", "backtest/*data_feed*.py"],
                    "tests": ["test_*market*.py", "test_*data_feed*.py"],
                    "release": ["release/*/audit/*market_data*.json"],
                },
            },
            {
                "capability_id": "RISK_ENGINE",
                "name": "Risk Engine",
                "category": "RISK",
                "evidence_rules": {
                    "implementation": ["backtest/*risk*.py"],
                    "tests": ["test_*risk*.py"],
                    "release": ["release/*/audit/*risk*.json"],
                },
            },
        ],
    }


class TestV761(unittest.TestCase):
    def test_complete_when_all_evidence_categories_exist(self):
        result = audit_repository(
            [
                "data/market.py",
                "test_market.py",
                "release/v41/audit/market_data_result_v41_0.json",
            ],
            [
                "data/market.py",
                "test_market.py",
                "release/v41/audit/market_data_result_v41_0.json",
            ],
            make_config(),
        )
        item = result["capabilities"][0]
        self.assertEqual(item["state"], "COMPLETE")
        self.assertFalse(item["behavior_verified"])

    def test_partial_without_release(self):
        result = audit_repository(
            ["backtest/risk.py", "test_risk.py"],
            ["backtest/risk.py", "test_risk.py"],
            make_config(),
        )
        risk = result["capabilities"][1]
        self.assertEqual(risk["state"], "PARTIAL")

    def test_missing_without_evidence(self):
        result = audit_repository([], [], make_config())
        self.assertEqual(result["missing_count"], 2)

    def test_local_only_detected(self):
        result = audit_repository(
            [],
            ["backtest/risk.py"],
            make_config(),
        )
        risk = result["capabilities"][1]
        self.assertEqual(risk["state"], "PARTIAL")
        self.assertEqual(risk["local_only_evidence_count"], 1)

    def test_windows_paths_normalized(self):
        result = audit_repository(
            [
                r"data\market.py",
                r"test_market.py",
                r"release\v41\audit\market_data_result_v41_0.json",
            ],
            [
                r"data\market.py",
                r"test_market.py",
                r"release\v41\audit\market_data_result_v41_0.json",
            ],
            make_config(),
        )
        self.assertEqual(result["capabilities"][0]["state"], "COMPLETE")

    def test_duplicate_paths_removed(self):
        result = audit_repository(
            ["data/market.py", "data/market.py"],
            ["data/market.py", "data/market.py"],
            make_config(),
        )
        self.assertEqual(result["tracked_file_count"], 1)

    def test_missing_on_disk_detected(self):
        result = audit_repository(
            ["data/market.py", "test_market.py"],
            ["data/market.py"],
            make_config(),
        )
        self.assertEqual(result["tracked_missing_on_disk_count"], 1)
        self.assertIn("test_market.py", result["missing_on_disk_paths"])

    def test_deterministic_audit_id(self):
        tracked = ["data/market.py", "test_market.py"]
        a = audit_repository(tracked, tracked, make_config())
        b = audit_repository(tracked, tracked, make_config())
        self.assertEqual(a["audit_id"], b["audit_id"])

    def test_audit_hash(self):
        result = audit_repository([], [], make_config())
        observed = result.pop("audit_sha256")
        self.assertEqual(observed, sha256_of(result))

    def test_no_side_effects(self):
        result = audit_repository([], [], make_config())
        self.assertEqual(result["orders_submitted"], 0)
        self.assertEqual(result["repository_mutations"], 0)
        self.assertFalse(result["network_used"])
        self.assertFalse(result["broker_connected"])
        self.assertFalse(result["approved_for_live"])

    def test_input_not_mutated(self):
        config = make_config()
        before = copy.deepcopy(config)
        audit_repository([], [], config)
        self.assertEqual(config, before)

    def test_unsafe_config_rejected(self):
        config = make_config()
        config["order_submission_allowed"] = True
        with self.assertRaises(RepositoryAuditError):
            audit_repository([], [], config)

    def test_utf16_path_list(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "files.txt"
            path.write_text("data/market.py\n", encoding="utf-16")
            self.assertEqual(read_path_list(path), ["data/market.py"])

    def test_main_writes_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = root / "tracked.txt"
            all_files = root / "all.txt"
            config = root / "config.json"
            output = root / "output"
            tracked.write_text(
                "data/market.py\ntest_market.py\n"
                "release/v41/audit/market_data_result_v41_0.json\n",
                encoding="utf-16",
            )
            all_files.write_text(
                "data/market.py\ntest_market.py\n"
                "release/v41/audit/market_data_result_v41_0.json\n",
                encoding="utf-16",
            )
            config.write_text(json.dumps(make_config()), encoding="utf-8")
            rc = main([
                "--tracked-files", str(tracked),
                "--all-files", str(all_files),
                "--config", str(config),
                "--output-dir", str(output),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(
                (output / "repository_functional_capability_audit_v76_1.json").exists()
            )

    def test_main_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text(json.dumps(make_config()), encoding="utf-8")
            rc = main([
                "--tracked-files", str(root / "missing.txt"),
                "--all-files", str(root / "also_missing.txt"),
                "--config", str(config),
                "--output-dir", str(root / "output"),
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
