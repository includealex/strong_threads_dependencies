import re
from pathlib import Path
from .regexps import TS_PATTERN
from .constants import (
    S_TO_US,
)

class FirstLastStamperParserException(Exception):
    pass

class FirstLastStamperParser:
    @classmethod
    def get_first_and_last_us(cls, trace: Path | list[str])->tuple[int, int]:
        if isinstance(trace, Path):
            with open(trace, "r") as itrace:
                trace = itrace.readlines()

        first_ts_us = cls.parse_first_timestamp_us(trace)
        last_ts_us = cls.parse_last_timestamp_us(trace)

        return first_ts_us, last_ts_us

    @classmethod
    def search_for_ts(cls, trace: list[str])->int | None:
        ts_us = None        
        for cur_line in trace:
            if (match:=re.search(TS_PATTERN, cur_line)):
                ts_us=int(float(match["time"])*S_TO_US)
                break
        return ts_us

    @classmethod
    def parse_first_timestamp_us(cls, trace: Path | list[str])->int:
        if isinstance(trace, Path):
            with open(trace, "r") as itrace:
                trace = itrace.readlines()

        first_ts_us = cls.search_for_ts(trace)
        
        if first_ts_us:
            return first_ts_us
        else:
            raise FirstLastStamperParserException("no first timestamp in trace")

    @classmethod
    def parse_last_timestamp_us(cls, trace: Path | list[str])->int:
        if isinstance(trace, Path):
            with open(trace, "r") as itrace:
                trace = itrace.readlines()

        last_ts_us = cls.search_for_ts(trace[::-1])
        
        if last_ts_us:
            return last_ts_us
        else:
            raise FirstLastStamperParserException("no last timestamp in trace")
