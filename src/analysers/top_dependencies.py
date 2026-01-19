import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pathlib import Path

_BANNED_THREADS=["<idle>", "timeout"]

class DependenciesLister:
    @classmethod
    def run_analysis(cls, input_folder: Path, output_dir: Path):
        dfs_lst = []
        dfs_inv_lst = []
        for cur_file in input_folder.iterdir():
            df = pd.read_csv(cur_file)
            df = cls.drop_banned_dependencies(df)
            dfs_lst.append(cls.get_top_dependencies(df))
            dfs_inv_lst.append(cls.get_top_inv_dependencies(df))
        res_df = pd.concat(dfs_lst).groupby("waker_waiter_pair", as_index=False).sum()
        res_inv_df = pd.concat(dfs_inv_lst).groupby("waker_waiter_pair", as_index=False).sum()
        cls.plot_dependencies(res_df, output_dir, "top_depedencies.png", "Overall statistics")
        cls.plot_dependencies(res_inv_df, output_dir, "top_capacity_inversion_depedencies.png", "Inversion related statistics")

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
    def get_top_inv_dependencies(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        returns top by amount and top by wait time
        dependencies when inversion happened
        """

        wdf = df.copy()

        unknown_core_mask = wdf["wait_start_waker_freq"].astype(int) == -1
        cap_inversion_mask = wdf["wait_start_waker_freq"].astype(int) < wdf["wait_start_waiter_freq"].astype(int)
        wdf = wdf[cap_inversion_mask & (~unknown_core_mask)].copy()

        wdf["waker_info"] = wdf["waker_comm"] + "-" + wdf["waker_pid"].astype(str) 
        wdf["waiter_info"] = wdf["waiter_comm"] + "-" + wdf["waiter_pid"].astype(str) 
        wdf["waker_waiter_pair"] = wdf["waker_info"] + "_" + wdf["waiter_info"]

        res_df = wdf.groupby("waker_waiter_pair").agg(
            total_duration_us=("waiting_duration_us", "sum"),
            total_dependencies=("waiting_duration_us", "count")
        ).reset_index()

        return res_df

    @classmethod
    def plot_dependencies(cls, df: pd.DataFrame, output_dir: Path, output_name: str, huge_title: str):
        output_dir.mkdir(exist_ok=True, parents=True)

        n_dependencies = 30
        top_duration = df.nlargest(n_dependencies, "total_duration_us").sort_values("total_duration_us")
        top_dependencies = df.nlargest(n_dependencies, "total_dependencies").sort_values("total_dependencies")        

        _fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8), dpi=300, sharex=False)

        for cur_ax, data, title, xlabel, idx in zip([ax1, ax2], 
                                        [top_duration, top_dependencies],
                                        ["total duration", "total amount of dependencies"],
                                        ["duration (us)", "dependencies"],
                                        [1,2]):
            
            values = data[data.columns[idx]].sort_values().reset_index(drop=True)

            for i, value in enumerate(values):
                cur_ax.broken_barh([(0, value)], (i - 0.4, 0.8), 
                            facecolors='steelblue', alpha=0.7)

            cur_ax.set_yticks(range(len(data)))
            cur_ax.set_yticklabels(data["waker_waiter_pair"], fontsize=8)
            cur_ax.set_xlabel(xlabel)
            cur_ax.set_title(f"top {n_dependencies} dependencies by {title}")
            cur_ax.grid(True, axis="x", alpha=0.3)


        plt.suptitle(huge_title)
        plt.tight_layout()
        plt.savefig(output_dir / output_name)
