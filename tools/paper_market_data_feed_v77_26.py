from _market_data_cli_v77_26_30 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--scheduled-runtime-certificate",required=True);p.add_argument("--output-dir",required=True)
    p.add_argument("--symbol",default="SPY");p.add_argument("--bar-count",type=int,default=30);p.add_argument("--interval-seconds",type=int,default=60)
    a=p.parse_args()
    return print_result(build_paper_market_data_feed(Path(a.scheduled_runtime_certificate),Path(a.output_dir),symbol=a.symbol,bar_count=a.bar_count,interval_seconds=a.interval_seconds))
if __name__=="__main__":raise SystemExit(main())
