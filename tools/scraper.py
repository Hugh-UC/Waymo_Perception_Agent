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

def scrape_reddit_sentiment(subreddit: list[str] | None = None) -> str:
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

 
if __name__ == "__main__":
    # quick test block to ensure it works when you run this file directly
    days_back : float | int = config['scraper']['news']['days_back']

    print(f"Testing News Scraper (Fetching last {get_search_time_str(days_back)})...\n")
    news_data = scrape_waymo_news()
    print(news_data)
    
    print("\nTesting Mock Reddit Scraper...\n")
    reddit_data = scrape_reddit_sentiment()
    print(reddit_data)