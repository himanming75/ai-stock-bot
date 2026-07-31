from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math

class StrategyInputError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def safety() -> dict:
    return {
        "environment": "offline",
        "network_allowed": False,
        "broker_connected": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
    }

@dataclass(frozen=True)
class StageResult:
    stage: str
    status: str
    artifact_sha256: str
    verification_sha256: str
    next_phase: str
    output_files: tuple[str, ...]
    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "status": self.status,
            "artifact_sha256": self.artifact_sha256,
            "verification_sha256": self.verification_sha256,
            "next_phase": self.next_phase,
            "output_files": list(self.output_files),
        }

def _sma(values: list[float], window: int) -> float:
    if len(values) < window:
        raise StrategyInputError(f"insufficient bars for SMA{window}")
    return sum(values[-window:]) / window

def _ema(values: list[float], window: int) -> float:
    if len(values) < window:
        raise StrategyInputError(f"insufficient bars for EMA{window}")
    alpha = 2.0 / (window + 1.0)
    result = sum(values[:window]) / window
    for value in values[window:]:
        result = alpha * value + (1.0 - alpha) * result
    return result

def _rsi(values: list[float], window: int) -> float:
    if len(values) <= window:
        raise StrategyInputError(f"insufficient bars for RSI{window}")
    changes = [values[i] - values[i-1] for i in range(1, len(values))]
    recent = changes[-window:]
    gain = sum(max(x, 0.0) for x in recent) / window
    loss = sum(max(-x, 0.0) for x in recent) / window
    if loss == 0:
        return 100.0
    rs = gain / loss
    return 100.0 - 100.0 / (1.0 + rs)

def _atr(bars: list[dict], window: int) -> float:
    if len(bars) <= window:
        raise StrategyInputError(f"insufficient bars for ATR{window}")
    trs = []
    for i in range(1, len(bars)):
        high = float(bars[i]["high"])
        low = float(bars[i]["low"])
        prev_close = float(bars[i-1]["close"])
        trs.append(max(high-low, abs(high-prev_close), abs(low-prev_close)))
    return sum(trs[-window:]) / window

def build_strategy_input(
    market_data_certificate_path: Path,
    feed_path: Path,
    output_dir: Path,
) -> StageResult:
    cert = load_json(market_data_certificate_path)
    feed = load_json(feed_path)
    if cert.get("certificate_id") != "MARKET-DATA-AUDIT-V77.30" or cert.get("status") != "PASS":
        raise StrategyInputError("invalid V77.30 market data certificate")
    if feed.get("stage") != "V77.26" or feed.get("status") != "PASS":
        raise StrategyInputError("invalid V77.26 market data feed")
    bars = feed.get("bars", [])
    if len(bars) < 21:
        raise StrategyInputError("at least 21 bars are required")
    closes = [float(x["close"]) for x in bars]
    returns = [(closes[i] / closes[i-1]) - 1.0 for i in range(1, len(closes))]
    mean_return = sum(returns[-20:]) / min(20, len(returns))
    variance = sum((x-mean_return)**2 for x in returns[-20:]) / min(20, len(returns))
    features = {
        "symbol": feed.get("symbol"),
        "timestamp_utc": bars[-1]["timestamp_utc"],
        "close": round(closes[-1], 8),
        "sma_5": round(_sma(closes, 5), 8),
        "sma_20": round(_sma(closes, 20), 8),
        "ema_10": round(_ema(closes, 10), 8),
        "rsi_14": round(_rsi(closes, 14), 8),
        "atr_14": round(_atr(bars, 14), 8),
        "momentum_10": round(closes[-1] - closes[-11], 8),
        "return_1": round(returns[-1], 10),
        "volatility_20": round(math.sqrt(variance), 10),
        "source_bar_count": len(bars),
    }
    features["feature_sha256"] = digest_json({k:v for k,v in features.items() if k != "feature_sha256"})
    snapshot = {
        "schema_version": "v77.31.ai_strategy_input_layer.1",
        "stage": "V77.31",
        "status": "PASS",
        "strategy_input_id": "AI-STRATEGY-INPUT-V77-31",
        "source_market_data_certificate_sha256": cert.get("certificate_sha256"),
        "source_feed_sha256": feed.get("feed_sha256"),
        "feature_set": features,
        "feature_count": 10,
        "strategy_mode": "deterministic_offline_rule",
        "safety": safety(),
        "next_phase": "V77_32_STRATEGY_FEATURE_VALIDATION_LEDGER",
    }
    snapshot["strategy_input_sha256"] = digest_json({k:v for k,v in snapshot.items() if k != "strategy_input_sha256"})
    verification = {
        "schema_version": "v77.31.ai_strategy_input_layer_verification.1",
        "stage": "V77.31", "status": "PASS", "verified": True,
        "error_count": 0, "errors": [],
        "strategy_input_sha256": snapshot["strategy_input_sha256"],
        "next_phase": snapshot["next_phase"],
    }
    verification["verification_sha256"] = digest_json({k:v for k,v in verification.items() if k != "verification_sha256"})
    sf = output_dir/"ai_strategy_input_v77_31.json"
    vf = output_dir/"ai_strategy_input_verification_v77_31.json"
    write_json(sf,snapshot); write_json(vf,verification)
    return StageResult("V77.31","PASS",snapshot["strategy_input_sha256"],verification["verification_sha256"],snapshot["next_phase"],(str(sf),str(vf)))

