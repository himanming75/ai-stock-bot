from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_ensemble_engine_v28_3 as m
from backtest.offline_ensemble_engine_v28_3 import (
    EnsembleError,
    EnsemblePolicy,
    combine_votes,
    create_model_vote,
    load_result,
    save_result,
    verify_result,
    verify_vote,
)


def check(name, condition):
    print(f"{name:<86}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except EnsembleError:
        return True
    return False


votes = (
    create_model_vote(
        model_id="MODEL-A",
        model_hash="a" * 64,
        classes=(-1, 0, 1),
        probabilities=(Decimal("0.05"), Decimal("0.15"), Decimal("0.80")),
        weight=Decimal("0.50"),
    ),
    create_model_vote(
        model_id="MODEL-B",
        model_hash="b" * 64,
        classes=(-1, 0, 1),
        probabilities=(Decimal("0.10"), Decimal("0.20"), Decimal("0.70")),
        weight=Decimal("0.30"),
    ),
    create_model_vote(
        model_id="MODEL-C",
        model_hash="c" * 64,
        classes=(-1, 0, 1),
        probabilities=(Decimal("0.60"), Decimal("0.25"), Decimal("0.15")),
        weight=Decimal("0.20"),
    ),
)

hard = combine_votes(
    votes,
    EnsemblePolicy(
        method="HARD",
        min_agreement=Decimal("0.50"),
        min_consensus_confidence=Decimal("0.50"),
        max_entropy=Decimal("0.95"),
    ),
)
soft = combine_votes(
    votes,
    EnsemblePolicy(
        method="SOFT",
        min_agreement=Decimal("0.50"),
        min_consensus_confidence=Decimal("0.50"),
        max_entropy=Decimal("0.95"),
    ),
)
weighted = combine_votes(
    votes,
    EnsemblePolicy(
        method="WEIGHTED",
        min_agreement=Decimal("0.50"),
        min_consensus_confidence=Decimal("0.50"),
        max_entropy=Decimal("0.95"),
    ),
)
confidence_weighted = combine_votes(
    votes,
    EnsemblePolicy(
        method="CONFIDENCE_WEIGHTED",
        min_agreement=Decimal("0.50"),
        min_consensus_confidence=Decimal("0.50"),
        max_entropy=Decimal("0.95"),
    ),
)

check("V28.3 engine version verified", m.VERSION == "28.3")
check("Model vote created", votes[0].model_id == "MODEL-A")
check("Model vote hash verified", verify_vote(votes[0]))
check("Hard voting completed", hard.method == "HARD")
check("Soft voting completed", soft.method == "SOFT")
check("Weighted voting completed", weighted.method == "WEIGHTED")
check("Confidence-weighted voting completed", confidence_weighted.method == "CONFIDENCE_WEIGHTED")
check("Hard voting selected BUY", hard.raw_label == 1)
check("Soft voting selected BUY", soft.raw_label == 1)
check("Weighted voting selected BUY", weighted.raw_label == 1)
check("Confidence-weighted voting selected BUY", confidence_weighted.raw_label == 1)
check("Agreement score calculated", hard.agreement_score == Decimal("0.666667"))
check("Consensus confidence calculated", weighted.consensus_confidence > Decimal("0.50"))
check("Entropy calculated", ZERO := Decimal("0") <= weighted.normalized_entropy <= Decimal("1"))
check("Model contributions recorded", len(weighted.contributions) == 3)
check("Contribution weights sum to one", sum(item.normalized_weight for item in weighted.contributions) == Decimal("1.000000"))
check("Ensemble result hash verified", verify_result(weighted))
check("Deterministic output returned", weighted == combine_votes(
    votes,
    EnsemblePolicy(
        method="WEIGHTED",
        min_agreement=Decimal("0.50"),
        min_consensus_confidence=Decimal("0.50"),
        max_entropy=Decimal("0.95"),
    ),
))

disagreement_votes = (
    create_model_vote(
        model_id="MODEL-D",
        model_hash="d" * 64,
        classes=(-1, 0, 1),
        probabilities=(Decimal("0.80"), Decimal("0.10"), Decimal("0.10")),
        weight=1,
    ),
    create_model_vote(
        model_id="MODEL-E",
        model_hash="e" * 64,
        classes=(-1, 0, 1),
        probabilities=(Decimal("0.10"), Decimal("0.10"), Decimal("0.80")),
        weight=1,
    ),
    create_model_vote(
        model_id="MODEL-F",
        model_hash="f" * 64,
        classes=(-1, 0, 1),
        probabilities=(Decimal("0.20"), Decimal("0.60"), Decimal("0.20")),
        weight=1,
    ),
)

disagreement = combine_votes(
    disagreement_votes,
    EnsemblePolicy(
        method="SOFT",
        min_agreement=Decimal("0.67"),
        min_consensus_confidence=Decimal("0.60"),
        max_entropy=Decimal("0.70"),
        force_hold_on_disagreement=True,
    ),
)

check("Disagreement detected", disagreement.forced_hold)
check("Disagreement forced HOLD", disagreement.final_label == 0)
check("Disagreement reasons recorded", bool(disagreement.reason_codes))

no_override = combine_votes(
    disagreement_votes,
    EnsemblePolicy(
        method="SOFT",
        min_agreement=Decimal("0.67"),
        min_consensus_confidence=Decimal("0.60"),
        max_entropy=Decimal("0.70"),
        force_hold_on_disagreement=False,
    ),
)
check("Disagreement override can be disabled", not no_override.forced_hold)

check("Duplicate model ID blocked", blocked(lambda: combine_votes(
    votes + (replace(votes[0], model_hash="9" * 64),),
)))
check("Duplicate model hash blocked", blocked(lambda: combine_votes(
    votes + (create_model_vote(
        model_id="MODEL-Z",
        model_hash="a" * 64,
        classes=(-1, 0, 1),
        probabilities=(Decimal("0.2"), Decimal("0.3"), Decimal("0.5")),
    ),),
)))
check("Class order mismatch blocked", blocked(lambda: combine_votes(
    votes + (create_model_vote(
        model_id="MODEL-Z",
        model_hash="9" * 64,
        classes=(0, -1, 1),
        probabilities=(Decimal("0.2"), Decimal("0.3"), Decimal("0.5")),
    ),),
)))
check("Invalid probability blocked", blocked(lambda: create_model_vote(
    model_id="BAD",
    model_hash="8" * 64,
    classes=(-1, 0, 1),
    probabilities=(Decimal("0.4"), Decimal("0.4"), Decimal("0.4")),
)))
check("Invalid weight blocked", blocked(lambda: create_model_vote(
    model_id="BAD",
    model_hash="8" * 64,
    classes=(-1, 0, 1),
    probabilities=(Decimal("0.2"), Decimal("0.3"), Decimal("0.5")),
    weight=0,
)))
check("Single model ensemble blocked", blocked(lambda: combine_votes((votes[0],))))
check("Missing HOLD class blocked", blocked(lambda: combine_votes((
    create_model_vote(
        model_id="X1",
        model_hash="1" * 64,
        classes=(-1, 1),
        probabilities=(Decimal("0.4"), Decimal("0.6")),
    ),
    create_model_vote(
        model_id="X2",
        model_hash="2" * 64,
        classes=(-1, 1),
        probabilities=(Decimal("0.3"), Decimal("0.7")),
    ),
))))

tampered_vote = replace(votes[0], confidence=Decimal("0.999999"))
check("Tampered vote detected", blocked(lambda: verify_vote(tampered_vote)))

tampered_result = replace(weighted, final_label=0)
check("Tampered result detected", blocked(lambda: verify_result(tampered_result)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "ensemble.json"
    save_result(weighted, path)
    loaded = load_result(path)
    check("Ensemble save and load passed", loaded == weighted)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["final_label"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved ensemble blocked", blocked(lambda: load_result(path)))

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

print("=" * 106)
print("V28.3 offline ensemble engine test completed successfully.")
print("Hard, soft, weighted, confidence-weighted voting, agreement, consensus,")
print("contributions, disagreement HOLD, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
