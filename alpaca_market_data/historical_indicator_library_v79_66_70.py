from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

def cj(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def hj(v:Any)->str:return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def wj(p:Path,v:Any):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding='utf-8')
def aw(p:Path,b:bytes):
 p.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile('wb',delete=False,dir=p.parent) as h:h.write(b);t=Path(h.name)
 os.replace(t,p)
@dataclass(frozen=True)
class IndicatorConfig:
 macd_fast:int=2;macd_slow:int=3;macd_signal:int=2;bollinger_window:int=3;stochastic_window:int=3;roc_window:int=2
 allow_network:bool=False;allow_credentials:bool=False;allow_trading_client:bool=False;allow_order_submission:bool=False;actual_orders_submitted:int=0
 def validate(self):
  if not(1<self.macd_fast<self.macd_slow) or min(self.macd_signal,self.bollinger_window,self.stochastic_window,self.roc_window)<2:raise ValueError('invalid windows')
  if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:raise ValueError('offline only')

def validate_feature_certificate(path:Path)->dict[str,Any]:
 if not path.is_file():raise FileNotFoundError(path)
 c=json.loads(path.read_text());u=dict(c);e=u.pop('certificate_sha256',None)
 if e!=hj(u) or c.get('stage')!='V79.65' or c.get('status')!='PASS':raise ValueError('bad feature certificate')
 return c

def locate_feature_data(output:Path,cert:dict[str,Any])->Path:
 cid=cert['feature_summary']['cache_id'];p=output/'cache'/cid/'historical_features.jsonl'
 if not p.is_file():raise FileNotFoundError(p)
 return p

def load_feature_rows(path:Path)->list[dict[str,Any]]:
 out=[]
 for n,line in enumerate(path.read_text().splitlines(),1):
  if not line.strip():continue
  try:x=json.loads(line)
  except Exception as e:raise ValueError(f'bad line {n}') from e
  if not {'symbol','timeframe','timestamp','source_close','features'}.issubset(x):raise ValueError('missing feature fields')
  out.append(x)
 if not out:raise ValueError('empty feature input')
 return out

def ema(values:list[float],window:int)->list[float]:
 a=2/(window+1);out=[];cur=None
 for v in values:cur=v if cur is None else a*v+(1-a)*cur;out.append(cur)
 return out

def build_indicator_registry(c:IndicatorConfig)->dict[str,Any]:
 c.validate();names=['macd','macd_signal','macd_histogram','bollinger_mid','bollinger_upper','bollinger_lower','stochastic_k','roc','obv']
 d={'stage':'V79.66','indicator_count':len(names),'indicators':[{'name':n,'dtype':'float'} for n in names]};d['registry_sha256']=hj(d);return d

def build_indicators(rows:list[dict[str,Any]],c:IndicatorConfig)->list[dict[str,Any]]:
 groups={}
 for x in rows:groups.setdefault(x['symbol'],[]).append(x)
 out=[]
 for s,items in groups.items():
  items=sorted(items,key=lambda x:x['timestamp']);cl=[float(x['source_close']) for x in items]
  fast=ema(cl,c.macd_fast);slow=ema(cl,c.macd_slow);macd=[a-b for a,b in zip(fast,slow)];sig=ema(macd,c.macd_signal);obv=0.0
  for i,x in enumerate(items):
   if i>0:obv+=1.0 if cl[i]>cl[i-1] else (-1.0 if cl[i]<cl[i-1] else 0.0)
   if i+1>=c.bollinger_window:
    w=cl[i-c.bollinger_window+1:i+1];mid=sum(w)/len(w);sd=(sum((v-mid)**2 for v in w)/len(w))**0.5
   else:mid=sd=None
   if i+1>=c.stochastic_window:
    w=cl[i-c.stochastic_window+1:i+1];lo=min(w);hi=max(w);st=50.0 if hi==lo else 100*(cl[i]-lo)/(hi-lo)
   else:st=None
   roc=None if i<c.roc_window else (cl[i]/cl[i-c.roc_window]-1)*100
   ind={'macd':macd[i],'macd_signal':sig[i],'macd_histogram':macd[i]-sig[i],'bollinger_mid':mid,'bollinger_upper':None if mid is None else mid+2*sd,'bollinger_lower':None if mid is None else mid-2*sd,'stochastic_k':st,'roc':roc,'obv':obv}
   out.append({'symbol':s,'timeframe':x['timeframe'],'timestamp':x['timestamp'],'source_close':cl[i],'indicators':ind})
 return sorted(out,key=lambda x:(x['symbol'],x['timestamp']))

