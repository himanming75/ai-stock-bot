import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.shadow_daily_automation import (
    ShadowDailyAutomation,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        source = {
            "status": "PASS",
            "state": "AUTOMATIC_SHADOW_SIGNAL_PIPELINE_READY",
            "automatic_shadow_signal_pipeline_ready": True,
            "pipeline_id": "pipeline-1",
            "shadow_session_id": "shadow-1",
            "safe_mode_engaged": False,
        }
        policy = {
            "runtime_id": "shadow-runtime-1",
            "shadow_only": True,
            "order_submission_enabled": False,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "continuous_loop_enabled": False,
            "max_retries": 3,
            "heartbeat_interval_minutes": 5,
            "auto_install_task": False,
        }
        recovery = {
            "recovery_required": False,
            "active_runtime_instances": 0,
            "runtime_lock_held": False,
            "signal_queue_corrupted": False,
            "recovery_verified": True,
        }
        evidence = {
            "signal_count": 3,
            "buy_count": 1,
            "sell_count": 1,
            "hold_count": 1,
            "risk_block_count": 0,
            "error_count": 0,
            "total_pnl": 12.5,
            "max_drawdown_pct": 1.2,
            "runtime_seconds": 30,
        }
        return source, policy, recovery, evidence

    def run_case(self, values):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        names = ["source", "policy", "recovery", "evidence"]
        paths = {name: root/f"{name}.json" for name in names}

        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        result = ShadowDailyAutomation().run(
            pipeline_result_path=paths["source"],
            runtime_policy_path=paths["policy"],
            recovery_snapshot_path=paths["recovery"],
            daily_evidence_path=paths["evidence"],
            scheduler_state_path=root/"scheduler.json",
            heartbeat_path=root/"heartbeat.json",
            recovery_report_path=root/"recovery_report.json",
            daily_report_path=root/"daily_report.json",
            automation_token_path=root/"token.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_wait_before_pipeline(self):
        source, policy, recovery, evidence = self.data()
        source = {
            "status": "PASS",
            "state": "WAIT_MULTI_DAY_SHADOW_VALIDATION",
            "automatic_shadow_signal_pipeline_ready": False,
            "safe_mode_engaged": False,
        }
        result, _ = self.run_case(
            (source, policy, recovery, evidence)
        )
        self.assertEqual(
            result["state"],
            "WAIT_AUTOMATIC_SHADOW_PIPELINE",
        )

    def test_daily_automation_ready(self):
        result, root = self.run_case(self.data())
        self.assertEqual(
            result["state"],
            "SHADOW_DAILY_AUTOMATION_READY",
        )
        self.assertTrue(result["shadow_daily_automation_ready"])
        self.assertTrue((root/"daily_report.json").exists())
        self.assertTrue((root/"token.json").exists())

    def test_continuous_loop_blocks(self):
        source, policy, recovery, evidence = self.data()
        policy = dict(policy)
        policy["continuous_loop_enabled"] = True
        result, _ = self.run_case(
            (source, policy, recovery, evidence)
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_runtime_blocks(self):
        source, policy, recovery, evidence = self.data()
        recovery = dict(recovery)
        recovery["active_runtime_instances"] = 2
        result, _ = self.run_case(
            (source, policy, recovery, evidence)
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_corrupted_queue_blocks(self):
        source, policy, recovery, evidence = self.data()
        recovery = dict(recovery)
        recovery["signal_queue_corrupted"] = True
        result, _ = self.run_case(
            (source, policy, recovery, evidence)
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_signal_count_mismatch_blocks(self):
        source, policy, recovery, evidence = self.data()
        evidence = dict(evidence)
        evidence["hold_count"] = 0
        result, _ = self.run_case(
            (source, policy, recovery, evidence)
        )
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
