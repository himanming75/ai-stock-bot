"""V24.4 offline-only audit trust-chain verification.

This module consumes immutable V24.3 audit-chain results and establishes a
rooted trust lineage entirely offline. It never imports or calls market-data,
account, network, broker, order-submission, or live-execution APIs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional, Tuple

from backtest.offline_paper_audit_cert_ledger_integrity_v24_1 import sha256_payload
from backtest.offline_audit_chain_v24_3 import (
    AuditChainV243Result,
    verify_chain_certificate,
    verify_chain_links,
)

VERSION = "V24.4"
SOURCE_VERSION = "V24.3"
REQUIRED_CONFIRMATION = "BUILD OFFLINE AUDIT TRUST CHAIN V24.4"
ROOT_PARENT_ID = "ROOT"


@dataclass(frozen=True)
class AuditTrustV244Policy:
    source_version: str = SOURCE_VERSION
    required_source_status: str = "AUDIT_CHAIN_VERIFIED"
    required_confirmation: str = REQUIRED_CONFIRMATION
    minimum_source_count: int = 1
    maximum_chain_depth: int = 1024
    require_unique_source_ids: bool = True
    require_root_anchor: bool = True
    require_acyclic_lineage: bool = True
    require_immutable_history: bool = True
    require_source_safety: bool = True
    allow_market_data_api: bool = False
    allow_account_api: bool = False
    allow_network: bool = False
    allow_broker_api: bool = False
    allow_order_submission: bool = False
    allow_live_execution: bool = False


@dataclass(frozen=True)
class TrustFindingV244:
    sequence: int
    check_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class RootTrustAnchorV244:
    anchor_id: str
    issued_at: str
    operator: str
    source_count: int
    source_ids_hash: str
    policy_hash: str
    execution_blocked: bool
    anchor_hash: str


@dataclass(frozen=True)
class TrustNodeV244:
    depth: int
    node_id: str
    parent_id: str
    source_chain_result_id: str
    source_created_at: str
    source_final_chain_hash: str
    source_certificate_hash: str
    source_result_hash: str
    node_hash: str


@dataclass(frozen=True)
class TrustCertificateV244:
    certificate_id: str
    issued_at: str
    certificate_status: str
    root_anchor_id: str
    root_anchor_hash: str
    source_count: int
    maximum_depth: int
    final_trust_hash: str
    immutable_history_hash: str
    findings_hash: str
    trust_score: int
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    certificate_hash: str


@dataclass(frozen=True)
class AuditTrustV244Result:
    version: str
    created_at: str
    trust_result_id: str
    result_status: str
    source_contracts_verified: bool
    source_certificates_verified: bool
    source_chain_links_verified: bool
    unique_sources_verified: bool
    root_anchor_verified: bool
    lineage_verified: bool
    cycle_free_verified: bool
    chain_depth_verified: bool
    immutable_history_verified: bool
    safety_verified: bool
    sources_remained_unchanged: bool
    trust_score: int
    certificate_created: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    policy: AuditTrustV244Policy
    root_anchor: RootTrustAnchorV244
    nodes: Tuple[TrustNodeV244, ...]
    findings: Tuple[TrustFindingV244, ...]
    certificate: Optional[TrustCertificateV244]
    reasons: Tuple[str, ...]
    source_path: str = ""
    result_path: str = ""


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    parsed = parsed.astimezone(timezone.utc)
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must resolve to UTC")
    return parsed


def validate_policy(policy: AuditTrustV244Policy) -> None:
    if not isinstance(policy, AuditTrustV244Policy):
        raise TypeError("policy must be AuditTrustV244Policy")
    if policy != AuditTrustV244Policy():
        raise ValueError("V24.4 policy is immutable and must use safe defaults")


def _source_hash(source: AuditChainV243Result) -> str:
    payload = asdict(source)
    payload.pop("source_path", None)
    payload.pop("result_path", None)
    return sha256_payload(payload)


def _anchor_payload(anchor: RootTrustAnchorV244) -> dict:
    payload = asdict(anchor)
    payload.pop("anchor_hash", None)
    return payload


def verify_root_anchor(anchor: RootTrustAnchorV244) -> bool:
    return isinstance(anchor, RootTrustAnchorV244) and anchor.anchor_hash == sha256_payload(_anchor_payload(anchor))


def _node_payload(node: TrustNodeV244) -> dict:
    payload = asdict(node)
    payload.pop("node_hash", None)
    return payload


def verify_trust_node(node: TrustNodeV244) -> bool:
    return isinstance(node, TrustNodeV244) and node.node_hash == sha256_payload(_node_payload(node))


def verify_trust_lineage(anchor: RootTrustAnchorV244, nodes: Tuple[TrustNodeV244, ...]) -> bool:
    if not verify_root_anchor(anchor) or not nodes:
        return False
    seen_ids = set()
    expected_parent = anchor.anchor_id
    for expected_depth, node in enumerate(nodes, start=1):
        if node.depth != expected_depth or node.parent_id != expected_parent:
            return False
        if node.node_id in seen_ids or node.node_id == node.parent_id:
            return False
        if not verify_trust_node(node):
            return False
        seen_ids.add(node.node_id)
        expected_parent = node.node_id
    return True


def detect_trust_cycle(anchor: RootTrustAnchorV244, nodes: Tuple[TrustNodeV244, ...]) -> bool:
    parent_by_id = {node.node_id: node.parent_id for node in nodes}
    parent_by_id[anchor.anchor_id] = ROOT_PARENT_ID
    for start in parent_by_id:
        seen = set()
        current = start
        while current in parent_by_id and current != ROOT_PARENT_ID:
            if current in seen:
                return True
            seen.add(current)
            current = parent_by_id[current]
    return False


def _history_hash(anchor: RootTrustAnchorV244, nodes: Tuple[TrustNodeV244, ...]) -> str:
    return sha256_payload({"root_anchor_hash": anchor.anchor_hash, "node_hashes": [n.node_hash for n in nodes]})


def _findings_hash(findings: Tuple[TrustFindingV244, ...]) -> str:
    return sha256_payload({"findings": [asdict(item) for item in findings]})


def _certificate_payload(certificate: TrustCertificateV244) -> dict:
    payload = asdict(certificate)
    payload.pop("certificate_hash", None)
    return payload


def verify_trust_certificate(certificate: TrustCertificateV244) -> bool:
    return isinstance(certificate, TrustCertificateV244) and certificate.certificate_hash == sha256_payload(_certificate_payload(certificate))


def build_offline_audit_trust_v24_4(
    sources: Tuple[AuditChainV243Result, ...],
    *,
    operator: str,
    confirmation: str,
    trust_time: str,
    policy: AuditTrustV244Policy = AuditTrustV244Policy(),
    source_path: str = "",
) -> AuditTrustV244Result:
    """Build a rooted, immutable offline trust lineage from V24.3 results."""
    validate_policy(policy)
    if not isinstance(sources, tuple):
        raise TypeError("sources must be a tuple of V24.3 results")
    if len(sources) < policy.minimum_source_count:
        raise ValueError("at least one V24.3 source result is required")
    if not all(isinstance(item, AuditChainV243Result) for item in sources):
        raise TypeError("every source must be a V24.3 audit-chain result")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("operator must be a non-empty string")
    operator = operator.strip()
    if confirmation != policy.required_confirmation:
        raise PermissionError("exact V24.4 confirmation is required")

    created_at = _parse_utc(trust_time)
    source_times = tuple(_parse_utc(item.created_at) for item in sources)
    if created_at < max(source_times):
        raise ValueError("trust time cannot be before a source creation time")

    before_hashes = tuple(_source_hash(item) for item in sources)
    source_ids = tuple(item.chain_result_id for item in sources)

    source_contracts_verified = all(
        item.version == policy.source_version
        and item.result_status == policy.required_source_status
        and item.certificate_created
        and item.sources_remained_unchanged
        and item.certificate is not None
        for item in sources
    )
    source_certificates_verified = all(item.certificate is not None and verify_chain_certificate(item.certificate) for item in sources)
    source_chain_links_verified = all(verify_chain_links(item.entries) for item in sources)
    unique_sources_verified = len(source_ids) == len(set(source_ids))

    unsigned_anchor = RootTrustAnchorV244(
        anchor_id=sha256_payload({"version": VERSION, "issued_at": created_at.isoformat(), "operator": operator, "source_ids": source_ids}),
        issued_at=created_at.isoformat(),
        operator=operator,
        source_count=len(sources),
        source_ids_hash=sha256_payload({"source_ids": source_ids}),
        policy_hash=sha256_payload(asdict(policy)),
        execution_blocked=True,
        anchor_hash="",
    )
    root_anchor = replace(unsigned_anchor, anchor_hash=sha256_payload(_anchor_payload(unsigned_anchor)))
    root_anchor_verified = verify_root_anchor(root_anchor)

    nodes_list = []
    parent_id = root_anchor.anchor_id
    for depth, (source, source_hash) in enumerate(zip(sources, before_hashes), start=1):
        source_cert_hash = source.certificate.certificate_hash if source.certificate else ""
        final_chain_hash = source.certificate.final_chain_hash if source.certificate else ""
        node_id = sha256_payload({"depth": depth, "parent_id": parent_id, "source_chain_result_id": source.chain_result_id, "source_result_hash": source_hash})
        unsigned_node = TrustNodeV244(
            depth=depth,
            node_id=node_id,
            parent_id=parent_id,
            source_chain_result_id=source.chain_result_id,
            source_created_at=source.created_at,
            source_final_chain_hash=final_chain_hash,
            source_certificate_hash=source_cert_hash,
            source_result_hash=source_hash,
            node_hash="",
        )
        node = replace(unsigned_node, node_hash=sha256_payload(_node_payload(unsigned_node)))
        nodes_list.append(node)
        parent_id = node.node_id
    nodes = tuple(nodes_list)

    lineage_verified = verify_trust_lineage(root_anchor, nodes)
    cycle_free_verified = not detect_trust_cycle(root_anchor, nodes)
    chain_depth_verified = len(nodes) <= policy.maximum_chain_depth and all(node.depth <= policy.maximum_chain_depth for node in nodes)
    history_before = _history_hash(root_anchor, nodes)
    immutable_history_verified = history_before == _history_hash(root_anchor, nodes)

    safety_verified = all(
        not item.market_data_api_called and not item.account_api_called and not item.network_accessed
        and not item.broker_api_called and not item.broker_order_created and not item.order_submitted
        and not item.live_execution_authorized and item.execution_blocked
        and not item.funds_reserved and not item.holdings_reserved
        and item.certificate is not None and item.certificate.execution_blocked
        and not item.certificate.funds_reserved and not item.certificate.holdings_reserved
        for item in sources
    )
    after_hashes = tuple(_source_hash(item) for item in sources)
    sources_remained_unchanged = before_hashes == after_hashes

    checks = (
        ("source_contracts", source_contracts_verified, "V24.3 source contracts"),
        ("source_certificates", source_certificates_verified, "V24.3 certificate hashes"),
        ("source_chain_links", source_chain_links_verified, "V24.3 chain linkage"),
        ("unique_sources", unique_sources_verified, "duplicate/replay prevention"),
        ("root_anchor", root_anchor_verified, "root trust anchor"),
        ("trust_lineage", lineage_verified, "parent-child trust lineage"),
        ("cycle_free", cycle_free_verified, "cycle-free lineage"),
        ("chain_depth", chain_depth_verified, "maximum chain depth"),
        ("immutable_history", immutable_history_verified, "immutable trust history"),
        ("source_safety", safety_verified, "offline execution safety"),
        ("source_immutability", sources_remained_unchanged, "sources unchanged"),
    )
    findings = tuple(TrustFindingV244(i, name, passed, detail) for i, (name, passed, detail) in enumerate(checks, start=1))
    reasons = tuple(detail for _, passed, detail in checks if not passed)
    passed_count = sum(1 for item in findings if item.passed)
    trust_score = int(round((passed_count / len(findings)) * 100))
    all_passed = all(item.passed for item in findings)
    result_status = "AUDIT_TRUST_VERIFIED" if all_passed else "AUDIT_TRUST_FAILED"
    immutable_history_hash = _history_hash(root_anchor, nodes)
    trust_result_id = sha256_payload({"version": VERSION, "created_at": created_at.isoformat(), "root_anchor_hash": root_anchor.anchor_hash, "immutable_history_hash": immutable_history_hash, "findings_hash": _findings_hash(findings), "result_status": result_status})

    output_certificate = None
    if all_passed:
        unsigned_certificate = TrustCertificateV244(
            certificate_id=trust_result_id,
            issued_at=created_at.isoformat(),
            certificate_status=result_status,
            root_anchor_id=root_anchor.anchor_id,
            root_anchor_hash=root_anchor.anchor_hash,
            source_count=len(sources),
            maximum_depth=len(nodes),
            final_trust_hash=nodes[-1].node_hash,
            immutable_history_hash=immutable_history_hash,
            findings_hash=_findings_hash(findings),
            trust_score=trust_score,
            operator=operator,
            execution_blocked=True,
            funds_reserved=False,
            holdings_reserved=False,
            certificate_hash="",
        )
        output_certificate = replace(unsigned_certificate, certificate_hash=sha256_payload(_certificate_payload(unsigned_certificate)))

    return AuditTrustV244Result(
        version=VERSION, created_at=created_at.isoformat(), trust_result_id=trust_result_id,
        result_status=result_status, source_contracts_verified=source_contracts_verified,
        source_certificates_verified=source_certificates_verified,
        source_chain_links_verified=source_chain_links_verified,
        unique_sources_verified=unique_sources_verified, root_anchor_verified=root_anchor_verified,
        lineage_verified=lineage_verified, cycle_free_verified=cycle_free_verified,
        chain_depth_verified=chain_depth_verified,
        immutable_history_verified=immutable_history_verified, safety_verified=safety_verified,
        sources_remained_unchanged=sources_remained_unchanged, trust_score=trust_score,
        certificate_created=output_certificate is not None,
        market_data_api_called=False, account_api_called=False, network_accessed=False,
        broker_api_called=False, broker_order_created=False, order_submitted=False,
        live_execution_authorized=False, execution_blocked=True,
        funds_reserved=False, holdings_reserved=False, policy=policy,
        root_anchor=root_anchor, nodes=nodes, findings=findings,
        certificate=output_certificate, reasons=reasons, source_path=str(source_path),
    )


def save_trust_result(result: AuditTrustV244Result, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def load_trust_result(path: str | Path) -> AuditTrustV244Result:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload["policy"] = AuditTrustV244Policy(**payload["policy"])
    payload["root_anchor"] = RootTrustAnchorV244(**payload["root_anchor"])
    payload["nodes"] = tuple(TrustNodeV244(**item) for item in payload["nodes"])
    payload["findings"] = tuple(TrustFindingV244(**item) for item in payload["findings"])
    if payload["certificate"] is not None:
        payload["certificate"] = TrustCertificateV244(**payload["certificate"])
    payload["reasons"] = tuple(payload["reasons"])
    return AuditTrustV244Result(**payload)


__all__ = [
    "VERSION", "SOURCE_VERSION", "REQUIRED_CONFIRMATION", "ROOT_PARENT_ID",
    "AuditTrustV244Policy", "TrustFindingV244", "RootTrustAnchorV244",
    "TrustNodeV244", "TrustCertificateV244", "AuditTrustV244Result",
    "validate_policy", "verify_root_anchor", "verify_trust_node",
    "verify_trust_lineage", "detect_trust_cycle", "verify_trust_certificate",
    "build_offline_audit_trust_v24_4", "save_trust_result", "load_trust_result",
]
