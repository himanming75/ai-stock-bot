from _market_data_cli_v77_26_30 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--feed",required=True);p.add_argument("--detector",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
    return print_result(recover_market_data(Path(a.feed),Path(a.detector),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
