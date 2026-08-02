from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

class LedgerRecoveryStatus(str, Enum):
    RECOVERED='RECOVERED'; EXTERNAL_ORDER='EXTERNAL_ORDER'; UNKNOWN_ORDER='UNKNOWN_ORDER'; NO_OPEN_ORDERS='NO_OPEN_ORDERS'

@dataclass(frozen=True)
class NormalizedBrokerOrder:
    broker_order_id:str; client_order_id:str; symbol:str; side:str; quantity:str; order_type:str; time_in_force:str; status:str; submitted_at:str; filled_quantity:str; limit_price:str|None
    def to_json_dict(self): return asdict(self)

@dataclass(frozen=True)
class LegacyOrderEvidence:
    source_path:str; match_type:str; matched_value:str; confidence:str
    def to_json_dict(self): return asdict(self)

@dataclass(frozen=True)
class RecoveredLedgerEntry:
    broker_order_id:str; client_order_id:str; symbol:str; side:str; quantity:str; order_type:str; time_in_force:str; status:str; submitted_at:str; filled_quantity:str; limit_price:str|None; owner:str; source:str; recovery_status:LedgerRecoveryStatus; evidence:tuple[LegacyOrderEvidence,...]
    def to_json_dict(self):
        d=asdict(self); d['recovery_status']=self.recovery_status.value; d['evidence']=[x.to_json_dict() for x in self.evidence]; return d

@dataclass(frozen=True)
class LedgerRecoveryReport:
    status:LedgerRecoveryStatus; safe_mode_engaged:bool; autonomous_order_allowed:bool; open_order_count:int; recovered_count:int; external_count:int; unknown_count:int; entries:tuple[RecoveredLedgerEntry,...]; scanned_file_count:int; evidence_count:int; read_requests_executed:int=0; write_requests_executed:int=0; actual_paper_orders_submitted:int=0; live_orders_submitted:int=0
    def to_json_dict(self):
        d=asdict(self); d['status']=self.status.value; d['entries']=[x.to_json_dict() for x in self.entries]; return d

class BrokerOrderNormalizer:
    ALIASES={'broker_order_id':('id','order_id','broker_order_id'),'client_order_id':('client_order_id','clientOrderId'),'symbol':('symbol',),'side':('side',),'quantity':('qty','quantity'),'order_type':('type','order_type','orderType'),'time_in_force':('time_in_force','timeInForce'),'status':('status',),'submitted_at':('submitted_at','submittedAt','created_at'),'filled_quantity':('filled_qty','filled_quantity','filledQty'),'limit_price':('limit_price','limitPrice')}
    def normalize(self,order:Any)->NormalizedBrokerOrder:
        sources=[order]
        for n in ('raw','_raw','data','_data','payload','order'):
            v=(order.get(n) if isinstance(order,Mapping) else getattr(order,n,None))
            if v is not None and v is not order: sources.append(v)
        vals={}
        for target,names in self.ALIASES.items():
            vals[target]=None
            for src in sources:
                for n in names:
                    v=src.get(n) if isinstance(src,Mapping) else getattr(src,n,None)
                    if v not in (None,''): vals[target]=v; break
                if vals[target] not in (None,''): break
        def text(v):
            if v is None:return ''
            if hasattr(v,'value'):v=v.value
            return str(v).strip()
        def iso(v): return v.isoformat() if hasattr(v,'isoformat') else text(v)
        lp=text(vals['limit_price']) or None
        return NormalizedBrokerOrder(text(vals['broker_order_id']),text(vals['client_order_id']),text(vals['symbol']).upper(),text(vals['side']).upper(),text(vals['quantity']),text(vals['order_type']).upper(),text(vals['time_in_force']).upper(),text(vals['status']).upper(),iso(vals['submitted_at']),text(vals['filled_quantity']) or '0',lp)

