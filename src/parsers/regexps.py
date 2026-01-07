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