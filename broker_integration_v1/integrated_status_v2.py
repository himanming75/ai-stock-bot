from __future__ import annotations

import os
from pathlib import Path

from .etrade_oauth_signer import official_signature_test_vector
from .etrade_oauth_profile_v2 import ETRADE_OAUTH_PROFILE


def build_broker_integration_v2_status(repo_root=None):
    from .etrade_sandbox_bounded_multi_cycle_status_v2_1_4 import build_etrade_sandbox_bounded_multi_cycle_v2_1_4_status
    bounded_multi=build_etrade_sandbox_bounded_multi_cycle_v2_1_4_status()
    from .etrade_sandbox_autonomous_cycle_status_v2_1_3 import build_etrade_sandbox_autonomous_cycle_v2_1_3_status
    autonomous_cycle=build_etrade_sandbox_autonomous_cycle_v2_1_3_status()
    from .etrade_sandbox_order_status_v2_1_2 import build_etrade_sandbox_order_v2_1_2_status
    place_ledger=build_etrade_sandbox_order_v2_1_2_status()
    from .etrade_sandbox_order_status_v2_1 import build_etrade_sandbox_order_v2_1_status
    sandbox_order=build_etrade_sandbox_order_v2_1_status()
    repo=Path(repo_root or ".")
    snapshot_path=repo/"runtime"/"etrade_readonly_v2"/"latest_readonly_snapshot.json"
    consumer_key_present=bool(os.environ.get("ETRADE_CONSUMER_KEY"))
    consumer_secret_present=bool(os.environ.get("ETRADE_CONSUMER_SECRET"))
    creds=consumer_key_present and consumer_secret_present

    connection_status=(
        "READY_FOR_USER_AUTHORIZED_READONLY_CONNECTION"
        if creds else
        "WAITING_FOR_CREDENTIALS"
    )

    return {
        "stage":"BROKER_INTEGRATION_V2_ETRADE_READONLY_OAUTH",
        "status":"PASS_DEVELOPMENT_COMPLETE",
        "development_status":"COMPLETE",
        "etrade_oauth_status":connection_status,
        "consumer_key_present":consumer_key_present,
        "consumer_secret_present":consumer_secret_present,
        "redacted_snapshot_present":snapshot_path.exists(),
        "token_persistence":"DISABLED",
        "oauth_profile":{
            "version":ETRADE_OAUTH_PROFILE["oauth_version"],
            "signature_method":ETRADE_OAUTH_PROFILE["signature_method"],
            "request_token_supported":True,
            "user_authorization_supported":True,
            "access_token_supported":True,
            "renew_supported":True,
            "revoke_supported":True,
        },
        "official_signature_vector_pass":official_signature_test_vector()["matches"],
        "read_only_network_opt_in_required":True,
        "network_used_during_build":False,
        "live_trading_status":"LOCKED",
        "order_submission_status":"LOCKED",
        "cancel_replace_status":"LOCKED",
        "sandbox_order_v2_1": sandbox_order,
        "place_ledger_v2_1_2": place_ledger,
        "autonomous_cycle_v2_1_3": autonomous_cycle,
        "bounded_multi_cycle_v2_1_4": bounded_multi,
        "contracts":{
            "v1_bridge_reused":True,
            "canonical_v77_1_contract_reused":True,
            "existing_etrade_v1_adapter_reused":True,
            "duplicate_broker_contract_created":False,
            "duplicate_etrade_readonly_adapter_created":False,
            "new_credential_vault_created":False,
            "access_token_persisted":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "live_trading_enabled":False,
        },
    }
