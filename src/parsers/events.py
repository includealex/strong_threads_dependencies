from dataclasses import dataclass
from .constants import S_TO_US

@dataclass
class SchedWakingEvent:
    time_us: int
    waker_pid: int
    waiter_pid: int
    waker_comm: str
    waiter_comm: str
    waiter_prio: int
    waker_cpu: int
    target_cpu: int

    @classmethod
    def from_match(cls, match: dict):
        return cls(
            time_us=int(float(match["time"]) * S_TO_US),
            waker_pid=int(match["waker_pid"]),
            waiter_pid=int(match["waiter_pid"]),
            waker_comm=match["waker_comm"],
            waiter_comm=match["waiter_comm"],
            waiter_prio=int(match["waiter_prio"]),
            waker_cpu=int(match["cpu"]),
            target_cpu=int(match["target_cpu"]),
        )

@dataclass
class SchedSwitchOnEvent:
    time_us: int
    next_core: int
    next_pid: int
    next_prio: int
    next_comm: str

    @classmethod
    def from_match(cls, match: dict):
        return cls(
            time_us=int(float(match["time"]) * S_TO_US),
            next_core=int(match["cpu"]),
            next_pid=int(match["next_pid"]),
            next_prio=int(match["next_prio"]),
            next_comm=match["next_comm"]
        )

@dataclass
class SchedSwitchOffEvent:
    time_us: int
    prev_core: int
    prev_pid: int
    prev_state: str
    prev_prio: int
    prev_comm: str

    @classmethod
    def from_match(cls, match: dict):
        return cls(
            time_us=int(float(match["time"]) * S_TO_US),
            prev_core=int(match["cpu"]),
            prev_pid=int(match["prev_pid"]),
            prev_state=match["prev_state"],
            prev_prio=int(match["prev_prio"]),
            prev_comm=match["prev_comm"],
        )

