import matplotlib.pyplot as plt
import pandas as pd

from pathlib import Path

_BANNED_THREADS=["<idle>", "timeout"]

class DependenciesLister:
    @classmethod
    def run_analysis(cls, input_folder: Path, output_dir: Path):
        dfs_lst = []
        for cur_file in input_folder.iterdir():
            df = pd.read_csv(cur_file)
            df = cls.drop_banned_dependencies(df)
            dfs_lst.append(cls.get_top_dependencies(df))

        res_df = pd.concat(dfs_lst).groupby("waker_waiter_pair", as_index=False).sum()
        cls.plot_dependencies(res_df, output_dir)

    @classmethod
    def drop_banned_dependencies(cls, df: pd.DataFrame) -> pd.DataFrame:
        banned_waker_mask = ~df["waker_comm"].astype(str).str.startswith(tuple(_BANNED_THREADS))
        banned_waiter_mask = ~df["waiter_comm"].astype(str).str.startswith(tuple(_BANNED_THREADS))

        return df[banned_waiter_mask & banned_waker_mask].copy()

    @classmethod
    def get_top_dependencies(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        returns top by amount and top by wait time
        dependencies
        """

        wdf = df.copy()
        wdf["waker_info"] = wdf["waker_comm"] + "-" + wdf["waker_pid"].astype(str) 
        wdf["waiter_info"] = wdf["waiter_comm"] + "-" + wdf["waiter_pid"].astype(str) 
        wdf["waker_waiter_pair"] = wdf["waker_info"] + "_" + wdf["waiter_info"]

        res_df = wdf.groupby("waker_waiter_pair").agg(
            total_duration_us=("waiting_duration_us", "sum"),
            total_dependencies=("waiting_duration_us", "count")
        ).reset_index()

        return res_df

    @classmethod
    def plot_dependencies(cls, df: pd.DataFrame, output_dir: Path):
        output_dir.mkdir(exist_ok=True, parents=True)

        n_dependencies = 30
        top_duration = df.nlargest(n_dependencies, "total_duration_us").sort_values("total_duration_us")
        top_dependencies = df.nlargest(n_dependencies, "total_dependencies").sort_values("total_dependencies")        

        _fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8), dpi=300)

        for ax, data, title, xlabel in zip([ax1, ax2], 
                                        [top_duration, top_dependencies],
                                        ["total duration", "total amount of dependencies"],
                                        ["duration (us)", "dependencies"]):
            
            _bars = ax.barh(range(len(data)), data[data.columns[1]].sort_values())
            ax.set_yticks(range(len(data)))
            ax.set_yticklabels(data["waker_waiter_pair"], fontsize=8)
            ax.set_xlabel(xlabel)
            ax.set_title(f"top {n_dependencies} dependencies by {title}")
            ax.grid(True, axis="x", alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir/"top_depedencies.png")
