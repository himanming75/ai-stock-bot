from _recovery_release_cli_v77_11_15 import *
def main():
 p=argparse.ArgumentParser()
 for n in ("v11","v12","v13","v14"):p.add_argument("--"+n,required=True)
 p.add_argument("--output-dir",required=True);a=p.parse_args()
 return print_result(issue_release_certificate(Path(a.v11),Path(a.v12),Path(a.v13),Path(a.v14),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
