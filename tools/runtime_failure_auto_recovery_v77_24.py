from _scheduled_runtime_cli_v77_21_25 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--watchdog",required=True);p.add_argument("--execution-ledger",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
 return print_result(auto_recover(Path(a.watchdog),Path(a.execution_ledger),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
