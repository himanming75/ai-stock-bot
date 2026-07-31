from _recovery_release_cli_v77_11_15 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",required=True);p.add_argument("--manifest",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
 return print_result(build_bundle(Path(a.repository_root).resolve(),Path(a.manifest),Path(a.output_dir)))
if __name__=="__main__":raise SystemExit(main())