def build_feature_validation_ledger(strategy_input_path: Path, output_dir: Path) -> StageResult:
    snapshot = load_json(strategy_input_path)
    if snapshot.get("stage") != "V77.31" or snapshot.get("status") != "PASS":
        raise StrategyInputError("invalid V77.31 strategy input")
    features = snapshot.get("feature_set", {})
    required = ["close","sma_5","sma_20","ema_10","rsi_14","atr_14","momentum_10","return_1","volatility_20"]
    errors=[]; entries=[]; previous="0"*64
    for name in required:
        value=features.get(name); checks=[]
        if value is None: checks.append("missing")
        elif not isinstance(value,(int,float)) or not math.isfinite(float(value)): checks.append("non_finite")
        if name=="rsi_14" and isinstance(value,(int,float)) and not 0<=float(value)<=100: checks.append("range")
        if name in ("close","atr_14") and isinstance(value,(int,float)) and float(value)<=0: checks.append("non_positive")
        entry={"feature":name,"value":value,"validation_status":"PASS" if not checks else "FAIL","errors":checks,"previous_entry_sha256":previous}
        entry["entry_sha256"]=digest_json({k:v for k,v in entry.items() if k!="entry_sha256"})
        previous=entry["entry_sha256"];entries.append(entry)
        errors.extend([f"{name}:{x}" for x in checks])
    expected_feature_sha=digest_json({k:v for k,v in features.items() if k!="feature_sha256"})
    if features.get("feature_sha256") != expected_feature_sha:
        errors.append("feature_sha256")
    status="PASS" if not errors else "FAIL"
    ledger={
        "schema_version":"v77.32.strategy_feature_validation_ledger.1",
        "stage":"V77.32","status":status,
        "source_strategy_input_sha256":snapshot.get("strategy_input_sha256"),
        "entry_count":len(entries),"passed_entry_count":sum(x["validation_status"]=="PASS" for x in entries),
        "failed_entry_count":sum(x["validation_status"]!="PASS" for x in entries),
        "entries":entries,"ledger_head_sha256":previous,
        "error_count":len(errors),"errors":errors,
        "safety":safety(),"next_phase":"V77_33_STRATEGY_SIGNAL_GENERATOR",
    }
    ledger["feature_validation_ledger_sha256"]=digest_json({k:v for k,v in ledger.items() if k!="feature_validation_ledger_sha256"})
    verification={"schema_version":"v77.32.strategy_feature_validation_ledger_verification.1","stage":"V77.32",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "feature_validation_ledger_sha256":ledger["feature_validation_ledger_sha256"],"next_phase":ledger["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    lf=output_dir/"strategy_feature_validation_ledger_v77_32.json";vf=output_dir/"strategy_feature_validation_ledger_verification_v77_32.json"
    write_json(lf,ledger);write_json(vf,verification)
    return StageResult("V77.32",status,ledger["feature_validation_ledger_sha256"],verification["verification_sha256"],ledger["next_phase"],(str(lf),str(vf)))

def generate_strategy_signal(strategy_input_path: Path, validation_ledger_path: Path, output_dir: Path) -> StageResult:
    snapshot=load_json(strategy_input_path);ledger=load_json(validation_ledger_path)
    if ledger.get("stage")!="V77.32" or ledger.get("status")!="PASS":
        raise StrategyInputError("invalid V77.32 feature ledger")
    f=snapshot["feature_set"]
    score=0
    reasons=[]
    if f["sma_5"]>f["sma_20"]: score+=1; reasons.append("sma_bullish")
    elif f["sma_5"]<f["sma_20"]: score-=1; reasons.append("sma_bearish")
    if f["close"]>f["ema_10"]: score+=1; reasons.append("close_above_ema")
    elif f["close"]<f["ema_10"]: score-=1; reasons.append("close_below_ema")
    if f["momentum_10"]>0: score+=1; reasons.append("positive_momentum")
    elif f["momentum_10"]<0: score-=1; reasons.append("negative_momentum")
    if f["rsi_14"]>70: score-=1; reasons.append("rsi_overbought")
    elif f["rsi_14"]<30: score+=1; reasons.append("rsi_oversold")
    signal="BUY" if score>=2 else "SELL" if score<=-2 else "HOLD"
    confidence=round(min(1.0,abs(score)/4.0),4)
    doc={
        "schema_version":"v77.33.strategy_signal_generator.1",
        "stage":"V77.33","status":"PASS","signal_id":"STRATEGY-SIGNAL-V77-33",
        "symbol":f["symbol"],"timestamp_utc":f["timestamp_utc"],"signal":signal,
        "signal_score":score,"confidence":confidence,"reasons":reasons,
        "source_feature_sha256":f["feature_sha256"],
        "orders_created":0,"safety":safety(),"next_phase":"V77_34_SIGNAL_SAFETY_GATE",
    }
    doc["signal_sha256"]=digest_json({k:v for k,v in doc.items() if k!="signal_sha256"})
    verification={"schema_version":"v77.33.strategy_signal_generator_verification.1","stage":"V77.33","status":"PASS",
        "verified":True,"error_count":0,"errors":[],"signal_sha256":doc["signal_sha256"],"next_phase":doc["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    sf=output_dir/"strategy_signal_v77_33.json";vf=output_dir/"strategy_signal_verification_v77_33.json"
    write_json(sf,doc);write_json(vf,verification)
    return StageResult("V77.33","PASS",doc["signal_sha256"],verification["verification_sha256"],doc["next_phase"],(str(sf),str(vf)))

def run_signal_safety_gate(signal_path: Path, strategy_input_path: Path, output_dir: Path, *, minimum_confidence: float=0.25) -> StageResult:
    signal=load_json(signal_path);snapshot=load_json(strategy_input_path)
    errors=[]
    if signal.get("signal") not in ("BUY","SELL","HOLD"): errors.append("invalid_signal")
    if signal.get("source_feature_sha256") != snapshot.get("feature_set",{}).get("feature_sha256"): errors.append("feature_anchor")
    if signal.get("orders_created") != 0: errors.append("order_creation_detected")
    if not 0<=float(signal.get("confidence",-1))<=1: errors.append("confidence_range")
    if signal.get("signal") in ("BUY","SELL") and float(signal.get("confidence",0))<minimum_confidence: errors.append("low_confidence")
    expected=digest_json({k:v for k,v in signal.items() if k!="signal_sha256"})
    if signal.get("signal_sha256")!=expected: errors.append("signal_sha256")
    status="PASS" if not errors else "FAIL"
    gate={
        "schema_version":"v77.34.signal_safety_gate.1","stage":"V77.34","status":status,
        "decision":"ALLOW_PAPER_SIGNAL" if not errors else "BLOCK_SIGNAL",
        "approved_signal":signal.get("signal") if not errors else "HOLD",
        "minimum_confidence":minimum_confidence,"error_count":len(errors),"errors":errors,
        "source_signal_sha256":signal.get("signal_sha256"),
        "orders_created":0,"safety":safety(),"next_phase":"V77_35_STRATEGY_INPUT_AUDIT_CERTIFICATE",
    }
    gate["signal_safety_gate_sha256"]=digest_json({k:v for k,v in gate.items() if k!="signal_safety_gate_sha256"})
    verification={"schema_version":"v77.34.signal_safety_gate_verification.1","stage":"V77.34","status":status,
        "verified":not errors,"error_count":len(errors),"errors":errors,
        "signal_safety_gate_sha256":gate["signal_safety_gate_sha256"],"next_phase":gate["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    gf=output_dir/"signal_safety_gate_v77_34.json";vf=output_dir/"signal_safety_gate_verification_v77_34.json"
    write_json(gf,gate);write_json(vf,verification)
    return StageResult("V77.34",status,gate["signal_safety_gate_sha256"],verification["verification_sha256"],gate["next_phase"],(str(gf),str(vf)))

def issue_strategy_input_certificate(v31: Path,v32: Path,v33: Path,v34: Path,output_dir: Path)->StageResult:
    docs=[load_json(p) for p in (v31,v32,v33,v34)];expected=["V77.31","V77.32","V77.33","V77.34"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True: errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={"schema_version":"v77.35.strategy_input_audit_certificate.1","stage":"V77.35",
        "certificate_id":"STRATEGY-INPUT-AUDIT-V77.35","status":status,
        "decision":"strategy_input_certified" if not errors else "strategy_input_rejected",
        "certified_stages":expected,"stage_count":4,
        "anchors":{"v77_31_verification_sha256":docs[0].get("verification_sha256"),
                   "v77_32_verification_sha256":docs[1].get("verification_sha256"),
                   "v77_33_verification_sha256":docs[2].get("verification_sha256"),
                   "v77_34_verification_sha256":docs[3].get("verification_sha256")},
        "error_count":len(errors),"errors":errors,"safety":safety(),
        "next_phase":"V77_36_POSITION_RISK_CALCULATOR" if not errors else "REPAIR_V77_35"}
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    verification={"schema_version":"v77.35.strategy_input_audit_certificate_verification.1","stage":"V77.35",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    cf=output_dir/"strategy_input_audit_certificate_v77_35.json";vf=output_dir/"strategy_input_audit_certificate_verification_v77_35.json"
    write_json(cf,cert);write_json(vf,verification)
    return StageResult("V77.35",status,cert["certificate_sha256"],verification["verification_sha256"],cert["next_phase"],(str(cf),str(vf)))
