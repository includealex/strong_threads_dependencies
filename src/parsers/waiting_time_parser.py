import pandas as pd
import re
import portion

from dataclasses import dataclass
from pathlib import Path
from .constants import SLEEP_STATES
from .events import (
    SchedSwitchOnEvent,
    SchedSwitchOffEvent,
    SchedWakingEvent,
)
from .interrupts import InterruptsParser
from .regexps import (
    SCHED_SWITCH_PATTERN,
    SCHED_WAKING_PATTERN,
)

class WaitingTimeParserException(Exception):
    pass

@dataclass
class WaitingIntervalInfo:
    waiting_time_start_us: int
    waiting_time_end_us: int
    waiter_pid: int
    waker_pid: int
    waiting_duration_us: int
    waiter_comm: str
    waker_comm: str
    waiter_state: str
    waker_end_cpu: int
    wait_end_target_cpu: int
    wait_start_waiter_core: int
    wait_start_waiter_prio: int
    wait_start_waker_core: int = -1
    wait_start_waker_prio: int = -1


class WaitingTimeParser:
    @classmethod
    def __init__(cls, n_cores: int = 20):
        cls.interrupts_parser = InterruptsParser(n_cores=n_cores)

    @classmethod
    def gain_wait_info(cls, trace: Path) -> pd.DataFrame:
        if not trace.exists():
            raise WaitingTimeParserException(f"no {trace=} provided exists")

        with open(trace, "r") as ifile:
            ilines = ifile.readlines()

        _ss_on_df, ss_off_df, sw_df = cls.parse_sched_events(ilines)
        interrupts_info = cls.interrupts_parser.parse_interrupts(trace)
        wait_df = cls.find_wait_dependencies(ss_off_df, sw_df, interrupts_info)
        # TODO: apply here info update about default -1 waiting intervals info
        # _ss_on_df should be used there.

        return wait_df

    @classmethod
    def find_wait_dependencies(
        cls,
        ss_off_df: pd.DataFrame,
        sw_df: pd.DataFrame,
        interrupts_info: dict[int, portion.Interval],
    ) -> pd.DataFrame:
        """
        For wait dependencies, sched_switch offs with sleep states only(S,D) are used.
        wait trace example:
                     ...  no interrupt context start
                     ...  time_1 ... sched_switch: ... prev_info=A prev_state=S(or D)
        waker_info=B ...  time_2 ... sched_waking: ...    waiter=A
                     ...  no interrupt context end
        Here, waiting time = time_2 - time_1, waker is B, waiter is A.
        """

        sleep_df = ss_off_df[ss_off_df["prev_state"].isin(SLEEP_STATES)].copy()
        wake_df = sw_df.copy()

        match_col="_match_key_"
        sleep_df[match_col] = sleep_df["prev_pid"].astype(str) + "_" + sleep_df["prev_comm"]
        wake_df[match_col] = wake_df["waiter_pid"].astype(str) + "_" + wake_df["waiter_comm"]

        merged = pd.merge(
            sleep_df,
            wake_df,
            left_on=match_col,
            right_on=match_col,
            suffixes=("_sleep", "_wake"),
        )

        if merged.empty:
            return pd.Series()

        merged["time_diff"] = abs(merged["time_us_wake"] - merged["time_us_sleep"])
        result = []
        for _, sleep_row in sleep_df.iterrows():
            sleep_start_time_us = sleep_row["time_us"]
            match_key = sleep_row[match_col]

            matching = merged[merged[match_col] == match_key].copy()
            
            if matching.empty:
                continue

            matching["time_diff"] = abs(matching["time_us_wake"] - sleep_start_time_us)
            closest = matching.loc[matching["time_diff"].idxmin()]

            wt_end_us = closest["time_us_wake"]
            waker_end_cpu = closest["waker_cpu"]

            # Check, if wake was due to interrupt context.
            interrupt_interval = interrupts_info[waker_end_cpu]
            if wt_end_us in interrupt_interval:
                continue

            result.append(WaitingIntervalInfo(
                wait_start_waiter_core=sleep_row["prev_core"],
                wait_start_waiter_prio=sleep_row["prev_prio"],
                wait_end_target_cpu=closest["target_cpu"],
                waiter_pid=sleep_row["prev_pid"],
                waiter_state=sleep_row["prev_state"],
                waker_end_cpu=waker_end_cpu,
                waiter_comm=sleep_row["prev_comm"],
                waker_pid=closest["waker_pid"],
                waker_comm=closest["waker_comm"],
                waiting_time_start_us=sleep_start_time_us,
                waiting_time_end_us=wt_end_us,
                waiting_duration_us=wt_end_us - sleep_start_time_us,               
            ))

        return pd.DataFrame(result)

    @classmethod
    def parse_sched_events(cls, trace: Path | list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if isinstance(trace, Path):
            if not trace.exists():
                raise WaitingTimeParserException(f"no {trace=} provided exists")

            with open(trace, "r") as ifile:
                trace = ifile.readlines()

        sched_switches_on = []
        sched_switches_off = []
        sched_waking = []

        for iline in trace:
            if "sched_switch" in iline and (match:=re.search(SCHED_SWITCH_PATTERN, iline)):
                sched_switches_on.append(SchedSwitchOnEvent.from_match(match))
                sched_switches_off.append(SchedSwitchOffEvent.from_match(match))
        
            elif "sched_waking" in iline and (match:=re.search(SCHED_WAKING_PATTERN, iline)):
                sched_waking.append(SchedWakingEvent.from_match(match))

        return pd.DataFrame(sched_switches_on), \
                pd.DataFrame(sched_switches_off), \
                  pd.DataFrame(sched_waking)
