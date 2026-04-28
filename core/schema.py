"""
File: schema.py
Title: Waymo Perception Metrics Schema
Description: Defines the strict Pydantic data models used to enforce structured JSON output from the Gemini LLM.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date

class PerceptionMetrics(BaseModel):
    """
    The strict schema the AI must use when extracting metrics from a single media source.

    Args:
        BaseModel (BaseModel): Pydantic foundation class used to enforce data 
                               validation and strict JSON schema adherence for 
                               the Gemini AI agent.
    """
    # metadata
    scrape_date : date = Field(description="The date the article or post was published.")
    source_type : Literal["News", "Reddit", "Twitter", "Other"] = Field(description="Where the text came from.")
    location : str = Field(description="Geographic location mentioned, or 'Unknown'.")
    
    # core temporal metrics
    sentiment_polarity : float = Field(
        ge=-1.0, le=1.0, 
        description="Overall emotional tone. -1.0 is angry/negative, 1.0 is thrilled/positive."
    )
    safety_perception_score : int = Field(
        ge=1, le=10, 
        description="1 = Believes Waymo is dangerous. 10 = Believes Waymo is perfectly safe."
    )
    technological_optimism : Literal["Pessimistic", "Neutral", "Optimistic", "Inspired"] = Field(
        description="The author's general outlook on autonomous future."
    )
    
    # specific friction/utility
    primary_friction_point : Literal["None", "Traffic Blockage", "Job Displacement", "Safety/Creepiness", "Cost", "Other"] = Field(
        description="The main complaint or fear mentioned."
    )
    utility_score : Optional[int] = Field(
        default=None, ge=1, le=10, 
        description="If the person actually rode in a Waymo, rate their satisfaction 1-10. Null if they are just a bystander."
    )

    # narative metrics
    platform : str = Field(
        default="unknown",
        description="The social media or news platform the post originated from (e.g., 'reddit', 'tiktok', 'news')."
    )
    relatability_score : float = Field(
        default=0.0,
        description="Calculated engagement metric (0.0 to 1.0)."
    )
    individuality_score : float = Field(
        default=0.0,
        description="Calculated poster uniqueness metric (0.0 to 1.0)."
    )

class ScrapeBatch(BaseModel):
    """
    The final output for a daily run, containing a list of individual perception metrics.

    Args:
        BaseModel (BaseModel): Pydantic foundation class used to facilitate 
                               serialization of multiple media sources into a 
                               single, structured database entry.
    """
    run_date : date
    total_sources_analyzed : int
    metrics : list[PerceptionMetrics]


class TrendingNarrative(BaseModel):
    """
    Schema representing a single macro-narrative synthesized from multiple isolated posts.

    Args:
        BaseModel (BaseModel): Pydantic foundation class used to facilitate 
                               serialization of multiple media sources into a 
                               single, structured database entry.
    """
    title: str = Field(
        description="Headline of the Trend"
    )
    location: str = Field(
        description="City, State (or 'Global')"
    )
    synopsis: str = Field(
        description="A 2-sentence summary of what happened and the public's reaction."
    )
    future_impact: str = Field(
        description="Potential regulatory, PR, or technical consequences."
    )
    sentiment_label: Literal["Positive", "Negative", "Neutral", "Mixed"] = Field(
        description="Overall sentiment trend of this specific narrative."
    )
    first_seen_date: str = Field(
        description="The YYYY-MM-DD date of the earliest post involved in this trend."
    )

class NarrativeBatch(BaseModel):
    """
    Container for a batch of trending narratives, enforcing list structure.
    """
    narratives: list[TrendingNarrative] = Field(
        description="List of synthesized trending narratives."
    )