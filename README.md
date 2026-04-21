# The Waymo Perception Agent Project (Gemini AI)

## Directory Structure:

```
waymo_perception_agent/
│
├── core/
│   ├── __init__.py
│   ├── schema.py         # Pydantic models (Metrics definitions)
│   ├── agent.py          # PydanticAI agent initialization
│   └── graph.py          # LangGraph workflow orchestration
│
├── tools/
│   ├── __init__.py
│   ├── scraper.py        # Logic for Reddit/News API pulling
│   └── database.py       # Logic for saving JSON/Metrics to your DB
│
├── visualization/
│   ├── __init__.py
│   └── dashboard.py      # Logic for generating your daily & trend graphs
│
├── .env                  # Your API keys (Gemini, News, Reddit)
├── main.py               # The entry point to run the daily job
└── requirements.txt      # Dependencies (langgraph, pydantic-ai, google-genai, etc.)
```

---

<br>

## Creating Project Virtual Environment

### Build Virtual Environment:
Windows:
```sh
python -m venv venv
```
Ubuntu/Python3:
```sh
python3 -m venv venv
```
**Note:** On ubuntu you might need to first run and install venv:
```sh
sudo apt install python3-venv
```

<br>

### Source Virtual Environment:
Windows:
```sh
venv\Scripts\activate
```
Ubuntu:
```sh
source venv/bin/activate
```

<br>

### Install Project Libraries

#### Update Execution Policy
This allows the virtual environment scripts to run in PowerShell.

Windows:
```sh
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Ubuntu:

_Automatically handled by sourcing active script in previous step._

If given '`Permission denied`' error, use:
```sh
chmod +x <filename> 
```

#### Install the Package
**_Example installation of PydanticAI, LangGraph, Google GenAI & :_**

Windows:
```sh
pip install pydantic pydantic-ai langgraph google-genai python-dotenv
```

Ubuntu:
```sh
pip install pydantic pydantic-ai langgraph google-genai python-dotenv
```
**Note:** Make sure your virtual environment is activated (you will see (`venv`) in your terminal prompt) before running the installation command.

#### Update Requirements Document with new Packages
After installing, save your exact environment setup to a file so it can be easily replicated across different machines.

Windows/Ubuntu:
```sh
pip freeze > requirements.txt
```

---