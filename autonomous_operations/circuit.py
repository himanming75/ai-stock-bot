from __future__ import annotations


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_success_threshold: int = 2,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_success_threshold = recovery_success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> str:
        self.failure_count += 1
        self.success_count = 0
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
        return self.state

    def record_success(self) -> str:
        if self.state == "OPEN":
            self.state = "HALF_OPEN"
            self.success_count = 1
            return self.state

        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.recovery_success_threshold:
                self.state = "CLOSED"
                self.failure_count = 0
                self.success_count = 0
            return self.state

        self.failure_count = 0
        self.success_count = 0
        self.state = "CLOSED"
        return self.state

    def allow_request(self) -> bool:
        return self.state in {"CLOSED", "HALF_OPEN"}

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_success_threshold": (
                self.recovery_success_threshold
            ),
            "allow_request": self.allow_request(),
        }
