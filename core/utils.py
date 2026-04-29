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
# 
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
# 
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
        chart_type : str = config.get("type")
        
        if chart_type == "frequency_bar":
            category_col : str = config["category_col"]
            counts = df[category_col].value_counts().reset_index()
            counts.columns = [category_col, 'count']
            
            return {
                "labels": counts[category_col].tolist(),
                "datasets": [{"label": config["x_label"], "data": counts['count'].tolist()}]
            }
            
        elif chart_type == "avg_metric_bar":
            group_col : str  = config["group_col"]
            metric_col : str = config["metric_col"]
            
            # filter out unknown locations and calculate mean
            grouped = df[df[group_col] != 'Unknown'].groupby(group_col)[metric_col].mean().sort_values(ascending=False).reset_index()
            
            return {
                "labels": grouped[group_col].tolist(),
                "datasets": [{"label": config["x_label"], "data": grouped[metric_col].tolist()}]
            }
            
        elif chart_type == "dual_axis_line":
            date_col : str      = config["date_col"]
            y_cols : list[str]  = config["y_col"]        # expects list of two columns
            
            # group by date and calculate mean for both columns
            trends = df.groupby(date_col)[y_cols].mean().reset_index()
            # convert timestamp to string for JSON serialization
            trends[date_col] = trends[date_col].dt.strftime('%Y-%m-%d') 
            
            return {
                "labels": trends[date_col].tolist(),
                "datasets": [
                    {"label": config["y_label"], "data": trends[y_cols[0]].tolist(), "yAxisID": "y"},
                    {"label": config["y2_label"], "data": trends[y_cols[1]].tolist(), "yAxisID": "y1"}
                ]
            }
            
        elif chart_type == "bubble_scatter":
            # for scatter, Chart.js expects data in {x, y, r} format
            x_col, y_col, size_col, hue_col = config["x_col"], config["y_col"], config["size_col"], config["hue_col"]
            
            # normalize size column for bubble radius (e.g., scale 0-1 score to 5-25 pixels)
            df['r'] = (df[size_col] * 20) + 5
            
            # group by hue (source_type) to create separate datasets for legend
            datasets : list[dict | None] = []
            for name, group in df.groupby(hue_col):
                bubble_data = group[[x_col, y_col, 'r']].rename(columns={x_col: 'x', y_col: 'y'}).to_dict(orient='records')
                datasets.append({"label": str(name), "data": bubble_data})
                
            return {
                "labels": [],       # scatters don't use primary labels
                "datasets": datasets
            }
            
        else:
            return {"labels": [], "datasets": []}