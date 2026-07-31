from _scheduled_runtime_cli_v77_21_25 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--execution-ledger",required=True);p.add_argument("--output-dir",required=True);p.add_argument("--heartbeat-timeout-seconds",type=int,default=120);a=p.parse_args()
 return print_result(run_watchdog(Path(a.execution_ledger),Path(a.output_dir),heartbeat_timeout_seconds=a.heartbeat_timeout_seconds))
if __name__=="__main__":raise SystemExit(main())
