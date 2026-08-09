from __future__ import annotations

from decimal import Decimal

from .etrade_ai_signal_decision_v2_1_5 import (
    normalize_strategy_recommendation,
    decide_signal,
    SignalDecisionPolicy,
)
from .etrade_sandbox_autonomous_cycle_v2_1_3 import SandboxCycleSignal


class ETradeAISignalDecisionBridge:
    def __init__(self,policy=None):
        self.policy=policy or SignalDecisionPolicy()

    def evaluate(self,payload):
        recommendation=normalize_strategy_recommendation(payload)
        decision=decide_signal(recommendation,self.policy)

        result={
            "symbol":recommendation.symbol,
            "strategy_id":recommendation.strategy_id,
            "strategy_action":recommendation.action,
            "confidence":str(recommendation.confidence),
            "decision":decision["decision"],
            "decision_reason":decision["reason"],
            "order_eligible":decision["order_eligible"],
            "sandbox_signal":None,
            "profitability_validated":False,
        }

        if decision["order_eligible"]:
            result["sandbox_signal"]=SandboxCycleSignal(
                symbol=recommendation.symbol,
                side=decision["decision"],
                quantity=Decimal(recommendation.quantity),
                order_type="MARKET",
                strategy_id=recommendation.strategy_id,
            )

        return result

    def build_signal_queue(self,payloads,max_signals=3):
        decisions=[]
        signals=[]

        for payload in payloads:
            result=self.evaluate(payload)
            decisions.append(result)

            if result["order_eligible"]:
                signals.append(result["sandbox_signal"])

            if len(signals)>=max_signals:
                break

        return {
            "decisions":decisions,
            "signals":signals,
            "eligible_signal_count":len(signals),
            "hold_or_block_count":sum(
                1 for x in decisions if not x["order_eligible"]
            ),
            "max_signals":max_signals,
        }
