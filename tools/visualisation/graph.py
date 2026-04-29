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
from dataclasses import dataclass

# forces headless rendering for FastAPI background threads
matplotlib.use('Agg')

# ---------------------------------------------------------
# Graph Configuration Objects (Parameter Object Pattern)
# ---------------------------------------------------------
@dataclass
class BaseChartConfig:
    """ Base configuration holding universal graph attributes.
    """
    filename : str
    title : str
    x_label : str
    y_label : str

@dataclass
class DualAxisConfig(BaseChartConfig):
    """ Configuration for dual-axis timeline charts.
    """
    date_col : str
    y_col : list[str]
    y2_label : str

@dataclass
class FrequencyBarConfig(BaseChartConfig):
    """ Configuration for simple frequency/count bar charts.
    """
    category_col : str

@dataclass
class AvgMetricBarConfig(BaseChartConfig):
    """ Configuration for grouped, metric-averaging bar charts.
    """
    group_col : str
    metric_col : str

@dataclass
class BubbleScatterConfig(BaseChartConfig):
    """ Configuration for annotated, multi-dimensional scatter plots.
    """
    x_col : str
    y_col : str
    hue_col : str
    size_col : str


# ---------------------------------------------------------
# Graph Class (Different Graph Plot Methods)
# ---------------------------------------------------------
class GraphGenerator:
    """ Handles statistical aggregations and Matplotlib/Seaborn rendering.
    """
    def __init__(self, output_dir : str, dpi : int = 300) -> None:
        """
        Initializes the Graph generator, configures output quality, and sets global visual themes.

        Args:
            output_dir (str | Path): absolute path to export destination folder.
            dpi (int, optional): image resolution density. defaults to 300.
        """
        self.output_dir : str = output_dir
        self.dpi : int = dpi

        os.makedirs(self.output_dir, exist_ok=True)
        
        # set presentation-quality global styles
        plt.style.use('dark_background')
        sns.set_palette("muted")
        sns.set_context("talk")

    def _save_plot(self, filename_base : str) -> None:
        """
        Helper method to save the active plot in both PNG and SVG formats.

        Args:
            filename_base (str): filename prefix without extensions.
        """
        png_path : str = os.path.join(self.output_dir, f"{filename_base}.png")
        svg_path : str = os.path.join(self.output_dir, f"{filename_base}.svg")
        
        plt.savefig(png_path, dpi=self.dpi, bbox_inches='tight')
        plt.savefig(svg_path, format='svg', bbox_inches='tight')
        plt.close('all')
        print(f"  -> Graphs saved: {filename_base} (.png & .svg)")

    # --- dual axis trend line chart ---
    def generate_dual_axis_trend(self, df : pd.DataFrame, config : DualAxisConfig) -> None:
        """
        Generates a dual-axis line chart tracking two metrics over a shared timeline.

        Args:
            df (pd.DataFrame): source dataset containing temporal and numeric data.
            config (DualAxisConfig): configuration for axes labels, date columns, and y-axis metrics.
        """
        plt.figure(figsize=(12, 6))
        daily_trends : pd.DataFrame = df.groupby(config.date_col)[config.y_col].mean().reset_index()

        fig, ax1 = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('#020617')
        ax1.set_facecolor('#020617')

        color1 : str = '#3b82f6'
        ax1.set_xlabel(config.x_label, color='white')
        ax1.set_ylabel(config.y_label, color=color1)
        ax1.plot(daily_trends[config.date_col], daily_trends[config.y_col[0]], color=color1, marker='o', linewidth=3)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.tick_params(axis='x', colors='white')

        ax2 = ax1.twinx()
        color2 : str = '#a855f7'
        ax2.set_ylabel(config.y2_label, color=color2)
        ax2.plot(daily_trends[config.date_col], daily_trends[config.y_col[1]], color=color2, marker='s', linewidth=3)
        ax2.tick_params(axis='y', labelcolor=color2)

        plt.title(config.title, color='white', pad=20)
        fig.tight_layout()
        self._save_plot(config.filename)

    # --- horizontal frequency bar plot ---
    def generate_horizontal_bar(self, df : pd.DataFrame, config : FrequencyBarConfig) -> None:
        """
        Generates a horizontal frequency bar chart using the provided configuration object.

        Args:
            df (pd.DataFrame): source dataset containing categorical data.
            config (FrequencyBarConfig): configuration specifying category column and plot labels.
        """
        plt.figure(figsize=(10, 6), facecolor='#020617')
        ax = plt.gca()
        ax.set_facecolor('#020617')

        counts : pd.DataFrame = df[config.category_col].value_counts().reset_index()
        counts.columns = [config.category_col, 'count']

        sns.barplot(x='count', y=config.category_col, data=counts, palette='magma', ax=ax)
        plt.title(config.title, color='white', pad=20)
        plt.xlabel(config.x_label, color='white')
        plt.ylabel(config.y_label, color='white')
        ax.tick_params(colors='white')
        plt.tight_layout()
        self._save_plot(config.filename)

    # --- horizontal average metrics bar plot ---
    def generate_avg_metric_bar(self, df : pd.DataFrame, config : AvgMetricBarConfig) -> None:
        """
        Generates a ranked horizontal bar chart that displays the mean value of a metric per group.

        Args:
            df (pd.DataFrame): source dataset to be aggregated.
            config (AvgMetricBarConfig): configuration defining grouping column and numeric metric to average.
        """
        plt.figure(figsize=(12, 7), facecolor='#020617')
        ax = plt.gca()
        ax.set_facecolor('#020617')

        # filter out unknown locations and calculate mean
        grouped_data : pd.DataFrame = df[df[config.group_col] != 'Unknown'].groupby(config.group_col)[config.metric_col].mean().sort_values(ascending=False).reset_index()

        sns.barplot(x=config.metric_col, y=config.group_col, data=grouped_data, palette='coolwarm', ax=ax)
        plt.title(config.title, color='white', pad=20)
        plt.xlabel(config.x_label, color='white')
        plt.ylabel(config.y_label, color='white')
        ax.tick_params(colors='white')
        plt.axvline(x=0, color='gray', linestyle='--', linewidth=1.5)
        plt.tight_layout()
        self._save_plot(config.filename)

    # --- bubble scatter plot ---
    def generate_bubble_scatter(self, df : pd.DataFrame, config : BubbleScatterConfig) -> None:
        """
        Generates a 4-dimensional bubble chart with automated annotations for high-value outliers.

        Args:
            df (pd.DataFrame): source dataset containing x, y, hue, and size dimensions.
            config (BubbleScatterConfig): configuration for spatial mapping, color grouping, and bubble scaling.
        """
        plt.figure(figsize=(12, 7), facecolor='#020617')
        ax = plt.gca()
        ax.set_facecolor('#020617')

        sns.scatterplot(x=config.x_col, y=config.y_col, hue=config.hue_col, 
                        size=config.size_col, sizes=(100, 900), alpha=0.8, 
                        palette='Set2', data=df, ax=ax)
        
        plt.title(config.title, color='white', pad=20)
        plt.xlabel(config.x_label, color='white')
        plt.ylabel(config.y_label, color='white')
        ax.tick_params(colors='white')

        handles, labels = ax.get_legend_handles_labels()
        new_labels : list[str] = [label.replace('_', ' ').title() if label in [config.hue_col, config.size_col] else label for label in labels]
            
        plt.legend(handles, new_labels, bbox_to_anchor=(1.05, 1), loc='upper left', 
                   facecolor='#0f172a', edgecolor='white', framealpha=1.0, 
                   labelcolor='white', borderaxespad=0., frameon=True)

        if config.size_col in df.columns and config.hue_col in df.columns:
            threshold : float = df[config.size_col].quantile(0.85)
            top_points : pd.DataFrame = df[df[config.size_col] >= threshold]
            
            for i, row in top_points.iterrows():
                ax.text(row[config.x_col], row[config.y_col] + 0.25, 
                        f"{row[config.hue_col]} (Rel: {row[config.size_col]})", 
                        color='white', fontsize=10, ha='center', 
                        bbox=dict(facecolor='#020617', alpha=0.6, edgecolor='none', pad=1))

        plt.tight_layout()
        self._save_plot(config.filename)