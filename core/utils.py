"""
File: utils.py
Title: Core Utilities
Description: Helper functions for data formatting and string manipulation.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""
import pandas as pd
from typing import Any

# ---------------------------------------------------------
# Time Formatting
# ---------------------------------------------------------
def get_search_time_str(search_time: float | int) -> str:
    """
    Converts a numeric 'days_back' value into a human-readable string.
    Values greater than 3 days are returned in days; lesser values are converted to hours.

    Args:
        search_time (float | int): The numerical time value in days.

    Returns:
        str: search time in string format (e.g., "5 days" or "48 hours").
    """
    search_time_str : str = "0"

    if search_time > 3:
        search_time_str = f"{int(search_time)} days"
    else:
        time_in_hours : int = int(search_time * 24)
        search_time_str = f"{time_in_hours} hours"

    return search_time_str


# ---------------------------------------------------------
# Data Aggrigation Engine
# ---------------------------------------------------------
class DataAggregator:
    """
    Utility class for aggregating Pandas DataFrames into 
    lightweight JSON-serializable dictionaries for API endpoints.
    """
    @staticmethod
    def aggregate_by_config(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
        """
        Dynamically aggregates raw data based on a graph's JSON configuration.

        Args:
            df (pd.DataFrame): raw, unaggregated data.
            config (dict[str, Any]): JSON configuration dictionary for the specific graph.

        Returns:
            dict[str, Any]: dictionary containing 'labels' and 'datasets' ready for Chart.js.
        """
        # frequency / count aggregation
        # driven by: 'category_col'
        if "category_col" in config:
            category_col : str = config["category_col"]
            counts = df[category_col].value_counts().reset_index()
            counts.columns = [category_col, 'count']
            
            return {
                "labels": counts[category_col].tolist(),
                "datasets": [{"label": config.get("x_label", "Count"), "data": counts['count'].tolist()}]
            }
            
        # average metric by group aggregation
        # driven by: 'group_col' & 'metric_col'
        elif "group_col" in config and "metric_col" in config:
            group_col : str  = config["group_col"]
            metric_col : str = config["metric_col"]
            
            # filter out unknown locations and calculate mean
            grouped = df[df[group_col] != 'Unknown'].groupby(group_col)[metric_col].mean().sort_values(ascending=False).reset_index()
            
            return {
                "labels": grouped[group_col].tolist(),
                "datasets": [{"label": config.get("x_label", "Average"), "data": grouped[metric_col].tolist()}]
            }
            
        # 3. time series / dual axis aggregation
        # driven by : 'date_col'
        elif "date_col" in config and isinstance(config.get("y_col"), list):
            date_col : str      = config["date_col"]
            y_cols : list[str]  = config["y_col"]        # expects list of two columns
            
            # group by date and calculate mean
            trends = df.groupby(date_col)[y_cols].mean().reset_index()
            
            # convert timestamp to string for JSON serialization
            if pd.api.types.is_datetime64_any_dtype(trends[date_col]):
                trends[date_col] = trends[date_col].dt.strftime('%Y-%m-%d') 
            
            return {
                "labels": trends[date_col].tolist(),
                "datasets": [
                    {"label": config.get("y_label", y_cols[0]), "data": trends[y_cols[0]].tolist(), "yAxisID": "y"},
                    {"label": config.get("y2_label", y_cols[1]), "data": trends[y_cols[1]].tolist(), "yAxisID": "y1"}
                ]
            }
            
        # multi-dimensional scatter / bubble aggregation
        # driven by: 'x_col' & single 'y_col'
        elif "x_col" in config and isinstance(config.get("y_col"), str):
            x_col: str = config["x_col"]
            y_col: str = config["y_col"]
            
            # optional attributes
            size_col: str | None = config.get("size_col")
            hue_col: str | None  = config.get("hue_col")
            
            datasets : list[dict | None] = []
            
            # if size_col exists, format bubble {x, y, r}, otherwise scatter {x, y}
            if size_col:
                # force float conversion, prevents string math errors in js
                df[size_col] = pd.to_numeric(df[size_col], errors='coerce').fillna(0.1)
                df['r'] = (df[size_col] * 16) + 2
                cols_to_extract = [x_col, y_col, 'r']
            else:
                cols_to_extract = [x_col, y_col]

            # group by hue to create separate datasets for legend
            if hue_col:
                for name, group in df.groupby(hue_col):
                    scatter_data = group[cols_to_extract].rename(columns={x_col: 'x', y_col: 'y'}).to_dict(orient='records')
                    datasets.append({"label": str(name).title(), "data": scatter_data})
            else:
                scatter_data = df[cols_to_extract].rename(columns={x_col: 'x', y_col: 'y'}).to_dict(orient='records')
                datasets.append({"label": config.get("y_label", "Dataset"), "data": scatter_data})
                
            return {
                "labels": [],       # scatters don't use primary labels
                "datasets": datasets
            }
            
        # fallback
        else:
            return {"labels": [], "datasets": []}