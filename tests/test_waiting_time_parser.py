import pytest
import pandas as pd

from pathlib import Path
from src.parsers.interrupts import InterruptsParser
from src.parsers.waiting_time_parser import (
    WaitingTimeParser,
    WaitingIntervalInfo,
)
from src.parsers.events import (
    SchedSwitchOnEvent,
    SchedSwitchOffEvent,
    SchedWakingEvent,
)

INPUT_PATH = Path("tests/input/waitingtime")

@pytest.mark.parametrize(
    ("trace_path", "expected_ss_on", "expected_ss_off", "expected_sw"),
    [
        pytest.param(
            Path("single_sched_switch_D.trace"),
            pd.DataFrame([
                SchedSwitchOnEvent(
                    time_us=1,
                    next_core=9,
                    next_pid=0,
                    next_prio=120,
                    next_comm="swapper/9"
                ),
            ]),
            pd.DataFrame([
                SchedSwitchOffEvent(
                    time_us=1,
                    prev_core=9,
                    prev_pid=10292,
                    prev_state="D",
                    prev_prio=100,
                    prev_comm="kworker/u41:3"
                ),
            ]),
            pd.DataFrame([
                SchedWakingEvent(
                    time_us=9,
                    waker_pid=42,
                    waiter_pid=10292,
                    waker_comm="A/165B:34-C",
                    waiter_comm="kworker/u41:3",
                    waiter_prio=100,
                    waker_cpu=7,
                    target_cpu=9,
                ),
            ]),
            id="simple sched events",
        ),
    ]
)
def test_parse_sched_events(
    trace_path: Path,
    expected_ss_on: pd.DataFrame,
    expected_ss_off: pd.DataFrame,
    expected_sw: pd.DataFrame,
):
    parser = WaitingTimeParser()

    # sched_switches (off,on) and sched_wakings
    ss_on, ss_off, sw = parser.parse_sched_events(INPUT_PATH / trace_path)

    assert expected_ss_on.equals(ss_on)
    assert expected_ss_off.equals(ss_off)
    assert expected_sw.equals(sw)


@pytest.mark.parametrize(
    ("trace_path", "expected"),
    [
        pytest.param(
            Path("single_sched_switch_D.trace"),
            pd.DataFrame([
                WaitingIntervalInfo(
                    waiting_time_start_us=1,
                    waiting_time_end_us=9,
                    waiter_pid=10292,
                    waker_pid=42,
                    waiting_duration_us=8,
                    waiter_comm="kworker/u41:3",
                    waker_comm="A/165B:34-C",
                    waiter_state="D",
                    waker_end_cpu=7,
                    wait_end_target_cpu=9,
                    wait_start_waiter_core=9,
                    wait_start_waiter_prio=100,
                    wait_start_waker_core=-1,
                    wait_start_waker_prio=-1,
                ),
            ]),
            id="single wait",
        ),
        pytest.param(
            Path("multiple_waits.trace"),
            pd.DataFrame([
                WaitingIntervalInfo(
                    waiting_time_start_us=1,
                    waiting_time_end_us=9,
                    waiter_pid=1,
                    waker_pid=2,
                    waiting_duration_us=8,
                    waiter_comm="A",
                    waker_comm="B",
                    waiter_state="D",
                    waker_end_cpu=7,
                    wait_end_target_cpu=11,
                    wait_start_waiter_core=9,
                    wait_start_waiter_prio=100,
                    wait_start_waker_core=-1,
                    wait_start_waker_prio=-1,
                ),
                WaitingIntervalInfo(
                    waiting_time_start_us=5,
                    waiting_time_end_us=15,
                    waiter_pid=3,
                    waker_pid=4,
                    waiting_duration_us=10,
                    waiter_comm="C",
                    waker_comm="D",
                    waiter_state="S",
                    waker_end_cpu=5,
                    wait_end_target_cpu=13,
                    wait_start_waiter_core=6,
                    wait_start_waiter_prio=100,
                    wait_start_waker_core=-1,
                    wait_start_waker_prio=-1,
                )
            ]),
            id="multiple waits",
        )
    ]
)
def test_calc_waiting_time(trace_path: Path, expected: pd.DataFrame):
    wait_df = WaitingTimeParser().gain_wait_info(INPUT_PATH / trace_path)

    assert wait_df.equals(expected)