def validate_indicator_rows(rows,registry):
 names={x['name'] for x in registry['indicators']};keys=set()
 for x in rows:
  k=(x['symbol'],x['timeframe'],x['timestamp'])
  if k in keys:raise ValueError('duplicate indicator key')
  keys.add(k)
  if set(x['indicators'])!=names:raise ValueError('indicator schema')
  for v in x['indicators'].values():
   if v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v)):raise ValueError('invalid indicator')
 return {'indicator_row_count':len(rows),'unique_indicator_key_count':len(keys),'invalid_indicator_value_count':0}

def store_indicators(out:Path,src:Path,reg,rows,stats):
 data=''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows).encode();cid=f"indicators-{hb(src.read_bytes())[:16]}-{reg['registry_sha256'][:12]}";dp=out/'cache'/cid/'historical_indicators.jsonl'
 created=not dp.exists()
 if dp.exists() and dp.read_bytes()!=data:raise ValueError('indicator cache conflict')
 if created:aw(dp,data)
 rp=out/'indicator_registry.json';wj(rp,reg);led={'stage':'V79.68','cache_id':cid,'created':created,'reused_existing_cache':not created,**stats};led['ledger_sha256']=hj(led);lp=out/'indicator_cache_ledger.json';wj(lp,led)
 man={'stage':'V79.69','cache_id':cid,'indicator_count':reg['indicator_count'],**stats,'files':{},'network_requests_executed':0,'credentials_used':0,'trading_client_created':False,'actual_orders_submitted':0}
 for n,p in [('registry',rp),('ledger',lp),('indicators',dp)]:
  b=p.read_bytes();man['files'][n]={'relative_path':str(p.relative_to(out)).replace('\\','/'),'sha256':hb(b),'byte_size':len(b)}
 man['manifest_sha256']=hj(man);wj(out/'historical_indicator_manifest_v79_69.json',man)
 return {'cache_id':cid,'created':created,'reused_existing_cache':not created,'manifest':man}

def verify_indicator_manifest(out,man):
 u=dict(man);e=u.pop('manifest_sha256',None)
 if e!=hj(u):raise ValueError('manifest hash')
 for info in man['files'].values():
  p=out/info['relative_path'];b=p.read_bytes()
  if hb(b)!=info['sha256'] or len(b)!=info['byte_size']:raise ValueError('output integrity')
 return True

def run_indicator_library(feature_output:Path,cert_path:Path,c:IndicatorConfig,out:Path):
 cert=validate_feature_certificate(cert_path);src=locate_feature_data(feature_output,cert);reg=build_indicator_registry(c);rows=build_indicators(load_feature_rows(src),c);stats=validate_indicator_rows(rows,reg);st=store_indicators(out,src,reg,rows,stats);verify_indicator_manifest(out,st['manifest'])
 return {'stage':'V79.69','status':'PASS','registry':reg,'stats':stats,**st,'source_preserved':src.is_file(),'network_requests_executed':0,'credentials_used':0,'trading_client_created':False,'actual_orders_submitted':0}

def build_indicator_certificate(root:Path,out:Path,c:IndicatorConfig,r):
 checks={'v79_65_certificate_present':(root/'release/v79_65/output/historical_feature_store_certificate_v79_65.json').is_file(),'pipeline_status_pass':r['status']=='PASS','indicator_rows_positive':r['stats']['indicator_row_count']>0,'invalid_values_zero':r['stats']['invalid_indicator_value_count']==0,'source_preserved':r['source_preserved'] is True,'network_requests_zero':r['network_requests_executed']==0,'credentials_unused':r['credentials_used']==0,'trading_client_not_created':r['trading_client_created'] is False,'actual_orders_zero':r['actual_orders_submitted']==0}
 failed=[k for k,v in checks.items() if not v];status='PASS' if not failed else 'FAIL';cert={'stage':'V79.70','status':status,'scope':'OFFLINE_HISTORICAL_INDICATOR_LIBRARY','passed_stage_count':5 if status=='PASS' else 0,'failed_stage_count':0 if status=='PASS' else len(failed),'config':asdict(c),'indicator_summary':{'cache_id':r['cache_id'],'indicator_count':r['registry']['indicator_count'],**r['stats'],'cache_created':r['created'],'cache_reused':r['reused_existing_cache'],'source_preserved':r['source_preserved']},'indicator_manifest':r['manifest'],'checks':checks,'failed_checks':failed,'network_requests_executed':0,'credentials_used':0,'broker_connected':False,'trading_client_created':False,'actual_orders_submitted':0,'live_trading_authorized':False,'next_phase':'V79_71_HISTORICAL_SIGNAL_ENGINE'};cert['certificate_sha256']=hj(cert);cp=out/'historical_indicator_library_certificate_v79_70.json';wj(cp,cert);wj(out/'historical_indicator_library_verify_v79_70.json',{'stage':'V79.70','status':status,'verified':not failed,'certificate_sha256':cert['certificate_sha256'],'failed_checks':failed});return cert
sha256_indicator_json=hj
