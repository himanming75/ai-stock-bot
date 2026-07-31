from _scheduled_runtime_cli_v77_21_25 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--runtime-certificate",required=True);p.add_argument("--output-dir",required=True);p.add_argument("--interval-seconds",type=int,default=60);p.add_argument("--run-count",type=int,default=5);a=p.parse_args()
 return print_result(build_scheduler(Path(a.runtime_certificate),Path(a.output_dir),interval_seconds=a.interval_seconds,run_count=a.run_count))
if __name__=="__main__":raise SystemExit(main())
