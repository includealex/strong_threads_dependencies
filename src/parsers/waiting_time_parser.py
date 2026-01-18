import pandas as pd
import re
import portion

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from .constants import (
    IDLE_CORE,
    SLEEP_STATES,
    UNKNOWN_CORE,
    UNKNOWN_CPU_FREQ,
)
from .events import (
    SchedSwitchOnEvent,
    SchedSwitchOffEvent,
    SchedWakingEvent,
)
from .cpu_freq_parser import CpuFreqParser
from .interrupts import InterruptsParser
from .firstlaststamper import FirstLastStamperParser
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
    wait_start_waker_core: int = UNKNOWN_CORE
    wait_start_waker_prio: int = -1


class WaitingTimeParser:
    @classmethod
    def __init__(cls):
        cls.interrupts_parser = InterruptsParser()
        cls.cpu_freq_parser = CpuFreqParser()
        cls.running_per_core = defaultdict(lambda: defaultdict(lambda: portion.empty()))

    @classmethod
    def get_running_core(cls, pid: int, ts_us: int):
        core_dicts = cls.running_per_core[pid]

        result_core = IDLE_CORE
        for core, running_states in core_dicts.items():
            if ts_us in running_states:
                result_core = core
                break

        return result_core

    @classmethod
    def calc_running_states(cls, first_ts_us: int, last_ts_us: int, ss_on_df: pd.DataFrame, ss_off_df: pd.DataFrame):
        """
        parsers running info per each pid
        key is pid
        value is dict:
            - key is core number
            - value is running states
        """

        on_df = ss_on_df.copy()
        off_df = ss_off_df.copy()
        
        on_df = on_df.rename(columns={
            "next_core": "core",
            "next_pid": "pid",
            "time_us": "start_time"
        })
        
        off_df = off_df.rename(columns={
            "prev_core": "core",
            "prev_pid": "pid",
            "time_us": "end_time"
        })

        # Synthetic logics is needed for case, when no sched_switch_on
        # in the trace appeared but sched_switch off showed up.
        min_ends = off_df.groupby(["core", "pid"])["end_time"].min().reset_index()
        min_starts = on_df.groupby(["core", "pid"])["start_time"].min().reset_index()
        merged_mins = pd.merge(min_ends, min_starts, on=["core", "pid"], how="left")
        need_synthetic = merged_mins[
            merged_mins["start_time"].isna() | 
            (merged_mins["end_time"] < merged_mins["start_time"])
        ]
        if not need_synthetic.empty:
            synthetic = pd.DataFrame({
                "core": need_synthetic["core"],
                "pid": need_synthetic["pid"],
                "start_time": first_ts_us
            })
            on_df = pd.concat([on_df, synthetic], ignore_index=True)

        on_df = on_df.sort_values("start_time")
        off_df = off_df.sort_values("end_time")

        merged = pd.merge_asof(
            on_df,
            off_df,
            by=["core", "pid"],
            left_on="start_time",
            right_on="end_time",
            direction="forward",
        )[["start_time", "core", "pid", "end_time"]]

        # case when no sched_switch off happened until trace end 
        if not merged.empty:
            merged["end_time"] = merged["end_time"].fillna(last_ts_us)

        running_per_core = defaultdict(lambda: defaultdict(lambda: portion.empty()))
        
        for (pid, core), group in merged.groupby(["pid", "core"]):
            intervals = []
            for _, row in group.iterrows():
                start = int(row["start_time"])
                end = int(row["end_time"])
                if start <= end:
                    intervals.append(portion.closed(start, end))
            
            if intervals:
                running_per_core[pid][core] |= portion.Interval(*intervals)
        
        cls.running_per_core = running_per_core

        return running_per_core

    @classmethod
    def apply_cores_info(cls, wait_df: pd.DataFrame):
        df = wait_df.copy()

        def process_row(row):
            wait_start_us = int(row["waiting_time_start_us"])
            waiter_core = int(row["wait_start_waiter_core"])
            waker_pid = int(row["waker_pid"])
            waker_core = cls.get_running_core(waker_pid, wait_start_us)

            waiter_freq = cls.cpu_freq_parser.get_freq_info(waiter_core, wait_start_us)

            if waker_core != IDLE_CORE:
                waker_freq = cls.cpu_freq_parser.get_freq_info(waker_core, wait_start_us)
            else:
                waker_freq = 0
            
            return pd.Series({
                "wait_start_waiter_freq": waiter_freq,
                "wait_start_waker_core": waker_core,
                "wait_start_waker_freq": waker_freq
            })
        
        result_columns = df.apply(process_row, axis=1)
        df[["wait_start_waiter_freq", "wait_start_waker_core", "wait_start_waker_freq"]] = result_columns

        return df

    @classmethod
    def gain_wait_info(cls, trace: Path) -> pd.DataFrame:
        if not trace.exists():
            raise WaitingTimeParserException(f"no {trace=} provided exists")

        with open(trace, "r") as ifile:
            ilines = ifile.readlines()

        ss_on_df, ss_off_df, sw_df = cls.parse_sched_events(ilines)
        interrupts_info = cls.interrupts_parser.parse_interrupts(trace)
        wait_df = cls.find_wait_dependencies(ss_off_df, sw_df, interrupts_info)
        first_ts_us, last_ts_us = FirstLastStamperParser().get_first_and_last_us(trace)
        cls.calc_running_states(first_ts_us, last_ts_us, ss_on_df, ss_off_df)
        cls.cpu_freq_parser.parse_frequencies(trace)
        wait_df = cls.apply_cores_info(wait_df)

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
