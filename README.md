# The Waymo Perception Agent Project (Gemini AI)

A Python-based AI agent utilizing PydanticAI, LangGraph, and Gemini 1.5 Pro API to scrape media sites and generate structured temporal metrics on autonomous vehicle perception.

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
    - [5. Environment Variables](#5-environment-variables)

<br>

## Directory Structure:

```
waymo_perception_agent/
│
├── core/
│   ├── __init__.py
│   ├── schema.py         # Pydantic models (Metrics definitions)
│   ├── agent.py          # PydanticAI agent initialization
│   ├── graph.py          # LangGraph workflow orchestration
│   └── utils.py          # Helper functions
│
├── tools/
│   ├── __init__.py
│   ├── scraper.py        # Logic for Reddit/News API pulling
│   └── db.py             # Logic for saving JSON/Metrics to your DB
│
├── visualization/
│   ├── __init__.py
│   └── dash.py           # Logic for generating daily & trend graphs
│
├── .env                  # API keys (Gemini, News, Reddit)
├── main.py               # Entry point to run the daily job
├── index.html            # Frontend web view for the visualization dashboard
├── requirements.txt      # Dependencies (langgraph, pydantic-ai, google-genai, etc.)
│
├── LICENSE               # Apache 2.0 open-source license
└── .gitignore            # Excludes sensitive files (.env) and virtual environments (venv/)
```

***

<br>

# Getting Started

## Create Project Virtual Environment

### 1. Build Virtual Environment:
**Windows:**
```sh
python -m venv venv
```
**Ubuntu/Python3:**
```sh
python3 -m venv venv
```
**Note:** On ubuntu you might need to first run and install venv:
```sh
sudo apt install python3-venv
```

<br>

### 2. Source Virtual Environment:
**Windows:**
```sh
venv\Scripts\activate
```
**Ubuntu:**
```sh
source venv/bin/activate
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
pip install pydantic pydantic-ai langgraph google-genai python-dotenv
```

#### Update Requirements Document with new Packages
After installing, save your exact environment setup to a file so that packages can be easily reinstalled on future builds.

**Windows/Ubuntu:**
```sh
pip freeze > requirements.txt
```

<br>

### 5. Environment Variables
Because API keys are sensitive, the `.env` file is intentionally excluded from version control via `.gitignore`. You must create this file manually.

#### Create `.env` file in root directory:
**Windows:**
```sh
type nul > .env
```

**Ubuntu:**
```sh
touch .env
```

#### Add API keys to `.env`, using the following format:
```text
GEMINI_API_KEY="your_google_aistudio_key_here"
NEWS_API_KEY="your_newsapi_org_key_here"
```



***