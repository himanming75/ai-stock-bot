import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.stable_release_functional_capability_baseline_v76_0 import (
    CapabilityBaselineError,
    build_baseline,
    main,
    sha256_of,
)


def make_config():
    return {
        "transition_scope":
            "STABLE_RELEASE_TRANSITION_AND_FUNCTIONAL_CAPABILITY_BASELINE",
        "audit_evidence_anchor": "V75.2BE",
        "freeze_audit_evidence_layer": True,
        "preserve_existing_capabilities": True,
        "require_deterministic_baseline_id": True,
        "require_capability_inventory": True,
        "require_acceptance_gates": True,
        "require_gap_plan": True,
        "require_zero_trading_side_effects": True,
        "require_offline_only": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_order_submission_allowed": False,
        "paper_order_submission_allowed": False,
        "live_order_submission_allowed": False,
        "settlement_mutation_allowed": False,
        "cash_mutation_allowed": False,
        "position_mutation_allowed": False,
        "portfolio_mutation_allowed": False,
        "required_capabilities": [
            {
                "capability_id": "MARKET_DATA_PIPELINE",
                "name": "Market Data Pipeline",
                "category": "DATA",
                "required_for_stable_release": True,
                "default_next_action": "IMPLEMENT_AND_VALIDATE_MARKET_DATA_PIPELINE",
            },
            {
                "capability_id": "STRATEGY_ENGINE",
                "name": "Strategy Engine",
                "category": "DECISION",
                "required_for_stable_release": True,
                "default_next_action": "IMPLEMENT_AND_VALIDATE_STRATEGY_ENGINE",
            },
            {
                "capability_id": "BACKTEST_ENGINE",
                "name": "Backtest Engine",
                "category": "VALIDATION",
                "required_for_stable_release": True,
                "default_next_action": "IMPLEMENT_AND_VALIDATE_BACKTEST_ENGINE",
            },
        ],
    }


def make_inventory(states=None):
    states = states or {
        "MARKET_DATA_PIPELINE": "COMPLETE",
        "STRATEGY_ENGINE": "PARTIAL",
        "BACKTEST_ENGINE": "MISSING",
    }
    return {
        "inventory_scope": "AI_STOCK_BOT_FUNCTIONAL_INVENTORY",
        "capabilities": [
            {
                "capability_id": capability_id,
                "state": state,
                "evidence": (
                    [f"test:{capability_id.lower()}"]
                    if state == "COMPLETE"
                    else []
                ),
                "notes": "",
            }
            for capability_id, state in states.items()
        ],
    }


