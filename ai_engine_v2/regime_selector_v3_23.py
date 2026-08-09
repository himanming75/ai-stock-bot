from .common import safe_status, num

def build_regime_selector(regime, registry):
    cov=regime.get("coverage") or {}
    dc=num(cov.get("direction_coverage")) or 0
    vc=num(cov.get("volatility_coverage")) or 0
    evidence=int(regime.get("evidence_trade_count") or 0)
    if evidence<10 or min(dc,vc)<0.5:
        return safe_status("V3.23_REGIME_AWARE_STRATEGY_SELECTOR",
            "WAITING_FOR_REGIME_EVIDENCE",selector_enabled=False,
            direction_coverage=dc,volatility_coverage=vc,evidence_trade_count=evidence,
            selected_strategy=None,shadow_only=True)
    return safe_status("V3.23_REGIME_AWARE_STRATEGY_SELECTOR",
        "PASS_SHADOW_SELECTOR_READY",selector_enabled=True,
        selected_strategy="CURRENT_CHAMPION",selection_mode="SHADOW_RECOMMENDATION_ONLY",
        direction_coverage=dc,volatility_coverage=vc,evidence_trade_count=evidence,
        shadow_only=True)
