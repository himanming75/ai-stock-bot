from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _parse_dt(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(
        json.dumps(value,indent=2,sort_keys=True,default=str),
        encoding="utf-8",
    )
    os.replace(tmp,path)


def _sha_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk=f.read(1024*1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _finite(value):
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError,ValueError):
        return False


class TrainingDatasetBuilderV229:
    """
    Build leakage-controlled ML matrices from V2.2.8.1 forward-labeled rows.

    Two-pass streaming design:
      pass 1: collect unique market dates and source counts
      pass 2: emit chronological TRAIN/VALIDATION/TEST CSV files

    No broker/network/order code exists in this stage.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.source=(
            self.root/"runtime"/"ai_fast_data_acceleration_v2_2_8"/
            "training_forward_labels.jsonl"
        )
        self.policy_path=(
            self.root/"release"/
            "ai_trading_engine_v2_2_9_training_dataset_builder"/
            "config"/"training_dataset_policy.json"
        )
        self.runtime=(
            self.root/"runtime"/
            "ai_training_dataset_builder_v2_2_9"
        )
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.manifest=self.runtime/"dataset_manifest.json"
        self.latest=self.runtime/"latest_status.json"

    def policy(self):
        p=json.loads(self.policy_path.read_text(encoding="utf-8-sig"))
        if abs(
            float(p["train_fraction"])
            +float(p["validation_fraction"])
            +float(p["test_fraction"])
            -1.0
        ) > 1e-9:
            raise RuntimeError("INVALID_SPLIT_FRACTIONS")
        if int(p["embargo_trading_days"])<1:
            raise RuntimeError("EMBARGO_MUST_BE_AT_LEAST_ONE_DAY")
        if not p.get("feature_columns"):
            raise RuntimeError("FEATURE_COLUMNS_EMPTY")
        return p

    @staticmethod
    def _iter_jsonl(path):
        with path.open("r",encoding="utf-8") as f:
            for line_no,line in enumerate(f,1):
                if not line.strip():
                    continue
                try:
                    yield line_no,json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"INVALID_SOURCE_JSONL_LINE_{line_no}"
                    ) from exc

    @staticmethod
    def _market_date(row):
        return _parse_dt(row["timestamp"]).date().isoformat()

    def _first_pass(self):
        unique_dates=set()
        source_rows=0
        symbol_counts=Counter()
        feed_counts=Counter()
        malformed=0
        for _,row in self._iter_jsonl(self.source):
            source_rows+=1
            try:
                unique_dates.add(self._market_date(row))
                symbol_counts[str(row.get("symbol") or "")]+=1
                feed_counts[str(row.get("feed") or "")]+=1
            except Exception:
                malformed+=1
        return {
            "unique_dates":sorted(unique_dates),
            "source_rows":source_rows,
            "symbol_counts":dict(sorted(symbol_counts.items())),
            "feed_counts":dict(sorted(feed_counts.items())),
            "malformed_rows":malformed,
        }

    @staticmethod
    def _split_dates(dates,p):
        n=len(dates)
        embargo=int(p["embargo_trading_days"])
        if n<int(p["min_unique_market_dates"]):
            return None

        # Reserve two embargo blocks first, then split usable dates.
        usable=n-(2*embargo)
        if usable<3:
            return None

        train_n=max(1,int(usable*float(p["train_fraction"])))
        val_n=max(1,int(usable*float(p["validation_fraction"])))
        test_n=usable-train_n-val_n
        if test_n<1:
            # Rebalance from train where possible.
            shift=1-test_n
            train_n=max(1,train_n-shift)
            test_n=usable-train_n-val_n
        if test_n<1:
            return None

        i=0
        train=dates[i:i+train_n]; i+=train_n
        embargo1=dates[i:i+embargo]; i+=embargo
        validation=dates[i:i+val_n]; i+=val_n
        embargo2=dates[i:i+embargo]; i+=embargo
        test=dates[i:]

        if not train or not validation or not test:
            return None
        return {
            "train":train,
            "embargo_1":embargo1,
            "validation":validation,
            "embargo_2":embargo2,
            "test":test,
        }

    @staticmethod
    def _direction(ret,deadband):
        if ret>deadband:
            return "UP"
        if ret<-deadband:
            return "DOWN"
        return "FLAT"

    def _flat_row(self,row,horizon,p):
        features=row.get("features") or {}
        label=(row.get("forward_labels") or {}).get(f"{horizon}m")
        if label is None:
            return None,"MISSING_FORWARD_LABEL"

        vals={}
        for name in p["feature_columns"]:
            value=features.get(name)
            if p.get("require_all_features",True) and not _finite(value):
                return None,"MISSING_FEATURE"
            vals[name]=None if value is None else float(value)

        ret=label.get("forward_return_pct")
        mfe=label.get("mfe_pct")
        mae=label.get("mae_pct")
        if not (_finite(ret) and _finite(mfe) and _finite(mae)):
            return None,"INVALID_TARGET"

        market_date=self._market_date(row)
        ret=float(ret)
        flat={
            "timestamp":row["timestamp"],
            "market_date":market_date,
            "symbol":row.get("symbol"),
            "feed":row.get("feed"),
            **vals,
            "target_horizon_min":int(horizon),
            "target_return_pct":ret,
            "target_mfe_pct":float(mfe),
            "target_mae_pct":float(mae),
            "target_direction":self._direction(
                ret,float(p["direction_deadband_pct"])
            ),
            "target_timestamp":label.get("target_timestamp"),
        }
        return flat,None

    def build(self):
        p=self.policy()
        if not self.source.exists():
            result={
                "status":"WAITING_FOR_V2_2_8_1_TRAINING_FORWARD_LABELS",
                "source_exists":False,
                "dataset_ready":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
            _atomic_json(self.latest,result)
            return result

        first=self._first_pass()
        split=self._split_dates(first["unique_dates"],p)
        if split is None:
            result={
                "status":"WAITING_FOR_MORE_MARKET_DATES",
                "source_exists":True,
                "source_rows":first["source_rows"],
                "unique_market_dates":len(first["unique_dates"]),
                "minimum_unique_market_dates":
                    int(p["min_unique_market_dates"]),
                "dataset_ready":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
            _atomic_json(self.latest,result)
            return result

        date_to_split={}
        for d in split["train"]:
            date_to_split[d]="train"
        for d in split["validation"]:
            date_to_split[d]="validation"
        for d in split["test"]:
            date_to_split[d]="test"
        for d in split["embargo_1"]+split["embargo_2"]:
            date_to_split[d]="embargo"

        out_dir=self.runtime/"datasets"
        out_dir.mkdir(parents=True,exist_ok=True)

        fieldnames=(
            list(p["metadata_columns"])
            +list(p["feature_columns"])
            +[
                "target_horizon_min","target_return_pct",
                "target_mfe_pct","target_mae_pct",
                "target_direction","target_timestamp"
            ]
        )

        handles={}
        writers={}
        temp_paths={}
        final_paths={}
        try:
            for horizon in p["horizons_minutes"]:
                for split_name in ("train","validation","test"):
                    final=out_dir/f"{split_name}_{int(horizon)}m.csv"
                    temp=out_dir/f".{split_name}_{int(horizon)}m.csv.tmp"
                    h=temp.open("w",encoding="utf-8",newline="")
                    w=csv.DictWriter(h,fieldnames=fieldnames)
                    w.writeheader()
                    key=(int(horizon),split_name)
                    handles[key]=h
                    writers[key]=w
                    temp_paths[key]=temp
                    final_paths[key]=final

            counts=defaultdict(int)
            class_counts=defaultdict(Counter)
            skip_counts=Counter()
            emitted_source_rows=set()

            for line_no,row in self._iter_jsonl(self.source):
                try:
                    market_date=self._market_date(row)
                except Exception:
                    skip_counts["INVALID_TIMESTAMP"]+=1
                    continue
                split_name=date_to_split.get(market_date)
                if split_name=="embargo":
                    skip_counts["EMBARGO_DATE"]+=1
                    continue
                if split_name not in {"train","validation","test"}:
                    skip_counts["OUTSIDE_SPLIT"]+=1
                    continue

                any_emitted=False
                for horizon in p["horizons_minutes"]:
                    flat,reason=self._flat_row(row,int(horizon),p)
                    if flat is None:
                        skip_counts[f"{int(horizon)}m_{reason}"]+=1
                        continue
                    writers[(int(horizon),split_name)].writerow(flat)
                    counts[(int(horizon),split_name)]+=1
                    class_counts[(int(horizon),split_name)][
                        flat["target_direction"]
                    ]+=1
                    any_emitted=True
                if any_emitted:
                    emitted_source_rows.add(line_no)
        finally:
            for h in handles.values():
                h.close()

        for key,temp in temp_paths.items():
            os.replace(temp,final_paths[key])

        artifacts={}
        total_matrix_rows=0
        for horizon in p["horizons_minutes"]:
            hkey=f"{int(horizon)}m"
            artifacts[hkey]={}
            for split_name in ("train","validation","test"):
                key=(int(horizon),split_name)
                path=final_paths[key]
                n=counts[key]
                total_matrix_rows+=n
                artifacts[hkey][split_name]={
                    "path":str(path.relative_to(self.root)),
                    "rows":n,
                    "sha256":_sha_file(path),
                    "class_counts":dict(
                        sorted(class_counts[key].items())
                    ),
                }

        # Chronological and embargo assertions.
        chrono_ok=(
            max(split["train"]) < min(split["embargo_1"])
            and max(split["embargo_1"]) < min(split["validation"])
            and max(split["validation"]) < min(split["embargo_2"])
            and max(split["embargo_2"]) < min(split["test"])
        )

        leakage_guard={
            "chronological_split":True,
            "chronological_order_verified":bool(chrono_ok),
            "split_unit":"market_date",
            "embargo_trading_days":int(p["embargo_trading_days"]),
            "embargo_1_dates":split["embargo_1"],
            "embargo_2_dates":split["embargo_2"],
            "random_shuffle_before_split":False,
            "future_target_columns_excluded_from_features":True,
            "symbol_rows_can_span_splits_only_by_different_dates":True,
        }

        manifest={
            "stage":"AI_TRADING_ENGINE_V2_2_9_TRAINING_DATASET_BUILDER",
            "status":"PASS_TRAINING_DATASET_BUILD",
            "source_path":str(self.source.relative_to(self.root)),
            "source_sha256":_sha_file(self.source),
            "source_rows":first["source_rows"],
            "source_unique_market_dates":len(first["unique_dates"]),
            "source_symbol_counts":first["symbol_counts"],
            "source_feed_counts":first["feed_counts"],
            "features":list(p["feature_columns"]),
            "horizons_minutes":[int(x) for x in p["horizons_minutes"]],
            "split_dates":split,
            "leakage_guard":leakage_guard,
            "artifacts":artifacts,
            "source_rows_with_at_least_one_emitted_horizon":
                len(emitted_source_rows),
            "total_matrix_rows_across_horizons":total_matrix_rows,
            "skip_counts":dict(sorted(skip_counts.items())),
            "direction_deadband_pct":
                float(p["direction_deadband_pct"]),
            "minimum_rows_for_ready":int(p["min_rows_for_ready"]),
            "dataset_ready":(
                chrono_ok
                and all(
                    artifacts[f"{int(h)}m"][s]["rows"]
                    >= int(p["min_rows_for_ready"])
                    for h in p["horizons_minutes"]
                    for s in ("train","validation","test")
                )
            ),
            "broker_network_used":False,
            "orders_submitted":0,
            "live_trading":False,
        }
        _atomic_json(self.manifest,manifest)
        _atomic_json(self.latest,manifest)
        return manifest

    def status(self):
        if not self.manifest.exists():
            return {
                "status":"WAITING_FOR_DATASET_BUILD",
                "dataset_ready":False,
                "broker_network_used":False,
                "orders_submitted":0,
                "live_trading":False,
            }
        return json.loads(
            self.manifest.read_text(encoding="utf-8")
        )
