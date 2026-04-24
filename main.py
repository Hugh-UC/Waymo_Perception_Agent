"""
File: main.py
Title: Core Orchestrator
Description: Links the scrapers, the PydanticAI Agent, the database, and the exporter.
Author: Hugh Brennan
Date: 2026-04-24
Version: 0.2
"""
import sys
import asyncio
from datetime import date
from typing import Any
# Package Imports
from core.system_check import verify_system_integrity
from tools.scraper import scrape_waymo_news, scrape_reddit_sentiment
from core.agent import perception_agent
from tools.db import save_metrics
from visualization.dash import export_data_and_graphs

async def run_pipeline() -> bool:
    """
    Executes the full data ingestion, AI analysis, and export pipeline.
    
    Returns:
        bool: True if the entire pipeline completes successfully, False otherwise.
    """
    # Halt immediately if directory structure is broken
    if not verify_system_integrity():
        return False

    try:
        print("\n[1/4] Scraping News & Reddit...")
        news_data : str = scrape_waymo_news()
        reddit_data : str = scrape_reddit_sentiment()
        combined_data : str = f"{news_data}\n\n{reddit_data}"

        print("[2/4] Executing Gemini Perception Analysis (This may take a minute)...")
        prompt : str = (
            f"Today's date is {date.today().isoformat()}. Analyze the following scraped data and "
            f"extract the metrics for each individual comment/post.\n\n{combined_data}"
        )
        
        # send prompt and wait result
        result : Any = await perception_agent.run(prompt)

        print("[3/4] Saving to SQLite Database...")
        # strictly validated ScrapeBatch Pydantic object
        success : bool = save_metrics(result.output)
        
        if success:
            print("[4/4] Exporting CSV and SVG graphs...")
            export_data_and_graphs()
            print("\n✅ Pipeline completed successfully!")
            
        return success
    except Exception as e:
        print(f"\n❌ Pipeline Critical Failure: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(run_pipeline())