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
from datetime import datetime, timezone
# Package Imports
from core.schema import ScrapeBatch

# define directory and path of database file, SQLite automatically creates file if it doesn't exist.
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "waymo_metrics.db")


def init_db() -> None:
    """
    Creates the necessary tables for the database if they do not already exist.
    We split the data into two tables: one for the daily run summary, and one for the individual text metrics.
    """
    os.makedirs(DB_DIR, exist_ok=True)      # force Python to create 'data' folder, if it doesn't exist

    # create connection to database
    conn : sqlite3.Connection   = sqlite3.connect(DB_PATH)
    cursor : sqlite3.Cursor     = conn.cursor()
    
    # table 1: high-level overview of the daily run
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_overview (
            run_date TEXT PRIMARY KEY,
            run_count INTEGER DEFAULT 1,
            source_total INTEGER
        )
    ''')

    # table 2: individual logs for each time the scraper is run
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraper_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            run_time TEXT UNIQUE,
            source_count INTEGER
        )
    ''')

    # table 3: individual perception metrics text
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS perception_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            scrape_date TEXT,
            source_type TEXT,
            location TEXT,
            sentiment_polarity REAL,
            safety_score REAL,
            tech_optimism REAL,
            friction_point TEXT,
            utility_score REAL
        )
    ''')
    
    # update database and close connection
    conn.commit()
    conn.close()


def save_metrics(batch: ScrapeBatch) -> bool:
    """
    Unpacks the validated Pydantic ScrapeBatch object and writes it to the SQLite database.
    Logs the atomic run, updates the daily aggregate, and saves individual metrics.

    Args:
        batch (ScrapeBatch): The structured JSON output from the Gemini agent.

    Returns:
        bool: True if save was successful, False otherwise.
    """
    try:
        os.makedirs(DB_DIR, exist_ok=True)      # force Python to create 'data' folder, if it doesn't exist
        
        # create connection to database
        conn : sqlite3.Connection   = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor     = conn.cursor()
        
        # convert Python date object to ISO string for database storage
        run_date_str : str = batch.run_date.isoformat()
        run_time_str : str = datetime.now(timezone.utc).isoformat()
        sources_this_run : int = batch.total_sources_analyzed
        
        # 1. log this specific run
        cursor.execute('''
            INSERT INTO scraper_runs (run_date, run_time, source_count)
            VALUES (?, ?, ?)
        ''', (run_date_str, run_time_str, sources_this_run))
        
        # 2. insert or update the daily run record (UPSERT)
        cursor.execute('''
            INSERT INTO daily_overview (run_date, run_count, source_total)
            VALUES (?, 1, ?)
            ON CONFLICT(run_date) DO UPDATE SET 
                run_count = run_count + 1,
                source_total = source_total + excluded.source_total
        ''', (run_date_str, sources_this_run))
        
        # 3. insert metrics individually
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
        
        # update database and close connection
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