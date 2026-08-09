from .contract_reuse import contract_reuse_certificate
from .capability_matrix import build_capability_matrix
from .credential_isolation import credential_isolation_certificate
from .etrade_profile import etrade_profile_certificate
from .alpaca_existing_bridge import alpaca_reuse_certificate
from .broker_registry import build_broker_registry
from .live_safety_gateway import build_live_safety_gateway

def build_broker_integration_v1_status():
    return {
        "stage":"BROKER_INTEGRATION_V1_BRIDGE",
        "status":"PASS_DEVELOPMENT_COMPLETE_NETWORK_LOCKED",
        "development_status":"COMPLETE",
        "contract_reuse":contract_reuse_certificate(),
        "capability_matrix":build_capability_matrix(),
        "credential_isolation":credential_isolation_certificate(),
        "etrade_profile":etrade_profile_certificate(),
        "alpaca_reuse":alpaca_reuse_certificate(),
        "broker_registry":build_broker_registry(),
        "live_safety_gateway":build_live_safety_gateway(),
        "network_status":"LOCKED",
        "etrade_auth_status":"NOT_CONFIGURED",
        "etrade_readonly_status":"FOUNDATION_READY",
        "live_trading_status":"LOCKED",
        "contracts":{
            "duplicate_broker_contract_created":False,
            "duplicate_alpaca_market_data_stack_created":False,
            "broker_network_used":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "live_trading_enabled":False,
        },
    }
