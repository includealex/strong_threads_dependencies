import portion
import re

from collections import defaultdict
from pathlib import Path

from .constants import (
    S_TO_US,
    UNKNOWN_CPU_FREQ,
)
from .regexps import CPU_FREQUENCY_PATTERN
from .firstlaststamper import FirstLastStamperParser


class CpuFreqParserException(Exception):
    pass

class CpuFreqParser:
    @classmethod
    def __init__(cls):
        """
        key is cpu_id
        value is dictionary, where:
            key is cpu_freq
            value is intervals, when cpu_frequency was used
        """
        cls.frequency_per_core = defaultdict(lambda: defaultdict(lambda: portion.empty()))

    @classmethod
    def parse_frequencies(cls, input_trace: Path):
        if not input_trace.exists():
            raise CpuFreqParserException(f"input file doesn't exist: {input_trace}")
        
        with open(input_trace, "r") as ifile:
            ilines = ifile.readlines()
        
        last_ts_us = FirstLastStamperParser().parse_last_timestamp_us(ilines)

        # key is core, value is dict:
        #  - start_us is info about entry state start
        #  - cpu_freq is info about frequency at the start
        current_entry_states = defaultdict(dict)

        for iline in ilines:
            if not (("cpu_frequency" in iline) and (match := re.search(CPU_FREQUENCY_PATTERN, iline))):
                continue

            cur_time_us = int(float(match["time"])*S_TO_US)
            core = int(match["cpu_id"])
            cur_freq = int(match["cpu_freq"])

            if core  in current_entry_states.keys():
                prev_state = current_entry_states[core]
                prev_freq = prev_state["cpu_freq"]
                start_us = prev_state["start_us"]
                cls.frequency_per_core[core][prev_freq] |= portion.closed(start_us, cur_time_us)
                
            current_entry_states[core] = {
                "start_us": cur_time_us,
                "cpu_freq": cur_freq,
            }

        # this case matches state when no cpu_frequency
        # update was at the end of trace
        # ... cpu_frequency: cpu_id= state=A
        # ... trace_end
        # ... cpu_frequency: cpu_id= state=B <- assuming it will be here
        # cpu_frequency of state=A lasted till the end of the trace.
        for core in current_entry_states.keys():
            prev_state = current_entry_states[core]
            prev_freq = prev_state["cpu_freq"]
            start_us = prev_state["start_us"]
            cls.frequency_per_core[core][prev_freq] |= portion.closed(start_us, last_ts_us)

        return cls.frequency_per_core

    @classmethod
    def get_freq_info(cls, core: int, ts_us: int) -> int:
        if core not in cls.frequency_per_core.keys():
            return UNKNOWN_CPU_FREQ
        
        result_freq = UNKNOWN_CPU_FREQ

        states_per_core = cls.frequency_per_core[core]
        for cpu_freq, intervals in states_per_core.items():
            if ts_us in intervals:
                result_freq = cpu_freq
                break

        return result_freq

