import pytest
from src.parsers import CpuFreqParser
from src.parsers.constants import UNKNOWN_CPU_FREQ
import portion
from pathlib import Path

INPUT_PATH = Path("tests/input/cpu_frequencies")

@pytest.mark.parametrize(
    ("trace_path", "expected"),
    [
        pytest.param(
            Path("single_cpu_freq.trace"),
            {
                10: {400000: portion.closed(1, 10)}
            },
            id="single cpu frequency event",
        ),
        pytest.param(
            Path("multiple_frequencies.trace"),
            {
                0: {
                    1400000: portion.closed(63, 100),
                },
                10: {
                    400000: portion.closed(2, 11) | portion.closed(78, 100),
                    800000: portion.closed(11, 78),
                },
                12 : {
                    200000: portion.closed(13, 33),
                    1200000: portion.closed(33, 100),
                },
            },
            id="multiple cpu frequencies events"
        ),
    ]
)
def test_parse_frequencies(trace_path: Path, expected: dict):
    result = CpuFreqParser().parse_frequencies(INPUT_PATH / trace_path)

    assert result == expected

@pytest.mark.parametrize(
    ("trace_path", "core", "ts_us", "expected"),
    [
        pytest.param(
            Path("multiple_frequencies.trace"),
            4,
            42,
            UNKNOWN_CPU_FREQ,
            id="no info about frequencies for core"
        ),
        pytest.param(
            Path("multiple_frequencies.trace"),
            12,
            1,
            UNKNOWN_CPU_FREQ,
            id="no info about frequency at the time"
        ),
        pytest.param(
            Path("multiple_frequencies.trace"),
            10,
            79,
            400000,
            id="default frequency info check"
        ),
    ]
)
def test_get_freq_info(trace_path: Path, core: int, ts_us: int, expected: int):
    parser = CpuFreqParser()
    _ = parser.parse_frequencies(INPUT_PATH / trace_path)
    result = parser.get_freq_info(core, ts_us)

    assert result == expected