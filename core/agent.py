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
from core.schema import ScrapeBatch

# load environment variables
load_dotenv()

# load configuration from yaml
with open("config/params.yaml", "r") as file:
    config : dict[str, Any] = yaml.safe_load(file)

# extract agent configurations
agent_cfg : dict[str, Any]  = config['agent']
agent_model : str           = agent_cfg['model_name']
fallback_model : list[str]  = agent_cfg['fallback_model']
agent_temp : float          = agent_cfg['temperature']
agent_retries : int         = agent_cfg['retries']
out_retries : int           = agent_cfg['output_retries']

# initialize the PydanticAI Agent
perception_agent = Agent(
    model=agent_model,
    name="waymo_perception_agent",
    output_type=ScrapeBatch,
    retries=agent_retries,
    output_retries=out_retries,
    model_settings={'temperature': agent_temp},
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
        
        # provide agent with today's date for ScrapeBatch schema
        today : str = date.today().isoformat()
        
        prompt : str = (
            f"Today's date is {today}. Please analyse the following scraped data and "
            f"extract the metrics for each individual comment/post.\n\n"
            f"{mock_data}"
        )
        
        print(f"2. Sending data to {agent_model} (Temp: {agent_temp}). Please wait...")
        
        try:
            # execute the agent
            result = await perception_agent.run(prompt)
            
            print("\n=== STRUCTURED JSON OUTPUT ===")
            print(result.output.model_dump_json(indent=2))
            
        except Exception as e:
            error_message : str = str(e)

            # check if error is due to server overload (503) or rate limits (429)
            if "503" in error_message or "429" in error_message:
                print(f"\n[WARNING] Primary model overloaded or rate-limited.")
                print(f"\n[WARNING] Initiating fallback cascade...")

                fallback_success : bool = False
                for fb_model in fallback_model:
                    print(f"\n[ATTEMPTING] Rerouting to {fb_model}...")

                    try:
                        # alt run attempt
                        result = await perception_agent.run(prompt, model=fb_model)

                        print(f"\n=== STRUCTURED JSON OUTPUT (FALLBACK | Model: {fb_model}) ===")
                        print(result.output.model_dump_json(indent=2))
                        
                        # update success flag and close loop
                        fallback_success = True
                        break
                    
                    except Exception as fallback_error:
                        print(f"\n[CRITICAL ERROR] Fallback model '{fb_model}' failed: {fallback_error}")

                # handle alternative models being unsuccessful
                if not fallback_success:
                    print("\n[CRITICAL ERROR] All fallback models in the cascade failed!")

            else:
                # different error (like a strict validation failure), print it normally
                print(f"\n[ERROR] An unexpected error occurred: {e}")

    # run the async test
    asyncio.run(test_agent())