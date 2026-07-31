from _paper_runtime_cli_v77_16_20 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--recovery",required=True);p.add_argument("--output-dir",required=True);p.add_argument("--cycles",type=int,default=1000);a=p.parse_args()
 return print_result(run_stability(Path(a.recovery),Path(a.output_dir),cycles=a.cycles))
if __name__=="__main__":raise SystemExit(main())
