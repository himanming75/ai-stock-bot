from dataclasses import replace
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_model_registry_v28_2 as m
from backtest.offline_model_registry_v28_2 import (
    RegistryError,
    archive_model,
    create_model_record,
    create_registry,
    load_registry,
    promote_model,
    register_model,
    reject_model,
    rollback_to_model,
    save_registry,
    verify_record,
    verify_registry,
)


def check(name, condition):
    print(f"{name:<84}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except RegistryError:
        return True
    return False


model1 = create_model_record(
    model_version="1.0.0",
    model_hash="a" * 64,
    experiment_id="EXP-AAAA1111",
    pipeline_version="28.0",
    dataset_hash="1" * 64,
    feature_schema_hash="f" * 64,
    metadata={"accuracy": "0.80", "f1": "0.79"},
)

registry = create_registry()
registry = register_model(registry, model1)
registry = promote_model(registry, model1.model_id, note="initial production model")

model2 = create_model_record(
    model_version="1.1.0",
    model_hash="b" * 64,
    experiment_id="EXP-BBBB2222",
    pipeline_version="28.0",
    dataset_hash="2" * 64,
    feature_schema_hash="e" * 64,
    parent_model_id=model1.model_id,
    metadata={"accuracy": "0.85", "f1": "0.84"},
)
registry = register_model(registry, model2)
registry = promote_model(registry, model2.model_id, note="improved validation score")

model3 = create_model_record(
    model_version="1.2.0",
    model_hash="c" * 64,
    experiment_id="EXP-CCCC3333",
    pipeline_version="28.0",
    dataset_hash="3" * 64,
    feature_schema_hash="d" * 64,
    parent_model_id=model2.model_id,
    metadata={"accuracy": "0.76", "f1": "0.74"},
)
registry = register_model(registry, model3)
registry = reject_model(registry, model3.model_id, note="failed approval gate")

check("V28.2 engine version verified", m.VERSION == "28.2")
check("Semantic model version stored", model1.model_version == "1.0.0")
check("Model fingerprint created", len(model1.fingerprint) == 64)
check("Model record hash verified", verify_record(model1))
check("Candidate registered", any(r.model_id == model3.model_id for r in registry.records))
check("Production model tracked", registry.production_model_id == model2.model_id)
check("Previous production archived", next(r for r in registry.records if r.model_id == model1.model_id).status == "ARCHIVED")
check("Candidate promoted", next(r for r in registry.records if r.model_id == model2.model_id).status == "PRODUCTION")
check("Candidate rejected", next(r for r in registry.records if r.model_id == model3.model_id).status == "REJECTED")
check("Parent lineage stored", model2.parent_model_id == model1.model_id)
check("Promotion history recorded", any(e.action == "PROMOTE" for e in registry.events))
check("Registry hash verified", verify_registry(registry))

rolled_back = rollback_to_model(registry, model1.model_id, note="rollback after regression")
check("Rollback restored archived model", rolled_back.production_model_id == model1.model_id)
check("Former production archived after rollback", next(r for r in rolled_back.records if r.model_id == model2.model_id).status == "ARCHIVED")
check("Rollback history recorded", rolled_back.events[-1].action == "ROLLBACK")
check("Rolled-back registry verified", verify_registry(rolled_back))

model4 = create_model_record(
    model_version="2.0.0",
    model_hash="d" * 64,
    experiment_id="EXP-DDDD4444",
    pipeline_version="28.0",
    dataset_hash="4" * 64,
    feature_schema_hash="c" * 64,
    parent_model_id=model1.model_id,
)
with_candidate = register_model(rolled_back, model4)
archived_candidate = archive_model(with_candidate, model4.model_id, note="manual archive")
check("Candidate archive completed", next(r for r in archived_candidate.records if r.model_id == model4.model_id).status == "ARCHIVED")

check("Invalid semantic version blocked", blocked(lambda: create_model_record(
    model_version="v1",
    model_hash="9" * 64,
    experiment_id="EXP-X",
    pipeline_version="28.0",
    dataset_hash="8" * 64,
    feature_schema_hash="7" * 64,
)))
check("Invalid model hash blocked", blocked(lambda: create_model_record(
    model_version="3.0.0",
    model_hash="BAD",
    experiment_id="EXP-X",
    pipeline_version="28.0",
    dataset_hash="8" * 64,
    feature_schema_hash="7" * 64,
)))
check("Duplicate model version blocked", blocked(lambda: register_model(
    registry,
    create_model_record(
        model_version="1.1.0",
        model_hash="8" * 64,
        experiment_id="EXP-DUPV",
        pipeline_version="28.0",
        dataset_hash="7" * 64,
        feature_schema_hash="6" * 64,
    ),
)))
check("Duplicate model hash blocked", blocked(lambda: register_model(
    registry,
    create_model_record(
        model_version="9.0.0",
        model_hash="a" * 64,
        experiment_id="EXP-DUPH",
        pipeline_version="28.0",
        dataset_hash="7" * 64,
        feature_schema_hash="6" * 64,
    ),
)))
check("Unknown parent blocked", blocked(lambda: register_model(
    registry,
    create_model_record(
        model_version="9.1.0",
        model_hash="9" * 64,
        experiment_id="EXP-PARENT",
        pipeline_version="28.0",
        dataset_hash="7" * 64,
        feature_schema_hash="6" * 64,
        parent_model_id="MODEL-UNKNOWN",
    ),
)))
check("Production archive blocked", blocked(lambda: archive_model(
    registry,
    model2.model_id,
)))
check("Rejected model promotion blocked", blocked(lambda: promote_model(
    registry,
    model3.model_id,
)))
check("Non-archived rollback blocked", blocked(lambda: rollback_to_model(
    registry,
    model3.model_id,
)))

tampered_record = replace(model1, status="PRODUCTION")
check("Tampered record detected", blocked(lambda: verify_record(tampered_record)))

tampered_registry = replace(registry, production_model_id=model1.model_id)
check("Tampered registry detected", blocked(lambda: verify_registry(tampered_registry)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "model_registry.json"
    save_registry(rolled_back, path)
    loaded = load_registry(path)
    check("Registry save and load passed", loaded == rolled_back)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["production_model_id"] = model2.model_id
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved registry blocked", blocked(lambda: load_registry(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {
    "requests", "urllib", "httpx", "aiohttp", "socket",
    "alpaca_trade_api", "ib_insync", "ccxt",
}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent", not (imports & forbidden))
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

print("=" * 104)
print("V28.2 offline model registry test completed successfully.")
print("Semantic versions, lineage, registration, promotion, archive, rejection,")
print("rollback, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
