"""
File: utils.py
Title: Core Utilities
Description: Helper functions for data formatting and string manipulation.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""

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