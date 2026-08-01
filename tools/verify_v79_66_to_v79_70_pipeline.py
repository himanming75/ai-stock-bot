from pathlib import Path
import argparse,json
def main():
 p=argparse.ArgumentParser();p.add_argument('--repository-root',default='.');a=p.parse_args();o=Path(a.repository_root).resolve()/'release/v79_70/output';cp=o/'historical_indicator_library_certificate_v79_70.json';vp=o/'historical_indicator_library_verify_v79_70.json';mp=o/'historical_indicator_manifest_v79_69.json'
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f'VERIFY FAIL: missing {x}')
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());checks={'certificate_status_pass':c.get('status')=='PASS','verify_flag_true':v.get('verified') is True,'manifest_stage_v79_69':m.get('stage')=='V79.69','indicator_rows_positive':c.get('indicator_summary',{}).get('indicator_row_count',0)>0,'invalid_values_zero':c.get('indicator_summary',{}).get('invalid_indicator_value_count')==0,'actual_orders_zero':c.get('actual_orders_submitted')==0};failed=[k for k,z in checks.items() if not z];print(json.dumps({'stage_range':'V79.66-V79.70','status':'PASS' if not failed else 'FAIL','checks':checks,'failed_checks':failed,'next_phase':c.get('next_phase')},indent=2));return 0 if not failed else 1
if __name__=='__main__':raise SystemExit(main())
