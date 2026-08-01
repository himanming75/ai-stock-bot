from pathlib import Path
import argparse,hashlib,json
def d(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--repository-root',default='.'); a=p.parse_args(); out=Path(a.repository_root).resolve()/'release/v79_60/output'; cp=out/'historical_dataset_backup_restore_certificate_v79_60.json'; vp=out/'historical_dataset_backup_restore_verify_v79_60.json'; mp=out/'dataset_backup_restore_manifest_v79_59.json'; lp=out/'dataset_backup_restore_ledger.json'
 for x in (cp,vp,mp,lp):
  if not x.is_file(): raise SystemExit(f'VERIFY FAIL: missing {x}')
 c=json.loads(cp.read_text()); v=json.loads(vp.read_text()); m=json.loads(mp.read_text()); l=json.loads(lp.read_text()); u=dict(c); e=u.pop('certificate_sha256',None)
 checks={'certificate_status_pass':c.get('status')=='PASS','certificate_hash_valid':e==d(u),'verify_status_pass':v.get('status')=='PASS','verify_flag_true':v.get('verified') is True,'manifest_stage_v79_59':m.get('stage')=='V79.59','restored_hash_matches':c.get('checks',{}).get('restored_hash_matches') is True,'source_preserved':c.get('checks',{}).get('source_preserved') is True,'backup_preserved':c.get('checks',{}).get('backup_preserved') is True,'network_requests_zero':c.get('network_requests_executed')==0,'credentials_unused':c.get('credentials_used')==0,'trading_client_not_created':c.get('trading_client_created') is False,'actual_orders_zero':c.get('actual_orders_submitted')==0,'live_trading_not_authorized':c.get('live_trading_authorized') is False}; failed=[k for k,vv in checks.items() if not vv]; print(json.dumps({'stage_range':'V79.56-V79.60','status':'PASS' if not failed else 'FAIL','checks':checks,'failed_checks':failed,'next_phase':c.get('next_phase')},indent=2,sort_keys=True)); return 0 if not failed else 1
if __name__=='__main__': raise SystemExit(main())
