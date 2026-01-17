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
    # TODO: 
    # 1. Find out, how to define wait start waker core
    # 2. For capacity inversion information, capacity table
    # should be found out for device.
    wait_start_waker_core: int = -1
    wait_start_waker_prio: int = -1


class WaitingTimeParser:
    @classmethod
    def __init__(cls):
        cls.interrupts_parser = InterruptsParser()

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

        sleep_df = ss_off_df[ss_off_df["prev_state"].isin(SLEEP_STATES)].copy()
        wake_df = sw_df.copy()

        match_col = "_match_key_"
        sleep_df[match_col] = sleep_df["prev_pid"].astype(str) + "_" + sleep_df["prev_comm"]
        wake_df[match_col] = wake_df["waiter_pid"].astype(str) + "_" + wake_df["waiter_comm"]

        if sleep_df.empty or wake_df.empty:
            return pd.DataFrame()

        sleep_df = sleep_df.rename(columns={"time_us": "time_us_sleep"})
        wake_df = wake_df.rename(columns={"time_us": "time_us_wake"})

        sleep_df = sleep_df.sort_values("time_us_sleep")
        wake_df = wake_df.sort_values("time_us_wake")

        merged = pd.merge_asof(
            sleep_df,
            wake_df,
            by=match_col,
            left_on="time_us_sleep",
            right_on="time_us_wake",
            direction="forward",
            suffixes=("_sleep", "_wake"),
        ).dropna()

        if merged.empty:
            return pd.DataFrame()

        result = []
        for _, row in merged.iterrows():
            if pd.isna(row["time_us_wake"]):
                continue

            wt_end_us = int(row["time_us_wake"])
            waker_end_cpu = int(row["waker_cpu"])

            interrupt_interval = interrupts_info.get(waker_end_cpu)
            if interrupt_interval and wt_end_us in interrupt_interval:
                continue
            
            wt_start_us = int(row["time_us_sleep"])

            result.append(
                WaitingIntervalInfo(
                    wait_start_waiter_core=int(row["prev_core"]),
                    wait_start_waiter_prio=int(row["prev_prio"]),
                    wait_end_target_cpu=int(row["target_cpu"]),
                    waiter_pid=int(row["prev_pid"]),
                    waiter_state=row["prev_state"],
                    waker_end_cpu=waker_end_cpu,
                    waiter_comm=row["prev_comm"],
                    waker_pid=int(row["waker_pid"]),
                    waker_comm=row["waker_comm"],
                    waiting_time_start_us=wt_start_us,
                    waiting_time_end_us=wt_end_us,
                    waiting_duration_us=wt_end_us - wt_start_us,
                )
            )

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
