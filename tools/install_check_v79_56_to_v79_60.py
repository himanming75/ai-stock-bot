from pathlib import Path
import importlib,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
REQ=['alpaca_market_data/dataset_backup_restore_v79_56_60.py','tools/run_v79_56_to_v79_60_pipeline.py','tools/test_dataset_backup_restore_v79_56_to_v79_60.py','tools/verify_v79_56_to_v79_60_pipeline.py','release/v79_56/config/dataset_backup_restore_config_v79_56.json']
missing=[x for x in REQ if not (ROOT/x).is_file()]
if missing: raise SystemExit('MISSING: '+', '.join(missing))
importlib.import_module('alpaca_market_data.dataset_backup_restore_v79_56_60').BackupRestoreConfig().validate()
print('V79.56-V79.60 INSTALL CHECK PASS')
