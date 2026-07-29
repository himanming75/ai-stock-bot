from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_feature_selector_v27_5 as m
from backtest.offline_feature_selector_v27_5 import (
    FeatureMatrix, FeatureSelectionError, SelectionPolicy,
    load_result, save_result, select_features, verify_result,
)

def check(name, condition):
    print(f"{name:<74}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try: fn()
    except FeatureSelectionError: return True
    return False

names=("constant","signal","signal_duplicate","signal_correlated","noise","inverse_signal","low_variance")
rows=[]; labels=[]
for i in range(60):
    label=-1 if i<20 else 0 if i<40 else 1
    labels.append(label)
    signal=Decimal(label*10+(i%3))
    rows.append((
        Decimal("5"),
        signal,
        signal,
        signal+Decimal(i%2)/Decimal("100"),
        Decimal((i*7)%11),
        -signal,
        Decimal("1")+Decimal(i%2)/Decimal("1000"),
    ))
matrix=FeatureMatrix(names,tuple(rows),tuple(labels))
policy=SelectionPolicy(Decimal("0.0001"),Decimal("0.95"),3,5,Decimal("0.40"),Decimal("0.40"),Decimal("0.20"))
result=select_features(matrix,policy,{"noise":Decimal("0.10"),"signal":Decimal("0.90")})
score={s.feature:s for s in result.scores}

check("V27.5 engine version verified",m.VERSION=="27.5")
check("Feature selection result created",len(result.scores)==len(names))
check("Constant feature removed",score["constant"].removal_reason=="CONSTANT")
check("Low-variance feature removed",score["low_variance"].removal_reason=="LOW_VARIANCE")
check("Duplicate feature removed",score["signal_duplicate"].removal_reason.startswith("DUPLICATE_OF:"))
check("Highly correlated feature removed",any(s.removal_reason.startswith("HIGH_CORRELATION_WITH:") for s in result.scores))
check("Label correlation calculated",score["signal"].label_correlation>0)
check("Mutual information calculated",score["signal"].mutual_information>0)
check("External importance applied",score["signal"].external_importance==Decimal("0.9000"))
check("Composite score calculated",score["signal"].composite_score>0)
check("Maximum feature count enforced",len(result.selected_features)<=3)
check("Signal feature selected","signal" in result.selected_features)
check("Removed feature list created",len(result.removed_features)>=4)
check("Selection hash verified",verify_result(result))
check("Deterministic result returned",result==select_features(matrix,policy,{"noise":Decimal("0.10"),"signal":Decimal("0.90")}))

limited=select_features(matrix,replace(policy,max_features=1),{"signal":1})
check("Single-feature limit enforced",len(limited.selected_features)==1)
check("Duplicate feature names blocked",blocked(lambda:select_features(FeatureMatrix(("A","A"),((1,2),(2,3)),(0,1)),policy)))
check("Row/label mismatch blocked",blocked(lambda:select_features(FeatureMatrix(("A",),((1,),(2,)),(0,)),policy)))
check("Inconsistent feature width blocked",blocked(lambda:select_features(FeatureMatrix(("A","B"),((1,2),(3,)),(0,1)),policy)))
check("Single label class blocked",blocked(lambda:select_features(FeatureMatrix(("A",),((1,),(2,)),(1,1)),policy)))
check("Unknown external importance blocked",blocked(lambda:select_features(matrix,policy,{"UNKNOWN":1})))
check("Negative external importance blocked",blocked(lambda:select_features(matrix,policy,{"signal":-1})))
check("Invalid correlation threshold blocked",blocked(lambda:SelectionPolicy(correlation_threshold=Decimal("1.5"))))

tampered=replace(result,selected_features=result.selected_features+("constant",))
check("Tampered result detected",blocked(lambda:verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/"selection.json"
    save_result(result,path)
    loaded=load_result(path)
    check("Selection save and load passed",loaded==result)
    payload=json.loads(path.read_text(encoding="utf-8"))
    payload["selected_features"].append("constant")
    path.write_text(json.dumps(payload),encoding="utf-8")
    check("Tampered saved selection blocked",blocked(lambda:load_result(path)))

tree=ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden={"requests","urllib","httpx","aiohttp","socket","alpaca_trade_api","ib_insync","ccxt"}
imports=set()
for node in ast.walk(tree):
    if isinstance(node,ast.Import): imports.update(a.name.split(".")[0] for a in node.names)
    elif isinstance(node,ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent",not(imports&forbidden))
check("Market data API was not called",not m.MARKET_DATA_API_CALLED)
check("Account API was not called",not m.ACCOUNT_API_CALLED)
check("Network was not accessed",not m.NETWORK_ACCESSED)
check("Broker API was not called",not m.BROKER_API_CALLED)
check("Broker order was not created",not m.BROKER_ORDER_CREATED)
check("Order was not submitted",not m.ORDER_SUBMITTED)
check("Live execution not authorized",not m.LIVE_EXECUTION_AUTHORIZED)
check("Funds were not reserved",not m.FUNDS_RESERVED)
check("Holdings were not reserved",not m.HOLDINGS_RESERVED)
check("All checks passed",True)

print("="*94)
print("V27.5 offline feature selection test completed successfully.")
print("Constant, variance, duplicate, correlation, mutual-information, external")
print("importance, ranking, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
