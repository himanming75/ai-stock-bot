from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class IntelligenceSafetyPack:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try: return float(value)
        except (TypeError, ValueError): return default

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists(): return {}
        try: return json.loads(path.read_text(encoding='utf-8-sig'))
        except Exception: return {}

    @staticmethod
    def _load_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
        if not path.exists(): return []
        rows=[]
        try:
            for line in path.read_text(encoding='utf-8-sig').splitlines()[-limit:]:
                if not line.strip(): continue
                try:
                    item=json.loads(line)
                    if isinstance(item,dict): rows.append(item)
                except Exception: pass
        except Exception: return []
        return rows

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a',encoding='utf-8') as f: f.write(json.dumps(payload,sort_keys=True)+'\n')

    def _observability(self):
        return self._load(self.root/'runtime/paper_observability_intelligence/latest_observability_report.json')

    def _guard(self):
        return self._load(self.root/'runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json')

    def _candidate(self):
        c=self._observability().get('selected_candidate') or self._guard().get('candidate') or {}
        return {
            'symbol':str(c.get('symbol','')).upper(), 'side':str(c.get('side','HOLD')).upper(),
            'confidence':self._float(c.get('confidence')), 'consensus_score':self._float(c.get('consensus_score')),
            'reward_risk':self._float(c.get('reward_risk')), 'quantity':self._float(c.get('quantity')),
            'reference_price':self._float(c.get('reference_price')),
        }

    def multi_score(self):
        c=self._candidate(); m=self._guard().get('market_snapshot',{})
        confidence=c['confidence']; consensus=c['consensus_score']
        rr=min(max(c['reward_risk']/3.0,0),1); regime=self._float(m.get('market_regime_fit'),0.5)
        vol=self._float(m.get('volatility_risk'),0.5); riskq=1-min(max(vol,0),1)
        trend=min(max((confidence+consensus)/2,0),1); momentum=min(max(consensus,0),1)
        breakout=rr; liquidity=0.75 if c['symbol'] else 0
        total=.22*confidence+.18*consensus+.15*trend+.12*momentum+.10*breakout+.08*liquidity+.08*riskq+.07*regime
        return {'confidence_score':round(confidence,6),'consensus_score':round(consensus,6),'trend_score':round(trend,6),'momentum_score':round(momentum,6),'breakout_score':round(breakout,6),'liquidity_score':round(liquidity,6),'risk_quality_score':round(riskq,6),'regime_fit_score':round(regime,6),'total_score':round(min(max(total,0),1),6)}

    def market_regime(self):
        m=self._guard().get('market_snapshot',{}); fit=self._float(m.get('market_regime_fit'),0.5); vol=self._float(m.get('volatility_risk'),0.5)
        if vol>=.85: label='EXTREME_VOLATILITY'
        elif vol>=.70: label='HIGH_VOLATILITY'
        elif fit>=.80: label='STRONG_TREND'
        elif fit>=.65: label='TRENDING'
        elif fit<=.35: label='WEAK_OR_BEARISH'
        else: label='SIDEWAYS_OR_UNCERTAIN'
        conf=max(abs(fit-.5)*2, vol if vol>=.70 else 0)
        return {'label':label,'confidence':round(min(max(conf,0),1),6),'market_regime_fit':fit,'volatility_risk':vol,'source':'SHADOW_HEURISTIC_READ_ONLY'}

    def safety_heatmap(self):
        g=self._guard(); issues=[str(x.get('code')) for x in g.get('issues',[]) if x.get('code')]; warnings=[str(x.get('code')) for x in g.get('warnings',[]) if x.get('code')]
        severe={'EMERGENCY_STOP','ACCOUNT_TRADING_BLOCKED','DAILY_LOSS_LIMIT','LIVE_WRITE_MUST_REMAIN_OFF'}
        high={'DAILY_ORDER_LIMIT','OPEN_POSITION_LIMIT','SYMBOL_EXPOSURE_LIMIT','DUPLICATE_SYMBOL_BUY','CONSECUTIVE_LOSS_LIMIT'}
        if any(x in severe for x in issues): level,score='EXTREME',1.0
        elif any(x in high for x in issues): level,score='HIGH',.75
        elif issues: level,score='MEDIUM',.5
        elif warnings: level,score='LOW',.25
        else: level,score='LOW',.1
        return {'level':level,'risk_score':score,'blocking_issue_count':len(issues),'warning_count':len(warnings),'issue_codes':issues,'warning_codes':warnings}

    def smart_skip(self):
        score=self.multi_score()['total_score']; heat=self.safety_heatmap()['level']; side=self._candidate()['side']; reasons=[]
        if side not in {'BUY','SELL'}: reasons.append('NO_ACTIONABLE_SIDE')
        if score<.72: reasons.append('TOTAL_SCORE_BELOW_THRESHOLD')
        if heat in {'HIGH','EXTREME'}: reasons.append('SAFETY_HEAT_TOO_HIGH')
        return {'decision':'SKIP' if reasons else 'OBSERVE_AS_ELIGIBLE','skip':bool(reasons),'reasons':reasons,'enforced':False,'threshold':.72}

    def dynamic_risk_shadow(self):
        score=self.multi_score()['total_score']; heat=self.safety_heatmap()['level']
        if heat in {'HIGH','EXTREME'}: n=0.0
        elif score>=.90: n=100.0
        elif score>=.82: n=75.0
        elif score>=.75: n=50.0
        elif score>=.70: n=25.0
        else: n=0.0
        return {'suggested_notional':n,'current_hard_limit':100.0,'shadow_only':True,'enforced':False,'basis_total_score':score,'basis_safety_heat':heat}

    def confidence_calibration(self):
        rows=self._load_jsonl(self.root/'runtime/paper_observability_intelligence/trade_journal.jsonl'); vals=[]
        for r in rows:
            c=r.get('selected_candidate',{}); v=self._float(c.get('confidence'),-1)
            if 0<=v<=1: vals.append(v)
        if not vals: return {'sample_count':0,'mean_reported_confidence':None,'calibration_status':'INSUFFICIENT_DATA','recommended_adjustment':0.0}
        return {'sample_count':len(vals),'mean_reported_confidence':round(sum(vals)/len(vals),6),'calibration_status':'COLLECTING','recommended_adjustment':0.0,'note':'Outcome-linked calibration waits for closed-trade data.'}

    def self_learning(self):
        obs=self._load_jsonl(self.root/'runtime/paper_observability_intelligence/trade_journal.jsonl')
        guards=self._load_jsonl(self.root/'runtime/paper_autonomous_daily_session/shadow_guard_ledger.jsonl')
        issues={}; symbols={}
        for r in guards:
            for i in r.get('issues',[]):
                code=i.get('code')
                if code: issues[code]=issues.get(code,0)+1
        for r in obs:
            sym=str(r.get('selected_candidate',{}).get('symbol','')).upper()
            if sym: symbols[sym]=symbols.get(sym,0)+1
        return {'observability_samples':len(obs),'guard_samples':len(guards),'recurring_issue_patterns':[{'code':k,'count':v} for k,v in sorted(issues.items(),key=lambda x:(-x[1],x[0]))[:10]],'recurring_candidate_symbols':[{'symbol':k,'count':v} for k,v in sorted(symbols.items(),key=lambda x:(-x[1],x[0]))[:10]],'learning_mode':'READ_ONLY_PATTERN_DISCOVERY','automatic_parameter_changes':False}

    def live_readiness_shadow(self):
        c=self.confidence_calibration(); l=self.self_learning(); h=self.safety_heatmap()
        checks={'observability_data_present':l['observability_samples']>=5,'guard_data_present':l['guard_samples']>=5,'confidence_samples_present':c['sample_count']>=5,'current_safety_not_extreme':h['level']!='EXTREME','live_write_remains_off':True}
        passed=sum(checks.values())
        return {'status':'SHADOW_READY' if passed==len(checks) else 'NOT_READY','passed_checks':passed,'total_checks':len(checks),'checks':checks,'live_submission_enabled':False,'certification_effect':'ADVISORY_ONLY'}

    def run(self):
        runtime=self.root/'runtime/ai_intelligence_safety_v2'
        result={'stage':'AI_INTELLIGENCE_SAFETY_PACK_V2_0','status':'PASS','mode':'READ_ONLY_SHADOW','paper_only':True,'etrade_live_write_enabled':False,'broker_write_performed':False,'candidate':self._candidate(),'multi_score':self.multi_score(),'market_regime':self.market_regime(),'smart_skip':self.smart_skip(),'dynamic_risk_shadow':self.dynamic_risk_shadow(),'safety_heatmap':self.safety_heatmap(),'confidence_calibration':self.confidence_calibration(),'self_learning':self.self_learning(),'live_readiness_shadow':self.live_readiness_shadow(),'generated_at_utc':self._now()}
        self._write(runtime/'latest_intelligence_report.json',result); self._append(runtime/'intelligence_ledger.jsonl',result)
        self._write(runtime/'daily_ai_review.json',{'generated_at_utc':self._now(),'status':'PASS','selected_symbol':result['candidate']['symbol'],'total_score':result['multi_score']['total_score'],'regime':result['market_regime']['label'],'smart_skip':result['smart_skip']['decision'],'suggested_notional':result['dynamic_risk_shadow']['suggested_notional'],'safety_heat':result['safety_heatmap']['level'],'live_readiness':result['live_readiness_shadow']['status'],'broker_write_performed':False})
        self._write(runtime/'weekly_ai_review.json',{'generated_at_utc':self._now(),'status':'PASS','mode':'READ_ONLY_WEEKLY_REVIEW','observability_samples':result['self_learning']['observability_samples'],'guard_samples':result['self_learning']['guard_samples'],'confidence_sample_count':result['confidence_calibration']['sample_count'],'recurring_issue_patterns':result['self_learning']['recurring_issue_patterns'],'recurring_candidate_symbols':result['self_learning']['recurring_candidate_symbols'],'automatic_parameter_changes':False,'broker_write_performed':False})
        return result
