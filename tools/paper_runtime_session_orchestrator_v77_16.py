from _paper_runtime_cli_v77_16_20 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--release-certificate",required=True);p.add_argument("--output-dir",required=True);p.add_argument("--session-id");a=p.parse_args()
 return print_result(build_session_orchestrator(Path(a.release_certificate),Path(a.output_dir),session_id=a.session_id))
if __name__=="__main__":raise SystemExit(main())
