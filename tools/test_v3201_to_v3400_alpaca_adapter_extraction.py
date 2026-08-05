from __future__ import annotations
import inspect, os, tempfile, unittest
from pathlib import Path

from multi_broker_core.factory import BrokerFactory
from multi_broker_alpaca.credentials import EnvironmentAlpacaCredentialProvider
from multi_broker_alpaca.factory_registration import register_alpaca_adapter
from multi_broker_alpaca.parity import certify, fixture_responses
from multi_broker_alpaca.transport import FixtureTransport


class Tests(unittest.TestCase):
    def adapter(self):
        factory = register_alpaca_adapter(BrokerFactory())
        return factory.create("ALPACA", transport=FixtureTransport(fixture_responses()))

    def test_account_mapping(self):
        account = self.adapter().get_account()
        self.assertEqual(account.broker, "ALPACA")
        self.assertEqual(str(account.equity), "100014.45")

    def test_positions_mapping(self):
        self.assertEqual(len(self.adapter().list_positions()), 2)

    def test_orders_mapping(self):
        self.assertEqual(len(self.adapter().list_orders()), 1)

    def test_submission_blocked(self):
        with self.assertRaises(PermissionError):
            self.adapter().submit_order(None)

    def test_live_endpoint_guard(self):
        old = dict(os.environ)
        try:
            os.environ["APCA_API_KEY_ID"] = "x"
            os.environ["APCA_API_SECRET_KEY"] = "y"
            os.environ["APCA_API_BASE_URL"] = "https://api.alpaca.markets"
            with self.assertRaises(RuntimeError):
                EnvironmentAlpacaCredentialProvider().load()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = certify(Path(d))
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["actual_external_network_used"])

    def test_zero_order_contract(self):
        source = inspect.getsource(certify)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
