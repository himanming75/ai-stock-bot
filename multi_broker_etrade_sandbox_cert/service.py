from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
from multi_broker_core.factory import BrokerFactory
from multi_broker_etrade.factory_registration import register_etrade_adapter
from multi_broker_etrade.transport import FixtureTransport
from .fixtures import ACCOUNT_ID_KEY,FIXTURES
from .validation import classify_error,validate_payloads

class ETradeSandboxReadCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        names=("ETRADE_CONSUMER_KEY","ETRADE_CONSUMER_SECRET","ETRADE_ACCESS_TOKEN","ETRADE_ACCESS_SECRET")
        present={name:bool(os.environ.get(name,"").strip()) for name in names}
        readiness={"required_environment_variables":list(names),"present":present,"ready":all(present.values()),"missing":[n for n,v in present.items() if not v],"secret_values_exposed":False}
        contracts=validate_payloads(FIXTURES)
        responses={
            "/v1/accounts/list.json":FIXTURES["ACCOUNT_LIST"],
            f"/v1/accounts/{ACCOUNT_ID_KEY}/balance.json?instType=BROKERAGE&realTimeNAV=true":FIXTURES["BALANCE"],
            f"/v1/accounts/{ACCOUNT_ID_KEY}/portfolio.json":FIXTURES["PORTFOLIO"],
            f"/v1/accounts/{ACCOUNT_ID_KEY}/orders.json":FIXTURES["ORDERS"],
        }
        transport=FixtureTransport(responses)
        adapter=register_etrade_adapter(BrokerFactory()).create("ETRADE",transport=transport,account_id_key=ACCOUNT_ID_KEY)
        account=adapter.get_account(); positions=adapter.list_positions(); orders=adapter.list_orders()
        passed=all(x["payload_present"] and x["top_level_contract_passed"] and x["method"]=="GET" and not x["mutation_allowed"] for x in contracts)
        actual_status="READY_FOR_EXPLICIT_SANDBOX_READ" if readiness["ready"] else "READY_BLOCKED_BY_ETRADE_KEY_ISSUANCE"
        result={
            "stage":"V3801_TO_V4000_ETRADE_SANDBOX_ACCOUNT_READ_CERTIFICATION","status":"PASS" if passed else "BLOCKED",
            "generated_at":datetime.now(timezone.utc).isoformat(),"validation_mode":"FIXTURE_AND_CONTRACT",
            "actual_sandbox_validation_status":actual_status,"credential_readiness":readiness,
            "endpoint_contracts":contracts,"fixture_contract_passed":passed,
            "fixture_account":account.to_dict(),"fixture_positions":[x.to_dict() for x in positions],
            "fixture_orders":[x.to_dict() for x in orders],"requested_paths":transport.paths_requested,
            "error_classification_examples":{
                "401 OAuth token invalid":classify_error("401 OAuth token invalid"),
                "403 account restriction":classify_error("403 account restriction"),
                "503 unavailable":classify_error("503 unavailable"),
                "network timeout":classify_error("network timeout"),
            },
            "retry_policy":{
                "ETRADE_SERVER_ERROR":{"retry":True,"max_attempts":3,"backoff_seconds":[5,15,45]},
                "NETWORK_OR_TIMEOUT":{"retry":True,"max_attempts":3,"backoff_seconds":[5,15,45]},
                "RATE_LIMIT":{"retry":True,"max_attempts":2,"backoff_seconds":[60,180]},
                "AUTHENTICATION_OR_TOKEN":{"retry":False,"action":"RENEW_OR_REAUTHORIZE"},
                "AUTHORIZATION_OR_ACCOUNT_RESTRICTION":{"retry":False,"action":"CONTACT_ETRADE_SUPPORT"},
            },
            "key_issuance_blocker":{"active":not readiness["ready"],"owner":"ETRADE_OR_ACCOUNT_OPERATOR","blocks_code_development":False,"blocks_actual_sandbox_read":not readiness["ready"]},
            "explicit_actual_validation_runner_included":True,"automatic_actual_validation_enabled":False,
            "actual_external_network_used":False,"actual_broker_read_performed":False,
            "actual_broker_write_performed":False,"actual_order_submission_performed":False,
            "actual_paper_orders_submitted":0,"actual_live_orders_submitted":0,
            "existing_alpaca_controller_modified":False,"existing_market_polling_modified":False,
            "next_fixed_development":"V4001_TO_V4200_ETRADE_PRODUCTION_READ_ONLY_GUARD_AND_ACCOUNT_ROUTING",
            "deferred_external_validation":"RERUN_EXPLICIT_SANDBOX_CERTIFICATION_AFTER_KEY_ISSUANCE",
        }
        seed=dict(result); seed.pop("generated_at")
        result["certification_fingerprint"]=hashlib.sha256(json.dumps(seed,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        output_dir.mkdir(parents=True,exist_ok=True)
        outputs={
            "etrade_sandbox_read_certification.json":result,
            "etrade_endpoint_contract_report.json":{"contracts":contracts,"passed":passed},
            "etrade_key_issuance_blocker.json":result["key_issuance_blocker"],
            "etrade_actual_validation_readiness.json":{"status":actual_status,"credential_readiness":readiness,"explicit_runner_included":True},
            "etrade_error_retry_policy.json":{"classification_examples":result["error_classification_examples"],"retry_policy":result["retry_policy"]},
        }
        for name,payload in outputs.items():
            (output_dir/name).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        with (output_dir/"etrade_sandbox_certification_ledger.jsonl").open("a",encoding="utf-8") as h:
            h.write(json.dumps(result,sort_keys=True)+"\n")
        return result
