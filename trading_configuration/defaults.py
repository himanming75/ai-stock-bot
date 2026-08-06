from __future__ import annotations
from copy import deepcopy


PROFILES = {
    "READ_ONLY": {
        "display_name": "Read-Only",
        "risk_level": "NONE",
        "trading_style": "MONITOR_ONLY",
        "max_positions": 0,
        "max_position_percent": 0.0,
        "max_daily_loss_percent": 0.0,
        "cash_reserve_percent": 100.0,
        "allow_short": False,
        "allow_extended_hours": False,
    },
    "CONSERVATIVE": {
        "display_name": "Conservative",
        "risk_level": "LOW",
        "trading_style": "SWING",
        "max_positions": 3,
        "max_position_percent": 10.0,
        "max_daily_loss_percent": 0.5,
        "cash_reserve_percent": 50.0,
        "allow_short": False,
        "allow_extended_hours": False,
    },
    "BALANCED": {
        "display_name": "Balanced",
        "risk_level": "MEDIUM",
        "trading_style": "DAY_SWING",
        "max_positions": 5,
        "max_position_percent": 15.0,
        "max_daily_loss_percent": 1.0,
        "cash_reserve_percent": 30.0,
        "allow_short": False,
        "allow_extended_hours": False,
    },
    "AGGRESSIVE": {
        "display_name": "Aggressive",
        "risk_level": "HIGH",
        "trading_style": "DAY_TRADING",
        "max_positions": 8,
        "max_position_percent": 20.0,
        "max_daily_loss_percent": 2.0,
        "cash_reserve_percent": 15.0,
        "allow_short": True,
        "allow_extended_hours": False,
    },
}


STRATEGIES = {
    "EMA": {
        "enabled": True,
        "fast_period": 9,
        "slow_period": 21,
        "weight": 1.0,
    },
    "RSI": {
        "enabled": True,
        "period": 14,
        "oversold": 30,
        "overbought": 70,
        "weight": 1.0,
    },
    "MACD": {
        "enabled": False,
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "weight": 1.0,
    },
    "VWAP": {
        "enabled": False,
        "deviation_percent": 1.0,
        "weight": 1.0,
    },
    "BREAKOUT": {
        "enabled": False,
        "lookback_bars": 20,
        "volume_multiplier": 1.5,
        "weight": 1.0,
    },
}


def new_draft() -> dict:
    profile = deepcopy(PROFILES["READ_ONLY"])
    return {
        "profile_key": "READ_ONLY",
        "profile": profile,
        "account_scope": "ALL_READ_ONLY",
        "symbols": ["SPY", "QQQ"],
        "capital_limit": 0.0,
        "strategies": deepcopy(STRATEGIES),
        "execution": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "activation_enabled": False,
            "mode": "DRAFT_ONLY",
        },
    }
