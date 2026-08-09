from broker.contracts_v77_1 import BrokerEnvironment

def build_capability_matrix():
    return {
        "status": "PASS",
        "brokers": {
            "existing_sandbox_contract": {
                "contract_source": "broker.contracts_v77_1",
                "read_account": True,
                "read_positions": True,
                "read_orders": True,
                "submit_orders": False,
                "cancel_orders": False,
                "live": False,
            },
            "alpaca_existing_stack": {
                "contract_source": "existing project modules",
                "market_data_stack_reused": True,
                "new_market_data_client_created": False,
                "read_account_bridge": True,
                "read_positions_bridge": True,
                "read_orders_bridge": True,
                "submit_orders_added_by_v1": False,
                "live": False,
            },
            "etrade_v1_readonly": {
                "auth_protocol": "OAuth 1.0a / HMAC-SHA1",
                "read_accounts": True,
                "read_balances": True,
                "read_positions": True,
                "read_orders": True,
                "market_data": False,
                "submit_orders": False,
                "cancel_orders": False,
                "replace_orders": False,
                "live": False,
                "network_enabled_by_default": False,
            },
        },
        "environment": BrokerEnvironment.OFFLINE.value,
    }
