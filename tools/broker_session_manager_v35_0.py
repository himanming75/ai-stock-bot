#!/usr/bin/env python3
"""
V35.0 Broker Session Manager Foundation

Implements a broker-session state machine without network access.

Features:
- DISCONNECTED / CONNECTING / READY / DEGRADED / EXPIRED / CLOSED states
- Paper and live session separation
- Read-only health checks
- Heartbeat recording and timeout detection
- Deterministic reconnect policy with exponential backoff
- Session audit log with SHA-256 event fingerprints
- External broker sessions remain transport-disabled
- No credential use, login, socket, HTTP, or broker API calls

This module models session behavior only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Sequence


VERSION = "35.0"


class BrokerName(str, Enum):
    PAPER = "paper"
    IBKR = "ibkr"
    ALPACA = "alpaca"
    TRADESTATION = "tradestation"


class SessionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class SessionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    DEGRADED = "degraded"
    EXPIRED = "expired"
    CLOSED = "closed"


@dataclass(frozen=True)
class ReconnectPolicy:
    enabled: bool = True
    max_attempts: int = 5
    base_delay_seconds: int = 2
    max_delay_seconds: int = 60

    def delay_for_attempt(self, attempt: int) -> int:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        delay = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


@dataclass(frozen=True)
class SessionEvent:
    event_id: str
    generated_at: str
    broker: str
    mode: str
    previous_state: str
    new_state: str
    event_type: str
    message: str
    network_used: bool
    event_sha256: str


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str
    broker: str
    mode: str
    state: str
    network_transport_enabled: bool
    authenticated: bool
    connected: bool
    heartbeat_timeout_seconds: int
    last_heartbeat_at: str | None
    reconnect_attempts: int
    next_reconnect_delay_seconds: int | None
    audit_event_count: int
    generated_at: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class BrokerSession:
    def __init__(
        self,
        broker: BrokerName,
        mode: SessionMode,
        *,
        heartbeat_timeout_seconds: int = 30,
        reconnect_policy: ReconnectPolicy | None = None,
    ) -> None:
        if heartbeat_timeout_seconds < 1:
            raise ValueError("heartbeat_timeout_seconds must be >= 1")
        if broker == BrokerName.PAPER and mode != SessionMode.PAPER:
            raise ValueError("paper broker only supports paper mode")

        self.session_id = f"session-{uuid.uuid4().hex}"
        self.broker = broker
        self.mode = mode
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.reconnect_policy = reconnect_policy or ReconnectPolicy()
        self.state = SessionState.DISCONNECTED
        self.last_heartbeat_at: datetime | None = None
        self.reconnect_attempts = 0
        self._events: list[SessionEvent] = []

    @property
    def network_transport_enabled(self) -> bool:
        return False

    @property
    def authenticated(self) -> bool:
        return self.broker == BrokerName.PAPER and self.state == SessionState.READY

    @property
    def connected(self) -> bool:
        return self.state in {SessionState.READY, SessionState.DEGRADED}

    def _record(
        self,
        event_type: str,
        previous: SessionState,
        new: SessionState,
        message: str,
        now: datetime,
    ) -> SessionEvent:
        core = {
            "event_id": f"evt-{uuid.uuid4().hex}",
            "generated_at": iso(now),
            "broker": self.broker.value,
            "mode": self.mode.value,
            "previous_state": previous.value,
            "new_state": new.value,
            "event_type": event_type,
            "message": message,
            "network_used": False,
        }
        event = SessionEvent(
            **core,
            event_sha256=canonical_hash(core),
        )
        self._events.append(event)
        return event

    def start(self, now: datetime | None = None) -> SessionEvent:
        now = now or utc_now()
        if self.state == SessionState.CLOSED:
            raise RuntimeError("closed sessions cannot be restarted")

        previous = self.state
        self.state = SessionState.CONNECTING
        self._record(
            "start",
            previous,
            self.state,
            "Session entered connecting state.",
            now,
        )

        previous = self.state
        if self.broker == BrokerName.PAPER:
            self.state = SessionState.READY
            self.last_heartbeat_at = now
            self.reconnect_attempts = 0
            return self._record(
                "paper_ready",
                previous,
                self.state,
                "In-memory paper session is ready.",
                now,
            )

        self.state = SessionState.DISCONNECTED
        return self._record(
            "transport_disabled",
            previous,
            self.state,
            f"{self.broker.value} network transport is disabled in V35.0.",
            now,
        )

    def heartbeat(self, now: datetime | None = None) -> SessionEvent:
        now = now or utc_now()
        if self.state in {SessionState.CLOSED, SessionState.EXPIRED}:
            raise RuntimeError(f"heartbeat not allowed in {self.state.value} state")
        if self.broker != BrokerName.PAPER:
            previous = self.state
            return self._record(
                "heartbeat_rejected",
                previous,
                previous,
                "External broker heartbeat rejected because transport is disabled.",
                now,
            )

        previous = self.state
        self.state = SessionState.READY
        self.last_heartbeat_at = now
        self.reconnect_attempts = 0
        return self._record(
            "heartbeat",
            previous,
            self.state,
            "Paper session heartbeat recorded.",
            now,
        )

    def evaluate_timeout(self, now: datetime | None = None) -> SessionEvent | None:
        now = now or utc_now()
        if self.state not in {SessionState.READY, SessionState.DEGRADED}:
            return None
        if self.last_heartbeat_at is None:
            return None

        elapsed = (now - self.last_heartbeat_at).total_seconds()
        if elapsed <= self.heartbeat_timeout_seconds:
            return None

        previous = self.state
        self.state = SessionState.EXPIRED
        return self._record(
            "timeout",
            previous,
            self.state,
            f"Heartbeat expired after {int(elapsed)} seconds.",
            now,
        )

    def mark_degraded(
        self,
        message: str = "Session marked degraded.",
        now: datetime | None = None,
    ) -> SessionEvent:
        now = now or utc_now()
        if self.state != SessionState.READY:
            raise RuntimeError("only ready sessions can become degraded")
        previous = self.state
        self.state = SessionState.DEGRADED
        return self._record(
            "degraded",
            previous,
            self.state,
            message,
            now,
        )

    def request_reconnect(self, now: datetime | None = None) -> SessionEvent:
        now = now or utc_now()
        if self.state == SessionState.CLOSED:
            raise RuntimeError("closed sessions cannot reconnect")
        if not self.reconnect_policy.enabled:
            previous = self.state
            return self._record(
                "reconnect_disabled",
                previous,
                previous,
                "Reconnect policy is disabled.",
                now,
            )
        if self.reconnect_attempts >= self.reconnect_policy.max_attempts:
            previous = self.state
            self.state = SessionState.EXPIRED
            return self._record(
                "reconnect_exhausted",
                previous,
                self.state,
                "Maximum reconnect attempts were exhausted.",
                now,
            )

        self.reconnect_attempts += 1
        delay = self.reconnect_policy.delay_for_attempt(self.reconnect_attempts)
        previous = self.state
        self.state = SessionState.CONNECTING
        self._record(
            "reconnect_scheduled",
            previous,
            self.state,
            f"Reconnect attempt {self.reconnect_attempts} scheduled after {delay} seconds.",
            now,
        )

        previous = self.state
        if self.broker == BrokerName.PAPER:
            self.state = SessionState.READY
            self.last_heartbeat_at = now
            return self._record(
                "reconnect_success",
                previous,
                self.state,
                "Paper session reconnect simulation succeeded.",
                now,
            )

        self.state = SessionState.DISCONNECTED
        return self._record(
            "reconnect_blocked",
            previous,
            self.state,
            "External broker reconnect blocked because transport is disabled.",
            now,
        )

    def close(self, now: datetime | None = None) -> SessionEvent:
        now = now or utc_now()
        previous = self.state
        self.state = SessionState.CLOSED
        return self._record(
            "close",
            previous,
            self.state,
            "Session closed.",
            now,
        )

    def next_reconnect_delay(self) -> int | None:
        if not self.reconnect_policy.enabled:
            return None
        next_attempt = self.reconnect_attempts + 1
        if next_attempt > self.reconnect_policy.max_attempts:
            return None
        return self.reconnect_policy.delay_for_attempt(next_attempt)

    def snapshot(self, now: datetime | None = None) -> SessionSnapshot:
        now = now or utc_now()
        return SessionSnapshot(
            session_id=self.session_id,
            broker=self.broker.value,
            mode=self.mode.value,
            state=self.state.value,
            network_transport_enabled=False,
            authenticated=self.authenticated,
            connected=self.connected,
            heartbeat_timeout_seconds=self.heartbeat_timeout_seconds,
            last_heartbeat_at=(
                iso(self.last_heartbeat_at)
                if self.last_heartbeat_at
                else None
            ),
            reconnect_attempts=self.reconnect_attempts,
            next_reconnect_delay_seconds=self.next_reconnect_delay(),
            audit_event_count=len(self._events),
            generated_at=iso(now),
        )

    def audit_log(self) -> list[SessionEvent]:
        return list(self._events)


class BrokerSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, BrokerSession] = {}

    def create_session(
        self,
        broker: BrokerName,
        mode: SessionMode,
        **kwargs: Any,
    ) -> BrokerSession:
        session = BrokerSession(broker, mode, **kwargs)
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> BrokerSession:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session: {session_id}")
        return self._sessions[session_id]

    def dashboard(self) -> dict[str, Any]:
        snapshots = [
            asdict(session.snapshot())
            for session in self._sessions.values()
        ]
        ready = sum(item["state"] == SessionState.READY.value for item in snapshots)
        return {
            "schema_version": "v35.0.session_dashboard.1",
            "version": VERSION,
            "status": "PASS",
            "session_count": len(snapshots),
            "ready_session_count": ready,
            "network_transport_enabled": False,
            "sessions": snapshots,
            "generated_at": iso(utc_now()),
        }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V35.0 Broker Session Manager Foundation"
    )
    p.add_argument(
        "--broker",
        choices=[item.value for item in BrokerName],
        default="paper",
    )
    p.add_argument(
        "--mode",
        choices=[item.value for item in SessionMode],
        default="paper",
    )
    p.add_argument(
        "--action",
        choices=["start", "heartbeat", "timeout", "reconnect", "dashboard"],
        default="start",
    )
    p.add_argument("--timeout-seconds", type=int, default=30)
    p.add_argument(
        "--output",
        default="release/v35/audit/broker_session_result_v35_0.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    manager = BrokerSessionManager()

    if args.action == "dashboard":
        paper = manager.create_session(
            BrokerName.PAPER,
            SessionMode.PAPER,
            heartbeat_timeout_seconds=args.timeout_seconds,
        )
        paper.start()
        for broker in (
            BrokerName.IBKR,
            BrokerName.ALPACA,
            BrokerName.TRADESTATION,
        ):
            session = manager.create_session(
                broker,
                SessionMode.LIVE,
                heartbeat_timeout_seconds=args.timeout_seconds,
            )
            session.start()
        payload: Any = manager.dashboard()
        success = True
    else:
        session = manager.create_session(
            BrokerName(args.broker),
            SessionMode(args.mode),
            heartbeat_timeout_seconds=args.timeout_seconds,
        )
        session.start()

        if args.action == "heartbeat":
            session.heartbeat()
        elif args.action == "timeout":
            future = utc_now() + timedelta(
                seconds=args.timeout_seconds + 1
            )
            session.evaluate_timeout(future)
        elif args.action == "reconnect":
            session.request_reconnect()

        payload = {
            "snapshot": asdict(session.snapshot()),
            "audit_log": [asdict(event) for event in session.audit_log()],
        }
        success = True

    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
