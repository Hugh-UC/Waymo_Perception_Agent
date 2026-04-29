# The Waymo Perception Agent Project (Gemini AI)

A Python-based AI agent utilizing `PydanticAI` and the Gemini API to scrape media sites (News, Reddit, YouTube, Social Media) and generate structured temporal metrics and macro-narratives on autonomous vehicle perception.

The system architecture connects a multi-tiered data collection pipeline with a web-based interface. A FastAPI backend serves as the core engine, orchestrating requests between the frontend UI, local SQLite databases, and external data collection tools. Administrators interact with the system entirely through a dashboard built natively with HTML, CSS, and Vanilla JavaScript (Chart.js). This frontend provides system monitoring, configuration management via a dynamic setup wizard, and secure local authentication.

Under the hood, the Python orchestrator handles the backend execution—triggering the scraping modules, managing API rate limits with dynamic model fallback cascades, and enforcing strict JSON schema validation on the Gemini AI outputs. A secondary "Meta-Agent" automatically reviews historical metrics to synthesize real-time trending narratives.

***

### Release (v0.1)

***

## Table of Contents

- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
  - [Create Project Virtual Environment](#create-project-virtual-environment)
    - [1. Build Virtual Environment](#1-build-virtual-environment)
    - [2. Source Virtual Environment](#2-source-virtual-environment)
    - [3. Update Execution Policy](#3-update-execution-policy)
    - [4. Install Requirements](#4-install-requirements)
    - [Install the Package](#install-the-package)
    - [5. API Keys & Local Files](#5-api-keys--local-files)
    - [6. Running the Server](#6-running-the-server)
- [Operating Web Interface](#operating-web-interface)
  - [Initial System Setup](#initial-system-setup)
  - [Expanding the Frontend](#expanding-the-frontend)

***

## Directory Structure

```
waymo_perception_agent/
│
├── config/
│   ├── params.yaml         # Master configuration
│   ├── roles.json          # User permisions configuration
│   └── models.base.json    # Base model configuration (For intial setup/reset)
│
├── core/
│   ├── __init__.py
│   ├── schema.py           # Pydantic models (Metrics definitions)
│   ├── agent.py            # PydanticAI agent initialization
│   ├── system_check.py     # System Integrity & Auto-Recovery Engine
│   └── utils.py            # Helper functions
│
├── tools/
│   ├── __init__.py
│   ├── scraper.py          # Logic for Reddit/News API pulling
│   ├── export.py           # CSV/SVG generation and data export
│   ├── db.py               # Logic for saving JSON/Metrics to your DB
│   └── auth_db.py          # SQLite authentication and user management
│
├── visualization/
│   ├── __init__.py
│   └── (FUTURE DEV)
│
├── frontend/               # All web assets live here
│   ├── css/
│   │   ├── style.css       # Structural layout and responsive media queries
│   │   └── theme.css       # Dark/Light mode, color variables, and alt theme styles
│   ├── js/
│   │   ├── api.js          # Global API SDK and routing Gatekeeper
│   │   ├── auth.js         # Setup Wizard, login state, and password validation
│   │   ├── analytics.js    # Data visualisation and Chart.js controller
│   │   ├── datalist.js     # Dynamic UI lists and table population
│   │   └── settings.js     # UI validation for the YAML parameters
│   ├── index.html          # Dashboard, Login Overlay, and Setup Wizard
│   ├── analytics.html      # Data visualization and narrative dashboard
│   ├── settings.html       # System Configuration Editor
│   ├── prompt.html         # Prompt Editor
│   ├── export.html         # CSV/Excel/PNG Exporter
│   └── error.html          # Custom error routing page
│
├── server/                 # Your new backend bridge
│   └── app.py              # The FastAPI server
│
├── .env                    # API keys (Gemini, News, Reddit)
├── main.py                 # Entry point to run the daily job
├── requirements.txt        # Dependencies (langgraph, pydantic-ai, google-genai, etc.)
│
├── README.md               # Project Descriptor and Guide
├── ROADMAP.md              # Project Roadmap for future features
├── AI_DISCLOSURE.md        # Academic integrity disclosure
├── LICENSE                 # Apache 2.0 open-source license
└── .gitignore              # Excludes sensitive files (.env) and virtual environments (venv/)
```

***

## Program Flow
```
[ FRONTEND UI ]                                [ BACKEND & PIPELINE ]
      │                                                  │
 1. User Clicks ─────────(HTTP)─────────► app.py (FastAPI Server)
   "Run Scraper"                                         │
                                                         ▼
                                          main.py (The Orchestrator)
                                                         │
                                                         ├─► 2. tools/scraper.py
                                                         │      (Pulls Raw Text & Video Metadata)
                                                         │
                                                         ├─► 3. core/agent.py (Perception Agent)
                                                         │      (Turns Raw Text ➔ JSON Metrics)
                                                         │
                                                         ├─► 4. tools/db.py (save_metrics)
                                                         │      (Saves JSON ➔ SQLite)
                                                         │
                                                         ├─► 5. tools/db.py (get_historical_metrics)
                                                         │      (Pulls last 7 days of SQLite data)
                                                         │
                                                         ├─► 6. core/agent.py (Narrative Agent)
                                                         │      (Turns 7 Days Data ➔ Trending Narratives)
                                                         │
                                                         └─► 7. tools/db.py (save_trending_narratives)
                                                                (Saves Trends ➔ SQLite)
                                                                 │
                                                                 ▼
[ ANALYTICS UI ] ◄───────(HTTP)────────── app.py (API Endpoints)
 (Renders DB data)
```

***

<br>

# Getting Started

## Create Project Virtual Environment

### 1. Build Virtual Environment:
**Windows:**
```sh
python -m venv .venv
```
**Ubuntu/Python3:**
```sh
python3 -m venv .venv
```
**Note:** On ubuntu you might need to first run and install venv:
```sh
sudo apt install python3-venv
```

<br>

### 2. Source Virtual Environment:
**Windows:**
```sh
.venv\Scripts\activate
```
**Ubuntu:**
```sh
source .venv/bin/activate
```
**Note:** Make sure your virtual environment is activated (you will see (`venv`) in your terminal prompt) before proceeding.

<br>

### 3. Update Execution Policy
This allows the virtual environment scripts to run in PowerShell.

**Windows:**
```sh
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Ubuntu:**

_Automatically handled by sourcing active script in previous step._

If given '`Permission denied`' error, use:
```sh
chmod +x <filename> 
```

<br>

### 4. Install Requirements
If the ['requirements.txt'](requirements.txt) file is **missing** or **is not populated**, please follow the steps in ['Install the Package'](#install-the-package).
Else, all necessary packages can be installed following the instructions below.

**Windows/Ubuntu:**
```sh
pip install -r requirements.txt
```

<br>

### Install the Package
**ONLY IF** the ['requirements.txt'](requirements.txt) is **missing** or **empty**:

#### Create new `requirements.txt` file

**Windows:**
```sh
type nul > requirements.txt
```

**Ubuntu:**
```sh
touch requirements.txt
```

#### Install required packages

**Windows/Ubuntu:**
```sh
pip install fastapi uvicorn pydantic pydantic-ai google-genai python-dotenv pyyaml requests google-api-python-client duckduckgo-search pandas matplotlib seaborn
```

#### Update Requirements Document with new Packages
After installing, save your exact environment setup to a file so that packages can be easily reinstalled on future builds.

**Windows/Ubuntu:**
```sh
pip freeze > requirements.txt
```

<br>

### 5. Environment Variables
Project requires sensitive API keys and local configurations. To maintain security, these files are auto-generated during Web UI setup and intentionally excluded from GitHub via `.gitignore`.

**Excluded Files:**
* `.env`: Stores raw API keys. Keeps credentials out of public repositories.
* `config/auth.json`: Stores local admin hashed password.
* `config/settings.json`: Backs up browser-specific UI preferences.

**Required API Keys:**
Before running the system, generate these free keys:
1. **Gemini API Key:** Acquire from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. **NewsAPI Key:** Acquire from [NewsAPI.org](https://newsapi.org/register).

<br>

### 6. Running the Server
Backend uses FastAPI to serve the HTML frontend and handle API logic. 

Ensure virtual environment is active, then start server.

**Windows/Ubuntu:**  
As script:
```sh
python server/app.py
```
As module:
```sh
python -m server.app
```

Server runs on local loopback. Open web browser and navigate to:  

&ensp; [http://127.0.0.1:8000](http://127.0.0.1:8000)

This is the frontend interface for the entire program.  

***

<br>
<br>

# Operating Web Interface

This is the frontend interface for the entire program. It allows for comprehensive system **management** and **monitoring** through a web-based dashboard.

<br>

## Initial System Setup
On first launch, Global Gatekeeper forcefully redirects to Setup Wizard. Wizard configures `.env`, `params.yaml`, and `auth.json` files automatically.

### Step 1: API Integration
* Input Gemini and NewsAPI keys generated in Getting Started.
* System builds `.env` file. 
* Keys are masked (`***`) on future visits to prevent screen-reading leaks.

### Step 2: Agent Intelligence
* Select Primary model (e.g., `gemini-3-flash-preview`).
* Define Fallback models for rate-limit protection. 
* Custom models can be typed and added dynamically.
* System updates `config/params.yaml`.

### Step 3: Local Security
* Create local Admin Username and Password.
* Password must be min 8 chars, no shell metacharacters (`&`, `|`, `;`, `$`).
* Secures dashboard. Generates 24-hour session cookie and `config/auth.json` hash.

Once complete, dashboard unlocks. Future visits require Admin login unless 24-hour cookie remains active. Settings sync cross-checks `params.yaml` against browser cache to prevent desyncs.

<br>

## Expanding the Frontend
The frontend architecture relies on a strict Client-Side Gatekeeper (`BootManager` in `api.js`) to enforce authentication, session state, and routing rules across the application. 

If you are creating new views for the dashboard (e.g., `export.html` or `graphs.html`), you **must** build upon the following HTML skeleton.  
Including `api.js` and `auth.js` at the bottom of the `<body>` tag is mandatory. If these scripts are omitted, the page will bypass the system's security checks and fail to redirect unauthenticated or unconfigured users back to the setup wizard.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Waymo Agent | [Page_Title]</title>
    <link rel="stylesheet" href="css/theme.css">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>

    <script src="js/api.js"></script>
    <script src="js/auth.js"></script>
</body>
</html>
```

<br>

***