class TestV760(unittest.TestCase):
    def test_build_passes(self):
        out = build_baseline(make_inventory(), make_config())
        self.assertEqual(out["status"], "PASS")

    def test_audit_layer_frozen(self):
        out = build_baseline(make_inventory(), make_config())
        self.assertEqual(
            out["audit_evidence_layer"]["state"],
            "FROZEN_AS_BASELINE",
        )
        self.assertFalse(out["audit_evidence_layer"]["removal_allowed"])

    def test_gap_count(self):
        out = build_baseline(make_inventory(), make_config())
        self.assertEqual(out["complete_capability_count"], 1)
        self.assertEqual(out["functional_gap_count"], 2)
        self.assertFalse(out["stable_release_ready"])

    def test_missing_inventory_item_becomes_missing(self):
        inventory = make_inventory()
        inventory["capabilities"] = inventory["capabilities"][:1]
        out = build_baseline(inventory, make_config())
        by_id = {
            item["capability_id"]: item
            for item in out["capability_inventory"]
        }
        self.assertEqual(by_id["STRATEGY_ENGINE"]["state"], "MISSING")
        self.assertEqual(by_id["BACKTEST_ENGINE"]["state"], "MISSING")

    def test_all_complete_ready(self):
        states = {
            "MARKET_DATA_PIPELINE": "COMPLETE",
            "STRATEGY_ENGINE": "COMPLETE",
            "BACKTEST_ENGINE": "COMPLETE",
        }
        out = build_baseline(make_inventory(states), make_config())
        self.assertTrue(out["stable_release_ready"])
        self.assertEqual(out["functional_gap_count"], 0)
        self.assertEqual(
            out["next_phase"], "CREATE_STABLE_RELEASE_CANDIDATE"
        )

    def test_deterministic_id(self):
        a = build_baseline(make_inventory(), make_config())
        b = build_baseline(make_inventory(), make_config())
        self.assertEqual(a["baseline_id"], b["baseline_id"])

    def test_output_hash(self):
        out = build_baseline(make_inventory(), make_config())
        observed = out.pop("baseline_sha256")
        self.assertEqual(observed, sha256_of(out))

    def test_gap_priority(self):
        inventory = make_inventory({
            "MARKET_DATA_PIPELINE": "PARTIAL",
            "STRATEGY_ENGINE": "BLOCKED",
            "BACKTEST_ENGINE": "MISSING",
        })
        out = build_baseline(inventory, make_config())
        self.assertEqual(
            [
                item["capability_id"]
                for item in out["functional_gap_plan"]
            ],
            ["STRATEGY_ENGINE", "BACKTEST_ENGINE", "MARKET_DATA_PIPELINE"],
        )

    def test_no_side_effects(self):
        out = build_baseline(make_inventory(), make_config())
        for key in (
            "orders_submitted",
            "settlements_created",
            "cash_mutations",
            "position_mutations",
            "portfolio_mutations",
        ):
            self.assertEqual(out[key], 0)
        self.assertFalse(out["network_used"])
        self.assertFalse(out["broker_connected"])
        self.assertFalse(out["approved_for_live"])

    def test_input_not_mutated(self):
        inventory = make_inventory()
        config = make_config()
        inventory_before = copy.deepcopy(inventory)
        config_before = copy.deepcopy(config)
        build_baseline(inventory, config)
        self.assertEqual(inventory, inventory_before)
        self.assertEqual(config, config_before)

    def test_duplicate_inventory_rejected(self):
        inventory = make_inventory()
        inventory["capabilities"].append(
            copy.deepcopy(inventory["capabilities"][0])
        )
        with self.assertRaises(CapabilityBaselineError):
            build_baseline(inventory, make_config())

    def test_unknown_inventory_rejected(self):
        inventory = make_inventory()
        inventory["capabilities"].append({
            "capability_id": "UNKNOWN",
            "state": "COMPLETE",
            "evidence": [],
        })
        with self.assertRaises(CapabilityBaselineError):
            build_baseline(inventory, make_config())

    def test_invalid_state_rejected(self):
        inventory = make_inventory()
        inventory["capabilities"][0]["state"] = "DONE"
        with self.assertRaises(CapabilityBaselineError):
            build_baseline(inventory, make_config())

    def test_unsafe_config_rejected(self):
        config = make_config()
        config["live_order_submission_allowed"] = True
        with self.assertRaises(CapabilityBaselineError):
            build_baseline(make_inventory(), config)

    def test_acceptance_gate_pending(self):
        out = build_baseline(make_inventory(), make_config())
        gate = next(
            item for item in out["acceptance_gates"]
            if item["gate_id"] == "ALL_REQUIRED_CAPABILITIES_COMPLETE"
        )
        self.assertEqual(gate["state"], "PENDING")

    def test_manifest_counts(self):
        out = build_baseline(make_inventory(), make_config())
        self.assertEqual(out["required_capability_count"], 3)
        self.assertEqual(
            len(out["capability_inventory"]),
            out["required_capability_count"],
        )

    def test_main_writes_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            inventory_path = base / "inventory.json"
            config_path = base / "config.json"
            output_dir = base / "out"
            inventory_path.write_text(
                json.dumps(make_inventory()), encoding="utf-8"
            )
            config_path.write_text(
                json.dumps(make_config()), encoding="utf-8"
            )
            rc = main([
                "--inventory", str(inventory_path),
                "--config", str(config_path),
                "--output-dir", str(output_dir),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(
                (
                    output_dir
                    / "stable_release_functional_capability_baseline_v76_0.json"
                ).exists()
            )
            self.assertTrue(
                (output_dir / "functional_gap_plan_v76_0.json").exists()
            )

    def test_main_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config_path = base / "config.json"
            config_path.write_text(
                json.dumps(make_config()), encoding="utf-8"
            )
            rc = main([
                "--inventory", str(base / "missing.json"),
                "--config", str(config_path),
                "--output-dir", str(base / "out"),
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
