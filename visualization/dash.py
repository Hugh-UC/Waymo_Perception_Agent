"""
File: dash.py
Title: Data Export & Visualization
Description: Queries the SQLite database to generate raw CSV exports and native SVG visualizations.
Author: Hugh Brennan
Date: 2026-04-24
Version: 0.1
"""
import os
import csv
import sqlite3
from typing import Any

DB_PATH : str = os.path.join("data", "waymo_metrics.db")

def export_data_and_graphs() -> None:
    """
    Extracts DB records to CSV and generates a native SVG sentiment graph.
    Assumes the export directories have already been verified by the system checker.

    Returns:
        None
    """
    if not os.path.exists(DB_PATH):
        print("  -> Database not found. Skipping exports.")
        return

    conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor : sqlite3.Cursor = conn.cursor()
    
    # 1. export raw data to CSV
    cursor.execute("SELECT * FROM perception_metrics ORDER BY scrape_date ASC")
    rows : list[sqlite3.Row] = cursor.fetchall()
    
    if not rows:
        conn.close()
        return

    csv_path : str = os.path.join("exports", "csv", "raw_perception_data.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer : Any = csv.writer(f)
        writer.writerow(rows[0].keys()) # Write headers
        for row in rows:
            writer.writerow(row)
            
    # 2. generate native SVG graph (sentiment over time)
    svg_path : str = os.path.join("exports", "graphs", "sentiment_trend.svg")
    
    width : int = 800
    height : int = 400
    points : list[str] = []
    
    # map points (X = index, Y = sentiment polarity mapped to height)
    for i, row in enumerate(rows):
        x : float = 50 + (i * (700 / max(1, len(rows) - 1)))
        # sentiment range is '-1' to '1'. map to 'Y' coordinates (0 is top, 400 is bottom)
        sentiment : float = float(row['sentiment_polarity']) if row['sentiment_polarity'] else 0.0
        y : float = 200 - (sentiment * 150) 
        points.append(f"{x},{y}")
        
    path_data : str = " ".join(points)
    
    svg_content : str = f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#1e1e1e" />
        <line x1="50" y1="200" x2="750" y2="200" stroke="#555" stroke-width="2" stroke-dasharray="5,5" />
        <text x="10" y="195" fill="#aaa" font-family="sans-serif" font-size="12">Neutral</text>
        <polyline points="{path_data}" fill="none" stroke="#3399ff" stroke-width="3" />
        {''.join([f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="4" fill="#66b2ff" />' for p in points])}
    </svg>"""

    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    conn.close()
    print("  -> Exports successfully saved to exports/ directory.")