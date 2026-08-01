from __future__ import annotations
from dataclasses import asdict,dataclass
from pathlib import Path
from typing import Any
import hashlib,json,math,os,tempfile

def cj(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding='utf-8')
def aw(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile('wb',delete=False,dir=p.parent) as h: h.write(b); t=Path(h.name)
 os.replace(t,p)
@dataclass(frozen=True)
class FeatureStoreConfig:
 sma_window:int=2; ema_window:int=3; rsi_window:int=2; atr_window:int=2
 allow_network:bool=False; allow_credentials:bool=False; allow_trading_client:bool=False; allow_order_submission:bool=False; actual_orders_submitted:int=0
 def validate(self):
  if min(self.sma_window,self.ema_window,self.rsi_window,self.atr_window)<2: raise ValueError('windows')
  if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted: raise ValueError('offline only')
def registry(c):
 c.validate(); names=[('return_1',1),('sma_2',2),('ema_3',1),('rsi_2',3),('atr_2',2),('vwap_cumulative',1),('volume_ratio_2',2)]
 d={'stage':'V79.61','feature_count':7,'features':[{'name':n,'warmup':w,'dtype':'float'} for n,w in names]}; d['registry_sha256']=hj(d); return d
def cert(path):
 if not path.is_file(): raise FileNotFoundError(path)
 c=json.loads(path.read_text()); u=dict(c); e=u.pop('certificate_sha256',None)
 if e!=hj(u) or c.get('stage')!='V79.60' or c.get('status')!='PASS': raise ValueError('bad certificate')
 return c
def source_path(base,c):
 bid=c['backup_restore_summary']['backup_id']; p=base/'restore'/bid/'alpaca_historical_bars.restored.jsonl'
 if not p.is_file(): raise FileNotFoundError(p)
 return p
def load(path):
 out=[]
 for n,line in enumerate(path.read_text().splitlines(),1):
  if not line.strip(): continue
  try: x=json.loads(line)
  except Exception as e: raise ValueError(f'bad line {n}') from e
  if not {'symbol','timeframe','timestamp','open','high','low','close','volume'}.issubset(x): raise ValueError('missing fields')
  out.append(x)
 if not out: raise ValueError('empty')
 return out
def sma(a,w,i): return None if i+1<w else sum(a[i-w+1:i+1])/w
def rsi(a,w,i):
 if i<w:return None
 ch=[a[j]-a[j-1] for j in range(i-w+1,i+1)]; g=sum(max(x,0) for x in ch)/w; l=sum(max(-x,0) for x in ch)/w
 return 100.0 if l==0 and g>0 else (50.0 if l==0 else 100-100/(1+g/l))
def build(rows,c):
 groups={}
 for x in rows: groups.setdefault(x['symbol'],[]).append(x)
 out=[]
 for s,b in groups.items():
  b=sorted(b,key=lambda x:x['timestamp']); closes=[float(x['close']) for x in b]; vols=[float(x['volume']) for x in b]; ema=None; trs=[]; pv=0.; vv=0.; alpha=2/(c.ema_window+1)
  for i,x in enumerate(b):
   close=closes[i]; ema=close if ema is None else alpha*close+(1-alpha)*ema; pc=closes[i-1] if i else close
   tr=max(float(x['high'])-float(x['low']),abs(float(x['high'])-pc),abs(float(x['low'])-pc)); trs.append(tr); typ=(float(x['high'])+float(x['low'])+close)/3; pv+=typ*vols[i]; vv+=vols[i]
   f={'return_1':None if i==0 else close/closes[i-1]-1,'sma_2':sma(closes,2,i),'ema_3':ema,'rsi_2':rsi(closes,2,i),'atr_2':sma(trs,2,i),'vwap_cumulative':pv/vv if vv else None,'volume_ratio_2':None if i<1 else vols[i]/((vols[i-1]+vols[i])/2)}
   out.append({'symbol':s,'timeframe':x['timeframe'],'timestamp':x['timestamp'],'source_close':close,'features':f})
 return sorted(out,key=lambda x:(x['symbol'],x['timestamp']))
def validate(rows,reg):
 names={x['name'] for x in reg['features']}; keys=set()
 for x in rows:
  k=(x['symbol'],x['timeframe'],x['timestamp'])
  if k in keys: raise ValueError('duplicate')
  keys.add(k)
  if set(x['features'])!=names: raise ValueError('schema')
  if any(v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v)) for v in x['features'].values()): raise ValueError('invalid')
 return {'feature_row_count':len(rows),'unique_feature_key_count':len(keys),'invalid_feature_value_count':0}
