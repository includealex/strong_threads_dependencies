import pytest
from src.parsers import FirstLastStamperParser
from pathlib import Path

INPUT_PATH = Path("tests/input/firstlaststamper/")

@pytest.mark.parametrize(
    ("trace_path", "expected"),
    [
        pytest.param(
            Path("first_last_ts.trace"),
            (1111222333, 8880000111),
            id="single first last ts test",
        ),
    ]
)
def test_interrupts(trace_path: Path, expected: dict):
    parser = FirstLastStamperParser()
    
    result = parser.get_first_and_last_us(INPUT_PATH / trace_path)
    assert result == expected