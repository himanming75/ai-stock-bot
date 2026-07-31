from _scheduled_runtime_cli_v77_21_25 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--schedule",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
 return print_result(build_execution_ledger(Path(a.schedule),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
