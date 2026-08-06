from __future__ import annotations
from collections import defaultdict
from decimal import Decimal

from .models import AIVote, VotingDecision


D = Decimal


VALID_ACTIONS = {"BUY", "SELL", "WAIT"}


def normalize_action(action: str) -> str:
    value = str(action or "WAIT").upper()
    return value if value in VALID_ACTIONS else "WAIT"


def aggregate_votes(
    votes: list[AIVote],
    *,
    minimum_consensus: Decimal = D("0.55"),
) -> VotingDecision:
    if not votes:
        return VotingDecision(
            final_action="WAIT",
            weighted_scores={
                "BUY": D("0"),
                "SELL": D("0"),
                "WAIT": D("0"),
            },
            winning_score=D("0"),
            consensus_ratio=D("0"),
            veto_applied=False,
            reason="NO_VOTES",
        )

    if any(vote.veto for vote in votes):
        return VotingDecision(
            final_action="WAIT",
            weighted_scores={
                "BUY": D("0"),
                "SELL": D("0"),
                "WAIT": D("1"),
            },
            winning_score=D("1"),
            consensus_ratio=D("1"),
            veto_applied=True,
            reason="SAFETY_VETO_APPLIED",
        )

    scores: dict[str, Decimal] = defaultdict(
        lambda: D("0")
    )
    total_weight = D("0")

    for vote in votes:
        action = normalize_action(vote.action)
        contribution = vote.weight * vote.confidence
        scores[action] += contribution
        total_weight += vote.weight

    for action in VALID_ACTIONS:
        scores[action] += D("0")

    winner = sorted(
        scores.items(),
        key=lambda item: (-item[1], item[0]),
    )[0]
    winning_action, winning_score = winner

    denominator = sum(scores.values(), D("0"))
    consensus = (
        winning_score / denominator
        if denominator > 0
        else D("0")
    )

    if consensus < minimum_consensus:
        return VotingDecision(
            final_action="WAIT",
            weighted_scores=dict(scores),
            winning_score=winning_score,
            consensus_ratio=consensus,
            veto_applied=False,
            reason="CONSENSUS_BELOW_THRESHOLD",
        )

    return VotingDecision(
        final_action=winning_action,
        weighted_scores=dict(scores),
        winning_score=winning_score,
        consensus_ratio=consensus,
        veto_applied=False,
        reason="WEIGHTED_CONSENSUS",
    )
