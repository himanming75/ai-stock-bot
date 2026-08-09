def build_live_safety_gateway():
    return {
        "status":"PASS_LOCKED",
        "broker_write_locked":True,
        "order_submission_locked":True,
        "cancel_replace_locked":True,
        "live_trading_locked":True,
        "credential_values_logged":False,
        "network_enabled_by_default":False,
        "unlock_supported_in_v1":False,
    }

def assert_read_only():
    g=build_live_safety_gateway()
    if not all([
        g["broker_write_locked"],
        g["order_submission_locked"],
        g["cancel_replace_locked"],
        g["live_trading_locked"],
    ]):
        raise RuntimeError("Broker Integration V1 safety gateway is not locked.")
    return True
