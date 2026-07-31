from _paper_runtime_cli_v77_16_20 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--session",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
 return print_result(build_state_ledger(Path(a.session),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
