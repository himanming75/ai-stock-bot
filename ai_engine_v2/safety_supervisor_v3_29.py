from .common import safe_status, SAFETY_CONTRACTS

def build_safety_supervisor():
    locks={
        "live_trading_locked":True,
        "broker_write_locked":True,
        "automatic_promotion_locked":True,
        "automatic_strategy_change_locked":True,
        "paper_parameter_change_locked":True,
    }
    return safe_status("V3.29_SAFETY_SUPERVISOR","PASS_LOCKS_ENFORCED",
        locks=locks,contracts=dict(SAFETY_CONTRACTS))
