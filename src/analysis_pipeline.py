import argparse

from pathlib import Path

from parsers import WaitingTimeParser

class AnalysisPipeline:
    parsing_enabled: bool = False
    analysis_enabled: bool = False

    @classmethod
    def __init__(cls, parsing: bool, analysis: bool):
        cls.parsing_enabled = parsing
        cls.analysis_enabled = analysis
    
    @classmethod
    def run(cls, input_path: Path, output: Path):
        if cls.parsing_enabled:
            cls.run_parsing_stuff(input_path, output)
        if cls.analysis_enabled:
            cls.run_analysis_stuff(input_path, output)
    
    @classmethod
    def run_parsing_stuff(cls, input_path: Path, output: Path):
        output_parsing = output / "parsing"
        input_stem = input_path.stem
        wt_df = WaitingTimeParser().gain_wait_info(input_path)

        output_parsing.mkdir(exist_ok=True, parents=True)
        wt_df.to_csv(f"{output_parsing/input_stem}.csv", index=False)

    @classmethod
    def run_analysis_stuff(cls, input_path: Path, output: Path):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process trace files with parsing and analysis options"
    )
    parser.add_argument("--input", type=Path, required=True, help="path to input trace")
    parser.add_argument("--output", type=Path, default=Path("output_analysis"), help="path to output folder")
    parser.add_argument("--parsing", action="store_true", help="enable parsing mode")
    parser.add_argument("--analysis", action="store_true", help="enable analysis mode")
    args = parser.parse_args()

    pipeline = AnalysisPipeline(args.parsing, args.analysis)
    pipeline.run(args.input, args.output)

