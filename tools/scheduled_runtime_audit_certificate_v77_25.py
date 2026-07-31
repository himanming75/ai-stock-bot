from _scheduled_runtime_cli_v77_21_25 import *
def main():
 p=argparse.ArgumentParser()
 for n in ("v21","v22","v23","v24"):p.add_argument("--"+n,required=True)
 p.add_argument("--output-dir",required=True);a=p.parse_args()
 return print_result(issue_scheduled_runtime_certificate(Path(a.v21),Path(a.v22),Path(a.v23),Path(a.v24),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
