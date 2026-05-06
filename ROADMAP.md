# Project Roadmap | Multi-Modal Intelligence Synthesizer

## Table of Contents

- [Project Backlog & Future Epics (Unscheduled)](#-project-backlog--future-epics-unscheduled)
- [Project Sprints](#project-sprints)
    - [📅 Sprint 6](#-sprint-6-data-normalization--scraping-overhaul-planned) 
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

### 6. Security & Communications
* **Security Code Overhall:** Combe through every project file. Identify potential security risk and patch.
* **Error Handling:** Ensure that all potentail errors are caught and handled gracefully by the code base.
* **Page Routing:** Update page routing for firmer page control logic. Ensure backend is not vaulernerable to injection attacks.
* **Input Validation:** Unify validation code into a utility. Apply validation to any input received by backend.
* **Passwords & Recovery:** Add two-factor authentication:
    * Authenticator Apps,
    * PassKeys (Biometric Authentication),
    * Email/Text,
        * _Email_: Build email tool to utilise for authentication (General Email Module w/ two-factor specific methods).
        * _Text_: Requires paid SMS API (i.e. Twilio, Telesign, or ClickSend).
* **Email Module:** Python module for handling email sending and receiving. The sending system will rely on templates and defined themes (`theme.css`) to structure emails before they are dynamically populated. Email receiving will be a filtered system, it will not populate all the users emails, any email generated by the code base (and receieved by the user in this code base) should be tagged. The retreiving system will filter for this flag, populating the front end with only _'tagged'_ emails.
    * Requries additional setting panel for setting up user email (send/receive).
    * Installation/Importing new tools: `IMAP: imaplib, POP3: poplib, email`.
    * App Password or IMAP or POP3 enabling instructions for user.
    * Service accounts with: `Gmail API` or `Microsoft Graph`?
        * Set up program specific company email.
        * Used for sending compiled or formalised reports (i.e. weekly scraping results), maintanence warnings, password reset emails, etc.
        * No-reply emails.
        * Non-polling system, can wait for pushed emails to notify user.

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

## 📅 Sprint 6: Data Normalization & Scraping Overhaul (Planned)
**Objective:** Repair broken scraping pipelines, enforce strict data uniformity, and resolve fragmented database entities.
* **[PLANNED] Epic 1: Database Normalization**
    * Write a Python script to sweep the SQLite database and merge fragmented entities (e.g., merging "London" and "London, UK" via LLM entity resolution).
* **[PLANNED] Epic 2: LangGraph Validation Integration**
    * Restructure AI extraction logic into a LangGraph pipeline.
    * Create a "Validator Node" to enforce data uniformity before new scraped data enters the database.
* **[PLANNED] Epic 3: Scraper Engine Overhaul (The Fix)**
    * **Issue:** TikTok and Instagram Reels scraping is currently broken or improperly relegated to the narrative meta-agent.
    * **Solution:** Implement the "Search Engine Bypass" (via `duckduckgo_search` or Google Custom Search) to bypass Cloudflare/login-walls for `site:tiktok.com` and `site:instagram.com/reel`. Ensure the Perception Agent properly ingests these as primary data sources.

---

## 🏃‍♂️ Sprint 5: Dynamic Architecture & Agentic Data Quality (Current)
**Objective:** Decouple the frontend/backend rendering engines, transition the entire JS architecture to strict ES6 modules, and finalize enterprise-grade frontend controllers.

* **[IN PROGRESS] Epic 1: The Dynamic Graph Engine (Tech Debt)**
    * Audited and cleaned JS/Python files to remove hardcoded logic.
    * Extracted rendering logic to decoupled `graphs.json`.
    * Built dynamic `ChartRenderer.js` and modularized `settings.js` using Domain Managers and the Configuration Object Pattern.
    * *Files Changed:* `settings.js`, `api.js`, `utils.js` (Created), `ChartRenderer.js`, `graphs.json`, `app.py`, `export.py`, `graph.py`.
    * Still awaiting auditing of remaining Python, CSS, and HTML files.
* **[IN PROGRESS] Epic 2: ES6 Module & OOP Migration**
    * Transitioned the entire frontend from global `window` scopes to modern ES6 module imports.
    * Unified all procedural controllers (`export.js`, `api.js`) into strict static classes for architectural consistency.
    * Implemented `boot.js` as the global security gatekeeper and execution orchestrator.
    * Ensure all `.js` files are consistantly and thoroughly well documented, including:
        * JSDocs,
        * Code Comments, and
        * File Headers/Documentation Headers
* **[IN PROGRESS] Epic 3: Self-Healing Utilities**
    * Refactored `NotificationManager` into a highly dynamic, queue-based, and self-healing UI utility with custom interactive buttons, CSS-driven timeouts, and full DOM overlay blocking.
    * Refactor all `.js` files to ensure code extensability, SOC, and that all hardcoded elements are removed. They are either found by the code or populated from a `.json` template.

---

## 🏁 Sprint 4: Dashboard Foundation & Export Automation (Completed ~April 29 - May 2)
**Objective:** Establish a robust FastAPI backend, introduce AI prompt assistance, and automate the generation of presentation-ready exports.

* **[COMPLETED] Dynamic Routing & Security:** Built API interceptors to restrict page access until logged in, and implemented parameterized dynamic HTML error pages (`error.html` handles 404, 500).
* **[COMPLETED] Setup Wizard Refactor:** Updated the Boot Manager architecture from Sprint 3 to implement best practices and align with the new routing configurations.
* **[COMPLETED] Dynamic Data Chunking:** Refactored the backend API and frontend JS to dynamically request specific date ranges (defaulting to 60 days) to preserve memory and performance.
* **[COMPLETED] Automated Exporter:** Built a Python pipeline to generate flat CSVs and high-resolution (SVG/PNG) Matplotlib/Seaborn graphics for executive reporting.
* *Files Changed:* `export.py` (Created), `graph.py` (Created), `export.html` (Created), `export.js` (Created), `error.html` (Created), `app.py`, `analytics.js`, `settings.js`.

---

## 🏁 Sprint 3: Social Media & Video Integration (Completed ~April 28)
**Objective:** Expand scraping capabilities to include high-fidelity video platforms and establish baseline authentication.

* **[COMPLETED] System Setup Wizard:** Created a dynamic Boot Manager to intercept unconfigured states and guide users through API key input and admin creation.
* **[COMPLETED] Auth Architecture:** Implemented secure SHA-256 password hashing and session management.
* **[COMPLETED] Hybrid YouTube Scraper:** Implemented a graceful degradation model in `scraper.py`. Attempts the official YouTube Data API v3 for deep metadata; falls back to DuckDuckGo search parsing if quota fails or keys are missing.
* **[COMPLETED] UI Settings Integration:** Updated `setup.html` and `settings.html` to allow users to securely input optional API keys for YouTube and Google Custom Search.
* *Files Changed:* `auth.js` (Created), `auth_db.py` (Created), `auth-modals.html` (Created), `setup.html`, `settings.html`, `scraper.py`, `app.py`.