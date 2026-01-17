import pytest
import pandas as pd
import portion

from pathlib import Path
from src.parsers.constants import UNKNOWN_CORE
from src.parsers.firstlaststamper import FirstLastStamperParser
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
                    wait_start_waker_core=UNKNOWN_CORE,
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
                    wait_start_waker_core=UNKNOWN_CORE,
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
                    wait_start_waker_core=UNKNOWN_CORE,
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

@pytest.mark.parametrize(
    ("trace_path", "expected"),
    [
        pytest.param(
            Path("double_sched_switch_on_off.trace"),
            {
                1: {
                    9: portion.closed(1, 5) | portion.closed(10, 100)
                },
                2: {
                    9: portion.closed(5, 10),
                },
            },
            id="double sched switches running info",
        ),
        pytest.param(
            Path("multiple_sched_switch_on_off.trace"),
            {
                1: {
                    9: portion.closed(1, 5) | portion.closed(10, 100)
                },
                2: {
                    9: portion.closed(5, 10),
                    8: portion.closed(25, 30)
                },
                3: {
                    8: portion.closed(1, 25) | portion.closed(30, 100)
                },
            },
        )
    ]
)
def test_calc_running_states(trace_path: Path, expected: dict):
    parser = WaitingTimeParser()
    ss_on_df, ss_off_df, _sw_df = parser.parse_sched_events(INPUT_PATH / trace_path)
    first_ts_us, last_ts_us = FirstLastStamperParser.get_first_and_last_us(INPUT_PATH / trace_path)

    result = parser.calc_running_states(first_ts_us, last_ts_us, ss_on_df, ss_off_df)

    assert expected == result
