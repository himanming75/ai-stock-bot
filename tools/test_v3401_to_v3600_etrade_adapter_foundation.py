from __future__ import annotations
import inspect
import os
import tempfile
import unittest
from pathlib import Path

from multi_broker_core.factory import BrokerFactory
from multi_broker_etrade.certification import (
    ACCOUNT_KEY,
    certify,
    fixture_responses,
    official_signature_vector_passes,
)
from multi_broker_etrade.credentials import EnvironmentETradeCredentialProvider
from multi_broker_etrade.factory_registration import register_etrade_adapter
from multi_broker_etrade.transport import FixtureTransport


class Tests(unittest.TestCase):
    def adapter(self):
        factory = register_etrade_adapter(BrokerFactory())
        return factory.create(
            "ETRADE",
            transport=FixtureTransport(fixture_responses()),
            account_id_key=ACCOUNT_KEY,
        )

    def test_official_signature_vector(self):
        self.assertTrue(official_signature_vector_passes())

    def test_account_mapping(self):
        account = self.adapter().get_account()
        self.assertEqual(account.broker, "ETRADE")
        self.assertEqual(str(account.equity), "100500.75")

    def test_positions_mapping(self):
        self.assertEqual(len(self.adapter().list_positions()), 2)

    def test_orders_mapping(self):
        self.assertEqual(len(self.adapter().list_orders()), 1)

    def test_submission_blocked(self):
        with self.assertRaises(PermissionError):
            self.adapter().submit_order(None)

    def test_production_guard(self):
        old = dict(os.environ)
        try:
            os.environ["ETRADE_ENVIRONMENT"] = "PRODUCTION"
            os.environ["ETRADE_CONSUMER_KEY"] = "x"
            os.environ["ETRADE_CONSUMER_SECRET"] = "y"
            os.environ["ETRADE_ACCESS_TOKEN"] = "z"
            os.environ["ETRADE_ACCESS_SECRET"] = "w"
            os.environ.pop("ETRADE_ALLOW_PRODUCTION_READ", None)
            with self.assertRaises(RuntimeError):
                EnvironmentETradeCredentialProvider().load()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = certify(Path(directory))
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["actual_external_network_used"])

    def test_zero_order_contract(self):
        source = inspect.getsource(certify)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
