"""
File: app.py
Title: FastAPI Backend Server
Description: Serves the frontend HTML/JS/CSS, handles local authentication, and provides REST API endpoints for configuration management.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.2
"""

import os
import yaml
import json
import hashlib
import re
import sqlite3
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Initialize the server with strict typing
app : FastAPI = FastAPI(title="Waymo Perception Agent API")

# Define absolute paths to prevent directory traversal issues
BASE_DIR : str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR : str = os.path.join(BASE_DIR, "frontend")
PARAMS_PATH : str = os.path.join(BASE_DIR, "config", "params.yaml")
ENV_PATH : str = os.path.join(BASE_DIR, ".env")
PREFS_JSON_PATH : str = os.path.join(BASE_DIR, "config", "settings.json")
AUTH_PATH : str = os.path.join(BASE_DIR, "config", "auth.json")

# ---------------------------------------------------------
# Pydantic Schemas for API Payloads
# ---------------------------------------------------------

class EnvSetup(BaseModel):
    """
    Pydantic schema for validating the incoming .env file setup request.
    """
    gemini_key : str
    news_key : str

class YamlUpdate(BaseModel):
    """
    Pydantic schema for validating the incoming params.yaml update request.
    """
    scraper : dict[str, Any]
    agent : dict[str, Any]

class UserPreferences(BaseModel):
    """
    Pydantic schema for validating the incoming JSON preferences backup request.
    """
    timestamp : int
    config : dict[str, Any]

class UserAccount(BaseModel):
    """
    Pydantic schema for secure user registration and login requests.
    """
    username : str
    password : str

# ---------------------------------------------------------
# Authentication & Setup Endpoints
# ---------------------------------------------------------

