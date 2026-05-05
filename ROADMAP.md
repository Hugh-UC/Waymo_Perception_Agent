# Project Roadmap | Multi-Modal Intelligence Synthesizer

## Table of Contents

- [Project Backlog & Future Epics (Unscheduled)](#-project-backlog--future-epics-unscheduled)
- [Project Sprints](#project-sprints)
  - [🏃‍♂️ Sprint 5](#️-sprint-5-dynamic-architecture--agentic-data-quality-current)
  - [🏁 Sprint 4](#-sprint-4-dashboard-foundation--export-automation-completed-april-29---may-2)
  - [🏁 Sprint 3](#-sprint-3-social-media--video-integration-completed-april-28)

---

## 📋 Project Backlog & Future Epics (Unscheduled)

### 1. Architecture & Tech Debt
* **ES6 Module Migration:** Transition the frontend from global scope class declarations to modern ES6 module imports (`import { ChartRenderer } from './tools/ChartRenderer.js'`). This will clean the global namespace, clarify dependencies, and allow modern build tools to optimize the code. Requires updating all `.js` files and HTML `<script type="module">` tags.
* **Dynamic Data Chunking:** Refactor the backend API and Chart.js frontend to dynamically request specific date ranges (e.g., "Last 60 Days", "Custom Range") rather than loading the entire database into memory, preserving HTML/Python performance as the database scales.
* **Employee AI Token & Queue System:** Implement a token-based rate limiting and priority system for enterprise users. Managers can assign token quotas to employees to limit scraping sizes/requests, and VIP users can be assigned priority status to jump ahead in the scraping pipeline queue. Requires database schema upgrades and UI management panels.

---

### 2. UI / UX Overhaul
* **User Profile & Settings Unification:** Move Settings to a dedicated User Profile menu (accessed via a top-right circular avatar icon). Relocate the dark/light mode theme toggle into this menu.
* **Advanced Theme Preferences:** Build a 'My Preferences' panel allowing users to define predefined color palettes, create custom themes, and adjust text/font sizes globally.
* **Global Notification Center:** Expand `NotificationManager` into a persistent slide-out panel or overlay to log background system events and pipeline completions.
* **Dynamic HTML Error Pages:** Parameterize `error.html` to dynamically display specific HTTP status codes (404, 500) and detailed descriptions injected by FastAPI.
* **Secure Access Restrictions:** Ensure full frontend routing blocks unauthenticated access via `api.js` and `app.py`.

---

### 3. Advanced Visualizations
* **Keyword Sentiment Graphic:** 
    * Develop an interactive visual where keywords are enveloped by shared sentiment grouping circles (positive, negative, frustrated, etc.).
    * Groupings auto-generate based on best-fit categories.
    * Circle visuals: Semi-translucent, pastel-colored, toggleable.
    * Keyword sizing dynamically scales based on database frequency.
    * Implement semantic clustering: AI merges highly similar keywords to prevent UI clutter.
* **Custom Graph Builder:** Allow users to define new graphs dynamically from the UI, mapping database columns to specific graph types without writing JSON manually.

---

### 4. AI & Agent Upgrades
* **Prompt Developer Agent:** Create a dedicated AI agent to help users develop prompts for the system, ensuring scalability and strict output formatting when transitioning the software to analyze companies other than Waymo.
* **Source Weighting & Reliability Meta-Agent (Trust Architecture):**
    * Introduce transparent bias control and reliability scoring for incoming data.
    * Implement adjustable metrics (`relatability_score`, `individuality_score`) to down-weight low-effort posts or spam.
    * Build an asynchronous PydanticAI / LangGraph Agent to evaluate historical reliability of domains and assign a "Trust Weight".
    * Build a "Sources" UI dashboard for transparency and manual weight overrides.
* **Agnostic LLM Provider Integration:** Refactor the codebase to transition from hardcoded 'Gemini' references to a generalized 'Model Provider' architecture using PydanticAI. The tool should support any modern LLM API (OpenAI, Anthropic, local models) to ensure enterprise flexibility.

---

### 5. Database & Auth Tweaks
* **Master Admin Security:** Update database schema so the Master Admin ID = 0 (primary key starts at 0). Update user deletion logic to block deletion of ID 0 instead of 1.

---

## Tool Extensions (Extensions/Plugins)

### Legal Extension
* **Future Client Management Portal Intergration:** This implementation will include refactoring the code as a plugin for a pre-existing (yet to me created) client management portal program developed specifically for the Australian legal system (future: global legal system). It will introduce:
    * Legislation validation against scraping for potential new legal cases.
    * Greater Agent checks (for legal president) when scraping new cases.
    * Suggested Client base generators.
    * Suggested advertisement avenues.
    * Advertisement campaign success metrics.
    * New Potential Cases finder (using AI agents).
    * Data analytics, normalisation, organisation, representation, and exportation.
    * More to come...

---

<br>
<br>

# Project Sprints

## 🏃‍♂️ Sprint 5: Dynamic Architecture & Agentic Data Quality (Current)
**Objective:** Decouple the frontend/backend rendering engines, normalize fragmented database entities, and repair the scraping pipeline for video platforms.

* **[COMPLETED] Epic 1: The Dynamic Graph Engine (Tech Debt)**
    * Audited and cleaned JS/Python files to remove hardcoded logic.
    * Extracted rendering logic to decoupled `graphs.json`.
    * Built dynamic `ChartRenderer.js` and modularized `settings.js` using Domain Managers and the Configuration Object Pattern.
    * *Files Changed:* `settings.js`, `api.js`, `utils.js` (Created), `ChartRenderer.js`, `graphs.json`, `app.py`, `export.py`, `graph.py`.
* **[IN PROGRESS] Epic 2: Database Normalization**
    * Write a Python script to sweep the SQLite database and merge fragmented entities (e.g., merging "London" and "London, UK" via LLM entity resolution).
* **[PLANNED] Epic 3: LangGraph Validation Integration**
    * Restructure AI extraction logic into a LangGraph pipeline.
    * Create a "Validator Node" to enforce data uniformity before new scraped data enters the database.
* **[PLANNED] Epic 4: Scraper Engine Overhaul (The Fix)**
    * **Issue:** TikTok and Instagram Reels scraping is currently broken or improperly relegated to the narrative meta-agent.
    * **Solution:** Implement the "Search Engine Bypass" (via `duckduckgo_search` or Google Custom Search) to bypass Cloudflare/login-walls for `site:tiktok.com` and `site:instagram.com/reel`. Ensure the Perception Agent properly ingests these as primary data sources.

---

## 🏁 Sprint 4: Dashboard Foundation & Export Automation (Completed ~April 29 - May 2)
**Objective:** Establish a robust FastAPI backend, introduce AI prompt assistance, and automate the generation of presentation-ready exports.

* **Dynamic Routing & Security:** Built API interceptors to restrict page access until logged in, and implemented parameterized dynamic HTML error pages (`error.html` handles 404, 500).
* **Setup Wizard Refactor:** Updated the Boot Manager architecture from Sprint 3 to implement best practices and align with the new routing configurations.
* **Dynamic Data Chunking:** Refactored the backend API and frontend JS to dynamically request specific date ranges (defaulting to 60 days) to preserve memory and performance.
* **Automated Exporter:** Built a Python pipeline to generate flat CSVs and high-resolution (SVG/PNG) Matplotlib/Seaborn graphics for executive reporting.
* *Files Changed:* `export.py` (Created), `graph.py` (Created), `export.html` (Created), `export.js` (Created), `error.html` (Created), `app.py`, `analytics.js`, `settings.js`.

---

## 🏁 Sprint 3: Social Media & Video Integration (Completed ~April 28)
**Objective:** Expand scraping capabilities to include high-fidelity video platforms and establish baseline authentication.

* **System Setup Wizard:** Created a dynamic Boot Manager to intercept unconfigured states and guide users through API key input and admin creation.
* **Auth Architecture:** Implemented secure SHA-256 password hashing and session management.
* **Hybrid YouTube Scraper:** Implemented a graceful degradation model in `scraper.py`. Attempts the official YouTube Data API v3 for deep metadata; falls back to DuckDuckGo search parsing if quota fails or keys are missing.
* **UI Settings Integration:** Updated `setup.html` and `settings.html` to allow users to securely input optional API keys for YouTube and Google Custom Search.
* *Files Changed:* `auth.js` (Created), `auth_db.py` (Created), `auth-modals.html` (Created), `setup.html`, `settings.html`, `scraper.py`, `app.py`.