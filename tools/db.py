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
from datetime import datetime, timezone, timedelta
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
            utility_score REAL,
            platform TEXT DEFAULT 'unknown',
            relatability_score REAL DEFAULT 0.0,
            individuality_score REAL DEFAULT 0.0
        )
    ''')

    # table 4: trending naratives
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trending_narratives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            location TEXT,
            synopsis TEXT NOT NULL,
            future_impact TEXT,
            sentiment_label TEXT,
            first_seen_date TEXT NOT NULL
        )
    ''')
    
    # update database and close connection
    conn.commit()
    conn.close()


def check_metrics_setup() -> bool:
    """
    Verifies that the metrics database file exists and contains all required tables.

    Returns:
        bool: True if the database is fully initialized and healthy, False otherwise.
    """
    if not os.path.exists(DB_PATH):
        return False
        
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor = conn.cursor()

        # query SQLite's internal master table to list all existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables : set[str] = {row[0] for row in cursor.fetchall()}
        conn.close()

        # define exact tables system requires to function
        required_tables : set[str] = {
            "daily_overview", 
            "scraper_runs", 
            "perception_metrics", 
            "trending_narratives"
        }

        # all required tables are present in the database
        return required_tables.issubset(tables)
    
    except sqlite3.OperationalError:
        return False
    
    except Exception as e:
        print(f"[Metrics DB Error] Status check failed: {e}")
        return False


def repair_metrics_tables() -> bool:
    """
    Attempts to auto-heal missing metrics tables by re-running the initialization schema.

    Returns:
        bool: True if repair executes successfully, False otherwise.
    """
    try:
        init_db()
        return True
    
    except Exception as e:
        print(f"[Metrics DB Error] Repair failed: {e}")
        return False



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
                (run_date, scrape_date, source_type, location, sentiment_polarity, safety_score, tech_optimism, friction_point, utility_score, platform, relatability_score, individuality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_date_str,
                metric.scrape_date.isoformat(),
                metric.source_type,
                metric.location,
                metric.sentiment_polarity,
                metric.safety_perception_score,
                metric.technological_optimism,
                metric.primary_friction_point,
                metric.utility_score,
                metric.platform,
                metric.relatability_score,
                metric.individuality_score
            ))
        
        # update database and close connection
        conn.commit()
        conn.close()

        return True
        
    except Exception as e:
        print(f"[DB ERROR] Failed to save metrics: {e}")
        return False


def get_historical_metrics(days_back : int = 7) -> list[dict[str, Any]]:
    """
    Retrieves all perception metrics from the last X days to feed to the Narrative Agent.

    Args:
        days_back (int, optional): number days of history to fetch. default to 7.

    Returns:
        list[dict[str, Any]]: list of historical metric dictionaries.
    """
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor : sqlite3.Cursor = conn.cursor()
        
        cutoff_date : str = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT * FROM perception_metrics 
            WHERE scrape_date >= ?
            ORDER BY scrape_date ASC
        ''', (cutoff_date,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch historical metrics: {e}")
        return []


def save_trending_narratives(narratives_batch : dict[str, Any]) -> bool:
    """
    Saves the AI-synthesized trending narratives into the database.
    Ignores exact duplicates to prevent database bloating.

    Args:
        narratives_batch (dict[str, Any]): validated JSON dictionary from Narrative Agent.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor = conn.cursor()
        
        narratives : list[dict[str, Any]] = narratives_batch.get("narratives", [])
        
        for n in narratives:
            cursor.execute('SELECT id FROM trending_narratives WHERE title = ? AND first_seen_date = ?', 
                           (n['title'], n['first_seen_date']))
            if cursor.fetchone():
                continue
                
            cursor.execute('''
                INSERT INTO trending_narratives 
                (title, location, synopsis, future_impact, sentiment_label, first_seen_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                n['title'], n['location'], n['synopsis'], 
                n['future_impact'], n['sentiment_label'], n['first_seen_date']
            ))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[DB ERROR] Failed to save trending narratives: {e}")
        return False


def get_narratives(start : str | None = None, end : str | None = None) -> list[dict[str, Any]]:
    """
    Retrieves AI-synthesized narratives, dynamically filtered by chronological parameters.

    Args:
        start (str | None, optional): start date string (YYYY-MM-DD). Defaults to None.
        end (str | None, optional): end date string (YYYY-MM-DD). Defaults to None.

    Returns:
        list[dict[str, Any]]: list of narrative records.
    """
    try:
        if not os.path.exists(DB_PATH):
            return []

        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor : sqlite3.Cursor = conn.cursor()

        query : str = "SELECT * FROM trending_narratives WHERE 1=1"
        params : list[str] = []

        if start:
            query += " AND first_seen_date >= ?"
            params.append(start)
        if end:
            query += " AND first_seen_date <= ?"
            params.append(end)

        query += " ORDER BY first_seen_date DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch narratives: {e}")
        return []


def get_dashboard_totals() -> dict[str, int]:
    """
    Queries the SQLite database to fetch the all-time totals for the dashboard.

    Returns:
        dict[str, int]: dictionary containing 'total_runs' and 'total_sources'.
    """
    if not os.path.exists(DB_PATH):
        return {"total_runs": 0, "total_sources": 0}
        
    try:
        conn : sqlite3.Connection   = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor     = conn.cursor()
        
        cursor.execute("SELECT SUM(run_count), SUM(source_total) FROM daily_overview")
        row = cursor.fetchone()
        conn.close()
        
        return {
            "total_runs": row[0] if row[0] else 0,
            "total_sources": row[1] if row[1] else 0
        }
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch dashboard totals: {e}")
        return {"total_runs": 0, "total_sources": 0}



# A quick test block to ensure the tables generate correctly
if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}...")
    init_db()
    print("Database tables created successfully!")