import portion
from collections import defaultdict
from pathlib import Path
import re
from .constants import (
    S_TO_US,
)
from .regexps import (
    SOFTIRQ_ENTRY_PATTERN,
    SOFTIRQ_EXIT_PATTERN,
    TASKLET_ENTRY_PATTERN,
    TASKLET_EXIT_PATTERN,
    IRQHANDLER_ENTRY_PATTERN,
    IRQHANDLER_EXIT_PATTERN,
)
from .firstlaststamper import FirstLastStamperParser

class InterruptsParserException(Exception):
    pass

class InterruptsParser:
    interrupts_per_core = None

    @classmethod
    def __init__(cls):
        cls.interrupts_per_core = defaultdict(lambda: portion.empty())

    @classmethod
    def update_interrupt_info(
        cls,
        ilines: list[str], first_ts_us: int, last_ts_us: int,
        entry_str: str, entry_pattern: re.Pattern,
        exit_str: str, exit_pattern: re.Pattern,
    ):
        current_entry_state = {}

        for iline in ilines:
            if (entry_str in iline) and (match := re.search(entry_pattern, iline)):
                tmp_core = int(match["cpu"])
                cur_time_us = int(float(match["time"])*S_TO_US)
                current_entry_state[tmp_core] = cur_time_us

            elif (exit_str in iline) and (match := re.search(exit_pattern, iline)):
                tmp_core = int(match["cpu"])
                cur_time_us = int(float(match["time"])*S_TO_US)

                if tmp_core in current_entry_state.keys():
                    prev_time_us = current_entry_state.pop(tmp_core)

                # this case matches state when no irq_entry info was before
                # but irq_exit was met:
                # ... irq_entry <- assuming that entry was here
                # ... trace_start
                # ... irq_exit
                # for provided trace, it will be assumed that
                # irq_entry was from the trace_start ts. 
                else:
                    prev_time_us = first_ts_us

                result_portion = portion.closed(prev_time_us, cur_time_us)
                cls.interrupts_per_core[tmp_core] |= result_portion

        # this case matches state when no irq_exit info was at the end of trace
        # but irq_entry was met:
        # ... irq_entry
        # ... trace_end
        # ... irq_exit <- assuming that exit was here
        # for provided trace, it will be assumed that
        # irq_end was till the trace_end ts. 
        for tmp_core, prev_time_us in current_entry_state.items():
            result_portion = portion.closed(prev_time_us, last_ts_us)
            cls.interrupts_per_core[tmp_core] |= result_portion

    @classmethod
    def parse_interrupts(cls, input_trace: Path):
        if not input_trace.exists():
            raise InterruptsParserException(f"input file doesn't exist: {input_trace}")

        with open(input_trace, "r") as ifile:
            ilines = ifile.readlines()

        first_ts_us, last_ts_us = FirstLastStamperParser().get_first_and_last_us(ilines)

        cls.update_interrupt_info(
            ilines, first_ts_us, last_ts_us,
            "softirq_entry", SOFTIRQ_ENTRY_PATTERN,
            "softirq_exit", SOFTIRQ_EXIT_PATTERN,
        )
        cls.update_interrupt_info(
            ilines, first_ts_us, last_ts_us,
            "tasklet_entry", TASKLET_ENTRY_PATTERN,
            "tasklet_exit", TASKLET_EXIT_PATTERN,
        )
        cls.update_interrupt_info(
            ilines, first_ts_us, last_ts_us,
            "irq_handler_entry", IRQHANDLER_ENTRY_PATTERN,
            "irq_handler_exit", IRQHANDLER_EXIT_PATTERN,
        )

        return cls.interrupts_per_core