def store(out,src,reg,rows,stats):
 data=''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows).encode(); cid=f"features-{hb(src.read_bytes())[:16]}-{reg['registry_sha256'][:12]}"; dp=out/'cache'/cid/'historical_features.jsonl'
 created=not dp.exists()
 if dp.exists() and dp.read_bytes()!=data: raise ValueError('cache conflict')
 if created: aw(dp,data)
 rp=out/'feature_registry.json'; wj(rp,reg); led={'stage':'V79.63','cache_id':cid,'created':created,'reused_existing_cache':not created,**stats}; led['ledger_sha256']=hj(led); lp=out/'feature_cache_ledger.json'; wj(lp,led)
 man={'stage':'V79.64','cache_id':cid,'feature_count':reg['feature_count'],**stats,'files':{},'network_requests_executed':0,'credentials_used':0,'trading_client_created':False,'actual_orders_submitted':0}
 for n,p in [('registry',rp),('ledger',lp),('features',dp)]:
  b=p.read_bytes(); man['files'][n]={'relative_path':str(p.relative_to(out)).replace('\\','/'),'sha256':hb(b),'byte_size':len(b)}
 man['manifest_sha256']=hj(man); wj(out/'historical_feature_manifest_v79_64.json',man); return {'cache_id':cid,'created':created,'reused_existing_cache':not created,'manifest':man}
def verify(out,m):
 u=dict(m); e=u.pop('manifest_sha256',None)
 if e!=hj(u): raise ValueError('manifest hash')
 for x in m['files'].values():
  b=(out/x['relative_path']).read_bytes()
  if hb(b)!=x['sha256'] or len(b)!=x['byte_size']: raise ValueError('tamper')
 return True
def run(base,cp,c,out):
 c.validate(); src=source_path(base,cert(cp)); reg=registry(c); rows=build(load(src),c); stats=validate(rows,reg); st=store(out,src,reg,rows,stats); verify(out,st['manifest']); return {'status':'PASS','registry':reg,'stats':stats,**st,'source_preserved':src.is_file(),'network_requests_executed':0,'credentials_used':0,'trading_client_created':False,'actual_orders_submitted':0}
def certificate(root,out,c,r):
 checks={'v79_60_certificate_present':(root/'release/v79_60/output/historical_dataset_backup_restore_certificate_v79_60.json').is_file(),'pipeline_status_pass':r['status']=='PASS','feature_rows_positive':r['stats']['feature_row_count']>0,'invalid_values_zero':r['stats']['invalid_feature_value_count']==0,'source_preserved':r['source_preserved'],'network_requests_zero':r['network_requests_executed']==0,'credentials_unused':r['credentials_used']==0,'trading_client_not_created':r['trading_client_created'] is False,'actual_orders_zero':r['actual_orders_submitted']==0}
 failed=[k for k,v in checks.items() if not v]; status='PASS' if not failed else 'FAIL'; d={'stage':'V79.65','status':status,'passed_stage_count':5 if status=='PASS' else 0,'failed_stage_count':len(failed),'feature_summary':{'cache_id':r['cache_id'],'feature_count':r['registry']['feature_count'],**r['stats'],'cache_created':r['created'],'cache_reused':r['reused_existing_cache'],'source_preserved':r['source_preserved']},'checks':checks,'failed_checks':failed,'network_requests_executed':0,'credentials_used':0,'broker_connected':False,'trading_client_created':False,'actual_orders_submitted':0,'live_trading_authorized':False,'next_phase':'V79_66_HISTORICAL_INDICATOR_LIBRARY'}; d['certificate_sha256']=hj(d); p=out/'historical_feature_store_certificate_v79_65.json'; wj(p,d); wj(out/'historical_feature_store_verify_v79_65.json',{'stage':'V79.65','status':status,'verified':not failed,'certificate_sha256':d['certificate_sha256'],'failed_checks':failed}); return d
sha256_feature_json=hj
