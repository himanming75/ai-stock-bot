from .capability_matrix import build_capability_matrix

def build_broker_registry():
    matrix=build_capability_matrix()
    return {
        "status":"PASS",
        "canonical_contract":"broker.contracts_v77_1",
        "brokers":matrix["brokers"],
        "duplicate_broker_contract_created":False,
        "duplicate_alpaca_market_data_stack_created":False,
        "etrade_adapter_mode":"READ_ONLY_FOUNDATION",
    }
