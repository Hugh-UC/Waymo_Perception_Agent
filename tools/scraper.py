"""
File: scraper.py
Title: Media Scraper Tool
Description: Handles the data ingestion pipeline, pulling unstructured text from NewsAPI and Reddit based on YAML configurations.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""

import os
import yaml
import requests
from typing import Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
# Package Imports
from core.utils import get_search_time_str

# load the API keys from '.env' file
load_dotenv()
NEWS_API_KEY : str | None = os.getenv("NEWS_API_KEY")

# load parameter configuration from 'yaml'
with open("config/params.yaml", "r") as file:
    config = yaml.safe_load(file)


def scrape_waymo_news() -> str:
    """
    Fetches recent news articles mentioning Waymo using NewsAPI.

    Raises:
        ValueError: when NEWS_API_KEY is not found.

    Returns:
        str: compiled string of titles and summaries.
    """
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY is missing from the .env file.")
    
    # pull parameters from config
    news_cfg : dict[str, Any]   = config['scraper']['news']
    query : str                 = news_cfg['query']
    days_back : float | int     = news_cfg['days_back']
    max_articles : int          = news_cfg['max_articles']

    # calculate the date range for the search
    from_date : str = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    url : str = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&"
        f"from={from_date}&"
        f"sortBy=relevancy&"
        f"language=en&"
        f"apiKey={NEWS_API_KEY}"
    )

    try:
        response : requests.Response = requests.get(url)
        response.raise_for_status()     # throws error if web request fails
        data : dict[str, Any] = response.json()
        
        # grab the most relevant articles
        articles : list[dict[str, Any]] = data.get("articles", [])[:max_articles]
        
        if not articles:
            return f"No recent news articles found for {query}."

        # compile article text
        compiled : str = f"SOURCE: News Media (Query: {query})\n\n"
        for article in articles:
            # Headline
            title : str = article.get("title", "No Title")

            # Source
            source : str = article.get("source", {}).get("name", "Unknown Source")

            # Summary
            desc : str = article.get("description", "") or "No description available."
            desc = " ".join(desc.split()).strip()     # .replace('\n', ' ').replace('\r', ' ').strip()
            
            # Compiled
            compiled += f"Headline: {title}\nSource: {source}\nSummary: {desc}\n---\n"
            
        return compiled

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return ""


def scrape_reddit_sentiment(subreddit : list[str] | None = None) -> str:
    """
    Fetches recent posts and comments from Reddit.
    Subreddit parameter is pulled from config.yaml.

    Args:
        subreddit (list[str], optional): subreddit(s) to target.

    Returns:
        str: compiled string of fetched content.
    """
    reddit_cfg : dict[str, Any] = config['scraper']['reddit']
    subreddits : list[str]      = reddit_cfg.get('subreddit', [])
    max_posts : int             = reddit_cfg.get('max_posts', 10)
    
    compiled_data : str = "SOURCE: Reddit\n\n"

    # bypass 429 error: reddit blocks python's default user-agent
    headers = {'User-Agent': 'WaymoPerceptionAgent/1.0 (Data Pipeline)'}

    for sub in subreddits:
        compiled_data += f"--- Location: r/{sub} ---\n"
        url = f"https://www.reddit.com/r/{sub}/search.json?q=waymo&restrict_sr=on&sort=new&limit={max_posts}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            posts = response.json().get('data', {}).get('children', [])
            
            for i, post in enumerate(posts):
                post_data = post['data']
                title = post_data.get('title', '')
                text = post_data.get('selftext', '').replace('\n', ' ')
                
                # cap extremely long reddit posts to save LLM tokens
                if len(text) > 1000: text = text[:1000] + "..."
                
                compiled_data += f"Post {i+1}: {title}\nContent: {text}\n\n"
                
        except Exception as e:
            compiled_data += f"[Error fetching r/{sub}: {e}]\n\n"
            
    return compiled_data


def scrape_video_platforms(query : str, days_back : int) -> list[dict]:
    """
    Pipeline ready to receive TikTok/IG Playwright or API JSON.

    Args:
        query (str): _description_
        days_back (int): _description_

    Returns:
        list[dict]: _description_
    """
    scraped_reels = []
    # --- FUTURE API CALL GOES HERE ---
    
    # Example structured output the AI expects:
    mock_reel = {
        "platform": "tiktok",
        "content_text": "Self driving car just stopped in the middle of the intersection!",
        "relatability_score": calculate_relatability(views=10000, likes=1200, comments=45, shares=200),
        "individuality_score": calculate_individuality(account_total_posts=300, waymo_specific_posts=2),
        "timestamp": "2026-04-26T14:30:00Z"
    }
    scraped_reels.append(mock_reel)
    return scraped_reels


def calculate_relatability(views : int, likes : int, comments : int, shares : int) -> float:
    """
    Calculates Relatability based on industry-standard engagement weighting.
    Shares (High Intent) > Comments (Medium Intent) > Likes (Low Intent).
    Returns a normalized score between 0.0 and 1.0.

    Args:
        views (int): _description_
        likes (int): _description_
        comments (int): _description_
        shares (int): _description_

    Returns:
        float: _description_
    """
    if views == 0: return 0.0
    
    # weighted engagement formula
    weighted_engagement : float = (likes * 1) + (comments * 2.5) + (shares * 4)
    raw_score : float           = weighted_engagement / views
    
    # normalize to 0.0 -> 1.0 scale (assuming a 15% engagement rate is 'viral' / 1.0)
    normalized = min(raw_score / 0.15, 1.0)
    return round(normalized, 3)


def calculate_individuality(account_total_posts : int, waymo_specific_posts : int) -> float:
    """
    Calculates Individuality (Is this an organic poster or a dedicated Waymo-spam account?).
    1.0 = Highly Individual (First time poster). 0.0 = Dedicated Spam/Shitposter.

    Args:
        account_total_posts (int): total number of posts made by user account.
        waymo_specific_posts (int): number of posts specifically mentioning Waymo.

    Returns:
        float: normalized individuality score between 0.0 and 1.0.
    """
    if account_total_posts == 0: return 1.0
    
    saturation_ratio : float = waymo_specific_posts / account_total_posts
    individuality : float    = 1.0 - saturation_ratio      # invert the ratio (high saturation = low individuality)

    return round(individuality, 3)

 
if __name__ == "__main__":
    # quick test block to ensure it works when you run this file directly
    days_back : float | int = config['scraper']['news']['days_back']

    print(f"Testing News Scraper (Fetching last {get_search_time_str(days_back)})...\n")
    news_data = scrape_waymo_news()
    print(news_data)
    
    print("\nTesting Mock Reddit Scraper...\n")
    reddit_data = scrape_reddit_sentiment()
    print(reddit_data)