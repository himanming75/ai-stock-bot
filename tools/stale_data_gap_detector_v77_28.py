from _market_data_cli_v77_26_30 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--feed",required=True);p.add_argument("--validation-ledger",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
    return print_result(detect_stale_data_gaps(Path(a.feed),Path(a.validation_ledger),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
