"""
File: export.py
Title: Data Export & Visualization
Description: Queries the SQLite database, processes it via Pandas, 
             and generates CSVs alongside high-res PNG/SVG analytical graphs.
Author: Hugh Brennan
Date: 2026-04-24
Version: 0.1
"""
import os
import json
import sqlite3
import yaml
import pandas as pd
from typing import Any
from datetime import datetime, timezone, timedelta

from tools.visualisation.graph import GraphGenerator, DualAxisConfig, FrequencyBarConfig, AvgMetricBarConfig, BubbleScatterConfig

# define absolute path
BASE_DIR : str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------
# Export Classes
# ---------------------------------------------------------
class DataExtractor:
    """ Handles secure database connections and data retrieval.
    """
    def __init__(self, db_path : str) -> None:
        """
        Initializes the DataExtractor.

        Args:
            db_path (str): absolute path to SQLite database.
        """
        self.db_path : str = db_path

    def fetch_recent_metrics(self, days_back: int) -> pd.DataFrame:
        """
        Retrieves perception metrics within a specified historical timeframe.

        Args:
            days_back (int): number of days into past to extract data from.

        Raises:
            FileNotFoundError: if specified database file does not exist.

        Returns:
            pd.DataFrame: pandas DataFrame containing the chronological database records.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        cutoff_date : str = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        # use pandas to directly read sql query into optimized dataframe
        with sqlite3.connect(self.db_path) as conn:
            query : str = "SELECT * FROM perception_metrics WHERE scrape_date >= ? ORDER BY scrape_date ASC"
            df : pd.DataFrame = pd.read_sql_query(query, conn, params=(cutoff_date,))
            
        if not df.empty:
            df['scrape_date'] = pd.to_datetime(df['scrape_date'])
        return df


class CSVGenerator:
    """ Handles formatting and writing Pandas DataFrames to flat CSV files.
    """
    def __init__(self, output_dir : str) -> None:
        """
        Initializes the CSV generator and ensures the target directory exists.

        Args:
            output_dir (str): absolute path to the export destination folder.
        """
        self.output_dir : str = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

    def export(self, df : pd.DataFrame, filename : str = "raw_perception_data.csv") -> None:
        """
        Exports the provided DataFrame to a standard UTF-8 encoded CSV file.

        Args:
            df (pd.DataFrame): data payload to be exported.
            filename (str, optional): data payload to be exported. defaults to "raw_perception_data.csv".
        """
        if df.empty:
            return
        
        export_path : str = os.path.join(self.output_dir, filename)
        df.to_csv(export_path, index=False, encoding='utf-8')
        print(f"  -> CSV saved: {export_path}")


# ---------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------
def export_data_and_graphs(selected_graphs: list[str] | None = None) -> None:
    """
    Triggers the extraction, CSV, and Graph generation pipeline.

    Args:
        selected_graphs (list[str] | None): specific keys of graphs to export. if None, exports all.

    Returns:
        None
    """
    # construct absolute paths
    db_path : str     = os.path.join(BASE_DIR, "data", "waymo_metrics.db")
    csv_dir : str     = os.path.join(BASE_DIR, "exports", "csv")
    graphs_dir : str  = os.path.join(BASE_DIR, "exports", "graphs")
    params_path : str = os.path.join(BASE_DIR, "config", "params.yaml")
    graph_cfg_path : str = os.path.join(BASE_DIR, "config", "graphs.json")

    # dynamically read days_back from params.yaml
    days_back : int = 60
    if os.path.exists(params_path):
        with open(params_path, 'r') as f:
            config_data = yaml.safe_load(f)
            days_back = config_data.get('exporter', {}).get('days_back', 60)
    
    try:
        extractor = DataExtractor(db_path)
        df : pd.DataFrame = extractor.fetch_recent_metrics(days_back=days_back)
        
        if df.empty:
            print("  -> No data found for the specified timeframe.")
            return

        print("  -> Processing exports...")
        
        # 1. generate and export cvs
        csv_gen : CSVGenerator = CSVGenerator(csv_dir)
        csv_gen.export(df)

        # 2. generate and export graphs from json config
        if os.path.exists(graph_cfg_path):
            with open(graph_cfg_path, 'r') as f:
                graph_configs = json.load(f)
                
            graph_generator : GraphGenerator = GraphGenerator(graphs_dir)

            for key, data in graph_configs.items():
                # filter based on user UI selection
                if selected_graphs is not None and key not in selected_graphs:
                    continue

                graph_type : str | None = data.pop('type', None)

                if not graph_type:
                    print(f"  -> Entry '{key}' missing graph type, gracefully skipping to next entry.")
                    continue
                
                if graph_type == 'dual_axis_line':
                    cfg : DualAxisConfig = DualAxisConfig(**data)
                    graph_generator.generate_dual_axis_trend(df, cfg)
                elif graph_type == 'frequency_bar':
                    cfg : FrequencyBarConfig = FrequencyBarConfig(**data)
                    graph_generator.generate_horizontal_bar(df, cfg)
                elif graph_type == 'avg_metric_bar':
                    cfg : AvgMetricBarConfig = AvgMetricBarConfig(**data)
                    graph_generator.generate_avg_metric_bar(df, cfg)
                elif graph_type == 'bubble_scatter':
                    cfg : BubbleScatterConfig = BubbleScatterConfig(**data)
                    graph_generator.generate_bubble_scatter(df, cfg)

        print("  -> All exports and visualizations successfully compiled.")

    except Exception as e:
        print(f"  -> Export Error: {e}")


if __name__ == "__main__":
    export_data_and_graphs()