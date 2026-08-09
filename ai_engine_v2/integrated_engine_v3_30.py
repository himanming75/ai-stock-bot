from .shadow_challenger_v3_19 import build_shadow_challenger
from .champion_challenger_evaluation_v3_20 import evaluate_champion_vs_challenger
from .promotion_gate_v3_21 import build_promotion_gate
from .strategy_registry_v3_22 import build_strategy_registry
from .regime_selector_v3_23 import build_regime_selector
from .portfolio_intelligence_v3_24 import build_portfolio_intelligence
from .ai_engine_v2_core_v3_25 import build_ai_engine_v2_core
from .promotion_manager_v3_26 import build_promotion_manager
from .rollback_manager_v3_27 import build_rollback_manager
from .lifecycle_automation_v3_28 import build_lifecycle
from .safety_supervisor_v3_29 import build_safety_supervisor

def build_integrated_ai_engine_v2(analytics,status_payload,shadow_observations=None):
    improvement=analytics.get("strategy_improvement_candidates") or {}
    regime=analytics.get("market_regime_analysis") or {}
    historical=analytics.get("historical") or {}

    shadow=build_shadow_challenger(improvement)
    evaluation=evaluate_champion_vs_challenger(historical,shadow,shadow_observations)
    gate=build_promotion_gate(evaluation)
    registry=build_strategy_registry(shadow)
    selector=build_regime_selector(regime,registry)
    portfolio=build_portfolio_intelligence(status_payload)
    core=build_ai_engine_v2_core(shadow,evaluation,gate,registry,selector,portfolio)
    promotion=build_promotion_manager(gate)
    rollback=build_rollback_manager(registry)
    lifecycle=build_lifecycle(shadow,evaluation,gate,promotion)
    safety=build_safety_supervisor()

    stages={
        "V3.19":shadow,"V3.20":evaluation,"V3.21":gate,"V3.22":registry,
        "V3.23":selector,"V3.24":portfolio,"V3.25":core,"V3.26":promotion,
        "V3.27":rollback,"V3.28":lifecycle,"V3.29":safety,
    }

    evidence_waiting=any(
        str(x.get("status","")).startswith("WAITING")
        for x in stages.values()
    )

    return {
        "stage":"V3.30_INTEGRATED_AUTONOMOUS_AI_ENGINE_V2",
        "status":"PASS_DEVELOPMENT_COMPLETE_WAITING_FOR_EVIDENCE" if evidence_waiting else "PASS_DEVELOPMENT_COMPLETE",
        "development_status":"COMPLETE",
        "real_evidence_status":"IN_PROGRESS" if evidence_waiting else "SUFFICIENT_FOR_CURRENT_GATES",
        "live_trading_status":"LOCKED",
        "automatic_promotion_status":"LOCKED",
        "stage_count":12,
        "stages":stages,
        "contracts":{
            "synthetic_fixture_validates_software_not_profitability":True,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "live_trading_enabled":False,
            "automatic_promotion":False,
            "automatic_strategy_change":False,
            "paper_parameter_change":False,
        },
    }
