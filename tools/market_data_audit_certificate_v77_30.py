from _market_data_cli_v77_26_30 import *
def main():
    p=argparse.ArgumentParser()
    for n in ("v26","v27","v28","v29"): p.add_argument("--"+n,required=True)
    p.add_argument("--output-dir",required=True);a=p.parse_args()
    return print_result(issue_market_data_certificate(Path(a.v26),Path(a.v27),Path(a.v28),Path(a.v29),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
