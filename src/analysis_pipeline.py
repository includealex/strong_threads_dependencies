import argparse

from pathlib import Path

from parsers import WaitingTimeParser
from analysers import DependenciesLister

class AnalysisPipeline:
    parsing_enabled: bool = False
    analysis_enabled: bool = False

    @classmethod
    def __init__(cls, parsing: bool, analysis: bool):
        cls.parsing_enabled = parsing
        cls.analysis_enabled = analysis
    
    @classmethod
    def create_output_dirs(cls, output: Path):
        cls.output_parsing = output / "parsing"
        cls.output_analysis = output / "analysis"
        cls.output_parsing.mkdir(exist_ok=True, parents=True)
        cls.output_analysis.mkdir(exist_ok=True, parents=True)

    @classmethod
    def run(cls, input_path: Path, output: Path):
        cls.create_output_dirs(output)

        if input_path.is_dir():
            input_files = input_path.iterdir()
        else:
            input_files = [input_path]

        if cls.parsing_enabled:
            for cur_file in input_files:
                cls.run_parsing_stuff(cur_file, cls.output_parsing)

        if cls.analysis_enabled:
            cls.run_analysis_stuff(cls.output_parsing, cls.output_analysis)

    @classmethod
    def run_parsing_stuff(cls, input_path: Path, output_path: Path):
        wt_df = WaitingTimeParser().gain_wait_info(input_path)
        wt_df.to_csv(Path(f"{output_path / input_path.stem}.csv"), index=False)

    @classmethod
    def run_analysis_stuff(cls, parsing_result_folder: Path, output: Path):            
        DependenciesLister().run_analysis(parsing_result_folder, output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process trace files with parsing and analysis options"
    )
    parser.add_argument("--input", type=Path, required=True, help="path to input trace")
    parser.add_argument("--output", type=Path, default=Path("output_analysis"), help="path to output folder")
    parser.add_argument("-p", "--parsing", action="store_true", help="enable parsing mode")
    parser.add_argument("-a", "--analysis", action="store_true", help="enable analysis mode")
    args = parser.parse_args()

    pipeline = AnalysisPipeline(args.parsing, args.analysis)
    pipeline.run(args.input, args.output)

