import pytest
from src.parsers import InterruptsParser
import portion
from pathlib import Path

INPUT_PATH = Path("tests/input/interrupts")

@pytest.mark.parametrize(
    ("n_cores", "trace_path", "expected"),
    [
        pytest.param(
            1,
            Path("softirq_simple_test.trace"),
            {
                0: portion.closed(7180168353,7180168512),
            },
            id="single softirq test",
        ),
        pytest.param(
            1,
            Path("tasklet_simple_test.trace"),
            {
                0: portion.closed(7180168353,7180168512),
            },
            id="single tasklet test",
        ),
        pytest.param(
            1,
            Path("irq_handler_simple_test.trace"),
            {
                0: portion.closed(7180168353,7180168512),
            },
            id="single irq_handler test",
        ),
        pytest.param(
            1,
            Path("no_entry_interrupt.trace"),
            {
                0: portion.closed(1111222333,7180168512),
            },
            id="missed irq entry trace",
        ),
        pytest.param(
            1,
            Path("no_exit_interrupt.trace"),
            {
                0: portion.closed(7180168512,8880000111),
            },
            id="missed irq exit trace",
        ),
        pytest.param(
            2,
            Path("multiple_interrupts.trace"),
            {
                0: portion.closed(1000100, 1000450),
                1: portion.closed(1000100, 1000200),
            },
            id="multiple interruptors"
        )
    ]
)
def test_interrupts(n_cores: int, trace_path: Path, expected: dict):
    parser = InterruptsParser(n_cores=n_cores)
    
    result = parser.parse_interrupts(INPUT_PATH / trace_path)
    assert result == expected

