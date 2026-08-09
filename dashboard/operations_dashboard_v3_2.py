from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse
import json
import subprocess

ROOT_DEFAULT = Path(r"C:\stock-bot")
TEMPLATE_REL = Path("dashboard/templates/operations_dashboard_v3_2.html")

FIXED = {
    "v294": Path("runtime/regime_aware_buy_shadow_v2_9_4/latest_runtime_observation_gate_v2_9_4.json"),
    "v30": Path("runtime/paper_2week_validation_v3_0/latest_validation_report.json"),
    "shadow_snapshot": Path("runtime/regime_aware_buy_shadow_v2_7/latest_shadow_snapshot.json"),
    "shadow_ledger": Path("runtime/regime_aware_buy_shadow_v2_7/shadow_candidate_ledger.jsonl"),
    "hook_ledger": Path("runtime/regime_aware_buy_shadow_v2_8_1/hook_ledger.jsonl"),
    "paper_session": Path("runtime/paper_autonomous_daily_session/session_ledger.jsonl"),
}


def read_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def read_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def num(value):
    try:
        return float(value)
    except Exception:
        return None


def first(mapping, *keys):
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def find_nested(obj, names):
    wanted = {name.lower() for name in names}
    found = []

    def walk(value, path=""):
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else key
                if key.lower() in wanted:
                    found.append((child_path, child))
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value[:100]):
                walk(child, f"{path}[{index}]")

    walk(obj)
    return found


def runtime_candidates(root: Path):
    runtime = root / "runtime"
    if not runtime.exists():
        return []

    candidates = []
    for path in runtime.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
            continue

        name = path.name.lower()
        if not any(
            token in name
            for token in ("account", "position", "order", "portfolio", "snapshot", "metrics", "ledger")
        ):
            continue

        try:
            candidates.append((path.stat().st_mtime, path))
        except Exception:
            pass

    return [path for _, path in sorted(candidates, reverse=True)[:250]]


def load_candidate(path: Path):
    if path.suffix.lower() == ".jsonl":
        rows = read_jsonl(path)
        return rows[-1] if rows else {}
    return read_json(path)


def discover_account_positions_orders(root: Path):
    account = {"equity": None, "cash": None, "buying_power": None}
    positions = []
    open_orders = []
    recent_orders = []
    used_sources = []

    for path in runtime_candidates(root):
        obj = load_candidate(path)
        if not obj:
            continue

        if all(account[key] is None for key in account):
            equity = find_nested(obj, {"equity", "portfolio_value", "account_equity"})
            cash = find_nested(obj, {"cash", "cash_balance"})
            buying_power = find_nested(obj, {"buying_power", "buyingpower"})

            if equity or cash or buying_power:
                account["equity"] = num(equity[0][1]) if equity else None
                account["cash"] = num(cash[0][1]) if cash else None
                account["buying_power"] = num(buying_power[0][1]) if buying_power else None
                used_sources.append(str(path.relative_to(root)).replace("\\", "/"))

        if not positions:
            for _, value in find_nested(obj, {"positions", "current_positions", "open_positions"}):
                if not isinstance(value, list) or not value:
                    continue

                normalized = []
                for item in value:
                    if not isinstance(item, dict):
                        continue

                    symbol = first(item, "symbol", "ticker")
                    if not symbol:
                        continue

                    normalized.append(
                        {
                            "symbol": str(symbol),
                            "qty": first(item, "qty", "quantity", "position_qty"),
                            "avg_entry_price": num(
                                first(item, "avg_entry_price", "average_entry_price", "avg_price")
                            ),
                            "market_value": num(first(item, "market_value", "value")),
                            "unrealized_pl": num(
                                first(
                                    item,
                                    "unrealized_pl",
                                    "unrealized_pnl",
                                    "unrealized_profit_loss",
                                )
                            ),
                        }
                    )

                if normalized:
                    positions = normalized
                    used_sources.append(str(path.relative_to(root)).replace("\\", "/"))
                    break

        if not open_orders:
            for _, value in find_nested(obj, {"open_orders", "orders", "pending_orders"}):
                if not isinstance(value, list) or not value:
                    continue

                normalized = []
                for item in value:
                    if not isinstance(item, dict):
                        continue

                    order_status = str(first(item, "status", "order_status") or "")
                    if order_status.lower() in {
                        "filled",
                        "canceled",
                        "cancelled",
                        "rejected",
                        "expired",
                    }:
                        continue

                    symbol = first(item, "symbol", "ticker")
                    if not symbol:
                        continue

                    normalized.append(
                        {
                            "time": first(
                                item,
                                "submitted_at",
                                "created_at",
                                "timestamp",
                                "time",
                            ),
                            "symbol": str(symbol),
                            "side": first(item, "side", "action"),
                            "qty": first(item, "qty", "quantity"),
                            "status": order_status,
                        }
                    )

                if normalized:
                    open_orders = normalized
                    used_sources.append(str(path.relative_to(root)).replace("\\", "/"))
                    break

    return account, positions, open_orders, recent_orders, used_sources


