from __future__ import annotations
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from multi_broker_etrade_oauth.certification import certify
from multi_broker_etrade_oauth.models import OAuthAccessToken
from multi_broker_etrade_oauth.session import ETradeOAuthSessionManager
from multi_broker_etrade_oauth.storage import JsonTokenStore
from multi_broker_etrade_oauth.transport import FixtureOAuthTransport
from multi_broker_etrade_oauth.workflow import ETradeOAuthWorkflow


class Tests(unittest.TestCase):
    def workflow(self):
        responses = {
            ETradeOAuthWorkflow.REQUEST_TOKEN_URL: (
                "oauth_token=req&oauth_token_secret=reqsec&"
                "oauth_callback_confirmed=true"
            ),
            ETradeOAuthWorkflow.ACCESS_TOKEN_URL: (
                "oauth_token=acc&oauth_token_secret=accsec"
            ),
            ETradeOAuthWorkflow.RENEW_TOKEN_URL: (
                "oauth_token=acc&renewed=true"
            ),
            ETradeOAuthWorkflow.REVOKE_TOKEN_URL: (
                "revoked=true"
            ),
        }
        return ETradeOAuthWorkflow(
            consumer_key="key",
            consumer_secret="secret",
            transport=FixtureOAuthTransport(responses),
        )

    def test_request_and_access_token(self):
        workflow = self.workflow()
        request = workflow.request_token()
        access = workflow.access_token(request, verifier="12345")
        self.assertTrue(request.callback_confirmed)
        self.assertEqual(access.oauth_token, "acc")

    def test_authorization_url(self):
        workflow = self.workflow()
        request = workflow.request_token()
        self.assertIn("token=req", workflow.authorization_url(request))

    def test_renew_revoke(self):
        workflow = self.workflow()
        token = OAuthAccessToken(
            oauth_token="acc",
            oauth_token_secret="accsec",
            issued_at_utc=datetime.now(timezone.utc).isoformat(),
            environment="SANDBOX",
        )
        self.assertTrue(workflow.renew(token))
        self.assertTrue(workflow.revoke(token))

    def test_inactivity_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = ETradeOAuthSessionManager(
                JsonTokenStore(Path(directory) / "state.json")
            )
            token = OAuthAccessToken(
                oauth_token="acc",
                oauth_token_secret="accsec",
                issued_at_utc=datetime.now(timezone.utc).isoformat(),
                environment="SANDBOX",
            )
            manager.save_access_token(token)
            now = datetime.now(timezone.utc)
            state = manager.state(
                now=now,
                last_activity_utc=now - timedelta(hours=3),
            )
            self.assertTrue(state.renew_required)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = certify(Path(directory))
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(
                result["actual_sandbox_network_validation_performed"]
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = certify(Path(directory))
            self.assertFalse(result["actual_broker_write_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
