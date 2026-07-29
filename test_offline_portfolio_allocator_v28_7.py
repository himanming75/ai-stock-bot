from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_portfolio_allocator_v28_7 as m
from backtest.offline_portfolio_allocator_v28_7 import (
    AllocationCandidate,
    AllocationError,
    AllocationPolicy,
    allocate_portfolio,
    load_result,
    save_result,
    verify_result,
)

def check(name, condition):
    print(f"{name:<92}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except AllocationError:
        return True
    return False

candidates = (
    AllocationCandidate("AAPL","TECH",Decimal("0.85"),Decimal("0.25"),Decimal("0.20"),Decimal("0.18"),Decimal("0.12"),"a"*64,"1"*64),
    AllocationCandidate("MSFT","TECH",Decimal("0.75"),Decimal("0.30"),Decimal("0.18"),Decimal("0.16"),Decimal("0.10"),"b"*64,"2"*64),
    AllocationCandidate("JPM","FINANCE",Decimal("0.65"),Decimal("0.35"),Decimal("0.25"),Decimal("0.12"),Decimal("0.08"),"c"*64,"3"*64),
)

equal = allocate_portfolio(candidates, AllocationPolicy(method="EQUAL"))
confidence = allocate_portfolio(candidates, AllocationPolicy(method="CONFIDENCE_WEIGHTED"))
risk_parity = allocate_portfolio(candidates, AllocationPolicy(method="RISK_PARITY"))
kelly = allocate_portfolio(candidates, AllocationPolicy(method="KELLY_WEIGHTED"))

check("V28.7 engine version verified", m.VERSION == "28.7")
check("Equal allocation completed", equal.method == "EQUAL")
check("Confidence-weighted allocation completed", confidence.method == "CONFIDENCE_WEIGHTED")
check("Risk-parity allocation completed", risk_parity.method == "RISK_PARITY")
check("Kelly-weighted allocation completed", kelly.method == "KELLY_WEIGHTED")
check("Three allocation lines created", len(equal.lines) == 3)
check("Cash reserve maintained", equal.cash_fraction >= Decimal("0.200000"))
check("Maximum position cap enforced", all(line.capped_weight <= Decimal("0.150000") for line in equal.lines))
check("Approved fraction respected", dict((c.symbol,c.approved_fraction) for c in candidates)["AAPL"] >= next(l.capped_weight for l in equal.lines if l.symbol=="AAPL"))
check("Sector exposure cap enforced", sum(l.capped_weight for l in equal.lines if l.sector=="TECH") <= Decimal("0.400000"))
check("Portfolio fractions sum to one", equal.invested_fraction + equal.cash_fraction == Decimal("1.000000"))
check("Allocation hash verified", verify_result(equal))
check("Deterministic allocation returned", equal == allocate_portfolio(candidates, AllocationPolicy(method="EQUAL")))

check("Duplicate symbol blocked", blocked(lambda: allocate_portfolio(candidates + (candidates[0],))))
check("Invalid decision hash blocked", blocked(lambda: allocate_portfolio((replace(candidates[0], decision_hash="BAD"),))))
check("Invalid volatility blocked", blocked(lambda: allocate_portfolio((replace(candidates[0], volatility=Decimal("-0.1")),))))
check("Invalid method blocked", blocked(lambda: AllocationPolicy(method="BAD")))
check("Invalid reserve policy blocked", blocked(lambda: AllocationPolicy(cash_reserve_fraction=Decimal("0.30"), max_total_invested_fraction=Decimal("0.80"))))

tampered = replace(equal, cash_fraction=Decimal("0.50"))
check("Tampered allocation detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "allocation.json"
    save_result(equal, path)
    loaded = load_result(path)
    check("Allocation save and load passed", loaded == equal)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cash_fraction"] = "0.500000"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved allocation blocked", blocked(lambda: load_result(path)))

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

print("="*112)
print("V28.7 offline portfolio allocation test completed successfully.")
print("Equal, confidence-weighted, risk-parity, Kelly-weighted allocation,")
print("cash reserve, position/sector caps, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