@app.get("/api/status")
async def get_system_status() -> dict[str, Any]:
    """
    Checks the granular status of the system to drive the frontend Setup Wizard routing.
    Parses the .env file to dynamically generate masked API keys.

    Returns:
        dict[str, Any]: A highly detailed dictionary containing boolean flags for missing 
                        components, masked string values, and the current YAML config.
    """
    env_exists : bool = os.path.exists(ENV_PATH)
    auth_exists : bool = os.path.exists(AUTH_PATH)
    
    missing_env : bool = True
    missing_auth : bool = not auth_exists
    missing_config : bool = True
    
    masked_gemini : str | None = None
    masked_news : str | None = None
    config_data : dict[str, Any] | None = None
    
    # 1. Parse .env and mask keys
    if env_exists:
        with open(ENV_PATH, "r") as f:
            content : str = f.read()
            
            g_match = re.search(r'GEMINI_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
            n_match = re.search(r'NEWS_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
            
            if g_match and n_match:
                g_key : str = g_match.group(1).strip()
                n_key : str = n_match.group(1).strip()
                
                if g_key and n_key:
                    missing_env = False
                    masked_gemini = "*" * 12 + g_key[-4:] if len(g_key) > 4 else "***"
                    masked_news = "*" * 12 + n_key[-4:] if len(n_key) > 4 else "***"

    # 2. Parse params.yaml
    if os.path.exists(PARAMS_PATH):
        try:
            with open(PARAMS_PATH, "r") as f:
                config_data = yaml.safe_load(f)
                if config_data and "agent" in config_data:
                    missing_config = False
        except Exception:
            pass

    # 3. Determine overall setup state
    needs_setup : bool = missing_env or missing_config or missing_auth

    return {
        "needs_setup": needs_setup,
        "missing_env": missing_env,
        "missing_config": missing_config,
        "missing_auth": missing_auth,
        "masked_gemini": masked_gemini,
        "masked_news": masked_news,
        "config": config_data
    }

@app.post("/api/setup")
async def setup_env_file(keys : EnvSetup) -> dict[str, str]:
    """
    Creates or overwrites the local .env file with the provided API keys.
    If the frontend sends an empty string (or the masked string), it skips writing 
    that specific key to prevent overwriting valid keys with asterisks.

    Args:
        keys (EnvSetup): A structured payload containing the Gemini and News API keys.

    Raises:
        HTTPException: If the server encounters a file system error while writing the .env file.

    Returns:
        dict[str, str]: A status dictionary confirming successful generation.
    """
    try:
        # Read existing keys to prevent overwriting with blanks/masks
        existing_g_key = ""
        existing_n_key = ""
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r") as f:
                content = f.read()
                g_match = re.search(r'GEMINI_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
                n_match = re.search(r'NEWS_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
                if g_match: existing_g_key = g_match.group(1)
                if n_match: existing_n_key = n_match.group(1)

        # Only update if the frontend provided a real, unmasked string
        final_g_key = keys.gemini_key if (keys.gemini_key and "*" not in keys.gemini_key) else existing_g_key
        final_n_key = keys.news_key if (keys.news_key and "*" not in keys.news_key) else existing_n_key

        with open(ENV_PATH, "w") as f:
            f.write(f'GEMINI_API_KEY="{final_g_key}"\n')
            f.write(f'NEWS_API_KEY="{final_n_key}"\n')
            
        return {"status": "success", "message": ".env generated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {str(e)}")

@app.post("/api/register")
async def register_user(user : UserAccount) -> dict[str, str]:
    """
    Hashes the provided password and saves the local admin account credentials to auth.json.

    Args:
        user (UserAccount): The plaintext username and password submitted during the setup wizard.

    Raises:
        HTTPException: If the server fails to create the config directory or write to auth.json.

    Returns:
        dict[str, str]: A status dictionary confirming successful registration.
    """
    hashed_pw : str = hashlib.sha256(user.password.encode()).hexdigest()
    try:
        os.makedirs(os.path.dirname(AUTH_PATH), exist_ok=True)
        with open(AUTH_PATH, "w") as f:
            json.dump({"username": user.username, "password": hashed_pw}, f)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/login")
async def login_api(user : UserAccount) -> dict[str, bool]:
    """
    Verifies incoming login credentials against the stored SHA-256 hash in auth.json.

    Args:
        user (UserAccount): The login attempt containing a username and plaintext password.

    Raises:
        HTTPException: If the auth.json file does not exist (status 404).

    Returns:
        dict[str, bool]: A dictionary containing an 'authenticated' boolean flag indicating success or failure.
    """
    if not os.path.exists(AUTH_PATH):
        raise HTTPException(status_code=404, detail="No account configured.")
        
    with open(AUTH_PATH, "r") as f:
        stored : dict[str, str] = json.load(f)
    
    attempt : str = hashlib.sha256(user.password.encode()).hexdigest()
    is_valid : bool = (user.username == stored["username"] and attempt == stored["password"])
    
    return {"authenticated": is_valid}

# ---------------------------------------------------------
# Configuration Endpoints
# ---------------------------------------------------------

@app.get("/api/config")
async def get_yaml_config() -> dict[str, Any]:
    """
    Reads the params.yaml file and sends it to the frontend settings page.

    Raises:
        HTTPException: If the server fails to read or parse the YAML file.

    Returns:
        dict[str, Any]: A dictionary representation of the core YAML configuration.
    """
    try:
        with open(PARAMS_PATH, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")

@app.post("/api/config")
async def update_yaml_config(new_config : YamlUpdate) -> dict[str, str]:
    """
    Overwrites the params.yaml file with the sanitized data sent from the frontend UI.

    Args:
        new_config (YamlUpdate): The structured payload containing the updated config parameters.

    Raises:
        HTTPException: If the server fails to write the YAML data to the file system.

    Returns:
        dict[str, str]: A status dictionary confirming successful update.
    """
    try:
        with open(PARAMS_PATH, "w") as f:
            yaml.dump(new_config.model_dump(), f, default_flow_style=False, sort_keys=False)
        return {"status": "success", "message": "params.yaml updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")

@app.get("/api/preferences")
async def get_user_preferences() -> dict[str, Any]:
    """
    Retrieves the backup settings.json file used for browser-to-file reconciliation.

    Raises:
        HTTPException: If the server fails to read or parse the JSON file.

    Returns:
        dict[str, Any]: A dictionary representation of user preferences, or a default 
                        empty configuration dictionary if the backup file does not exist.
    """
    if not os.path.exists(PREFS_JSON_PATH):
        return {"timestamp": 0, "config": {}}
    try:
        with open(PREFS_JSON_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read preferences: {str(e)}")

@app.post("/api/preferences")
async def save_user_preferences(prefs : UserPreferences) -> dict[str, str]:
    """
    Saves the user preferences to a persistent settings.json file with a unix timestamp.

    Args:
        prefs (UserPreferences): A structured payload containing the timestamp and config dictionary.

    Raises:
        HTTPException: If the server fails to write the JSON data to the file system.

    Returns:
        dict[str, str]: A status dictionary confirming successful backup.
    """
    try:
        os.makedirs(os.path.dirname(PREFS_JSON_PATH), exist_ok=True)
        with open(PREFS_JSON_PATH, "w") as f:
            json.dump(prefs.model_dump(), f, indent=4)
        return {"status": "success", "message": "settings.json updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")

# ---------------------------------------------------------
# Static File Mounting & Routing
# ---------------------------------------------------------

@app.get("/")
async def serve_index() -> FileResponse:
    """
    Serves the root dashboard page.

    Returns:
        FileResponse: The index.html file located in the frontend directory.
    """
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{page_name}.html")
async def serve_pages(page_name : str) -> FileResponse:
    """
    Dynamically routes and serves specific HTML pages from the frontend directory, 
    falling back to the custom 404 page if the file is missing.

    Args:
        page_name (str): The specific HTML file requested by the browser.

    Returns:
        FileResponse: The requested HTML file, or the 404.html fallback with a 404 status code.
    """
    file_path : str = os.path.join(FRONTEND_DIR, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "404.html"), status_code=404)

@app.exception_handler(404)
async def custom_404_handler(request: Any, __: Any) -> FileResponse:
    """
    Intercepts standard FastAPI 404 errors and serves the custom HTML error page.

    Args:
        request (Any): The incoming request object that triggered the 404.
        __ (Any): The exception object (unused).

    Returns:
        FileResponse: The custom 404.html file with a 404 status code.
    """
    return FileResponse(os.path.join(FRONTEND_DIR, "404.html"), status_code=404)


@app.get("/api/dashboard/summary")
async def get_dashboard_summary() -> dict[str, int]:
    """
    Queries the SQLite database to fetch the all-time totals for the dashboard.
    """
    db_path : str = os.path.join(BASE_DIR, "data", "waymo_metrics.db")
    
    # return zeros, if daatabase doesnt exists
    if not os.path.exists(db_path):
        return {"total_runs": 0, "total_sources": 0}
        
    try:
        # create connection to database
        conn : sqlite3.Connection   = sqlite3.connect(db_path)
        cursor : sqlite3.Cursor     = conn.cursor()
        
        # sum counts from daily overview table
        cursor.execute("SELECT SUM(run_count), SUM(source_total) FROM daily_overview")
        row = cursor.fetchone()
        conn.close()
        
        return {
            "total_runs": row[0] if row[0] else 0,
            "total_sources": row[1] if row[1] else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database read error: {str(e)}")

# mount frontend directory to serve CSS and JS assets
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # run server (local loopback address)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)