"""
File: scraper.py
Title: Media Scraper Tool
Description: Handles the data ingestion pipeline, pulling unstructured text from NewsAPI, Reddit, and other web crawling APIs, based on YAML configurations.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""
from googleapiclient.discovery import build
from duckduckgo_search import DDGS
import os
import time
import yaml
import requests
from typing import Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
# Package Imports
from core.utils import get_search_time_str

# load the API keys from '.env' file
load_dotenv()
GEMINI_API_KEY : str | None     = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY : str | None       = os.getenv("NEWS_API_KEY")
GCS_API_KEY : str | None        = os.getenv("GCS_API_KEY")
GCS_CX_ID : str | None          = os.getenv("GCS_CX_ID")
YOUTUBE_API_KEY : str | None    = os.getenv("YOUTUBE_API_KEY")

# load parameter configuration from 'yaml'
with open("config/params.yaml", "r") as file:
    config = yaml.safe_load(file)


# ---------------------------------------------------------
# News/Forums Scraping Engine
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Hybrid Social Media Scraping Engine
# ---------------------------------------------------------

def scrape_social_via_ddg(query : str, platform : str, max_results : int = 5) -> str:
    """
    Universal keyless fallback scraper using DuckDuckGo.

    Args:
        query (str): subject to search for.
        platform (str): target domain to restrict the search to.
        max_results (int, optional): maximum number of search results to retrieve. defaults to 5.

    Returns:
        str: compiled string of search result titles and snippets.
    """
    search_query : str = f"site:{platform} {query}"
    compiled_data : str = f"--- SCRAPED FROM {platform.upper()} (VIA DDG) ---\n"
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=max_results))
            if not results: return compiled_data + "No results found.\n"
            
            for res in results:
                compiled_data += f"Title: {res.get('title', 'Unknown')}\n"
                compiled_data += f"Snippet: {res.get('body', 'No description available.')}\n\n"

        return compiled_data
    
    except Exception as e:
        print(f"[DDG Fallback Error] {platform}: {e}")
        return compiled_data + "Failed to retrieve data.\n"


def scrape_social_via_gcs(query : str, platform : str, max_results : int = 5) -> str:
    """
    Primary scraper using Google Custom Search API.

    Args:
        query (str): subject to search for.
        platform (str): target domain to restrict the search to.
        max_results (int, optional): maximum number of search results to retrieve. defaults to 5.

    Raises:
        ValueError: if GCS_API_KEY or GCS_CX_ID is missing from the environment.

    Returns:
        str: compiled string of search result titles and snippets from the GCS API.
    """
    if not GCS_API_KEY or not GCS_CX_ID:
        raise ValueError("GCS Keys missing.")

    search_query : str = f"site:{platform} {query}"
    compiled_data : str = f"--- SCRAPED FROM {platform.upper()} (VIA GCS API) ---\n"
    
    service = build("customsearch", "v1", developerKey=GCS_API_KEY, cache_discovery=False)
    res = service.cse().list(q=search_query, cx=GCS_CX_ID, num=max_results).execute()
    
    items = res.get('items', [])
    if not items: return compiled_data + "No results found.\n"
    
    for item in items:
        compiled_data += f"Title: {item.get('title', 'Unknown')}\n"
        compiled_data += f"Snippet: {item.get('snippet', 'No description available.')}\n\n"
        
    return compiled_data


def scrape_youtube_api(query : str, max_results : int = 5) -> str:
    """
    Primary scraper for YouTube using the official Data API v3.

    Args:
        query (str): subject to search for on youtube.
        max_results (int, optional): maximum number of videos to retrieve. defaults to 5.

    Raises:
        ValueError: if YOUTUBE_API_KEY is missing from the environment variables.

    Returns:
        str: compiled string of YouTube video titles, statistics, and descriptions.
    """
    if not YOUTUBE_API_KEY:
        raise ValueError("YouTube API Key missing.")

    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, cache_discovery=False)
    compiled_data : str = "--- SCRAPED FROM YOUTUBE (OFFICIAL API) ---\n"

    search_res = youtube.search().list(q=query, part='id,snippet', maxResults=max_results, type='video', order='date').execute()
    video_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
    
    if not video_ids: return compiled_data + "No recent videos found.\n"

    stats_res = youtube.videos().list(part='statistics,snippet', id=','.join(video_ids)).execute()

    for item in stats_res.get('items', []):
        snip = item['snippet']
        stat = item.get('statistics', {})
        compiled_data += f"Title: {snip['title']}\n"
        compiled_data += f"Views: {stat.get('viewCount', '0')} | Likes: {stat.get('likeCount', '0')}\n"
        compiled_data += f"Description: {snip['description'][:200]}...\n\n"

    return compiled_data

# --- The Orchestrators ---
def scrape_social_hybrid(query : str, platform : str, max_results : int = 5) -> str:
    """
    Attempts GCS API, gracefully degrades to DDG on failure.

    Args:
        query (str): subject to search for.
        platform (str): target domain to restrict the search to.
        max_results (int, optional): maximum number of search results to retrieve. Defaults to 5.

    Returns:
        str: compiled data string from either the GCS API or the DDG fallback.
    """
    try:
        return scrape_social_via_gcs(query, platform, max_results)
    except Exception as e:
        print(f"    -> [Fallback Triggered] GCS failed for {platform} ({e}). Using DDG...")
        return scrape_social_via_ddg(query, platform, max_results)


def scrape_youtube_hybrid(query: str, max_results: int = 5) -> str:
    """
    Attempts Official YT API, gracefully degrades to DDG on failure.

    Args:
        query (str): subject to search for.
        max_results (int, optional): maximum number of videos to retrieve. Defaults to 5.

    Returns:
        str: compiled data string from either the official YouTube API or the DDG fallback.
    """
    try:
        return scrape_youtube_api(query, max_results)
    except Exception as e:
        print(f"    -> [Fallback Triggered] YouTube API failed ({e}). Using DDG...")
        return scrape_social_via_ddg(query, "youtube.com", max_results)


# ---------------------------------------------------------
# Metrics Calculations
# ---------------------------------------------------------

def calculate_relatability(views : int, likes : int, comments : int, shares : int) -> float:
    """
    Calculates Relatability based on industry-standard engagement weighting.
    Shares (High Intent) > Comments (Medium Intent) > Likes (Low Intent).
    Returns a normalized score between 0.0 and 1.0.

    Args:
        views (int): total number of times the video has been viewed.
        likes (int): total number of likes the video received.
        comments (int): total number of comments on the video.
        shares (int): total number of times the video was shared.

    Returns:
        float: normalized engagement score between 0.0 and 1.0.
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