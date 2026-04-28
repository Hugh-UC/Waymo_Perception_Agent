# Project Roadmap | Multi-Modal Intelligence Synthesizer

## Current Sprint: Phase 3 (Social Media & Video Integration)
**Objective:** Expand scraping capabilities beyond News/Reddit to include high-fidelity video platforms without incurring massive API costs.

* **Hybrid YouTube Scraper:** Implement a graceful degradation model. Attempt to use the official YouTube Data API v3 first for deep metadata (likes, views, comments). If the user hasn't provided a key or the quota fails, seamlessly fall back to DuckDuckGo search parsing.
* **Hostile Platform Bypassing:** Implement DuckDuckGo Search (`site:tiktok.com` and `site:instagram.com/reel`) to bypass anti-bot walls (Cloudflare/Login-walls) for TikTok and Instagram, extracting video snippets and links for the AI.
* **UI Settings Integration:** Update `setup.html` and `settings.html` to allow users to securely input optional API keys for YouTube and Google Custom Search, enabling progressive enhancement of the scraper.

## Future Sprint: Phase 4 (Advanced Data Visualization)
**Objective:** Overhaul the `analytics.html` dashboard to support massive datasets without performance drops.

* **Dynamic Data Chunking:** Refactor the backend API and Chart.js frontend to dynamically request specific date ranges (e.g., "Last 60 Days", "Custom Range") rather than loading the entire database at once, preserving HTML/Python performance.
* **Keyword Sentiment Graphic:**
    * Generate an interactive graphic where keywords are enveloped by shared sentiment groupings (e.g., positive, negative, frustrated).
    * Keywords are sized dynamically based on their frequency of occurrence.
    * Semantic clustering: The AI merges highly similar keywords to prevent UI clutter.
    * Visual design: Semi-translucent, pastel-colored circles that can be toggled on/off by the user.

## Future Sprint: Phase 5 (Source Weighting & Trust Architecture)
**Objective:** Introduce transparent bias control and reliability scoring for incoming data.

* **Custom Weighting Engine:** Implement adjustable metrics (e.g., `relatability_score`, `individuality_score`) to down-weight low-effort posts or spam accounts.
* **Reliability Meta-Agent:** Create a new asynchronous PydanticAI Agent whose sole job is to evaluate the historical reliability of specific domains (e.g., major news networks vs. niche blogs) and assign a "Trust Weight".
* **Transparency UI:** Build a new "Sources" dashboard where users can view exactly how the AI weighted specific domains and manually override the Trust Weight if desired.
* **LangGraph Integration (Optional):** Explore using `langgraph` to facilitate cyclic debates between the Perception Agent and the Reliability Agent to reach a consensus on highly controversial articles.