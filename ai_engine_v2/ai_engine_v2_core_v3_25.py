from .common import safe_status

def build_ai_engine_v2_core(shadow,evaluation,gate,registry,selector,portfolio):
    components={
        "shadow_challenger":shadow.get("status"),
        "evaluation":evaluation.get("status"),
        "promotion_gate":gate.get("status"),
        "strategy_registry":registry.get("status"),
        "regime_selector":selector.get("status"),
        "portfolio_intelligence":portfolio.get("status"),
    }
    return safe_status("V3.25_AI_TRADING_ENGINE_V2_CORE","PASS_DEVELOPMENT_READY",
        components=components,component_count=len(components),
        real_evidence_required=True,execution_enabled=False)
