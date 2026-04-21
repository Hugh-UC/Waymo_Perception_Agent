"""
File: db.py
Title: Database Storage Tool
Description: Handles the permanent storage of structured JSON metrics into a local SQLite database.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""
import os
import sqlite3
from typing import Any
# Package Imports
from core.schema import ScrapeBatch

# Define the directory and the specific path. SQLite automatically creates file, if it doesn't exist.
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "waymo_metrics.db")

def init_db() -> None:
    """
    Creates the necessary tables for the database if they do not already exist.
    We split the data into two tables: one for the daily run summary, and one for the individual text metrics.
    """
    os.makedirs(DB_DIR, exist_ok=True)      # force Python to create 'data' folder, if it doesn't exist

    conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
    cursor : sqlite3.Cursor = conn.cursor()
    
    # Table 1: High-level overview of the daily run
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT UNIQUE,
            total_sources INTEGER
        )
    ''')
    
    # Table 2: The granular perception metrics scraped by the agent
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS perception_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            scrape_date TEXT,
            source_type TEXT,
            location TEXT,
            sentiment_polarity REAL,
            safety_score INTEGER,
            tech_optimism TEXT,
            friction_point TEXT,
            utility_score INTEGER,
            FOREIGN KEY(run_date) REFERENCES daily_runs(run_date)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_metrics(batch: ScrapeBatch) -> bool:
    """
    Unpacks the validated Pydantic ScrapeBatch object and writes it to the SQLite database.

    Args:
        batch (ScrapeBatch): The structured JSON output from the Gemini agent.

    Returns:
        bool: True if save was successful, False otherwise.
    """
    try:
        os.makedirs(DB_DIR, exist_ok=True)      # force Python to create 'data' folder, if it doesn't exist
        
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor = conn.cursor()
        
        # Convert the Python date object to an ISO string for database storage
        run_date_str : str = batch.run_date.isoformat()
        
        # 1. Insert the daily run record. 
        # Using 'INSERT OR IGNORE' prevents crashing if you run the script twice in one day.
        cursor.execute('''
            INSERT OR IGNORE INTO daily_runs (run_date, total_sources)
            VALUES (?, ?)
        ''', (run_date_str, batch.total_sources_analyzed))
        
        # 2. Loop through the array of metrics and insert them individually
        for metric in batch.metrics:
            cursor.execute('''
                INSERT INTO perception_metrics 
                (run_date, scrape_date, source_type, location, sentiment_polarity, safety_score, tech_optimism, friction_point, utility_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_date_str,
                metric.scrape_date.isoformat(),
                metric.source_type,
                metric.location,
                metric.sentiment_polarity,
                metric.safety_perception_score,
                metric.technological_optimism,
                metric.primary_friction_point,
                metric.utility_score
            ))
            
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[DB ERROR] Failed to save metrics: {e}")
        return False

# A quick test block to ensure the tables generate correctly
if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}...")
    init_db()
    print("Database tables created successfully!")