def collect_event_rows(root: Path):
    rows = []
    seen = set()

    for path in runtime_candidates(root):
        if path.suffix.lower() != ".jsonl":
            continue

        for record in read_jsonl(path)[-500:]:
            if not isinstance(record, dict):
                continue

            event = str(first(record, "event_type", "event", "stage", "type") or "")
            if not event:
                continue

            if not any(
                token in event.upper()
                for token in ("TRADE", "ORDER", "ENTRY", "EXIT", "FILL", "POSITION")
            ):
                continue

            row = {
                "time": first(
                    record,
                    "timestamp_utc",
                    "generated_at_utc",
                    "timestamp",
                    "time",
                    "checkpoint_et",
                ),
                "event": event,
                "symbol": first(record, "symbol", "ticker"),
                "side": first(record, "side", "action"),
                "qty": first(record, "qty", "quantity"),
                "pnl": first(
                    record,
                    "pnl",
                    "profit_loss",
                    "realized_pnl",
                    "net_pnl",
                    "net_return_after_cost",
                ),
                "reason": first(record, "reason", "exit_reason", "status"),
            }

            key = tuple(str(row[key]) for key in ("time", "event", "symbol", "side", "qty", "pnl"))
            if key in seen:
                continue

            seen.add(key)
            rows.append(row)

    rows.sort(key=lambda row: str(row.get("time") or ""), reverse=True)
    return rows[:100]


def closed_trade_metrics(events, start_date=None):
    closed = [
        row
        for row in events
        if "CLOSED_TRADE" in str(row.get("event", "")).upper()
    ]

    pnls = [num(row.get("pnl")) for row in closed]
    pnls = [value for value in pnls if value is not None]

    validation_closed = [
        row
        for row in closed
        if start_date and str(row.get("time") or "")[:10] >= str(start_date)
    ]

    gains = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]

    profit_factor = None
    if gains and losses and sum(losses) != 0:
        profit_factor = sum(gains) / abs(sum(losses))

    return {
        "validation_closed_trades": len(validation_closed),
        "historical_closed_trades": len(closed),
        "historical_realized_pnl": sum(pnls) if pnls else 0.0,
        "win_rate": len(gains) / len(pnls) if pnls else None,
        "profit_factor": profit_factor,
    }


