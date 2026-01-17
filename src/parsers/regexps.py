import re

from functools import lru_cache

TS_PATTERN = re.compile(
    r"\[\d+\].*?"
    r"(?P<time>\d+\.\d+):.*"
)

@lru_cache(maxsize=None)
def make_irq_pattern(event: str) -> re.Pattern:
    """Memoized pattern factory."""
    return re.compile(
        r"\[(?P<cpu>\d+)\].*?"
        r"(?P<time>\d+\.\d+):.*"
        rf"{event}"
    )

SOFTIRQ_ENTRY_PATTERN = make_irq_pattern("softirq_entry")
SOFTIRQ_EXIT_PATTERN = make_irq_pattern("softirq_exit")
TASKLET_ENTRY_PATTERN = make_irq_pattern("tasklet_entry")
TASKLET_EXIT_PATTERN = make_irq_pattern("tasklet_exit")
IRQHANDLER_ENTRY_PATTERN = make_irq_pattern("irq_handler_entry")
IRQHANDLER_EXIT_PATTERN = make_irq_pattern("irq_handler_exit")

SCHED_SWITCH_PATTERN = re.compile(
    r"\[(?P<cpu>\d+)\].*?"
    r"(?P<time>\d+\.\d+):.*"
    r"sched_switch: "
    r"prev_comm=(?P<prev_comm>.+?) "
    r"prev_pid=(?P<prev_pid>\d+) "
    r"prev_prio=(?P<prev_prio>\d+) "
    r"prev_state=(?P<prev_state>[A-Z+]+) "
    r"==> "
    r"next_comm=(?P<next_comm>.+?) "
    r"next_pid=(?P<next_pid>\d+) "
    r"next_prio=(?P<next_prio>\d+)"
)

SCHED_WAKING_PATTERN = re.compile(
    r"(?P<waker_comm>\S+)-(?P<waker_pid>\d+).*"
    r"\[(?P<cpu>\d+)\].*?"
    r"(?P<time>\d+\.\d+):.*"
    r"sched_waking: "
    r"comm=(?P<waiter_comm>.+?) "
    r"pid=(?P<waiter_pid>\d+) "
    r"prio=(?P<waiter_prio>\d+) "
    r"target_cpu=(?P<target_cpu>\d+)"
)

CPU_FREQUENCY_PATTERN = re.compile(
    r"\[\d+\].*?"
    r"(?P<time>\d+\.\d+):.*"
    r"cpu_frequency: "
    r"state=(?P<cpu_freq>\d+) "
    r"cpu_id=(?P<cpu_id>\d+)"
)
