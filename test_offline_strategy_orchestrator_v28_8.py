from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_strategy_orchestrator_v28_8 as m
from backtest.offline_strategy_orchestrator_v28_8 import (
    StrategyError,
    StrategyInput,
    StrategyPolicy,
    create_history,
    create_strategy_plan,
    load_history,
    save_history,
    verify_history,
    verify_line,
    verify_plan,
)

def check(name, condition):
    print(f"{name:<94}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except StrategyError:
        return True
    return False

policy = StrategyPolicy()

items = (
    StrategyInput(
        "S-AAPL","2026-07-28T23:10:00-07:00","AAPL","TECH",1,
        Decimal("0.85"),Decimal("0.10"),True,Decimal("0.08"),
        Decimal("0.07"),Decimal("4.5"),Decimal("0.25"),
        "a"*64,"1"*64,"f"*64,
    ),
    StrategyInput(
        "S-MSFT","2026-07-28T23:11:00-07:00","MSFT","TECH",-1,
        Decimal("0.78"),Decimal("0.09"),True,Decimal("0.06"),
        Decimal("0.05"),Decimal("3.0"),Decimal("0.30"),
        "b"*64,"2"*64,"e"*64,
    ),
    StrategyInput(
        "S-NVDA","2026-07-28T23:12:00-07:00","NVDA","TECH",1,
        Decimal("0.40"),Decimal("0.12"),True,Decimal("0.10"),
        Decimal("0.08"),Decimal("6.0"),Decimal("0.20"),
        "c"*64,"3"*64,"d"*64,
    ),
    StrategyInput(
        "S-TSLA","2026-07-28T23:13:00-07:00","TSLA","CONSUMER",1,
        Decimal("0.82"),Decimal("0.10"),False,Decimal("0.00"),
        Decimal("0.08"),Decimal("5.0"),Decimal("0.90"),
        "4"*64,"5"*64,"6"*64,
    ),
    StrategyInput(
        "S-SPY","2026-07-28T23:14:00-07:00","SPY","ETF",0,
        Decimal("0.60"),Decimal("0.00"),True,Decimal("0.00"),
        Decimal("0.00"),Decimal("0.0"),Decimal("0.10"),
        "7"*64,"8"*64,"9"*64,
    ),
)

plan = create_strategy_plan(items, policy)

check("V28.8 engine version verified", m.VERSION == "28.8")
check("Strategy plan created", plan.plan_id.startswith("PLAN-"))
check("Five strategy lines created", len(plan.lines) == 5)
check("BUY action created", next(line for line in plan.lines if line.symbol=="AAPL").final_action == "BUY")
check("SELL action created", next(line for line in plan.lines if line.symbol=="MSFT").final_action == "SELL")
check("Original HOLD retained", next(line for line in plan.lines if line.symbol=="SPY").final_action == "HOLD")
check("Low confidence forced HOLD", next(line for line in plan.lines if line.symbol=="NVDA").final_action == "HOLD")
check("Risk rejection forced HOLD", next(line for line in plan.lines if line.symbol=="TSLA").final_action == "HOLD")
check("Trade size reconciled by minimum input", next(line for line in plan.lines if line.symbol=="AAPL").target_fraction == Decimal("0.070000"))
check("Executable count calculated", plan.executable_count == 2)
check("Blocked count calculated", plan.blocked_count == 2)
check("Cash fraction preserved", plan.cash_fraction > Decimal("0"))
check("Priority ranking created", plan.lines[0].priority_score >= plan.lines[-1].priority_score)
check("Strategy line hashes verified", all(verify_line(line) for line in plan.lines))
check("Strategy plan hash verified", verify_plan(plan))
check("Deterministic strategy plan returned", plan == create_strategy_plan(items, policy))

no_override = create_strategy_plan(
    (replace(items[2], strategy_id="S-NVDA-NO", symbol="NVDA2"),),
    replace(policy, force_hold_on_mismatch=False),
)
check("Mismatch override can be disabled", no_override.lines[0].final_action == "BUY")

check("Duplicate strategy ID blocked", blocked(lambda: create_strategy_plan(items + (items[0],), policy)))
check("Duplicate symbol blocked", blocked(lambda: create_strategy_plan(items + (replace(items[0], strategy_id="S-DUP"),), policy)))
check("Invalid confidence blocked", blocked(lambda: create_strategy_plan((replace(items[0], decision_confidence=Decimal("1.5")),), policy)))
check("Invalid decision hash blocked", blocked(lambda: create_strategy_plan((replace(items[0], decision_hash="BAD"),), policy)))
check("Unknown decision label blocked", blocked(lambda: create_strategy_plan((replace(items[0], decision_label=9),), policy)))
check("Invalid policy blocked", blocked(lambda: StrategyPolicy(min_trade_fraction=Decimal("0.20"), max_trade_fraction=Decimal("0.10"))))

tampered_line = replace(plan.lines[0], target_fraction=Decimal("0.50"))
check("Tampered strategy line detected", blocked(lambda: verify_line(tampered_line)))

tampered_plan = replace(plan, cash_fraction=Decimal("0.50"))
check("Tampered strategy plan detected", blocked(lambda: verify_plan(tampered_plan)))

history = create_history((plan,))
check("Strategy history created", len(history.plans) == 1)
check("History hash verified", verify_history(history))
check("Duplicate plan blocked", blocked(lambda: create_history((plan, plan))))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "strategy_history.json"
    save_history(history, path)
    loaded = load_history(path)
    check("Strategy history save and load passed", loaded == history)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["plans"][0]["cash_fraction"] = "0.500000"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved strategy history blocked", blocked(lambda: load_history(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {"requests","urllib","httpx","aiohttp","socket","alpaca_trade_api","ib_insync","ccxt"}
imports=set()
for node in ast.walk(tree):
    if isinstance(node,ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node,ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent", not(imports & forbidden))
check("Market data API was not called", not m.MARKET_DATA_API_CALLED)
check("Account API was not called", not m.ACCOUNT_API_CALLED)
check("Network was not accessed", not m.NETWORK_ACCESSED)
check("Broker API was not called", not m.BROKER_API_CALLED)
check("Broker order was not created", not m.BROKER_ORDER_CREATED)
check("Order was not submitted", not m.ORDER_SUBMITTED)
check("Live execution not authorized", not m.LIVE_EXECUTION_AUTHORIZED)
check("Funds were not reserved", not m.FUNDS_RESERVED)
check("Holdings were not reserved", not m.HOLDINGS_RESERVED)
check("All checks passed", True)

print("="*114)
print("V28.8 offline strategy orchestrator test completed successfully.")
print("Decision/risk/allocation binding, BUY/HOLD/SELL planning, priority ranking,")
print("size reconciliation, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
