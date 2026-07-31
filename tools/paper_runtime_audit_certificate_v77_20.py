from _paper_runtime_cli_v77_16_20 import *
def main():
 p=argparse.ArgumentParser()
 for n in ("v16","v17","v18","v19"):p.add_argument("--"+n,required=True)
 p.add_argument("--output-dir",required=True);a=p.parse_args()
 return print_result(issue_runtime_certificate(Path(a.v16),Path(a.v17),Path(a.v18),Path(a.v19),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
