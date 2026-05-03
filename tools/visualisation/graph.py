"""
File: graph.py
Title: Graph Generation & Rendering Engine
Description: Contains configuration dataclasses and the generator class for rendering Matplotlib/Seaborn visualizations.
Author: Hugh Brennan
Date: 2026-04-30
Version: 0.1
"""
import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Any

# forces headless rendering for FastAPI background threads
matplotlib.use('Agg')

# ---------------------------------------------------------
# Graph Class (Dynamic Configuration Router)
# ---------------------------------------------------------
class GraphGenerator:
    """ 
    Handles statistical aggregations and Matplotlib/Seaborn rendering dynamically.
    Routes data to specific plotting helper methods based on JSON configuration shapes.
    """
    def __init__(self, output_dir : str, dpi : int = 300) -> None:
        """
        Initializes the Graph generator, configures output quality, and sets global visual themes.

        Args:
            output_dir (str): absolute path to export destination folder.
            dpi (int, optional): image resolution density. Defaults to 300.
            
        Returns:
            None
        """
        self.output_dir : str = output_dir
        self.dpi : int = dpi

        os.makedirs(self.output_dir, exist_ok=True)
        
        # set presentation-quality global styles
        plt.style.use('dark_background')
        sns.set_context("talk")

    def _save_plot(self, filename_base : str) -> None:
        """
        Helper method to save the active plot in both PNG and SVG formats.

        Args:
            filename_base (str): filename prefix without extensions.
            
        Returns:
            None
        """
        png_path : str = os.path.join(self.output_dir, f"{filename_base}.png")
        svg_path : str = os.path.join(self.output_dir, f"{filename_base}.svg")
        
        plt.savefig(png_path, dpi=self.dpi, bbox_inches='tight')
        plt.savefig(svg_path, format='svg', bbox_inches='tight')
        plt.close('all')
        print(f"  -> Graphs saved: {filename_base} (.png & .svg)")

    # --- Modular Plotting Helpers ---
    def _plot_frequency_bar(self, df : pd.DataFrame, config : dict[str, Any], ax : plt.Axes, palette : str) -> None:
        """
        Generates a horizontal frequency bar chart and applies it to the provided axes.

        Args:
            df (pd.DataFrame): source dataset containing categorical data.
            config (dict[str, Any]): configuration dictionary specifying category columns.
            ax (plt.Axes): matplotlib axes object to draw the plot on.
            palette (str): seaborn color palette name to use for rendering.

        Returns:
            None
        """
        category_col = config["category_col"]
        counts = df[category_col].value_counts().reset_index()
        counts.columns = [category_col, 'count']
        sns.barplot(x='count', y=category_col, data=counts, palette=palette, ax=ax)

    def _plot_avg_metric_bar(self, df : pd.DataFrame, config : dict[str, Any], ax : plt.Axes, palette : str, pres : dict[str, Any]) -> None:
        """
        Generates a ranked horizontal bar chart of grouped metric averages.

        Args:
            df (pd.DataFrame): source dataset containing groupings and numeric metrics.
            config (dict[str, Any]): configuration specifying group and metric columns.
            ax (plt.Axes): Matplotlib axes object to draw the plot on.
            palette (str): Seaborn color palette name to use for rendering.
            pres (dict[str, Any]): presentation settings, such as zero-line drawing flags.

        Returns:
            None
        """
        group_col = config["group_col"]
        metric_col = config["metric_col"]
        grouped = df[df[group_col] != 'Unknown'].groupby(group_col)[metric_col].mean().sort_values(ascending=False).reset_index()
        sns.barplot(x=metric_col, y=group_col, data=grouped, palette=palette, ax=ax)
        
        if pres.get("draw_zero_line"):
            ax.axvline(x=0, color='gray', linestyle='--', linewidth=1.5)

    def _plot_time_series(self, df : pd.DataFrame, config : dict[str, Any], ax1 : plt.Axes, pres : dict[str, Any]) -> None:
        """
        Generates a line plot tracking one or more metrics over time, supporting dual axes.

        Args:
            df (pd.DataFrame): source dataset containing temporal and numeric data.
            config (dict[str, Any]): configuration defining the date column and y-axis metrics.
            ax1 (plt.Axes): primary Matplotlib axes object for the main timeline.
            pres (dict[str, Any]): presentation settings detailing dual-axis requirements.

        Returns:
            None
        """
        y_cols = config["y_col"]
        trends = df.groupby(config["date_col"])[y_cols].mean().reset_index()
        
        color1 = '#3b82f6'
        ax1.plot(trends[config["date_col"]], trends[y_cols[0]], color=color1, marker='o', linewidth=3)
        ax1.set_ylabel(config.get("y_label", ""), color=color1)
        ax1.tick_params(axis='y', labelcolor=color1)

        if pres.get("has_dual_axis") and len(y_cols) > 1:
            ax2 = ax1.twinx()
            color2 = '#a855f7'
            ax2.plot(trends[config["date_col"]], trends[y_cols[1]], color=color2, marker='s', linewidth=3)
            ax2.set_ylabel(config.get("y2_label", ""), color=color2)
            ax2.tick_params(axis='y', labelcolor=color2)

    def _plot_bubble_scatter(self, df : pd.DataFrame, config : dict[str, Any], ax : plt.Axes) -> None:
        """
        Generates a multi-dimensional scatter plot (bubble chart) with optional sizing and hues.

        Args:
            df (pd.DataFrame): source dataset containing x, y, hue, and size dimensions.
            config (dict[str, Any]): configuration for spatial mapping and color grouping.
            ax (plt.Axes): Matplotlib axes object to draw the plot on.

        Returns:
            None
        """
        hue_col = config.get("hue_col")
        size_col = config.get("size_col")
        
        kwargs = {"x": config["x_col"], "y": config["y_col"], "data": df, "ax": ax, "palette": "Set2", "alpha": 0.8}
        if hue_col: kwargs["hue"] = hue_col
        
        if size_col:
            df[size_col] = pd.to_numeric(df[size_col], errors='coerce').fillna(0.1)
            kwargs["size"] = size_col
            kwargs["sizes"] = (100, 900)

        sns.scatterplot(**kwargs)
        
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            new_labels = [l.replace('_', ' ').title() if l in [hue_col, size_col] else l for l in labels]
            ax.legend(handles, new_labels, bbox_to_anchor=(1.05, 1), loc='upper left',
                        facecolor='#0f172a', edgecolor='white', framealpha=1.0, labelcolor='white')

    # --- master router ---
    def generate_from_config(self, df : pd.DataFrame, config : dict[str, Any]) -> None:
        """
        Master routing method. Reads the data shape defined in graphs.json and 
        dynamically routes to the appropriate Matplotlib/Seaborn export method.

        Args:
            df (pd.DataFrame): The raw, unaggregated dataset to be visualized.
            config (dict[str, Any]): The JSON configuration mapping for the specific graph.

        Returns:
            None
        """
        pres = config.get("presentation", {})
        palette = pres.get("palette", "muted")
        
        # baseline canvas setup
        fig, ax1 = plt.subplots(figsize=(12, 6))
        bg_color = '#020617'
        fig.patch.set_facecolor(bg_color)
        ax1.set_facecolor(bg_color)

        # route to appropriate rendering method
        if "category_col" in config:
            self._plot_frequency_bar(df, config, ax1, palette)
        elif "group_col" in config and "metric_col" in config:
            self._plot_avg_metric_bar(df, config, ax1, palette, pres)
        elif "date_col" in config and isinstance(config.get("y_col"), list):
            self._plot_time_series(df, config, ax1, pres)
        elif "x_col" in config and isinstance(config.get("y_col"), str):
            self._plot_bubble_scatter(df, config, ax1)
        else:
            print(f"  -> Skipping unsupported configuration: {config.get('filename')}")
            plt.close(fig)
            return

        # --- universal formatting application ---
        ax1.set_title(config.get("title", ""), color='white', pad=20)
        ax1.set_xlabel(config.get("x_label", ""), color='white')
        
        # prevent double-labeling if dual axis already set it
        if not pres.get("has_dual_axis"):
            ax1.set_ylabel(config.get("y_label", ""), color='white')
            
        ax1.tick_params(colors='white', axis='x')
        if not pres.get("has_dual_axis"):
            ax1.tick_params(colors='white', axis='y')

        plt.tight_layout()
        self._save_plot(config.get("filename", "export"))