def discover_git_executable():
    import shutil

    found = shutil.which("git")
    if found:
        return found

    candidates = [
        Path(r"C:\Program Files\Git\cmd\git.exe"),
        Path(r"C:\Program Files\Git\bin\git.exe"),
        Path(r"C:\Program Files (x86)\Git\cmd\git.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Git" / "cmd" / "git.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def git_state(root: Path):
    git_exe = discover_git_executable()

    if not git_exe:
        return {
            "branch": "UNKNOWN",
            "head_short": "",
            "origin_main_short": "",
            "synced": True,
            "available": False,
            "error": "GIT_EXECUTABLE_NOT_FOUND",
        }

    def run(*args):
        try:
            process = subprocess.run(
                [git_exe, *args],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            return (process.stdout or "").strip()
        except Exception:
            return ""

    head = run("rev-parse", "HEAD")
    origin = run("rev-parse", "origin/main")
    branch = run("branch", "--show-current")

    return {
        "branch": branch or "UNKNOWN",
        "head_short": head[:8],
        "origin_main_short": origin[:8],
        "synced": True if not head or not origin else head == origin,
        "available": True,
        "error": None,
    }


def _build_status_v3_2(root: Path):
    v294 = read_json(root / FIXED["v294"])
    v30 = read_json(root / FIXED["v30"])
    shadow_snapshot = read_json(root / FIXED["shadow_snapshot"])
    shadow_rows = read_jsonl(root / FIXED["shadow_ledger"])
    hook_rows = read_jsonl(root / FIXED["hook_ledger"])
    session_rows = read_jsonl(root / FIXED["paper_session"])

    git = git_state(root)
    account, positions, open_orders, recent_orders, discovered_sources = (
        discover_account_positions_orders(root)
    )
    timeline = collect_event_rows(root)

    validation_state = v30.get("validation_state", {}) or {}
    validation_start = validation_state.get("validation_start_trading_date")
    performance = closed_trade_metrics(timeline, validation_start)

    successful_hooks = int(v294.get("successful_hook_count", 0) or 0)
    required_hooks = int(v294.get("required_successful_hooks", 3) or 3)

    blocked = any(
        [
            str(v294.get("status", "")).startswith("BLOCKED"),
            str(v30.get("status", "")).startswith("BLOCKED"),
            any(
                row.get("primary_paper_flow_blocked") is True
                for row in hook_rows
            ),
            not git["synced"],
        ]
    )

    health = (
        "BLOCKED_ATTENTION_REQUIRED"
        if blocked
        else ("WAITING_FOR_RUNTIME" if successful_hooks < required_hooks else "HEALTHY")
    )

    signals = [
        row
        for row in shadow_rows
        if row.get("event_type") == "SHADOW_SIGNAL"
    ]
    outcomes = [
        row
        for row in shadow_rows
        if row.get("event_type") == "SHADOW_OUTCOME"
    ]

    fixed_sources = [
        str(path).replace("\\", "/")
        for path in FIXED.values()
        if (root / path).exists()
    ]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "health": {"overall": health},
        "git": git,
        "runtime_gate": {
            "status": v294.get("status", "NO_GATE_REPORT"),
            "successful_hooks": successful_hooks,
            "required_hooks": required_hooks,
        },
        "two_week": {
            "status": v30.get("status", "NO_V3_REPORT"),
            "completed_days": int(
                validation_state.get("completed_trading_days", 0) or 0
            ),
            "required_days": int(
                validation_state.get("required_trading_days", 10) or 10
            ),
            "remaining_days": int(
                validation_state.get("remaining_trading_days", 10) or 10
            ),
            "start_date": validation_start,
        },
        "account": account,
        "positions": positions,
        "open_orders": open_orders,
        "recent_orders": recent_orders,
        "performance": performance,
        "shadow": {
            "status": shadow_snapshot.get("status", "NO_SHADOW_SNAPSHOT"),
            "signal_count": len(signals),
            "outcome_count": len(outcomes),
        },
        "paper": {
            "record_count": len(session_rows),
            "latest_stage": session_rows[-1].get("stage")
            if session_rows
            else None,
        },
        "timeline": timeline[:25],
        "data_sources": sorted(set(fixed_sources + discovered_sources)),
        "contracts": {
            "read_only": True,
            "runtime_files_modified": False,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "production_parameter_modified": False,
            "production_selector_modified": False,
        },
    }


def build_status(root: Path):
    payload = _build_status_v3_2(root)

    try:
        import importlib.util

        module_path = root / "dashboard" / "visualization_v3_4.py"

        spec = importlib.util.spec_from_file_location(
            "ai_stock_bot_visualization_v3_4",
            module_path,
        )

        if spec is None or spec.loader is None:
            raise ModuleNotFoundError(
                f"Unable to load visualization module: {module_path}"
            )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        payload["visualization"] = module.build_visualization(
            root,
            payload,
        )
        payload["visualization_status"] = "PASS"
    except Exception as exc:
        payload["visualization"] = {
            "equity_history": [],
            "daily_realized_pnl": [],
            "generic_pnl_history": [],
            "position_allocation": [],
            "validation_slots": [],
            "summary": {},
            "contracts": {
                "read_only": True,
                "broker_network_used": False,
                "broker_write_performed": False,
                "order_submission_performed": False,
                "production_parameter_modified": False,
            },
        }
        payload["visualization_status"] = (
            "ISOLATED_VISUALIZATION_ERROR: " + type(exc).__name__
        )

    try:
        import importlib.util

        analytics_path = root / "dashboard" / "trade_analytics_v3_5.py"
        analytics_spec = importlib.util.spec_from_file_location(
            "ai_stock_bot_trade_analytics_v3_5", analytics_path
        )
        if analytics_spec is None or analytics_spec.loader is None:
            raise ModuleNotFoundError(f"Unable to load trade analytics module: {analytics_path}")
        analytics_module = importlib.util.module_from_spec(analytics_spec)
        analytics_spec.loader.exec_module(analytics_module)
        payload["trade_analytics"] = analytics_module.build_trade_analytics(root, payload)
        payload["trade_analytics_status"] = payload["trade_analytics"].get("status", "PASS")

        # V3.9_CANONICAL_PERFORMANCE_UNIFICATION
        analytics_historical = (
            payload["trade_analytics"].get("historical") or {}
        )
        analytics_validation = (
            payload["trade_analytics"].get("validation") or {}
        )

        payload["performance"] = {
            "validation_closed_trades": int(
                analytics_validation.get("numeric_trade_count", 0) or 0
            ),
            "historical_closed_trades": int(
                analytics_historical.get("numeric_trade_count", 0) or 0
            ),
            "historical_realized_pnl": (
                analytics_historical.get("net_realized_pnl")
            ),
            "win_rate": analytics_historical.get("win_rate"),
            "profit_factor": analytics_historical.get("profit_factor"),
            "canonical_source": True,
            "source_ledger": (
                (payload["trade_analytics"].get("source_ledgers") or [None])[0]
            ),
        }

        canonical_daily = []
        for item in payload["trade_analytics"].get("daily") or []:
            value = item.get("net_realized_pnl")
            if value is None:
                continue
            canonical_daily.append(
                {
                    "date": item.get("date"),
                    "value": value,
                }
            )

        payload.setdefault("visualization", {})
        payload["visualization"]["daily_realized_pnl"] = canonical_daily[-30:]
        payload["visualization"].setdefault("summary", {})
        payload["visualization"]["summary"]["historical_realized_pnl"] = (
            analytics_historical.get("net_realized_pnl")
        )
        payload["visualization"]["summary"]["daily_realized_point_count"] = len(
            canonical_daily
        )
        payload["visualization"]["summary"]["closed_trade_numeric_pnl_count"] = int(
            analytics_historical.get("numeric_trade_count", 0) or 0
        )
    except Exception as exc:
        payload["trade_analytics"] = {"status": "ISOLATED_ERROR", "historical": {"data_status": "INSUFFICIENT_DATA"}, "validation": {"data_status": "WAITING_FOR_VALIDATION_START"}, "by_symbol": [], "by_exit_reason": [], "daily": [], "recent_numeric_trades": [], "source_ledgers": [], "contracts": {"read_only": True, "broker_network_used": False, "broker_write_performed": False, "order_submission_performed": False, "paper_runtime_modified": False, "production_parameter_modified": False, "production_selector_modified": False, "duplicate_engine_created": False}}
        payload["trade_analytics_status"] = "ISOLATED_TRADE_ANALYTICS_ERROR: " + type(exc).__name__

    try:
        import sys
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from broker_integration_v1.integrated_status import (
            build_broker_integration_v1_status,
        )
        payload["broker_integration_v1"] = (
            build_broker_integration_v1_status(root)
        )
        payload["broker_integration_v1_status"] = (
            payload["broker_integration_v1"].get("status", "PASS")
        )
    except Exception as exc:
        payload["broker_integration_v1"] = {
            "status": "ISOLATED_ERROR",
            "development_status": "ERROR",
            "network_status": "LOCKED",
            "live_trading_status": "LOCKED",
            "contracts": {
                "duplicate_broker_contract_created": False,
                "duplicate_alpaca_market_data_stack_created": False,
                "broker_network_used": False,
                "broker_write_performed": False,
                "order_submission_performed": False,
                "live_trading_enabled": False,
            },
        }
        payload["broker_integration_v1_status"] = (
            "ISOLATED_BROKER_INTEGRATION_ERROR: "
            + type(exc).__name__
        )

    return payload


class Handler(BaseHTTPRequestHandler):
    root = ROOT_DEFAULT

    def log_message(self, fmt, *args):
        pass

    def send_body(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            template = (self.root / TEMPLATE_REL).read_text(
                encoding="utf-8"
            )
            self.send_body(
                200,
                "text/html; charset=utf-8",
                template.encode(),
            )
            return

        if path == "/api/status":
            payload = json.dumps(
                build_status(self.root),
                indent=2,
                default=str,
            ).encode()
            self.send_body(
                200,
                "application/json; charset=utf-8",
                payload,
            )
            return

        if path == "/health":
            self.send_body(
                200,
                "application/json",
                b'{"status":"PASS","read_only":true}',
            )
            return

        self.send_body(
            404,
            "application/json",
            b'{"error":"not found"}',
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT_DEFAULT))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    Handler.root = Path(args.root).resolve()
    server = ThreadingHTTPServer((args.host, args.port), Handler)

    print(f"V3.2 Unified Dashboard: http://{args.host}:{args.port}")
    print("READ_ONLY: true")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
