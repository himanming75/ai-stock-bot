from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

class RecoveryAuditCertificateError(ValueError):
    pass

def canonical_json(value: Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_json(value: Any)->str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class RecoveryAuditCertificate:
    schema_version: str
    certificate_id: str
    status: str
    chain_start_version: str
    chain_end_version: str
    stage_count: int
    stages: tuple[MappingProxyType,...]
    safety_policy: MappingProxyType
    state_continuity: MappingProxyType
    certificate_sha256: str
    def unsigned_payload(self)->dict[str,Any]:
        return {"schema_version":self.schema_version,"certificate_id":self.certificate_id,
        "status":self.status,"chain_start_version":self.chain_start_version,
        "chain_end_version":self.chain_end_version,"stage_count":self.stage_count,
        "stages":[dict(x) for x in self.stages],"safety_policy":dict(self.safety_policy),
        "state_continuity":dict(self.state_continuity)}
    def as_dict(self)->dict[str,Any]:
        x=self.unsigned_payload();x["certificate_sha256"]=self.certificate_sha256;return x

class RecoveryAuditCertificateBuilder:
    SCHEMA="v77.10.recovery_audit_certificate.1"
    def build(self,*,certificate_id:str,stages:list[dict[str,Any]],
              safety_policy:dict[str,Any],state_continuity:dict[str,Any]):
        if not certificate_id.strip():raise RecoveryAuditCertificateError("certificate_id required")
        if len(stages)!=5:raise RecoveryAuditCertificateError("exactly five stages required")
        required=("V77.5","V77.6","V77.7","V77.8","V77.9")
        if tuple(x.get("version") for x in stages)!=required:
            raise RecoveryAuditCertificateError("stage order invalid")
        if not all(x.get("status")=="PASS" for x in stages):
            raise RecoveryAuditCertificateError("all stages must pass")
        if not all(safety_policy.values()):
            raise RecoveryAuditCertificateError("safety policy failed")
        if not all(state_continuity.values()):
            raise RecoveryAuditCertificateError("state continuity failed")
        unsigned={"schema_version":self.SCHEMA,"certificate_id":certificate_id.strip(),
        "status":"PASS","chain_start_version":"V77.5","chain_end_version":"V77.9",
        "stage_count":len(stages),"stages":stages,"safety_policy":safety_policy,
        "state_continuity":state_continuity}
        return RecoveryAuditCertificate(self.SCHEMA,certificate_id.strip(),"PASS","V77.5","V77.9",
        len(stages),tuple(MappingProxyType(dict(x)) for x in stages),
        MappingProxyType(dict(safety_policy)),MappingProxyType(dict(state_continuity)),
        sha256_json(unsigned))
    def verify(self,cert:RecoveryAuditCertificate)->bool:
        return cert.status=="PASS" and cert.stage_count==5 and cert.certificate_sha256==sha256_json(cert.unsigned_payload())
