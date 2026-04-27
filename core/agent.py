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
import json
from datetime import date
from typing import Any
from dotenv import load_dotenv
from pydantic_ai import Agent
# Package Imports
from core.schema import ScrapeBatch, NarrativeBatch

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


# ---------------------------------------------------------
# 1. Perception Agent
# ---------------------------------------------------------

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

async def extract_perception_metrics(prompt_text : str) -> dict[str, Any] | None:
    """
    Instructs the perception agent to analyze a raw text payload and extract sentiment metrics.
    Includes an automatic fallback cascade if the primary model hits rate limits (503/429).

    Args:
        prompt_text (str): raw text from the scraped sources.

    Returns:
        dict[str, Any] | None: validated dictionary matching the ScrapeBatch schema, 
                               or None if all models fail.
    """
    prompt : str = (
        f"Today's date is {date.today().isoformat()}. Analyze the following scraped data and "
        f"extract the metrics for each individual comment/post.\n\n{prompt_text}"
    )

    try:
        # primary attempt
        result = await perception_agent.run(prompt)
        return result.data.model_dump()
        
    except Exception as e:
        error_message : str = str(e)
        if "503" in error_message or "429" in error_message:
            print(f"\n[WARNING] Primary model overloaded. Initiating perception fallback cascade...")
            
            for fb_model in fallback_model:
                print(f"\n[ATTEMPTING] Rerouting to {fb_model}...")
                try:
                    result = await perception_agent.run(prompt, model=fb_model)
                    return result.data.model_dump()
                except Exception as fallback_error:
                    print(f"[CRITICAL ERROR] Fallback model '{fb_model}' failed: {fallback_error}")
            
            print("\n[CRITICAL ERROR] All fallback models in the perception cascade failed!")
            return None
        else:
            print(f"\n[ERROR] An unexpected validation or API error occurred: {e}")
            return None


# ---------------------------------------------------------
# 2. Narrative Agent (Meta Agent)
# ---------------------------------------------------------

# initialize the Narrative Synthesizer Agent
narrative_agent = Agent(
    model=agent_model,
    name="waymo_narrative_agent",
    output_type=NarrativeBatch,
    retries=agent_retries,
    output_retries=out_retries,
    system_prompt=(
        "You are an expert AI data analyst specializing in public sentiment regarding autonomous vehicles. "
        "Your objective is to read a historical batch of highly structured perception metrics and extract overarching macro-narratives. "
        "You must evaluate the psychological and practical dimensions of the public's perception of Waymo over time. "
        "Group similar isolated incidents or recurring themes into overarching 'Trending Narratives' (e.g., 'Waymo Sued Over Crowd Incident'). "
        "If a metric discusses autonomous vehicles generally or a competitor (like Tesla), infer the sentiment only if it explicitly compares to or impacts Waymo. "
        "Identify the earliest mention of each trend from the provided data and extract it for the 'first_seen_date' field. "
        "Ensure strict adherence to the provided output schema."
    )
)

async def synthesize_trending_narratives(raw_posts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Instructs the narrative agent to analyze isolated posts and cluster them into overarching trends.
    Includes an automatic fallback cascade if the primary model hits rate limits (503/429).

    Args:
        raw_posts (list[dict[str, Any]]): A list of dictionaries representing scraped posts/articles.

    Returns:
        dict[str, Any] | None: A dictionary containing the parsed narratives (matching NarrativeBatch schema), 
                               or None if all models fail.
    """
    prompt : str = (
        f"Today's date is {date.today().isoformat()}. Analyze these structured historical "
        f"data points and extract the trending macro-narratives:\n\n{json.dumps(raw_posts, indent=2)}"
    )

    try:
        # primary attempt
        result = await narrative_agent.run(prompt)
        return result.data.model_dump()
        
    except Exception as e:
        error_message : str = str(e)
        if "503" in error_message or "429" in error_message:
            print(f"\n[WARNING] Primary model overloaded. Initiating narrative fallback cascade...")
            
            for fb_model in fallback_model:
                print(f"\n[ATTEMPTING] Rerouting to {fb_model}...")
                try:
                    result = await narrative_agent.run(prompt, model=fb_model)
                    return result.data.model_dump()
                except Exception as fallback_error:
                    print(f"[CRITICAL ERROR] Fallback model '{fb_model}' failed: {fallback_error}")
            
            print("\n[CRITICAL ERROR] All fallback models in the narrative cascade failed!")
            return None
        else:
            print(f"\n[ERROR] An unexpected validation or API error occurred: {e}")
            return None


if __name__ == "__main__":
    pass