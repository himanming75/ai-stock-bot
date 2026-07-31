from _recovery_release_cli_v77_11_15 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",required=True);p.add_argument("--certificate",required=True);p.add_argument("--config",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
 cfg=load_json(Path(a.config))
 return print_result(build_manifest(Path(a.repository_root).resolve(),Path(a.certificate),Path(a.output_dir),cfg["expected_certificate_file_sha256"]))
if __name__=="__main__":raise SystemExit(main())
