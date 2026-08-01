from __future__ import annotations

from enum import Enum


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    SUBSCRIBING = "SUBSCRIBING"
    STREAMING = "STREAMING"
    BACKING_OFF = "BACKING_OFF"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class ConnectionStateMachine:
    _allowed = {
        ConnectionState.DISCONNECTED: {ConnectionState.CONNECTING, ConnectionState.STOPPED},
        ConnectionState.CONNECTING: {ConnectionState.AUTHENTICATING, ConnectionState.BACKING_OFF, ConnectionState.FAILED},
        ConnectionState.AUTHENTICATING: {ConnectionState.SUBSCRIBING, ConnectionState.BACKING_OFF, ConnectionState.FAILED},
        ConnectionState.SUBSCRIBING: {ConnectionState.STREAMING, ConnectionState.BACKING_OFF, ConnectionState.FAILED},
        ConnectionState.STREAMING: {ConnectionState.BACKING_OFF, ConnectionState.STOPPED, ConnectionState.FAILED},
        ConnectionState.BACKING_OFF: {ConnectionState.CONNECTING, ConnectionState.STOPPED, ConnectionState.FAILED},
        ConnectionState.STOPPED: set(),
        ConnectionState.FAILED: {ConnectionState.BACKING_OFF, ConnectionState.STOPPED},
    }

    def __init__(self):
        self.state = ConnectionState.DISCONNECTED
        self.history = [self.state]

    def transition(self, target: ConnectionState) -> ConnectionState:
        if target not in self._allowed[self.state]:
            raise RuntimeError(f"invalid transition: {self.state.value} -> {target.value}")
        self.state = target
        self.history.append(target)
        return target