class RepositoryOrderEvidenceScanner:
    SUFFIXES={'.json','.txt','.md','.log','.py','.ps1','.yaml','.yml'}
    EXCLUDED={'.git','.venv','__pycache__','node_modules'}
    def scan(self,repository_root:Path,broker_order_id:str,client_order_id:str):
        ev=[]; scanned=0
        for p in repository_root.rglob('*'):
            if not p.is_file() or p.suffix.lower() not in self.SUFFIXES or any(x in self.EXCLUDED for x in p.parts): continue
            rel=str(p.relative_to(repository_root)).replace('\\','/')
            if rel.endswith('actual_open_order_identity_result.json'): continue
            if rel.startswith('release/v124_00/'): continue
            if 'v123_01_to_v124_00' in rel.lower(): continue
            try:t=p.read_text(encoding='utf-8',errors='ignore')
            except OSError:continue
            scanned+=1
            for typ,needle in (('CLIENT_ORDER_ID',client_order_id),('BROKER_ORDER_ID',broker_order_id)):
                if not needle or needle not in t: continue
                low=rel.lower(); conf='HIGH' if any(k in low for k in ('ledger','recovery','execution','submission','order')) else ('MEDIUM' if 'client_order_id' in t else 'LOW')
                ev.append(LegacyOrderEvidence(rel,typ,needle,conf))
        return tuple(ev),scanned

class AutonomousOrderLedgerRecovery:
    def __init__(self,normalizer=None,scanner=None): self.normalizer=normalizer or BrokerOrderNormalizer(); self.scanner=scanner or RepositoryOrderEvidenceScanner()
    def recover(self,repository_root:Path,open_orders:Sequence[Any],internal_order_ledger:Sequence[Mapping[str,Any]]):
        if not open_orders:return LedgerRecoveryReport(LedgerRecoveryStatus.NO_OPEN_ORDERS,False,True,0,0,0,0,(),0,0)
        cids={str(x.get('client_order_id','')).strip() for x in internal_order_ledger if str(x.get('client_order_id','')).strip()}; bids={str(x.get('broker_order_id','')).strip() for x in internal_order_ledger if str(x.get('broker_order_id','')).strip()}
        entries=[]; scanned=0; ec=0
        for raw in open_orders:
            n=self.normalizer.normalize(raw); ev,s=self.scanner.scan(repository_root,n.broker_order_id,n.client_order_id); scanned=max(scanned,s); ec+=len(ev)
            direct=n.client_order_id in cids or (n.broker_order_id and n.broker_order_id in bids); strong=any(x.confidence in {'HIGH','MEDIUM'} for x in ev)
            if direct: st=LedgerRecoveryStatus.RECOVERED; owner='BOT'; source='INTERNAL_LEDGER'
            elif strong: st=LedgerRecoveryStatus.RECOVERED; owner='LEGACY_BOT'; source='REPOSITORY_EVIDENCE'
            elif n.client_order_id: st=LedgerRecoveryStatus.EXTERNAL_ORDER; owner='EXTERNAL'; source='BROKER_ONLY'
            else: st=LedgerRecoveryStatus.UNKNOWN_ORDER; owner='UNKNOWN'; source='BROKER_ONLY'
            entries.append(RecoveredLedgerEntry(n.broker_order_id,n.client_order_id,n.symbol,n.side,n.quantity,n.order_type,n.time_in_force,n.status,n.submitted_at,n.filled_quantity,n.limit_price,owner,source,st,ev))
        rec=sum(x.recovery_status==LedgerRecoveryStatus.RECOVERED for x in entries); ext=sum(x.recovery_status==LedgerRecoveryStatus.EXTERNAL_ORDER for x in entries); unk=sum(x.recovery_status==LedgerRecoveryStatus.UNKNOWN_ORDER for x in entries); block=ext+unk
        overall=LedgerRecoveryStatus.RECOVERED if block==0 else (LedgerRecoveryStatus.UNKNOWN_ORDER if unk else LedgerRecoveryStatus.EXTERNAL_ORDER)
        return LedgerRecoveryReport(overall,block>0,block==0,len(entries),rec,ext,unk,tuple(entries),scanned,ec)
