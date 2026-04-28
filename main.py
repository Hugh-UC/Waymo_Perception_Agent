"""
File: main.py
Title: Core Orchestrator
Description: Links the scrapers, the PydanticAI Agent, the database, and the exporter.
Author: Hugh Brennan
Date: 2026-04-24
Version: 0.1
"""
import sys
import asyncio
from datetime import date
from typing import Any

# Package Imports
from core.system_check import verify_system_integrity
from tools.scraper import scrape_waymo_news, scrape_reddit_sentiment, scrape_social_hybrid, scrape_youtube_hybrid
from core.agent import extract_perception_metrics, synthesize_trending_narratives
from tools.db import save_metrics, get_historical_metrics, save_trending_narratives
from tools.export import export_data_and_graphs

async def run_pipeline() -> bool:
    """
    Executes the full data ingestion, AI analysis, narrative synthesis, and export pipeline.
    
    Returns:
        bool: True if the entire pipeline completes successfully, False otherwise.
    """
    # halt immediately if directory structure is broken
    if not verify_system_integrity():
        return False

    try:
        print("\n[1/6] Scraping News & Reddit...")
        news_data : str = scrape_waymo_news()
        reddit_data : str = scrape_reddit_sentiment()
        
        print("[2/6] Scraping Video Platforms (YouTube, TikTok, IG)...")
        # Extracting top 3 most relevant results per platform to balance token limits
        yt_data : str = scrape_youtube_hybrid("Waymo review", max_results=3)
        tiktok_data : str = scrape_social_hybrid("Waymo", "tiktok.com", max_results=3)
        ig_data : str = scrape_social_hybrid("Waymo", "instagram.com/reel", max_results=3)
        
        # Combine all unstructured text into a single payload for the AI
        combined_data : str = f"{news_data}\n\n{reddit_data}\n\n{yt_data}\n\n{tiktok_data}\n\n{ig_data}"

        print("[3/6] Executing Gemini Perception Analysis (Extracting Metrics)...")
        metrics_dict : dict[str, Any] | None = await extract_perception_metrics(combined_data)

        if not metrics_dict:
            print("\n❌ Pipeline Failed: Perception agent returned None.")
            return False

        print("[4/6] Saving Metrics to SQLite Database...")
        from core.schema import ScrapeBatch
        metrics_obj = ScrapeBatch(**metrics_dict)
        save_success : bool = save_metrics(metrics_obj)
        
        if not save_success:
            print("\n❌ Pipeline Failed: Could not save metrics to database.")
            return False

        print("[5/6] Fetching 7-Day History & Synthesizing Narratives...")
        historical_data : list[dict[str, Any]] = get_historical_metrics(days_back=7)

        if historical_data:
            narrative_dict : dict[str, Any] | None = await synthesize_trending_narratives(historical_data)

            if narrative_dict:
                save_trending_narratives(narrative_dict)
            else:
                print("      [Warning] Narrative synthesis returned empty.")
        else:
             print("      [Warning] No historical data found to synthesize.")

        print("[6/6] Exporting CSV and SVG graphs...")
        export_data_and_graphs()
        print("\n✅ Pipeline completed successfully!")
            
        return True
        
    except Exception as e:
        print(f"\n❌ Pipeline Critical Failure: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(run_pipeline())