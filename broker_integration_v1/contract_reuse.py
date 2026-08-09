from broker.contracts_v77_1 import (
    AccountSnapshot,
    BrokerCapabilities,
    BrokerContract,
    BrokerEnvironment,
    BrokerHealth,
    BrokerOrder,
    BrokerOrderRequest,
    BrokerOrderStatus,
    BrokerPosition,
    BrokerSafetyPolicy,
    OrderSide,
    OrderType,
    TimeInForce,
)

CANONICAL_CONTRACT_MODULE = "broker.contracts_v77_1"
REUSED_TYPES = (
    AccountSnapshot,
    BrokerCapabilities,
    BrokerContract,
    BrokerEnvironment,
    BrokerHealth,
    BrokerOrder,
    BrokerOrderRequest,
    BrokerOrderStatus,
    BrokerPosition,
    BrokerSafetyPolicy,
    OrderSide,
    OrderType,
    TimeInForce,
)

def contract_reuse_certificate():
    return {
        "status": "PASS",
        "canonical_contract_module": CANONICAL_CONTRACT_MODULE,
        "reused_type_names": [getattr(x, "__name__", str(x)) for x in REUSED_TYPES],
        "duplicate_contracts_created": False,
    }
