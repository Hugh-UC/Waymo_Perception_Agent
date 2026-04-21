"""
File: agent.py
Title: Perception Analysis Agent
Description: Initializes the PydanticAI agent, loads Gemini configurations, and defines the system prompt for metric extraction.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""

import os
import yaml
from datetime import date
from typing import Any
from dotenv import load_dotenv
from pydantic_ai import Agent
# Package Imports
from core.schema import DailyScrapeBatch

# load environment variables
load_dotenv()

# load configuration from yaml
with open("config/params.yaml", "r") as file:
    config : dict[str, Any] = yaml.safe_load(file)

agent_model : str = config['agent']['model_name']

# initialize the PydanticAI Agent
perception_agent = Agent(
    model=agent_model,
    result_type=DailyScrapeBatch,
    system_prompt=(
        "You are an expert AI data analyst specialising in public sentiment regarding autonomous vehicles. "
        "Your objective is to read raw text scraped from media sites and extract highly structured metrics. "
        "You must evaluate the psychological and practical dimensions of the public's perception of Waymo. "
        "If an article or comment discusses autonomous vehicles generally or a competitor (like Tesla), "
        "infer the sentiment only if it explicitly compares to or impacts Waymo. If it is completely irrelevant, "
        "do your best to filter it out or score it neutrally. "
        "Ensure strict adherence to the provided output schema."
    )
)

# test block to ensure Gemini is properly structuring data
if __name__ == "__main__":
    import asyncio
    # Package Imports
    from tools.scraper import scrape_reddit_sentiment
    
    async def test_agent():
        print("1. Fetching mock Reddit data...")
        mock_data : str = scrape_reddit_sentiment()
        
        # provide agent with today's date for DailyScrapeBatch schema
        today : str = date.today().isoformat()
        
        prompt : str = (
            f"Today's date is {today}. Please analyse the following scraped data and "
            f"extract the metrics for each individual comment/post.\n\n"
            f"{mock_data}"
        )
        
        print(f"2. Sending data to {agent_model}... (This may take a few seconds)")
        
        try:
            # execute the agent
            result = await perception_agent.run(prompt)
            
            print("\n=== STRUCTURED JSON OUTPUT ===")
            print(result.data.model_dump_json(indent=2))
            
        except Exception as e:
            print(f"\nAn error occurred: {e}")

    # run the async test
    asyncio.run(test_agent())